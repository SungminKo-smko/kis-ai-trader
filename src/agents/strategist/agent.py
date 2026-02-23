"""
Strategist Agent - 투자방향 설정 에이전트

분석 결과를 기반으로 투자방향 결정 및 매매신호 생성합니다.

역할:
- 분석 리포트 기반 매매신호 생성
- 시장 레짐에 따른 투자 방향 설정
- 다중 전략 관리 및 신호 우선순위 정렬
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from core.event_bus import Event, EventBus
from core.events import EventTypes


logger = logging.getLogger("strategist_agent")


class StrategyType(str, Enum):
    MOMENTUM = "momentum"
    VALUE = "value"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    COMPOSITE = "composite"


@dataclass
class TradeSignal:
    symbol: str
    direction: str
    strength: float
    target_price: float | None = None
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    strategy_name: str = ""
    reasoning: str = ""
    max_position_pct: float = 0.05
    urgency: str = "THIS_WEEK"
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InvestmentThesis:
    regime: str
    mode: str
    cash_target_pct: float
    sector_allocation: dict[str, float]
    risk_level: str


class StrategistAgent:
    def __init__(
        self,
        event_bus: EventBus,
        config: dict[str, Any] | None = None,
    ):
        self.event_bus = event_bus
        self.config = config or {}
        
        self._running = False
        self._strategies: dict[StrategyType, Any] = {}
        self._active_signals: dict[str, TradeSignal] = {}
        self._current_thesis: InvestmentThesis | None = None
        self._regime = "SIDEWAYS"
    
    def register_strategy(self, strategy_type: StrategyType, strategy: Any):
        self._strategies[strategy_type] = strategy
        logger.info(f"Registered strategy: {strategy_type.value}")
    
    async def start(self):
        self._running = True
        
        self._current_thesis = InvestmentThesis(
            regime="SIDEWAYS",
            mode="NEUTRAL",
            cash_target_pct=0.20,
            sector_allocation={},
            risk_level="MEDIUM",
        )
        
        logger.info("Strategist Agent started")
        
        await self.event_bus.publish(Event(
            type=EventTypes.TRADE_SIGNAL,
            payload={"message": "Strategist Agent started"},
            source="strategist_agent",
        ))
    
    async def stop(self):
        self._running = False
        logger.info("Strategist Agent stopped")
    
    async def generate_signal(
        self,
        analysis_report: dict,
        strategy_type: StrategyType = StrategyType.COMPOSITE,
    ) -> TradeSignal | None:
        try:
            strategy = self._strategies.get(strategy_type)
            if not strategy:
                logger.warning(f"Strategy {strategy_type.value} not found")
                return None
            
            signal = await strategy.generate(analysis_report, self._current_thesis)
            
            if signal:
                self._active_signals[signal.symbol] = signal
                
                await self._publish_signal(signal)
            
            return signal
            
        except Exception as e:
            logger.error(f"Signal generation failed: {e}")
            return None
    
    async def evaluate_universe(
        self,
        reports: list[dict],
    ) -> list[TradeSignal]:
        signals = []
        
        for report in reports:
            try:
                signal = await self.generate_signal(report)
                if signal and signal.direction != "HOLD":
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Failed to evaluate {report.get('symbol')}: {e}")
        
        signals = self._rank_signals(signals)
        
        return signals
    
    async def set_investment_direction(
        self,
        regime: str,
        volatility: float | None = None,
    ) -> InvestmentThesis:
        self._regime = regime
        
        if regime == "BULL":
            thesis = InvestmentThesis(
                regime="BULL",
                mode="AGGRESSIVE",
                cash_target_pct=0.10,
                sector_allocation=self._calculate_sector_allocation("BULL"),
                risk_level="HIGH",
            )
        elif regime == "BEAR":
            thesis = InvestmentThesis(
                regime="BEAR",
                mode="DEFENSIVE",
                cash_target_pct=0.40,
                sector_allocation=self._calculate_sector_allocation("BEAR"),
                risk_level="LOW",
            )
        else:
            thesis = InvestmentThesis(
                regime="SIDEWAYS",
                mode="NEUTRAL",
                cash_target_pct=0.20,
                sector_allocation=self._calculate_sector_allocation("SIDEWAYS"),
                risk_level="MEDIUM",
            )
        
        self._current_thesis = thesis
        logger.info(f"Investment thesis updated: {thesis.mode}")
        
        return thesis
    
    def _calculate_sector_allocation(self, regime: str) -> dict[str, float]:
        if regime == "BULL":
            return {
                "technology": 0.25,
                "consumer": 0.20,
                "finance": 0.15,
                "energy": 0.15,
                "etc": 0.25,
            }
        elif regime == "BEAR":
            return {
                "technology": 0.10,
                "consumer": 0.15,
                "finance": 0.20,
                "energy": 0.10,
                "etc": 0.45,
            }
        else:
            return {
                "technology": 0.15,
                "consumer": 0.15,
                "finance": 0.15,
                "energy": 0.10,
                "etc": 0.45,
            }
    
    def _rank_signals(self, signals: list[TradeSignal]) -> list[TradeSignal]:
        scored = []
        
        for signal in signals:
            score = signal.strength
            
            if signal.urgency == "IMMEDIATE":
                score *= 1.5
            elif signal.urgency == "TODAY":
                score *= 1.2
            
            if self._regime == "BULL" and signal.direction == "BUY":
                score *= 1.2
            elif self._regime == "BEAR" and signal.direction == "SELL":
                score *= 1.2
            
            scored.append((score, signal))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [s[1] for s in scored]
    
    async def _publish_signal(self, signal: TradeSignal):
        await self.event_bus.publish(Event(
            type=EventTypes.TRADE_SIGNAL,
            payload=signal,
            source="strategist_agent",
        ))
    
    def get_active_signals(self) -> dict[str, TradeSignal]:
        return self._active_signals
    
    def get_signal(self, symbol: str) -> TradeSignal | None:
        return self._active_signals.get(symbol)
    
    def get_current_thesis(self) -> InvestmentThesis | None:
        return self._current_thesis
    
    def get_status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "regime": self._regime,
            "strategies": list(self._strategies.keys()),
            "active_signals": len(self._active_signals),
            "thesis": {
                "mode": self._current_thesis.mode if self._current_thesis else None,
                "cash_target_pct": self._current_thesis.cash_target_pct if self._current_thesis else None,
            } if self._current_thesis else None,
        }
