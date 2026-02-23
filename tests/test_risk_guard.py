"""
Tests for Risk Guard
"""

import pytest
from datetime import datetime

from risk_guard import (
    RiskGuard,
    RiskCheckResult,
    RiskCheckReport,
    DailyLossRecord,
)


@pytest.fixture
def event_bus():
    from core.event_bus import EventBus
    return EventBus()


@pytest.fixture
def risk_guard(event_bus):
    return RiskGuard(
        event_bus=event_bus,
        config={
            "max_position_pct": 0.10,
            "max_single_order_pct": 0.05,
            "max_daily_loss_pct": 0.02,
            "max_daily_trades": 20,
            "min_cash_reserve_pct": 0.10,
            "circuit_breaker_enabled": True,
            "circuit_breaker_loss_pct": 0.05,
        },
    )


class TestRiskGuard:
    def test_risk_guard_creation(self, risk_guard):
        assert risk_guard is not None
        assert risk_guard._circuit_breaker_triggered is False
        assert len(risk_guard._blocked_symbols) == 0

    @pytest.mark.asyncio
    async def test_validate_order_passed(self, risk_guard):
        result = await risk_guard.validate_order(
            symbol="005930",
            direction="BUY",
            quantity=100,
            price=50000,
            portfolio_total=10000000,
            current_positions={},
        )
        
        assert result.result == RiskCheckResult.PASSED
        assert "passed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_validate_order_blocked_symbol(self, risk_guard):
        risk_guard.block_symbol("005930", "Testing block")
        
        result = await risk_guard.validate_order(
            symbol="005930",
            direction="BUY",
            quantity=100,
            price=50000,
            portfolio_total=10000000,
            current_positions={},
        )
        
        assert result.result == RiskCheckResult.BLOCKED

    @pytest.mark.asyncio
    async def test_validate_order_exceeds_position_limit(self, risk_guard):
        result = await risk_guard.validate_order(
            symbol="005930",
            direction="BUY",
            quantity=300,
            price=50000,
            portfolio_total=10000000,
            current_positions={
                "005930": {"market_value": 4000000}
            },
        )
        
        assert result.result == RiskCheckResult.FAILED

    @pytest.mark.asyncio
    async def test_validate_order_exceeds_single_order_limit(self, risk_guard):
        result = await risk_guard.validate_order(
            symbol="005930",
            direction="BUY",
            quantity=200,
            price=50000,
            portfolio_total=10000000,
            current_positions={},
        )
        
        assert result.result == RiskCheckResult.FAILED
        assert "exceeds" in result.message.lower()

    @pytest.mark.asyncio
    async def test_validate_order_cash_reserve_violation(self, risk_guard):
        result = await risk_guard.validate_order(
            symbol="005930",
            direction="BUY",
            quantity=200,
            price=50000,
            portfolio_total=10000000,
            current_positions={
                "000660": {"market_value": 9000000}
            },
        )
        
        assert result.result == RiskCheckResult.FAILED

    @pytest.mark.asyncio
    async def test_circuit_breaker_trigger(self, risk_guard):
        await risk_guard.update_daily_pnl(
            realized_pnl=-600000,
            unrealized_pnl=0,
        )
        
        assert risk_guard._circuit_breaker_triggered is True

    def test_block_symbol(self, risk_guard):
        risk_guard.block_symbol("005930", "Test block")
        
        assert risk_guard.is_symbol_blocked("005930") is True
        
        risk_guard.unblock_symbol("005930")
        
        assert risk_guard.is_symbol_blocked("005930") is False

    def test_get_status(self, risk_guard):
        status = risk_guard.get_status()
        
        assert "circuit_breaker_triggered" in status
        assert "blocked_symbols" in status
        assert "daily_trades" in status
        assert "limits" in status


class TestRiskCheckResult:
    def test_risk_check_result_values(self):
        assert RiskCheckResult.PASSED.value == "PASSED"
        assert RiskCheckResult.FAILED.value == "FAILED"
        assert RiskCheckResult.WARNING.value == "WARNING"
        assert RiskCheckResult.BLOCKED.value == "BLOCKED"


class TestRiskCheckReport:
    def test_risk_check_report_creation(self):
        report = RiskCheckReport(
            check_name="test_check",
            result=RiskCheckResult.PASSED,
            message="Test passed",
            details={"value": 100},
        )
        
        assert report.check_name == "test_check"
        assert report.result == RiskCheckResult.PASSED
        assert report.message == "Test passed"
        assert report.details["value"] == 100

    def test_risk_check_report_defaults(self):
        report = RiskCheckReport(
            check_name="test",
            result=RiskCheckResult.FAILED,
            message="Failed",
        )
        
        assert report.details == {}
        assert report.timestamp is not None


class TestDailyLossRecord:
    def test_daily_loss_record_creation(self):
        record = DailyLossRecord(
            date=datetime.now(),
            realized_pnl=-100000,
            unrealized_pnl=-50000,
            trades_count=5,
        )
        
        assert record.realized_pnl == -100000
        assert record.unrealized_pnl == -50000
        assert record.trades_count == 5

    def test_daily_loss_record_defaults(self):
        record = DailyLossRecord(date=datetime.now())
        
        assert record.realized_pnl == 0
        assert record.unrealized_pnl == 0
        assert record.trades_count == 0


class TestPositionLimits:
    @pytest.mark.asyncio
    async def test_check_position_limits_warning(self, risk_guard):
        positions = {
            "005930": {"market_value": 2000000},
            "000660": {"market_value": 1500000},
        }
        
        reports = await risk_guard.check_position_limits(
            positions=positions,
            portfolio_total=10000000,
        )
        
        assert len(reports) > 0

    @pytest.mark.asyncio
    async def test_check_position_limits_ok(self, risk_guard):
        positions = {
            "005930": {"market_value": 500000},
        }
        
        reports = await risk_guard.check_position_limits(
            positions=positions,
            portfolio_total=10000000,
        )
        
        assert len(reports) == 0
