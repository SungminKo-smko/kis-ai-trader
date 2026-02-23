"""
Value Strategy

밸류 전략: 저평가된 종목을 매수하는 전략입니다.
"""

from __future__ import annotations

from agents.strategist.strategies.base import BaseStrategy
from agents.strategist.agent import TradeSignal, InvestmentThesis


class ValueStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("Value")
    
    async def generate(
        self,
        analysis_report: dict,
        thesis: InvestmentThesis | None = None,
    ) -> TradeSignal | None:
        symbol = analysis_report.get("symbol")
        if not symbol:
            return None
        
        fundamental = analysis_report.get("fundamental", {})
        
        score = 0.0
        reasons = []
        
        per = fundamental.get("per")
        if per:
            if 5 < per < 15:
                score += 0.4
                reasons.append(f"PER low ({per:.1f})")
            elif 15 <= per < 25:
                score += 0.2
                reasons.append(f"PER moderate ({per:.1f})")
        
        pbr = fundamental.get("pbr")
        if pbr:
            if 0.5 < pbr < 1.5:
                score += 0.3
                reasons.append(f"PBR low ({pbr:.1f})")
        
        roe = fundamental.get("roe")
        if roe and roe > 15:
            score += 0.3
            reasons.append(f"ROE high ({roe:.1f}%)")
        
        if score < 0.3:
            return None
        
        direction = "BUY"
        strength = min(score, 1.0)
        
        current_price = fundamental.get("current_price") or 50000
        target_price = current_price * 1.15
        stop_loss = current_price * 0.95
        
        urgency = self._determine_urgency(strength, thesis.regime if thesis else "SIDEWAYS")
        
        return TradeSignal(
            symbol=symbol,
            direction=direction,
            strength=strength,
            target_price=target_price,
            stop_loss_price=stop_loss,
            take_profit_price=target_price,
            strategy_name=self.name,
            reasoning=", ".join(reasons),
            max_position_pct=0.10,
            urgency=urgency,
        )
