"""
Tests for Portfolio Manager Agent
"""

import pytest
from unittest.mock import MagicMock

from agents.portfolio.agent import (
    PortfolioManager,
    Portfolio,
    Position,
    OrderProposal,
    RebalanceTrigger,
)
from core.event_bus import EventBus


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def portfolio_manager(event_bus):
    return PortfolioManager(event_bus=event_bus)


class TestPortfolioManager:
    @pytest.mark.asyncio
    async def test_portfolio_manager_creation(self, portfolio_manager):
        assert portfolio_manager is not None
        assert portfolio_manager._running is False
        assert portfolio_manager._portfolio.cash == 0
        assert len(portfolio_manager._portfolio.positions) == 0

    @pytest.mark.asyncio
    async def test_start_and_stop(self, portfolio_manager):
        await portfolio_manager.start()
        assert portfolio_manager._running is True
        
        await portfolio_manager.stop()
        assert portfolio_manager._running is False

    @pytest.mark.asyncio
    async def test_get_portfolio(self, portfolio_manager):
        portfolio = portfolio_manager.get_portfolio()
        
        assert isinstance(portfolio, Portfolio)
        assert portfolio.total_value == 0
        assert portfolio.cash == 0

    @pytest.mark.asyncio
    async def test_get_position_not_found(self, portfolio_manager):
        position = portfolio_manager.get_position("005930")
        assert position is None

    @pytest.mark.asyncio
    async def test_get_status(self, portfolio_manager):
        status = portfolio_manager.get_status()
        
        assert "running" in status
        assert "total_value" in status
        assert "cash" in status
        assert "positions" in status


class TestPortfolio:
    def test_portfolio_creation(self):
        portfolio = Portfolio(
            total_value=10000000,
            cash=5000000,
        )
        
        assert portfolio.total_value == 10000000
        assert portfolio.cash == 5000000
        assert portfolio.positions == {}
        assert portfolio.last_rebalance is None

    def test_portfolio_defaults(self):
        portfolio = Portfolio()
        
        assert portfolio.total_value == 0
        assert portfolio.cash == 0
        assert portfolio.positions == {}


class TestPosition:
    def test_position_creation(self):
        position = Position(
            symbol="005930",
            quantity=100,
            avg_price=75000,
            current_price=80000,
            market_value=8000000,
            unrealized_pnl=500000,
            weight=0.40,
        )
        
        assert position.symbol == "005930"
        assert position.quantity == 100
        assert position.avg_price == 75000
        assert position.current_price == 80000
        assert position.market_value == 8000000
        assert position.unrealized_pnl == 500000

    def test_position_defaults(self):
        position = Position(symbol="005930")
        
        assert position.symbol == "005930"
        assert position.quantity == 0
        assert position.avg_price == 0
        assert position.current_price == 0
        assert position.market_value == 0


class TestOrderProposal:
    def test_order_proposal_creation(self):
        proposal = OrderProposal(
            symbol="005930",
            direction="BUY",
            quantity=100,
            price=75000,
            order_type="LIMIT",
            reason="Momentum signal",
            priority=8,
        )
        
        assert proposal.symbol == "005930"
        assert proposal.direction == "BUY"
        assert proposal.quantity == 100
        assert proposal.price == 75000
        assert proposal.order_type == "LIMIT"
        assert proposal.priority == 8

    def test_order_proposal_defaults(self):
        proposal = OrderProposal(
            symbol="005930",
            direction="SELL",
            quantity=50,
        )
        
        assert proposal.price is None
        assert proposal.order_type == "MARKET"
        assert proposal.reason == ""
        assert proposal.priority == 0


class TestRebalanceTrigger:
    def test_rebalance_trigger_values(self):
        assert RebalanceTrigger.DAILY.value == "daily"
        assert RebalanceTrigger.WEEKLY.value == "weekly"
        assert RebalanceTrigger.SIGNAL.value == "signal"
        assert RebalanceTrigger.THRESHOLD.value == "threshold"
        assert RebalanceTrigger.EMERGENCY.value == "emergency"


class TestPortfolioOperations:
    @pytest.mark.asyncio
    async def test_execute_buy_order(self, portfolio_manager):
        portfolio_manager._portfolio.cash = 10000000
        
        proposal = OrderProposal(
            symbol="005930",
            direction="BUY",
            quantity=100,
            price=50000,
        )
        
        await portfolio_manager.execute_order(proposal)
        
        assert "005930" in portfolio_manager._portfolio.positions
        assert portfolio_manager._portfolio.cash == 5000000

    @pytest.mark.asyncio
    async def test_execute_sell_order(self, portfolio_manager):
        portfolio_manager._portfolio.cash = 5000000
        portfolio_manager._portfolio.positions["005930"] = Position(
            symbol="005930",
            quantity=100,
            avg_price=50000,
            current_price=55000,
            market_value=5500000,
        )
        
        proposal = OrderProposal(
            symbol="005930",
            direction="SELL",
            quantity=50,
            price=55000,
        )
        
        await portfolio_manager.execute_order(proposal)
        
        assert portfolio_manager._portfolio.positions["005930"].quantity == 50
        assert portfolio_manager._portfolio.cash == 7750000

    @pytest.mark.asyncio
    async def test_check_risk_limits_pass(self, portfolio_manager):
        portfolio_manager._portfolio.total_value = 10000000
        portfolio_manager._portfolio.cash = 5000000
        
        proposal = OrderProposal(
            symbol="005930",
            direction="BUY",
            quantity=100,
            price=50000,
        )
        
        passed, message = portfolio_manager.check_risk_limits(proposal)
        
        assert passed is True
        assert message == "OK"

    @pytest.mark.asyncio
    async def test_check_risk_limits_cash_reserve(self, portfolio_manager):
        portfolio_manager._portfolio.total_value = 10000000
        portfolio_manager._portfolio.cash = 500000
        portfolio_manager._portfolio.positions["005930"] = Position(
            symbol="005930",
            quantity=100,
            avg_price=50000,
            current_price=50000,
            market_value=5000000,
        )
        
        proposal = OrderProposal(
            symbol="005930",
            direction="BUY",
            quantity=100,
            price=50000,
        )
        
        passed, message = portfolio_manager.check_risk_limits(proposal)
        
        assert passed is False
        assert "Cash reserve" in message
