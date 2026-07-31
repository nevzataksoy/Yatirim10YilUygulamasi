from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.backtest.validation import (
    calibrate_edge_thresholds,
    classify_shadow_readiness,
    replay_ethbtc_core,
    summarize_core_replay,
)
from app.collectors.alpha_vantage import AlphaVantageCollector
from app.collectors.crypto import CryptoCollector
from app.collectors.derivatives import DerivativesCollector
from app.collectors.fred import FredCollector
from app.collectors.globalx_ura import GlobalXUraHoldingsCollector
from app.collectors.sec import SecCollector
from app.collectors.tcmb import TcmbCollector
from app.database.db import DatabaseService
from app.database.repository import Repository
from app.engines.decision import DecisionEngine
from app.engines.factors import neutral, score_derivatives, score_flow, score_macro, score_momentum, score_trend, score_value, score_volatility
from app.engines.regime import detect_regime
from app.engines.signal_state import apply_signal_state
from app.engines.ura import sec_monitor_quality_from_weight, score_event_monitor, score_ura_breadth, score_ura_holdings_fundamentals
from app.features.builders import crypto_features, ura_features
from app.models import AppSettings, Decision
from app.notifications.telegram import TelegramNotifier
from app.realtime.coinbase_orderbook import BookMetrics, CoinbaseOrderBookWorker
from app.spool import SpoolQueue
from app.version import MODEL_VERSION

LOG=logging.getLogger(__name__)


