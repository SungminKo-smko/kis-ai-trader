"""
Base Strategy

모든 투자 전략의 기본 클래스입니다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from agents.strategist.agent import TradeSignal, InvestmentThesis


class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def generate(
        self,
        analysis_report: dict,
        thesis: InvestmentThesis | None = None,
    ) -> TradeSignal | None:
        pass
    
    def _calculate_risk_reward(
        self,
        target_price: float,
        stop_loss: float,
        current_price: float,
    ) -> float:
        if stop_loss == 0:
            return 0
        
        reward = abs(target_price - current_price)
        risk = abs(current_price - stop_loss)
        
        if risk == 0:
            return 0
        
        return reward / risk
    
    def _determine_urgency(self, strength: float, regime: str) -> str:
        if strength >= 0.8:
            return "IMMEDIATE"
        elif strength >= 0.6:
            return "TODAY"
        else:
            return "THIS_WEEK"
