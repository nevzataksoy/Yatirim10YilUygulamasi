from __future__ import annotations

import json
from pathlib import Path

from app.engines.risk import risk_and_size
from app.engines.veto import evaluate_late_entry
from app.models import AppSettings, Decision, FactorScore


class DecisionEngine:
    def __init__(self, settings: AppSettings, defaults_path: Path) -> None:
        self.settings=settings; self.defaults=json.loads(defaults_path.read_text(encoding="utf-8"))

    def weights(self, system: str, regime: str) -> dict[str,float]:
        return self.defaults["factor_weights"].get(system,{}).get(regime) or self.defaults["factor_weights"][system]["NEUTRAL"]

    def build(self, system: str, as_of: str, regime: str, features: dict[str,dict], factors: dict[str,FactorScore], event_veto: bool=False) -> tuple[Decision,dict[str,float]]:
        weights=self.weights(system,regime); numerator=0.0; denom=0.0; qnum=0.0; qden=sum(weights.values()) or 1.0; signed=[]
        for code,w in weights.items():
            f=factors.get(code)
            if not f or f.quality<=0: continue
            qw=w*(f.quality/100); numerator+=f.score*qw; denom+=qw; qnum+=f.quality*w
            if f.score > 1e-9:
                signed.append(1)
            elif f.score < -1e-9:
                signed.append(-1)
        edge_signed=numerator/max(denom,1e-9); edge=abs(edge_signed); quality=qnum/max(qden,1e-9)
        agreement=abs(sum(signed))/len(signed)*100 if signed else 0.0
        confidence=min(100,max(0,edge*0.65+quality*0.20+agreement*0.15)); uncertainty=100-confidence
        bullish=edge_signed>=0
        direction=("BTC→ETH" if bullish else "ETH→BTC") if system=="ETH/BTC" else ("USD→URA" if bullish else "URA→USD")
        late,reasons=evaluate_late_entry(features,bullish,self.settings.max_late_entry_cross_age_days)
        risk,size,risk_details=risk_and_size(features,confidence,self.settings.base_tranche_pct,self.settings.max_regime_pct)
        if quality<self.settings.min_data_quality: status="NO_ACTION_DATA"
        elif event_veto: status="BLOCKED_EVENT"
        elif late and edge>=self.settings.min_action_edge: status="BLOCKED_LATE"
        elif edge>=self.settings.min_action_edge and confidence>=self.settings.min_action_confidence: status="ACTION"
        elif edge>=55: status="WATCH"
        else: status="WAIT"
        if status!="ACTION": size=0.0
        d=Decision(system,as_of,direction,regime,round(edge,2),round(confidence,2),round(uncertainty,2),round(quality,2),round(risk,2),round(size,4),late,event_veto,status,status=="ACTION" and self.settings.realtime_execution_enabled,factors,{"edge_signed":edge_signed,"agreement":agreement,"late_reasons":reasons,"risk":risk_details})
        return d,weights