class InvestmentEngine:
    def __init__(self, settings: AppSettings, project_root: Path) -> None:
        self.settings=settings; self.project_root=project_root
        self.db=DatabaseService(settings); self.repo=Repository(self.db); self.spool=SpoolQueue()
        self.crypto=CryptoCollector(); self.alpha=AlphaVantageCollector(settings.alpha_vantage_api_key)
        self.derivatives=DerivativesCollector(); self.fred=FredCollector(settings.fred_api_key); self.sec=SecCollector(settings.sec_user_agent); self.tcmb=TcmbCollector()
        self.globalx=GlobalXUraHoldingsCollector()
        self.telegram=TelegramNotifier(settings.telegram_bot_token,settings.telegram_chat_id)
        self.decision_engine=DecisionEngine(settings,project_root/"config"/"defaults.json")
        self.fred_series=json.loads((project_root/"config"/"defaults.json").read_text(encoding="utf-8"))["fred_series"]
        self._execution_threads: list[threading.Thread]=[]

    def start(self) -> None:
        self.db.open(); self.repo.publish_health("ENGINE","OK","Engine başlatıldı",{"mode":self.settings.engine_mode})

    def stop(self) -> None:
        self.repo.publish_health("ENGINE","STOPPED","Engine durduruldu"); self.db.close()

    def hourly_job(self) -> None:
        started=datetime.now(timezone.utc)
        try:
            pair=self.derivatives.fetch_pair(self.settings.derivatives_provider)
            # Persist only after BTC and ETH have both succeeded on the same venue.
            self.repo.insert_derivative_snapshot(pair.btc)
            self.repo.insert_derivative_snapshot(pair.eth)
            details={
                "provider": pair.provider,
                "fallback_used": pair.fallback_used,
                "provider_errors": pair.errors,
                "underlyings": ["BTC", "ETH"],
            }
            message=f"{pair.provider.upper()} BTC/ETH snapshot güncel"
            if pair.fallback_used:
                message += " (fallback)"
            self.repo.publish_health("DERIVATIVES","OK",message,details)
            self.repo.log_job("hourly_job","OK",started,details=details)
        except Exception as exc:
            LOG.exception("hourly_job derivatives failed")
            message=str(exc)[:500]
            self.repo.publish_health("DERIVATIVES","ERROR",message,{"provider_mode":self.settings.derivatives_provider})
            self.repo.log_job("hourly_job","ERROR",started,message,{"provider_mode":self.settings.derivatives_provider})
            if self.settings.engine_mode=="live":
                try:
                    self.telegram.send(f"⚠️ DERIVATIVES hatası: {message[:350]}")
                except Exception:
                    pass
        finally:
            try:
                self.flush_spool()
            except Exception as exc:
                LOG.warning("spool flush failed: %s", exc, exc_info=True)

    def macro_job(self) -> None:
        started=datetime.now(timezone.utc)
        try:
            for series_id in self.fred_series:
                self.repo.upsert_macro(self.fred.fetch_series(series_id))
            latest=self.repo.get_latest_macro_observations(self.fred_series)
            factor=score_macro(latest, datetime.now(timezone.utc).date())
            details={
                "quality": factor.quality,
                "observation_dates": factor.details.get("observation_dates", {}),
                "stale_or_missing": factor.details.get("stale_or_missing", []),
                "degraded": factor.details.get("degraded", []),
            }
            if factor.quality >= 90:
                status="OK"; message=f"FRED serileri güncel (quality {factor.quality:.1f})"
            elif factor.quality >= 60:
                status="DEGRADED"; message=f"FRED freshness düşük (quality {factor.quality:.1f})"
            else:
                status="ERROR"; message=f"FRED verisi karar için yetersiz/stale (quality {factor.quality:.1f})"
            self.repo.publish_health("MACRO",status,message,details)
            self.repo.log_job("macro_job",status,started,message,details)
        except Exception as exc:
            LOG.exception("macro_job failed"); self._health_fail("MACRO",exc); self._job_fail("macro_job",started,exc)

    def _ensure_derivatives_fresh(self) -> dict:
        """Best-effort preflight so a missed hourly run does not silently stale crypto inputs.

        The decision engine remains fail-safe: if refresh also fails, derivatives
        stay quality=0 and the normal data-quality gate can block an action.
        """
        btc, eth, venue = self.repo.get_latest_derivative_pair(max_age_hours=3)
        if btc and eth and venue:
            return {"refresh_attempted": False, "available": True, "provider": venue}
        self.hourly_job()
        btc, eth, venue = self.repo.get_latest_derivative_pair(max_age_hours=3)
        return {"refresh_attempted": True, "available": bool(btc and eth and venue), "provider": venue}

    def daily_crypto_job(self) -> Decision | None:
        started=datetime.now(timezone.utc)
        if self.settings.engine_mode=="maintenance": return None
        try:
            bundle=self.crypto.fetch(1300); self.repo.upsert_price_bars(bundle.btc); self.repo.upsert_price_bars(bundle.eth)
            btc_last=bundle.btc[-1]; eth_last=bundle.eth[-1]
            if btc_last.date != eth_last.date:
                raise RuntimeError(f"BTC/ETH son kapanış tarihleri farklı: {btc_last.date} / {eth_last.date}")
            self.repo.publish_market_snapshot("BTC/USD",btc_last.close,"USD",bundle.provider,btc_last.date)
            self.repo.publish_market_snapshot("ETH/USD",eth_last.close,"USD",bundle.provider,eth_last.date)
            self.repo.publish_market_snapshot("ETH/BTC",eth_last.close/btc_last.close,"RATIO",bundle.provider,btc_last.date)
            f=crypto_features(bundle.btc,bundle.eth); as_of=str(f["as_of"]["value"]); self.repo.upsert_features("ETH/BTC",as_of,f)
            macro=self.repo.get_latest_macro_observations(self.fred_series, as_of); macro_factor=score_macro(macro, as_of)
            regime,probs,regime_details=detect_regime(f,macro_factor.score); self.repo.insert_regime("ETH/BTC",as_of,regime,probs,regime_details)
            derivatives_preflight=self._ensure_derivatives_fresh()
            factors={
                "value":score_value(f),"trend":score_trend(f),"momentum":score_momentum(f),"volatility":score_volatility(f),
                "derivatives":self._derivatives_factor(),
                "flow":score_flow(f),"macro":macro_factor,"event":neutral("event",0,"Crypto event/sentiment provider bağlı değil; eksik veri nötr oy sayılmaz."),
            }
            veto,_events=self.repo.recent_event_veto("ETH",48)
            decision,weights=self.decision_engine.build("ETH/BTC",as_of,regime,f,factors,event_veto=veto)
            decision.rationale.update(self._provenance("ETH/BTC",as_of,bundle.provider,factors))
            self.repo.insert_factor_scores("ETH/BTC",as_of,regime,factors,weights); self._persist_decision(decision,bundle.provider)
            crypto_details={"provider":bundle.provider,"derivatives_preflight":derivatives_preflight,"data_quality":decision.data_quality,"status":decision.status}
            self.repo.publish_health("CRYPTO","OK",f"{bundle.provider} {as_of}",crypto_details); self.repo.log_job("daily_crypto_job","OK",started,details=crypto_details)
            return decision
        except Exception as exc:
            LOG.exception("daily_crypto_job failed"); self._health_fail("CRYPTO",exc); self._job_fail("daily_crypto_job",started,exc); return None

    def daily_ura_job(self) -> Decision | None:
        started=datetime.now(timezone.utc)
        if self.settings.engine_mode=="maintenance": return None
        try:
            daily=self.alpha.fetch_daily("URA"); weekly=self.alpha.fetch_weekly("URA"); monthly=self.alpha.fetch_monthly("URA")
            self.repo.upsert_price_bars(daily,"etf")
            ura_last=daily[-1]
            self.repo.publish_market_snapshot("URA/USD",ura_last.close,"USD","alpha_vantage",ura_last.date)
            f=ura_features(daily,weekly,monthly); as_of=str(f["as_of"]["value"]); self.repo.upsert_features("URA/USD",as_of,f)

            # Official Global X holdings are best-effort: price/technical collection
            # must remain usable if the issuer site is temporarily unavailable.
            try:
                holdings=self.globalx.fetch(self.settings.ura_holdings_csv_url)
                self.repo.upsert_ura_holdings(holdings)
                breadth_row=self.repo.calculate_and_upsert_ura_breadth(as_of)
                self.repo.publish_health("URA_HOLDINGS","OK",f"Global X holdings {holdings.holding_date}",{
                    "holding_date":holdings.holding_date,"constituents":len(holdings.holdings),"source_url":holdings.source_url,
                    "breadth_quality":float((breadth_row or {}).get("quality") or 0),
                })
            except Exception as holdings_exc:
                LOG.warning("URA holdings refresh failed: %s", holdings_exc, exc_info=True)
                self.repo.publish_health("URA_HOLDINGS","DEGRADED",str(holdings_exc)[:500],{"quality":0})

            macro_factor=score_macro(self.repo.get_latest_macro_observations(self.fred_series, as_of), as_of); regime,probs,details=detect_regime(f,macro_factor.score); self.repo.insert_regime("URA/USD",as_of,regime,probs,details)
            holdings_summary=self.repo.get_ura_holdings_summary(as_of,ura_last.close)
            breadth=self.repo.get_latest_ura_breadth(as_of)
            event_health=self.repo.get_health("SEC_EVENTS",max_age_hours=30)
            if not event_health:
                self.sec_event_job()
                event_health=self.repo.get_health("SEC_EVENTS",max_age_hours=30)
            recent_events=self.repo.recent_events("URA",168)
            factors={
                "value":score_value(f),"trend":score_trend(f),"momentum":score_momentum(f),"volatility":score_volatility(f),"macro":macro_factor,
                "fundamentals":score_ura_holdings_fundamentals(holdings_summary),
                "breadth":score_ura_breadth(breadth,as_of),
                "event":score_event_monitor(event_health,recent_events),
            }
            veto,_events=self.repo.recent_event_veto("URA",72)
            decision,weights=self.decision_engine.build("URA/USD",as_of,regime,f,factors,event_veto=veto)
            decision.rationale.update(self._provenance("URA/USD",as_of,"alpha_vantage",factors))
            self.repo.insert_factor_scores("URA/USD",as_of,regime,factors,weights); self._persist_decision(decision,"alpha_vantage")
            self.repo.publish_health("URA","OK",as_of,{"data_quality":decision.data_quality,"status":decision.status}); self.repo.log_job("daily_ura_job","OK",started,details={"data_quality":decision.data_quality,"status":decision.status}); return decision
        except Exception as exc:
            LOG.exception("daily_ura_job failed"); self._health_fail("URA",exc); self._job_fail("daily_ura_job",started,exc); return None

    def _derivatives_factor(self):
        btc,eth,venue=self.repo.get_latest_derivative_pair(max_age_hours=3)
        factor=score_derivatives(btc,eth)
        factor.details.setdefault("provider",venue)
        factor.details["btc_observed_at"] = str(btc.get("observed_at")) if btc else None
        factor.details["eth_observed_at"] = str(eth.get("observed_at")) if eth else None
        return factor

    def _provenance(self, system: str, as_of: str, provider: str, factors: dict) -> dict:
        return {
            "provenance": {
                "system": system,
                "model_version": MODEL_VERSION,
                "engine_mode": self.settings.engine_mode,
                "market_data_date": as_of,
                "decision_evaluated_at": datetime.now(timezone.utc).isoformat(),
                "price_provider": provider,
                "derivatives_provider": factors.get("derivatives").details.get("provider") if factors.get("derivatives") else None,
                "derivatives_observed_at": {
                    "btc": factors.get("derivatives").details.get("btc_observed_at") if factors.get("derivatives") else None,
                    "eth": factors.get("derivatives").details.get("eth_observed_at") if factors.get("derivatives") else None,
                },
                "macro_observation_dates": factors.get("macro").details.get("observation_dates",{}) if factors.get("macro") else {},
            }
        }

    def daily_fx_job(self) -> None:
        started=datetime.now(timezone.utc)
        try:
            fx=self.tcmb.latest_usd_selling()
            self.repo.publish_market_snapshot("USD/TRY",fx["rate"],"TRY", "tcmb", fx["date"], {"source":fx["source"]})
            self.repo.publish_health("FX","OK",f"TCMB USD/TRY {fx['date']}")
            self.repo.log_job("daily_fx_job","OK",started,details={"date":fx["date"],"rate":fx["rate"]})
        except Exception as exc:
            LOG.exception("daily_fx_job failed"); self._health_fail("FX",exc); self._job_fail("daily_fx_job",started,exc)

    def sec_event_job(self) -> None:
        started=datetime.now(timezone.utc)
        try:
            holdings=self.repo.get_latest_holdings_tickers(limit=15)
            if not holdings:
                details={"quality":0,"reason":"URA holdings henüz yok; SEC entity listesi üretilemedi."}
                self.repo.publish_health("SEC_EVENTS","DEGRADED",details["reason"],details)
                self.repo.log_job("sec_event_job","DEGRADED",started,details["reason"],details)
                return
            ticker_map=self.sec.fetch_ticker_map()
            forms={"8-K","10-Q","10-K","6-K","20-F"}
            checked=0; inserted=0; unmatched=[]; matched=[]
            considered_weight=sum(max(0.0,float(h.get("weight") or 0)) for h in holdings)
            matched_weight=0.0
            for holding in holdings:
                ticker=str(holding.get("ticker") or "").upper().strip()
                # Global X uses exchange suffixes such as 'CCO CN'. Only exact
                # SEC-listed tickers are auto-resolved; uncertain cross-listing
                # aliases are never guessed.
                if " " in ticker or ticker not in ticker_map:
                    unmatched.append(ticker)
                    continue
                entity=ticker_map[ticker]; checked+=1; matched.append(ticker); matched_weight+=max(0.0,float(holding.get("weight") or 0))
                for filing in self.sec.fetch_recent_filings(entity["cik"],forms):
                    if not self.sec.is_recent(filing,days=14):
                        continue
                    self.repo.insert_event(
                        "SEC",entity["title"] or ticker,"URA",filing["form"],
                        filing["occurred_at"],f"{ticker} {filing['form']} filing",filing["url"],
                        severity=0,surprise=0,credibility=100,raw={**filing,"ticker":ticker},
                    )
                    inserted+=1
                time.sleep(0.15)
            quality=sec_monitor_quality_from_weight(matched_weight) if checked else 0.0
            status="OK" if quality>=50 else ("DEGRADED" if checked else "DEGRADED")
            details={
                "quality":quality,
                "entities_checked":checked,
                "filings_seen":inserted,
                "matched_tickers":matched[:20],
                "unmatched_tickers":unmatched[:20],
                "matched_fund_weight":round(matched_weight,6),
                "considered_top_n_weight":round(considered_weight,6),
                "scope_cap":70,
            }
            message=f"SEC filings kontrol edildi: {checked} entity, {inserted} recent filing, fund weight coverage {matched_weight*100:.1f}%"
            self.repo.publish_health("SEC_EVENTS",status,message,details)
            self.repo.log_job("sec_event_job",status,started,message,details)
        except Exception as exc:
            LOG.exception("sec_event_job failed"); self._health_fail("SEC_EVENTS",exc); self._job_fail("sec_event_job",started,exc)

    def weekly_job(self) -> None:
        started=datetime.now(timezone.utc)
        try:
            # Weekly maintenance is real work: macro freshness, official URA
            # holdings/breadth and SEC filing monitoring are refreshed.
            self.macro_job()
            holdings=self.globalx.fetch(self.settings.ura_holdings_csv_url)
            self.repo.upsert_ura_holdings(holdings)
            breadth=self.repo.calculate_and_upsert_ura_breadth(holdings.holding_date)
            self.sec_event_job()
            details={
                "holdings_date":holdings.holding_date,
                "holdings_count":len(holdings.holdings),
                "breadth_quality":float((breadth or {}).get("quality") or 0),
            }
            self.repo.publish_health("WEEKLY","OK","Haftalık veri bakımı tamamlandı",details)
            self.repo.log_job("weekly_job","OK",started,details=details)
        except Exception as exc:
            LOG.exception("weekly_job failed"); self._health_fail("WEEKLY",exc); self._job_fail("weekly_job",started,exc)

    def monthly_audit_job(self) -> None:
        started=datetime.now(timezone.utc)
        try:
            performance=self.repo.evaluate_mature_decisions((5,20,60))
            validation=self.model_validation_job(log_job=False)
            details={
                **performance,
                "validation":validation,
                "weights_changed":False,
                "note":"Performance ve validation ölçülür; factor ağırlıkları/thresholdlar otomatik değiştirilmez.",
            }
            self.repo.publish_health("MODEL_AUDIT","OK","Karar performansı ve model validation değerlendirildi; parametreler değiştirilmedi.",details)
            self.repo.log_job("monthly_audit_job","OK",started,details=details)
        except Exception as exc:
            LOG.exception("monthly_audit_job failed"); self._health_fail("MODEL_AUDIT",exc); self._job_fail("monthly_audit_job",started,exc)


    def backfill_crypto_history(self, days: int = 2500) -> dict:
        if days < 1300 or days > 4000:
            raise ValueError("Crypto history backfill 1300-4000 gün aralığında olmalıdır.")
        started=datetime.now(timezone.utc)
        try:
            bundle=self.crypto.fetch(days)
            common=len({x.date for x in bundle.btc} & {x.date for x in bundle.eth})
            minimum=int(days*0.85)
            if common < minimum:
                raise RuntimeError(f"Backfill ortak history yetersiz: {common} < {minimum}")
            self.repo.upsert_price_bars(bundle.btc)
            self.repo.upsert_price_bars(bundle.eth)
            details={
                "provider":bundle.provider,
                "requested_days":days,
                "btc_rows":len(bundle.btc),
                "eth_rows":len(bundle.eth),
                "common_days":common,
                "fallback_reason":bundle.fallback_reason,
            }
            self.repo.publish_health("CRYPTO_HISTORY","OK",f"Crypto history backfill tamamlandı: {common} ortak gün",details)
            self.repo.log_job("crypto_history_backfill","OK",started,details=details)
            return details
        except Exception as exc:
            LOG.exception("crypto history backfill failed")
            self._health_fail("CRYPTO_HISTORY",exc)
            self._job_fail("crypto_history_backfill",started,exc)
            raise

    def model_validation_job(self, *, log_job: bool = True) -> dict:
        """Run leakage-resistant core replay and Shadow readiness assessment.

        Historical replay deliberately excludes factors whose trustworthy
        point-in-time histories do not yet exist. It never changes production
        settings, weights or thresholds.
        """
        started=datetime.now(timezone.utc)
        try:
            btc=self.repo.get_price_bars("BTC-USD")
            eth=self.repo.get_price_bars("ETH-USD")
            macro_history=self.repo.get_macro_history(self.fred_series)
            points=replay_ethbtc_core(
                btc,eth,macro_history,self.settings,self.decision_engine,
            )
            core=summarize_core_replay(points,self.settings.min_action_edge)
            calibration=calibrate_edge_thresholds(points)
            core_status=str(core.get("status") or "UNKNOWN")
            core_details={
                "core_replay":core,
                "calibration":calibration,
                "model_version":MODEL_VERSION,
                "scope":"ETH/BTC directional core: value/trend/momentum/flow/macro; derivatives/event excluded historically.",
            }
            configured_h20=(core.get("configured_threshold_metrics") or {}).get("20") or {}
            self.repo.insert_validation_run(
                validation_type="PIT_CORE_REPLAY",system="ETH/BTC",status=core_status,
                started_at=started,start_date=core.get("start_date"),end_date=core.get("end_date"),
                observations=int(core.get("observations") or 0),
                signals=int(configured_h20.get("signals") or 0),
                metrics=core_details,details={"auto_apply":False},
            )
            self.repo.publish_validation_snapshot(
                validation_type="PIT_CORE_REPLAY",system="ETH/BTC",status=core_status,
                start_date=core.get("start_date"),end_date=core.get("end_date"),
                metrics=core_details,details={"auto_apply":False},
            )

            shadow_stats=self.repo.shadow_readiness_stats()
            shadow=classify_shadow_readiness(shadow_stats)
            shadow_status=str(shadow["status"])
            self.repo.insert_validation_run(
                validation_type="SHADOW_READINESS",system="ALL",status=shadow_status,
                started_at=started,start_date=None,end_date=None,
                observations=None,signals=None,metrics=shadow,details={"engine_mode":self.settings.engine_mode},
            )
            self.repo.publish_validation_snapshot(
                validation_type="SHADOW_READINESS",system="ALL",status=shadow_status,
                start_date=None,end_date=None,metrics=shadow,details={"engine_mode":self.settings.engine_mode},
            )

            # URA full PIT replay stays explicitly unavailable until constituent
            # breadth/holdings/event history has accumulated point-in-time.
            ura_status="NOT_READY"
            ura_details={
                "status":ura_status,
                "reason":"Full URA PIT replay için holdings/breadth/event tarihçesi henüz yeterli değil.",
                "holdings_dates":shadow_stats.get("ura_holdings_dates",0),
                "breadth_dates":shadow_stats.get("ura_breadth_dates",0),
                "model_version":MODEL_VERSION,
            }
            self.repo.insert_validation_run(
                validation_type="PIT_FULL_REPLAY",system="URA/USD",status=ura_status,
                started_at=started,start_date=None,end_date=None,
                observations=0,signals=0,metrics=ura_details,details={"auto_apply":False},
            )
            self.repo.publish_validation_snapshot(
                validation_type="PIT_FULL_REPLAY",system="URA/USD",status=ura_status,
                start_date=None,end_date=None,metrics=ura_details,details={"auto_apply":False},
            )

            overall={
                "model_version":MODEL_VERSION,
                "ethbtc_core":core,
                "calibration":calibration,
                "shadow_readiness":shadow,
                "ura_full_replay":ura_details,
                "weights_changed":False,
                "thresholds_changed":False,
            }
            health_status="OK" if core_status=="OK" else "DEGRADED"
            self.repo.publish_health(
                "MODEL_VALIDATION",health_status,
                f"Validation tamamlandı; Shadow {shadow_status}",overall,
            )
            if log_job:
                self.repo.log_job("model_validation_job",health_status,started,details=overall)
            return overall
        except Exception as exc:
            LOG.exception("model_validation_job failed")
            self._health_fail("MODEL_VALIDATION",exc)
            if log_job:
                self._job_fail("model_validation_job",started,exc)
            raise

    def _persist_decision(self, decision: Decision, provider: str) -> None:
        self._apply_signal_state(decision)
        decision_id=self.repo.insert_decision(decision)
        self.repo.publish_decision_history(decision_id,decision,provider)
        self.repo.publish_decision_snapshot(decision,provider)
        if decision.action_event:
            if self.settings.engine_mode=="live":
                self.telegram.send(self._decision_message(decision,decision_id))
            if decision.execution_required:
                self._start_execution_worker(decision,decision_id)

    def _apply_signal_state(self, decision: Decision) -> None:
        state=apply_signal_state(decision,self.repo.get_signal_state(decision.system),self.settings)
        self.repo.upsert_signal_state(
            decision.system,state["active_direction"],state["stage"],
            state["cumulative_size"],state["last_action_date"],state["reset_counter"],
        )

    def _decision_message(self, d: Decision, decision_id: int) -> str:
        stage=f"Kademe {d.action_stage}" if d.action_stage else "Yeni kademe yok"
        return (f"🟢 Rosa Investment Engine\nDecision #{decision_id}\n{d.system}: {d.direction}\n"
                f"Rejim: {d.regime}\nEdge: {d.edge_score:.1f}/100\nConfidence: {d.confidence:.1f}/100\n"
                f"Data Quality: {d.data_quality:.1f}/100\nRisk: {d.risk_score:.1f}/100\n"
                f"Aksiyon: {stage} — %{d.action_size*100:.1f}\n"
                f"Rejim kümülatif: %{d.regime_cumulative_size*100:.1f}\n"
                f"Late Entry: {'EVET' if d.late_entry else 'HAYIR'}\n"
                "Bu bir karar destek sinyalidir; otomatik emir verilmez.")

    def _start_execution_worker(self, decision: Decision, decision_id: int) -> None:
        t=threading.Thread(target=self._execution_run,args=(decision,decision_id),daemon=True,name=f"execution-{decision_id}"); t.start(); self._execution_threads.append(t)

    def _execution_run(self, decision: Decision, decision_id: int) -> None:
        worker=CoinbaseOrderBookWorker()
        def on_snapshot(m: BookMetrics) -> None:
            try:
                self.repo.insert_execution_snapshot(
                    decision_id=decision_id,observed_at=m.ts,product=m.product,spread_bps=m.spread_bps,
                    bid_depth_usd=m.bid_depth_usd,ask_depth_usd=m.ask_depth_usd,imbalance=m.imbalance,
                    microprice=m.microprice,ofi=m.ofi,trade_imbalance=m.trade_imbalance,
                    trade_notional_usd=m.trade_notional_usd,trade_gap_count=m.trade_gap_count,sample_window_seconds=m.sample_window_seconds,
                    is_test=False,
                )
            except Exception as exc: LOG.warning("execution snapshot DB error: %s",exc)
        try:
            worker.run(self.settings.realtime_execution_minutes*60,on_snapshot=on_snapshot,snapshot_every=60)
            metrics=[worker.metrics("BTC-USD"),worker.metrics("ETH-USD")]
            usable=[m for m in metrics if m]
            if usable and self.settings.engine_mode=="live":
                avg_spread=sum(m.spread_bps for m in usable)/len(usable); avg_imb=sum(m.imbalance for m in usable)/len(usable)
                avg_ofi=sum(m.ofi for m in usable)/len(usable); avg_trade=sum(m.trade_imbalance for m in usable)/len(usable)
                self.telegram.send(f"🔎 Execution gözlemi tamamlandı — Decision #{decision_id}\nOrt. spread: {avg_spread:.2f} bps\nOrt. book imbalance: {avg_imb:+.3f}\nOrt. OFI: {avg_ofi:+.3f}\nOrt. trade imbalance: {avg_trade:+.3f}\nManuel işlem öncesi Dashboard'u kontrol edin.")
        except Exception as exc:
            LOG.exception("execution worker failed"); self._health_fail("EXECUTION",exc)

    def realtime_smoke_test(self, duration_seconds: int = 20) -> dict:
        if duration_seconds < 5 or duration_seconds > 120:
            raise ValueError("Realtime smoke test süresi 5-120 saniye olmalıdır.")
        test_run_id=str(uuid.uuid4())
        worker=CoinbaseOrderBookWorker()
        snapshots=[]
        def on_snapshot(m: BookMetrics) -> None:
            self.repo.insert_execution_snapshot(
                decision_id=None,observed_at=m.ts,product=m.product,spread_bps=m.spread_bps,
                bid_depth_usd=m.bid_depth_usd,ask_depth_usd=m.ask_depth_usd,imbalance=m.imbalance,
                microprice=m.microprice,ofi=m.ofi,trade_imbalance=m.trade_imbalance,
                trade_notional_usd=m.trade_notional_usd,trade_gap_count=m.trade_gap_count,sample_window_seconds=m.sample_window_seconds,
                test_run_id=test_run_id,is_test=True,
            )
            snapshots.append(m)
        started=datetime.now(timezone.utc)
        try:
            worker.run(duration_seconds,on_snapshot=on_snapshot,snapshot_every=max(2,min(5,duration_seconds//2)))
            products=sorted({m.product for m in snapshots})
            if products != ["BTC-USD","ETH-USD"]:
                raise RuntimeError(f"Realtime testte iki ürün de alınamadı: {products}")
            details={
                "test_run_id":test_run_id,"duration_seconds":duration_seconds,"snapshots":len(snapshots),
                "products":products,"messages":worker.message_count,
                "latest":{m.product:{"spread_bps":m.spread_bps,"imbalance":m.imbalance,"ofi":m.ofi,"trade_imbalance":m.trade_imbalance,"trade_notional_usd":m.trade_notional_usd,"trade_gap_count":m.trade_gap_count} for m in snapshots[-2:]},
            }
            self.repo.publish_health("REALTIME_TEST","OK","Coinbase realtime smoke test başarılı",details)
            self.repo.log_job("realtime_test","OK",started,details=details)
            return details
        except Exception as exc:
            self.repo.publish_health("REALTIME_TEST","ERROR",str(exc)[:500],{"test_run_id":test_run_id})
            self.repo.log_job("realtime_test","ERROR",started,str(exc)[:500],{"test_run_id":test_run_id})
            raise

    def flush_spool(self) -> None:
        for item in self.spool.pending():
            try:
                payload=json.loads(item["payload"])
                if item["topic"]=="health": self.repo.publish_health(**payload)
                self.spool.ack(item["id"])
            except Exception as exc: self.spool.fail(item["id"],str(exc))

    def _health_fail(self, component: str, exc: Exception) -> None:
        payload={"component":component,"status":"ERROR","message":str(exc)[:500],"details":{}}
        try: self.repo.publish_health(**payload)
        except Exception: self.spool.enqueue("health",payload)
        try:
            if self.settings.engine_mode=="live": self.telegram.send(f"⚠️ {component} hatası: {str(exc)[:350]}")
        except Exception: pass

    def _job_fail(self, name: str, started: datetime, exc: Exception) -> None:
        try: self.repo.log_job(name,"ERROR",started,str(exc)[:500])
        except Exception: pass
