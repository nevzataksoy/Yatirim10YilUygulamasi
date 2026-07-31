from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Iterable

from app.database.db import DatabaseService
from app.database.feature_rows import build_feature_rows
from app.models import Decision, FactorScore, PriceBar
from app.version import MODEL_VERSION


class Repository:
    def __init__(self, db: DatabaseService) -> None:
        self.db = db

    def upsert_price_bars(self, bars: Iterable[PriceBar], asset_class: str = "crypto") -> None:
        rows = list(bars)
        if not rows:
            return
        sql = """
        insert into market.daily_prices
          (provider, asset_class, symbol, price_date, open, high, low, close, volume)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        on conflict (provider, symbol, price_date) do update set
          open=excluded.open, high=excluded.high, low=excluded.low,
          close=excluded.close, volume=excluded.volume, fetched_at=now()
        """
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.executemany(sql, [
                (b.provider, asset_class, b.symbol, b.date, b.open, b.high, b.low, b.close, b.volume)
                for b in rows
            ])
            conn.commit()

    def insert_derivative_snapshot(self, snapshot: dict) -> None:
        sql = """
        insert into market.derivatives_snapshots
          (observed_at, venue, underlying, instrument_name, open_interest, mark_price,
           index_price, basis_pct, funding_8h, current_funding, best_bid, best_ask,
           option_open_interest, option_volume_24h, option_mark_iv_mean, raw)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
        """
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute(sql, (
                snapshot["ts"], snapshot.get("venue", "unknown"), snapshot["currency"], snapshot["instrument"],
                snapshot["open_interest"], snapshot["mark_price"], snapshot["index_price"],
                snapshot["basis_pct"], snapshot["funding_8h"], snapshot["current_funding"],
                snapshot["best_bid"], snapshot["best_ask"], snapshot["option_open_interest"],
                snapshot["option_volume_24h"], snapshot["option_mark_iv_mean"], json.dumps(snapshot),
            ))
            conn.commit()

    def upsert_macro(self, observations: list[dict]) -> None:
        if not observations:
            return
        sql = """
        insert into macro.observations
          (series_id, observation_date, value, realtime_start, realtime_end)
        values (%s,%s,%s,%s,%s)
        on conflict (series_id, observation_date, realtime_start) do update set
          value=excluded.value, realtime_end=excluded.realtime_end, fetched_at=now()
        """
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.executemany(sql, [
                (x["series_id"], x["date"], x["value"], x.get("realtime_start") or x["date"], x.get("realtime_end"))
                for x in observations
            ])
            conn.commit()

    def upsert_features(self, system: str, as_of: str, features: dict[str, dict]) -> None:
        """Persist numeric feature rows; metadata remains in-memory only."""
        sql = """
        insert into model.features
          (as_of, system, feature_code, value, z_score, quality, details)
        values (%s,%s,%s,%s,%s,%s,%s::jsonb)
        on conflict (as_of, system, feature_code) do update set
          value=excluded.value, z_score=excluded.z_score, quality=excluded.quality,
          details=excluded.details, created_at=now()
        """
        rows = build_feature_rows(system, as_of, features)
        if not rows:
            return
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.executemany(sql, rows)
            conn.commit()

    def insert_factor_scores(self, system: str, as_of: str, regime: str,
                             factors: dict[str, FactorScore], weights: dict[str, float]) -> None:
        sql = """
        insert into model.factor_scores
          (as_of, system, regime_code, factor_code, score, quality, weight, weighted_score, details)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
        on conflict (as_of, system, factor_code) do update set
          regime_code=excluded.regime_code, score=excluded.score, quality=excluded.quality,
          weight=excluded.weight, weighted_score=excluded.weighted_score,
          details=excluded.details, created_at=now()
        """
        rows = []
        for code, factor in factors.items():
            w = float(weights.get(code, 0))
            rows.append((as_of, system, regime, code, factor.score, factor.quality, w,
                         factor.score * w * (factor.quality / 100.0), json.dumps(factor.details)))
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.executemany(sql, rows)
            conn.commit()

    def insert_regime(self, system: str, as_of: str, regime: str, probabilities: dict, details: dict) -> None:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                insert into model.regimes(as_of, system, primary_regime, probabilities, details)
                values (%s,%s,%s,%s::jsonb,%s::jsonb)
                on conflict(as_of,system) do update set primary_regime=excluded.primary_regime,
                  probabilities=excluded.probabilities, details=excluded.details, created_at=now()
            """, (as_of, system, regime, json.dumps(probabilities), json.dumps(details)))
            conn.commit()

    def insert_decision(self, decision: Decision) -> int:
        factors_json = {k: {"score": v.score, "quality": v.quality, "details": v.details} for k, v in decision.factors.items()}
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                insert into model.decisions
                  (as_of, system, direction, regime_code, edge_score, confidence, uncertainty,
                   data_quality, risk_score, recommended_size, late_entry, event_veto,
                   status, execution_required, action_event, action_stage, action_size, regime_cumulative_size,
                   model_version, factors, rationale)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                returning id
            """, (
                decision.as_of, decision.system, decision.direction, decision.regime,
                decision.edge_score, decision.confidence, decision.uncertainty,
                decision.data_quality, decision.risk_score, decision.recommended_size,
                decision.late_entry, decision.event_veto, decision.status,
                decision.execution_required, decision.action_event, decision.action_stage,
                decision.action_size, decision.regime_cumulative_size, MODEL_VERSION,
                json.dumps(factors_json), json.dumps(decision.rationale),
            ))
            row = cur.fetchone(); conn.commit()
            return int(row["id"])

    def get_signal_state(self, system: str) -> dict | None:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("select * from model.signal_state where system=%s", (system,))
            return cur.fetchone()

    def upsert_signal_state(self, system: str, active_direction: str | None, stage: int,
                            cumulative_size: float, last_action_date: str | None, reset_counter: int) -> None:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                insert into model.signal_state(system,active_direction,stage,cumulative_size,last_action_date,reset_counter,updated_at)
                values(%s,%s,%s,%s,%s,%s,now())
                on conflict(system) do update set
                  active_direction=excluded.active_direction, stage=excluded.stage,
                  cumulative_size=excluded.cumulative_size, last_action_date=excluded.last_action_date,
                  reset_counter=excluded.reset_counter, updated_at=now()
            """, (system, active_direction, stage, cumulative_size, last_action_date, reset_counter))
            conn.commit()

    def get_latest_decision(self, system: str) -> dict | None:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("select * from model.decisions where system=%s order by created_at desc limit 1", (system,))
            return cur.fetchone()

    def publish_decision_history(self, decision_id: int, decision: Decision, provider: str = "") -> None:
        factors = {code: {"score": f.score, "quality": f.quality} for code, f in decision.factors.items()}
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                insert into public.decision_history
                  (decision_id, generated_at, as_of, system, direction, status, regime_code,
                   edge_score, confidence, uncertainty, data_quality, risk_score, recommended_size,
                   late_entry, event_veto, execution_required, action_event, action_stage, action_size,
                   regime_cumulative_size, provider, model_version, factors, rationale)
                values (%s,now(),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                on conflict(decision_id) do nothing
            """, (
                decision_id, decision.as_of, decision.system, decision.direction, decision.status,
                decision.regime, decision.edge_score, decision.confidence, decision.uncertainty,
                decision.data_quality, decision.risk_score, decision.recommended_size,
                decision.late_entry, decision.event_veto, decision.execution_required,
                decision.action_event, decision.action_stage, decision.action_size, decision.regime_cumulative_size,
                provider, MODEL_VERSION, json.dumps(factors), json.dumps(decision.rationale),
            ))
            conn.commit()

    def publish_market_snapshot(self, symbol: str, value: float, unit: str, provider: str, data_date: str, details: dict | None = None) -> None:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                insert into public.market_snapshot(symbol,value,unit,provider,data_date,generated_at,details)
                values (%s,%s,%s,%s,%s,now(),%s::jsonb)
                on conflict(symbol) do update set
                  value=excluded.value, unit=excluded.unit, provider=excluded.provider,
                  data_date=excluded.data_date, generated_at=now(), details=excluded.details
            """, (symbol, value, unit, provider, data_date, json.dumps(details or {})))
            conn.commit()

    def publish_decision_snapshot(self, decision: Decision, provider: str = "") -> None:
        factors = {code: {"score": f.score, "quality": f.quality} for code, f in decision.factors.items()}
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                insert into public.decision_snapshot
                  (system, generated_at, as_of, direction, status, regime_code, edge_score,
                   confidence, uncertainty, data_quality, risk_score, recommended_size,
                   late_entry, event_veto, execution_required, action_event, action_stage, action_size,
                   regime_cumulative_size, provider, model_version, factors, rationale)
                values (%s,now(),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                on conflict(system) do update set
                  generated_at=now(), as_of=excluded.as_of, direction=excluded.direction,
                  status=excluded.status, regime_code=excluded.regime_code,
                  edge_score=excluded.edge_score, confidence=excluded.confidence,
                  uncertainty=excluded.uncertainty, data_quality=excluded.data_quality,
                  risk_score=excluded.risk_score, recommended_size=excluded.recommended_size,
                  late_entry=excluded.late_entry, event_veto=excluded.event_veto,
                  execution_required=excluded.execution_required, action_event=excluded.action_event,
                  action_stage=excluded.action_stage, action_size=excluded.action_size,
                  regime_cumulative_size=excluded.regime_cumulative_size, provider=excluded.provider,
                  model_version=excluded.model_version, factors=excluded.factors, rationale=excluded.rationale
            """, (
                decision.system, decision.as_of, decision.direction, decision.status, decision.regime,
                decision.edge_score, decision.confidence, decision.uncertainty, decision.data_quality,
                decision.risk_score, decision.recommended_size, decision.late_entry, decision.event_veto,
                decision.execution_required, decision.action_event, decision.action_stage,
                decision.action_size, decision.regime_cumulative_size, provider, MODEL_VERSION,
                json.dumps(factors), json.dumps(decision.rationale),
            ))
            conn.commit()

    def publish_health(self, component: str, status: str, message: str = "", details: dict | None = None) -> None:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                insert into public.engine_health_snapshot(component, status, message, checked_at, details)
                values (%s,%s,%s,now(),%s::jsonb)
                on conflict(component) do update set status=excluded.status, message=excluded.message,
                  checked_at=now(), details=excluded.details
            """, (component, status, message, json.dumps(details or {})))
            conn.commit()

    def log_job(self, job_name: str, status: str, started_at: datetime, message: str = "", details: dict | None = None) -> None:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                insert into system.job_runs(job_name, started_at, finished_at, status, message, details)
                values (%s,%s,now(),%s,%s,%s::jsonb)
            """, (job_name, started_at, status, message, json.dumps(details or {})))
            conn.commit()


    def get_latest_job_run(self, job_name: str) -> dict | None:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "select * from system.job_runs where job_name=%s order by started_at desc limit 1",
                (job_name,),
            )
            return cur.fetchone()

    def get_latest_derivative(self, currency: str, max_age_hours: int = 3, venue: str | None = None) -> dict | None:
        with self.db.connection() as conn, conn.cursor() as cur:
            if venue:
                cur.execute("""
                    select * from market.derivatives_snapshots
                    where underlying=%s and venue=%s
                      and observed_at >= now()-(%s || ' hours')::interval
                    order by observed_at desc limit 1
                """, (currency, venue, max_age_hours))
            else:
                cur.execute("""
                    select * from market.derivatives_snapshots
                    where underlying=%s and observed_at >= now()-(%s || ' hours')::interval
                    order by observed_at desc limit 1
                """, (currency, max_age_hours))
            return cur.fetchone()

    def get_latest_derivative_pair(self, max_age_hours: int = 3) -> tuple[dict | None, dict | None, str | None]:
        """Return the newest complete BTC+ETH pair from the same venue."""
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                select *
                from market.derivatives_snapshots
                where underlying in ('BTC','ETH')
                  and observed_at >= now()-(%s || ' hours')::interval
                order by observed_at desc
            """, (max_age_hours,))
            rows = cur.fetchall()
        by_venue: dict[str, dict[str, dict]] = {}
        for row in rows:
            venue = str(row.get("venue") or "")
            underlying = str(row.get("underlying") or "")
            if underlying not in {"BTC", "ETH"}:
                continue
            by_venue.setdefault(venue, {})
            by_venue[venue].setdefault(underlying, row)
        candidates = []
        for venue, pair in by_venue.items():
            if "BTC" in pair and "ETH" in pair:
                freshness = min(pair["BTC"]["observed_at"], pair["ETH"]["observed_at"] )
                candidates.append((freshness, venue, pair))
        if not candidates:
            return None, None, None
        _, venue, pair = max(candidates, key=lambda item: item[0])
        return pair["BTC"], pair["ETH"], venue

    def get_latest_macro(self, series_ids: list[str]) -> dict[str,float]:
        return {
            key: float(row["value"])
            for key, row in self.get_latest_macro_observations(series_ids).items()
        }

    def get_latest_macro_observations(self, series_ids: list[str], as_of: str | None = None) -> dict[str,dict]:
        out: dict[str,dict] = {}
        with self.db.connection() as conn, conn.cursor() as cur:
            for series_id in series_ids:
                if as_of:
                    cur.execute("""
                        select series_id, observation_date, value, fetched_at
                        from macro.observations
                        where series_id=%s and observation_date <= %s
                        order by observation_date desc limit 1
                    """, (series_id, as_of))
                else:
                    cur.execute("""
                        select series_id, observation_date, value, fetched_at
                        from macro.observations
                        where series_id=%s
                        order by observation_date desc limit 1
                    """, (series_id,))
                row=cur.fetchone()
                if row:
                    out[series_id]=row
        return out

    def insert_event(self, source: str, entity: str, asset: str, event_type: str,
                     occurred_at: str, title: str, url: str = "", severity: float = 0,
                     surprise: float = 0, credibility: float = 100, raw: dict | None = None) -> None:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                insert into events.events(source,entity,asset,event_type,occurred_at,title,url,severity,surprise,credibility,raw)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                on conflict(source,url) where url<>'' do nothing
            """, (source,entity,asset,event_type,occurred_at,title,url,severity,surprise,credibility,json.dumps(raw or {})))
            conn.commit()

    def recent_event_veto(self, asset: str, hours: int = 48) -> tuple[bool,list[dict]]:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                select source,entity,event_type,severity,title,occurred_at
                from events.events
                where asset in (%s,'ALL') and occurred_at >= now()-(%s || ' hours')::interval
                  and severity <= -80
                order by occurred_at desc
            """, (asset, hours))
            rows=cur.fetchall()
            return bool(rows), rows

    def insert_execution_snapshot(
        self,
        *,
        decision_id: int | None,
        observed_at: str,
        product: str,
        spread_bps: float,
        bid_depth_usd: float,
        ask_depth_usd: float,
        imbalance: float,
        microprice: float,
        ofi: float | None = None,
        trade_imbalance: float | None = None,
        trade_notional_usd: float | None = None,
        trade_gap_count: int = 0,
        sample_window_seconds: int | None = None,
        test_run_id: str | None = None,
        is_test: bool = False,
    ) -> None:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into market.execution_snapshots(
                  decision_id,observed_at,product,spread_bps,bid_depth_usd,ask_depth_usd,
                  imbalance,microprice,ofi,trade_imbalance,trade_notional_usd,trade_gap_count,
                  sample_window_seconds,test_run_id,is_test
                ) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    decision_id, observed_at, product, spread_bps, bid_depth_usd,
                    ask_depth_usd, imbalance, microprice, ofi, trade_imbalance,
                    trade_notional_usd, trade_gap_count, sample_window_seconds, test_run_id, is_test,
                ),
            )
            conn.commit()

    def upsert_ura_holdings(self, snapshot) -> None:
        rows = list(snapshot.holdings)
        if not rows:
            return
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                insert into fundamentals.ura_holdings(
                  holding_date,ticker,name,weight,shares,market_value,market_price,source_url
                ) values(%s,%s,%s,%s,%s,%s,%s,%s)
                on conflict(holding_date,ticker) do update set
                  name=excluded.name,weight=excluded.weight,shares=excluded.shares,
                  market_value=excluded.market_value,market_price=excluded.market_price,
                  source_url=excluded.source_url,fetched_at=now()
                """,
                [
                    (
                        h.holding_date, h.ticker, h.name, h.weight, h.shares,
                        h.market_value, h.market_price, h.source_url,
                    )
                    for h in rows
                ],
            )
            conn.commit()

    def get_ura_holdings_summary(self, as_of: str, ura_close: float | None = None) -> dict | None:
        """Return current/prior official holdings snapshot and a price-adjusted AUM-flow proxy."""
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select distinct holding_date
                from fundamentals.ura_holdings
                where holding_date <= %s
                order by holding_date desc
                limit 2
                """,
                (as_of,),
            )
            dates = [row["holding_date"] for row in cur.fetchall()]
            if not dates:
                return None

            def aggregate(holding_date):
                cur.execute(
                    """
                    select count(*) as constituents,
                           coalesce(sum(greatest(weight,0)),0) as weight_coverage,
                           coalesce(sum(market_value),0) as total_market_value
                    from fundamentals.ura_holdings
                    where holding_date=%s
                    """,
                    (holding_date,),
                )
                return cur.fetchone()

            current_date = dates[0]
            current = aggregate(current_date)
            previous_date = dates[1] if len(dates) > 1 else None
            from datetime import date as _date
            reference_date = _date.fromisoformat(str(as_of)[:10])
            result = {
                "current_date": str(current_date),
                "previous_date": str(previous_date) if previous_date else None,
                "reference_date": reference_date.isoformat(),
                "snapshot_age_days": (reference_date - current_date).days,
                "constituents": int(current["constituents"] or 0),
                "weight_coverage": float(current["weight_coverage"] or 0),
                "total_market_value": float(current["total_market_value"] or 0),
            }
            if not previous_date:
                return result
            previous = aggregate(previous_date)
            current_mv = float(current["total_market_value"] or 0)
            previous_mv = float(previous["total_market_value"] or 0)
            if previous_mv <= 0:
                return result

            cur.execute(
                """
                select price_date, close
                from market.daily_prices
                where symbol='URA' and price_date in (%s,%s)
                order by price_date
                """,
                (previous_date, current_date),
            )
            prices = {str(r["price_date"]): float(r["close"]) for r in cur.fetchall()}
            price_return_pct = None
            if str(previous_date) in prices and str(current_date) in prices and prices[str(previous_date)] > 0:
                price_return_pct = (prices[str(current_date)] / prices[str(previous_date)] - 1.0) * 100.0
            aum_change_pct = (current_mv / previous_mv - 1.0) * 100.0
            flow_proxy_pct = aum_change_pct - (price_return_pct or 0.0)
            result.update(
                {
                    "previous_total_market_value": previous_mv,
                    "aum_change_pct": aum_change_pct,
                    "price_return_pct": price_return_pct,
                    "flow_proxy_pct": flow_proxy_pct,
                    "days_between": (current_date - previous_date).days,
                }
            )
            return result

    def calculate_and_upsert_ura_breadth(self, as_of: str) -> dict | None:
        """Calculate breadth from the daily market-price history embedded in official holdings CSVs.

        Quality rises naturally as the engine accumulates history: positive-day
        can become available after two observations, 20DMA metrics after 20, 50DMA
        after 50, and 200DMA after 200. Missing components never get synthetic
        quality credit.
        """
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select max(holding_date) as d
                from fundamentals.ura_holdings
                where holding_date <= %s
                """,
                (as_of,),
            )
            latest_row = cur.fetchone()
            latest_date = latest_row["d"] if latest_row else None
            if not latest_date:
                return None
            cur.execute(
                """
                select ticker, weight
                from fundamentals.ura_holdings
                where holding_date=%s and weight > 0
                """,
                (latest_date,),
            )
            current = cur.fetchall()
            if not current:
                return None

            metrics = {
                "pct_above_20dma": [0.0, 0.0],
                "pct_above_50dma": [0.0, 0.0],
                "pct_above_200dma": [0.0, 0.0],
                "pct_positive_day": [0.0, 0.0],
                "new_20d_high_pct": [0.0, 0.0],
            }
            total_weight = sum(max(0.0, float(r["weight"] or 0)) for r in current) or 1.0
            history_counts: list[int] = []
            for item in current:
                ticker = str(item["ticker"])
                weight = max(0.0, float(item["weight"] or 0)) / total_weight
                cur.execute(
                    """
                    select holding_date, market_price
                    from fundamentals.ura_holdings
                    where ticker=%s and holding_date <= %s and market_price is not null and market_price > 0
                    order by holding_date desc
                    limit 220
                    """,
                    (ticker, latest_date),
                )
                history = cur.fetchall()
                prices = [float(r["market_price"]) for r in reversed(history)]
                history_counts.append(len(prices))
                if len(prices) >= 2:
                    metrics["pct_positive_day"][1] += weight
                    if prices[-1] > prices[-2]:
                        metrics["pct_positive_day"][0] += weight
                if len(prices) >= 20:
                    ma20 = sum(prices[-20:]) / 20
                    metrics["pct_above_20dma"][1] += weight
                    metrics["new_20d_high_pct"][1] += weight
                    if prices[-1] > ma20:
                        metrics["pct_above_20dma"][0] += weight
                    if prices[-1] >= max(prices[-20:]):
                        metrics["new_20d_high_pct"][0] += weight
                if len(prices) >= 50:
                    ma50 = sum(prices[-50:]) / 50
                    metrics["pct_above_50dma"][1] += weight
                    if prices[-1] > ma50:
                        metrics["pct_above_50dma"][0] += weight
                if len(prices) >= 200:
                    ma200 = sum(prices[-200:]) / 200
                    metrics["pct_above_200dma"][1] += weight
                    if prices[-1] > ma200:
                        metrics["pct_above_200dma"][0] += weight

            values: dict[str, float | None] = {}
            coverage_parts: list[float] = []
            for key, (positive_weight, covered_weight) in metrics.items():
                values[key] = positive_weight / covered_weight if covered_weight > 0 else None
                coverage_parts.append(min(1.0, covered_weight))
            quality = sum(coverage_parts) / len(coverage_parts) * 100.0
            details = {
                "source": "Global X URA full holdings CSV market-price history",
                "holding_date": str(latest_date),
                "constituents": len(current),
                "history_min": min(history_counts) if history_counts else 0,
                "history_max": max(history_counts) if history_counts else 0,
                "component_coverage": {k: round(v[1], 6) for k, v in metrics.items()},
            }
            cur.execute(
                """
                insert into fundamentals.ura_breadth(
                  breadth_date,pct_above_20dma,pct_above_50dma,pct_above_200dma,
                  pct_positive_day,new_20d_high_pct,quality,details
                ) values(%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                on conflict(breadth_date) do update set
                  pct_above_20dma=excluded.pct_above_20dma,
                  pct_above_50dma=excluded.pct_above_50dma,
                  pct_above_200dma=excluded.pct_above_200dma,
                  pct_positive_day=excluded.pct_positive_day,
                  new_20d_high_pct=excluded.new_20d_high_pct,
                  quality=excluded.quality,details=excluded.details,created_at=now()
                """,
                (
                    latest_date, values["pct_above_20dma"], values["pct_above_50dma"],
                    values["pct_above_200dma"], values["pct_positive_day"],
                    values["new_20d_high_pct"], quality, json.dumps(details),
                ),
            )
            conn.commit()
            return {"breadth_date": latest_date, **values, "quality": quality, "details": details}

    def get_latest_ura_breadth(self, as_of: str) -> dict | None:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select * from fundamentals.ura_breadth
                where breadth_date <= %s
                order by breadth_date desc limit 1
                """,
                (as_of,),
            )
            return cur.fetchone()

    def get_latest_holdings_tickers(self, limit: int = 15) -> list[dict]:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select ticker,name,weight,holding_date
                from fundamentals.ura_holdings
                where holding_date=(select max(holding_date) from fundamentals.ura_holdings)
                  and ticker <> '' and weight > 0
                order by weight desc
                limit %s
                """,
                (limit,),
            )
            return cur.fetchall()

    def get_health(self, component: str, max_age_hours: int | None = None) -> dict | None:
        with self.db.connection() as conn, conn.cursor() as cur:
            if max_age_hours is None:
                cur.execute("select * from public.engine_health_snapshot where component=%s", (component,))
            else:
                cur.execute(
                    """
                    select * from public.engine_health_snapshot
                    where component=%s and checked_at >= now()-(%s || ' hours')::interval
                    """,
                    (component, max_age_hours),
                )
            return cur.fetchone()

    def recent_events(self, asset: str, hours: int = 168) -> list[dict]:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select source,entity,asset,event_type,severity,surprise,credibility,title,url,occurred_at
                from events.events
                where asset in (%s,'ALL') and occurred_at >= now()-(%s || ' hours')::interval
                order by occurred_at desc
                """,
                (asset, hours),
            )
            return cur.fetchall()

    def evaluate_mature_decisions(self, horizons: tuple[int, ...] = (5, 20, 60)) -> dict:
        """Evaluate old decisions against subsequent market closes without changing weights."""
        summary = {"evaluated": 0, "skipped": 0, "horizons": list(horizons)}
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("select id,as_of,system,direction from model.decisions where status in ('ACTION','WATCH') order by as_of,id")
            decisions = cur.fetchall()
            for decision in decisions:
                for horizon in horizons:
                    cur.execute(
                        "select 1 from model.performance where decision_id=%s and horizon_days=%s",
                        (decision["id"], horizon),
                    )
                    if cur.fetchone():
                        continue
                    system = str(decision["system"])
                    as_of = decision["as_of"]
                    if system == "URA/USD":
                        cur.execute(
                            """
                            select price_date,close from market.daily_prices
                            where symbol='URA' and price_date >= %s
                            order by price_date asc limit %s
                            """,
                            (as_of, horizon + 1),
                        )
                        rows = cur.fetchall()
                        if len(rows) < horizon + 1:
                            summary["skipped"] += 1
                            continue
                        base = float(rows[0]["close"]); future = float(rows[horizon]["close"])
                        raw_return = future / base - 1.0
                        signed = raw_return if str(decision["direction"]) == "USD→URA" else -raw_return
                    elif system == "ETH/BTC":
                        ratios: list[float] = []
                        cur.execute(
                            """
                            select price_date,
                                   max(close) filter(where symbol='ETH-USD') as eth,
                                   max(close) filter(where symbol='BTC-USD') as btc
                            from market.daily_prices
                            where symbol in ('ETH-USD','BTC-USD') and price_date >= %s
                            group by price_date
                            having max(close) filter(where symbol='ETH-USD') is not null
                               and max(close) filter(where symbol='BTC-USD') is not null
                            order by price_date asc limit %s
                            """,
                            (as_of, horizon + 1),
                        )
                        rows = cur.fetchall()
                        if len(rows) < horizon + 1:
                            summary["skipped"] += 1
                            continue
                        ratios = [float(r["eth"]) / float(r["btc"]) for r in rows]
                        raw_return = ratios[horizon] / ratios[0] - 1.0
                        signed = raw_return if str(decision["direction"]) == "BTC→ETH" else -raw_return
                    else:
                        continue
                    cur.execute(
                        """
                        insert into model.performance(decision_id,system,horizon_days,relative_return,hit,evaluated_at)
                        values(%s,%s,%s,%s,%s,now())
                        on conflict(decision_id,horizon_days) do nothing
                        """,
                        (decision["id"], system, horizon, signed, signed > 0),
                    )
                    summary["evaluated"] += 1
            conn.commit()

            cur.execute(
                """
                select system,horizon_days,count(*) as observations,
                       avg(case when hit then 1.0 else 0.0 end) as hit_rate,
                       avg(relative_return) as avg_relative_return
                from model.performance
                where evaluated_at is not null
                group by system,horizon_days
                order by system,horizon_days
                """
            )
            summary["performance"] = [dict(r) for r in cur.fetchall()]
        return summary


    def get_price_bars(self, symbol: str) -> list[PriceBar]:
        """Return one preferred row per date for historical replay."""
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select distinct on(price_date)
                       provider,symbol,price_date,open,high,low,close,volume
                from market.daily_prices
                where symbol=%s
                order by price_date,
                         case provider when 'coinbase' then 0 when 'alpha_vantage' then 0
                                       when 'bitstamp' then 1 else 9 end,
                         fetched_at desc
                """,
                (symbol,),
            )
            rows = cur.fetchall()
        return [
            PriceBar(
                str(r["provider"]), str(r["symbol"]), str(r["price_date"]),
                float(r["open"]), float(r["high"]), float(r["low"]),
                float(r["close"]), float(r["volume"]),
            )
            for r in rows
        ]

    def get_macro_history(self, series_ids: list[str]) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {key: [] for key in series_ids}
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select series_id,observation_date,value,fetched_at
                from macro.observations
                where series_id = any(%s)
                order by series_id,observation_date
                """,
                (series_ids,),
            )
            for row in cur.fetchall():
                out.setdefault(str(row["series_id"]), []).append(row)
        return out

    def shadow_readiness_stats(self) -> dict:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                select min(created_at) as first_decision_at,
                       max(created_at) as last_decision_at
                from model.decisions
                where model_version=%s
            """, (MODEL_VERSION,))
            span = cur.fetchone() or {}
            first = span.get("first_decision_at")
            last = span.get("last_decision_at")
            calendar_days = ((last.date() - first.date()).days + 1) if first and last else 0

            cur.execute("""
                select system,
                       count(distinct as_of) as decision_days,
                       percentile_cont(0.5) within group(order by data_quality) as median_quality,
                       count(*) filter(where status='ACTION') as actions,
                       count(*) filter(where status='WATCH') as watches
                from model.decisions
                where model_version=%s
                group by system
            """, (MODEL_VERSION,))
            by_system = {str(r["system"]): r for r in cur.fetchall()}

            cur.execute("""
                select count(*) as jobs,
                       count(*) filter(where status in ('OK','DEGRADED','SKIPPED')) as successful
                from system.job_runs
                where started_at >= now()-interval '7 days'
                  and job_name not in ('realtime_test')
            """)
            jobs = cur.fetchone() or {}
            job_count = int(jobs.get("jobs") or 0)
            job_success = int(jobs.get("successful") or 0)

            cur.execute("""
                select finished_at
                from system.job_runs
                where job_name='realtime_test' and status='OK'
                order by finished_at desc limit 1
            """)
            rt = cur.fetchone()
            realtime_age = None
            if rt and rt.get("finished_at"):
                realtime_age = max(
                    0.0,
                    (datetime.now(timezone.utc) - rt["finished_at"]).total_seconds() / 86400.0,
                )

            cur.execute("select count(distinct holding_date) as n from fundamentals.ura_holdings")
            holdings_dates = int((cur.fetchone() or {}).get("n") or 0)
            cur.execute("select count(distinct breadth_date) as n from fundamentals.ura_breadth")
            breadth_dates = int((cur.fetchone() or {}).get("n") or 0)

            cur.execute("""
                select p.system,p.horizon_days,count(*) as n,
                       avg(case when hit then 1.0 else 0.0 end) as hit_rate,
                       avg(relative_return) as avg_return
                from model.performance p
                join model.decisions d on d.id=p.decision_id
                where d.model_version=%s
                group by p.system,p.horizon_days
                order by p.system,p.horizon_days
            """, (MODEL_VERSION,))
            performance = [dict(r) for r in cur.fetchall()]

        crypto = by_system.get("ETH/BTC", {})
        ura = by_system.get("URA/USD", {})
        return {
            "calendar_days": calendar_days,
            "first_decision_at": first.isoformat() if first else None,
            "last_decision_at": last.isoformat() if last else None,
            "crypto_decision_days": int(crypto.get("decision_days") or 0),
            "ura_decision_days": int(ura.get("decision_days") or 0),
            "crypto_median_quality": float(crypto["median_quality"]) if crypto.get("median_quality") is not None else None,
            "ura_median_quality": float(ura["median_quality"]) if ura.get("median_quality") is not None else None,
            "crypto_actions": int(crypto.get("actions") or 0),
            "crypto_watches": int(crypto.get("watches") or 0),
            "ura_actions": int(ura.get("actions") or 0),
            "ura_watches": int(ura.get("watches") or 0),
            "job_count": job_count,
            "job_success_rate": (job_success / job_count) if job_count else 0.0,
            "realtime_test_age_days": realtime_age,
            "ura_holdings_dates": holdings_dates,
            "ura_breadth_dates": breadth_dates,
            "performance": performance,
        }

    def insert_validation_run(
        self,
        *,
        validation_type: str,
        system: str,
        status: str,
        started_at: datetime,
        start_date: str | None,
        end_date: str | None,
        observations: int | None,
        signals: int | None,
        metrics: dict,
        details: dict | None = None,
    ) -> int:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into model.validation_runs(
                  validation_type,system,model_version,status,started_at,finished_at,
                  start_date,end_date,observations,signals,metrics,details
                ) values(%s,%s,%s,%s,%s,now(),%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                returning id
                """,
                (
                    validation_type, system, MODEL_VERSION, status, started_at,
                    start_date, end_date, observations, signals,
                    json.dumps(metrics), json.dumps(details or {}),
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["id"])

    def publish_validation_snapshot(
        self,
        *,
        validation_type: str,
        system: str,
        status: str,
        start_date: str | None,
        end_date: str | None,
        metrics: dict,
        details: dict | None = None,
    ) -> None:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.model_validation_snapshot(
                  validation_type,system,generated_at,model_version,status,start_date,end_date,metrics,details
                ) values(%s,%s,now(),%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                on conflict(validation_type,system) do update set
                  generated_at=now(),model_version=excluded.model_version,status=excluded.status,
                  start_date=excluded.start_date,end_date=excluded.end_date,
                  metrics=excluded.metrics,details=excluded.details
                """,
                (
                    validation_type, system, MODEL_VERSION, status, start_date, end_date,
                    json.dumps(metrics), json.dumps(details or {}),
                ),
            )
            conn.commit()
