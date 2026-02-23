"""
Composite Strategy

복합 전략: 여러 전략의 신호를 종합합니다.
"""

from __future__ import annotations

from agents.strategist.strategies.base import BaseStrategy
from agents.strategist.strategies.momentum import MomentumStrategy
from agents.strategist.strategies.value import ValueStrategy
from agents.strategist.strategies.mean_reversion import MeanReversionStrategy
from agents.strategist.agent import TradeSignal, InvestmentThesis


class CompositeStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("Composite")
        self.strategies = [
            MomentumStrategy(),
            ValueStrategy(),
            MeanReversionStrategy(),
        ]
    
    async def generate(
        self,
        analysis_report: dict,
        thesis: InvestmentThesis | None = None,
    ) -> TradeSignal | None:
        signals = []
        
        for strategy in self.strategies:
            try:
                signal = await strategy.generate(analysis_report, thesis)
                if signal:
                    signals.append(signal)
            except Exception:
                pass
        
        if not signals:
            return None
        
        avg_strength = sum(s.strength for s in signals) / len(signals)
        
        buy_count = sum(1 for s in signals if s.direction == "BUY")
        sell_count = sum(1 for s in signals if s.direction == "SELL")
        
        if buy_count > sell_count:
            direction = "BUY"
        elif sell_count > buy_count:
            direction = "SELL"
        else:
            direction = "BUY" if avg_strength > 0 else "SELL"
        
        best_signal = max(signals, key=lambda s: s.strength)
        
        return TradeSignal(
            symbol=analysis_report.get("symbol"),
            direction=direction,
            strength=avg_strength,
            target_price=best_signal.target_price,
            stop_loss_price=best_signal.stop_loss_price,
            take_profit_price=best_signal.take_profit_price,
            strategy_name=self.name,
            reasoning=f"Composite: {', '.join(s.strategy_name for s in signals)}",
            max_position_pct=0.08,
            urgency=best_signal.urgency,
        )
