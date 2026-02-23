"""
Momentum Strategy

모멘텀 전략: 상승 추세의 종목을 매수하는 전략입니다.
"""

from __future__ import annotations

from agents.strategist.strategies.base import BaseStrategy
from agents.strategist.agent import TradeSignal, InvestmentThesis


class MomentumStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("Momentum")
    
    async def generate(
        self,
        analysis_report: dict,
        thesis: InvestmentThesis | None = None,
    ) -> TradeSignal | None:
        symbol = analysis_report.get("symbol")
        if not symbol:
            return None
        
        technical = analysis_report.get("technical", {})
        sentiment = analysis_report.get("sentiment", {})
        
        score = 0.0
        reasons = []
        
        rsi = technical.get("rsi")
        if rsi:
            if 40 < rsi < 70:
                score += 0.3
                reasons.append(f"RSI moderate ({rsi:.1f})")
            elif rsi < 30:
                score -= 0.3
                reasons.append(f"RSI oversold ({rsi:.1f})")
        
        macd_hist = technical.get("macd_histogram")
        if macd_hist:
            if macd_hist > 0:
                score += 0.4
                reasons.append("MACD rising")
            else:
                score -= 0.2
                reasons.append("MACD falling")
        
        pattern = technical.get("pattern")
        if pattern == "UPTREND":
            score += 0.3
            reasons.append("uptrend")
        elif pattern == "DOWNTREND":
            score -= 0.3
            reasons.append("downtrend")
        
        sentiment_ratio = sentiment.get("sentiment_ratio", 0)
        if sentiment_ratio > 0.2:
            score += 0.2
            reasons.append("positive sentiment")
        
        if score < 0.1:
            return None
        
        direction = "BUY" if score > 0 else "SELL"
        strength = min(abs(score), 1.0)
        
        current_price = technical.get("sma_20") or 50000
        target_price = current_price * (1 + strength * 0.1)
        stop_loss = current_price * (1 - 0.03)
        
        urgency = self._determine_urgency(strength, thesis.regime if thesis else "SIDEWAYS")
        
        return TradeSignal(
            symbol=symbol,
            direction=direction,
            strength=strength,
            target_price=target_price,
            stop_loss_price=stop_loss,
            take_profit_price=target_price * 1.02,
            strategy_name=self.name,
            reasoning=", ".join(reasons),
            max_position_pct=0.08 if direction == "BUY" else 0.05,
            urgency=urgency,
        )
