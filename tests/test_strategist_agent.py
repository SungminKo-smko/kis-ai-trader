"""
Tests for Strategist Agent
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from agents.strategist.agent import (
    StrategistAgent,
    StrategyType,
    TradeSignal,
    InvestmentThesis,
)
from core.event_bus import EventBus


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def strategist_agent(event_bus):
    return StrategistAgent(event_bus=event_bus)


class TestStrategistAgent:
    @pytest.mark.asyncio
    async def test_strategist_agent_creation(self, strategist_agent):
        assert strategist_agent is not None
        assert strategist_agent._running is False
        assert strategist_agent._regime == "SIDEWAYS"

    @pytest.mark.asyncio
    async def test_start_and_stop(self, strategist_agent):
        await strategist_agent.start()
        assert strategist_agent._running is True
        assert strategist_agent._current_thesis is not None
        
        await strategist_agent.stop()
        assert strategist_agent._running is False

    @pytest.mark.asyncio
    async def test_register_strategy(self, strategist_agent):
        mock_strategy = MagicMock()
        mock_strategy.generate = AsyncMock(return_value=None)
        
        strategist_agent.register_strategy(StrategyType.MOMENTUM, mock_strategy)
        
        assert StrategyType.MOMENTUM in strategist_agent._strategies

    @pytest.mark.asyncio
    async def test_set_investment_direction_bull(self, strategist_agent):
        thesis = await strategist_agent.set_investment_direction("BULL")
        
        assert thesis.regime == "BULL"
        assert thesis.mode == "AGGRESSIVE"
        assert thesis.cash_target_pct == 0.10

    @pytest.mark.asyncio
    async def test_set_investment_direction_bear(self, strategist_agent):
        thesis = await strategist_agent.set_investment_direction("BEAR")
        
        assert thesis.regime == "BEAR"
        assert thesis.mode == "DEFENSIVE"
        assert thesis.cash_target_pct == 0.40

    @pytest.mark.asyncio
    async def test_set_investment_direction_sideways(self, strategist_agent):
        thesis = await strategist_agent.set_investment_direction("SIDEWAYS")
        
        assert thesis.regime == "SIDEWAYS"
        assert thesis.mode == "NEUTRAL"
        assert thesis.cash_target_pct == 0.20

    @pytest.mark.asyncio
    async def test_get_active_signals_empty(self, strategist_agent):
        signals = strategist_agent.get_active_signals()
        assert signals == {}

    @pytest.mark.asyncio
    async def test_get_signal_not_found(self, strategist_agent):
        signal = strategist_agent.get_signal("005930")
        assert signal is None

    @pytest.mark.asyncio
    async def test_get_status(self, strategist_agent):
        status = strategist_agent.get_status()
        
        assert "running" in status
        assert "regime" in status
        assert "strategies" in status
        assert status["regime"] == "SIDEWAYS"


class TestStrategyType:
    def test_strategy_type_values(self):
        assert StrategyType.MOMENTUM.value == "momentum"
        assert StrategyType.VALUE.value == "value"
        assert StrategyType.MEAN_REVERSION.value == "mean_reversion"
        assert StrategyType.BREAKOUT.value == "breakout"
        assert StrategyType.COMPOSITE.value == "composite"


class TestTradeSignal:
    def test_trade_signal_creation(self):
        from datetime import datetime
        
        signal = TradeSignal(
            symbol="005930",
            direction="BUY",
            strength=0.8,
            target_price=80000,
            stop_loss_price=72000,
            take_profit_price=85000,
            strategy_name="Momentum",
            reasoning="Strong uptrend with positive RSI",
            max_position_pct=0.10,
            urgency="TODAY",
        )
        
        assert signal.symbol == "005930"
        assert signal.direction == "BUY"
        assert signal.strength == 0.8
        assert signal.strategy_name == "Momentum"

    def test_trade_signal_defaults(self):
        signal = TradeSignal(
            symbol="005930",
            direction="HOLD",
            strength=0.0,
        )
        
        assert signal.target_price is None
        assert signal.stop_loss_price is None
        assert signal.strategy_name == ""
        assert signal.reasoning == ""
        assert signal.max_position_pct == 0.05
        assert signal.urgency == "THIS_WEEK"


class TestInvestmentThesis:
    def test_investment_thesis_creation(self):
        thesis = InvestmentThesis(
            regime="BULL",
            mode="AGGRESSIVE",
            cash_target_pct=0.10,
            sector_allocation={
                "technology": 0.30,
                "finance": 0.20,
            },
            risk_level="HIGH",
        )
        
        assert thesis.regime == "BULL"
        assert thesis.mode == "AGGRESSIVE"
        assert thesis.cash_target_pct == 0.10
        assert thesis.risk_level == "HIGH"

    def test_sector_allocation_bull(self, strategist_agent):
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(strategist_agent.set_investment_direction("BULL"))
        
        allocation = strategist_agent._calculate_sector_allocation("BULL")
        
        assert "technology" in allocation
        assert allocation["technology"] == 0.25
