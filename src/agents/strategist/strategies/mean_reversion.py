"""
Mean Reversion Strategy

평균회귀 전략: 과매수/과매도 종목을 거래하는 전략입니다.
"""

from __future__ import annotations

from agents.strategist.strategies.base import BaseStrategy
from agents.strategist.agent import TradeSignal, InvestmentThesis


class MeanReversionStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("MeanReversion")
    
    async def generate(
        self,
        analysis_report: dict,
        thesis: InvestmentThesis | None = None,
    ) -> TradeSignal | None:
        symbol = analysis_report.get("symbol")
        if not symbol:
            return None
        
        technical = analysis_report.get("technical", {})
        
        score = 0.0
        reasons = []
        
        rsi = technical.get("rsi")
        if rsi:
            if rsi < 30:
                score += 0.6
                reasons.append(f"RSI oversold ({rsi:.1f}) - BUY")
            elif rsi > 70:
                score += 0.6
                reasons.append(f"RSI overbought ({rsi:.1f}) - SELL")
            else:
                return None
        
        bb_lower = technical.get("bb_lower")
        bb_upper = technical.get("bb_upper")
        current_price = technical.get("sma_20") or 50000
        
        if bb_lower and current_price < bb_lower * 1.05:
            score += 0.3
            reasons.append("below Bollinger lower band")
        elif bb_upper and current_price > bb_upper * 0.95:
            score += 0.3
            reasons.append("above Bollinger upper band")
        
        if score < 0.3:
            return None
        
        if rsi and rsi < 30:
            direction = "BUY"
            target_price = current_price * 1.08
            stop_loss = current_price * 0.97
        elif rsi and rsi > 70:
            direction = "SELL"
            target_price = current_price * 0.92
            stop_loss = current_price * 1.03
        else:
            return None
        
        strength = min(score, 1.0)
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
            max_position_pct=0.05,
            urgency=urgency,
        )
