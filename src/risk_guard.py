"""
Risk Guard - Risk Validation Gateway

Risk Guard is a critical safety component that validates all orders
and trading activities against predefined risk parameters.

Responsibilities:
- Pre-trade risk validation
- Position limit checks
- Daily loss limit monitoring
- Volatility-based position sizing
- Emergency circuit breaker triggers
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from core.event_bus import Event, EventBus
from core.events import EventTypes


logger = logging.getLogger("risk_guard")


class RiskCheckResult(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


@dataclass
class RiskLimit:
    name: str
    value: float
    enabled: bool = True


@dataclass
class RiskCheckReport:
    check_name: str
    result: RiskCheckResult
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DailyLossRecord:
    date: datetime
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    trades_count: int = 0


class RiskGuard:
    """
    Risk Guard - Risk Validation Gateway
    
    Validates all orders and trading activities against risk parameters.
    Acts as a gatekeeper before any order reaches the broker.
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        config: dict[str, Any] | None = None,
    ):
        self.event_bus = event_bus
        self.config = config or {}
        
        # Risk limits
        self._max_position_pct = self.config.get("max_position_pct", 0.10)
        self._max_sector_pct = self.config.get("max_sector_pct", 0.30)
        self._max_single_order_pct = self.config.get("max_single_order_pct", 0.05)
        self._max_daily_loss_pct = self.config.get("max_daily_loss_pct", 0.02)
        self._max_daily_trades = self.config.get("max_daily_trades", 20)
        self._min_cash_reserve_pct = self.config.get("min_cash_reserve_pct", 0.10)
        
        # Circuit breaker
        self._circuit_breaker_enabled = self.config.get("circuit_breaker_enabled", True)
        self._circuit_breaker_loss_pct = self.config.get("circuit_breaker_loss_pct", 0.05)
        self._circuit_breaker_cooldown_minutes = self.config.get("circuit_breaker_cooldown_minutes", 60)
        
        # State
        self._daily_loss_record = DailyLossRecord(date=datetime.now())
        self._circuit_breaker_triggered = False
        self._circuit_breaker_triggered_at: datetime | None = None
        self._blocked_symbols: set[str] = set()
        
        # Event subscriptions
        self._event_subscriptions = []
    
    async def initialize(self):
        """Initialize Risk Guard"""
        logger.info("Risk Guard initialized")
        
        # Subscribe to events
        await self.event_bus.subscribe(EventTypes.ORDER_APPROVED, self._on_order_approved)
        await self.event_bus.subscribe(EventTypes.DAILY_CYCLE_COMPLETE, self._on_daily_cycle_complete)
    
    # =========================================================================
    # Pre-Trade Risk Checks
    # =========================================================================
    
    async def validate_order(
        self,
        symbol: str,
        direction: str,
        quantity: int,
        price: float,
        portfolio_total: float,
        current_positions: dict[str, Any],
    ) -> RiskCheckReport:
        """Validate an order before execution"""
        
        check_name = "pre_trade_validation"
        order_value = quantity * price
        
        # Check 1: Circuit breaker
        if self._circuit_breaker_triggered:
            return RiskCheckReport(
                check_name=check_name,
                result=RiskCheckResult.BLOCKED,
                message="Circuit breaker triggered - trading disabled",
                details={"circuit_breaker_triggered_at": self._circuit_breaker_triggered_at},
            )
        
        # Check 2: Blocked symbol
        if symbol in self._blocked_symbols:
            return RiskCheckReport(
                check_name=check_name,
                result=RiskCheckResult.BLOCKED,
                message=f"Symbol {symbol} is blocked",
                details={"blocked_symbols": list(self._blocked_symbols)},
            )
        
        # Check 3: Order value vs portfolio
        order_pct = order_value / portfolio_total if portfolio_total > 0 else 0
        if order_pct > self._max_single_order_pct:
            return RiskCheckReport(
                check_name=check_name,
                result=RiskCheckResult.FAILED,
                message=f"Order value {order_pct:.2%} exceeds max {self._max_single_order_pct:.2%}",
                details={"order_pct": order_pct, "max_pct": self._max_single_order_pct},
            )
        
        # Check 4: Position limit
        if direction == "BUY":
            current_position = current_positions.get(symbol, {})
            current_value = current_position.get("market_value", 0)
            new_value = current_value + order_value
            new_pct = new_value / portfolio_total if portfolio_total > 0 else 0
            
            if new_pct > self._max_position_pct:
                return RiskCheckReport(
                    check_name=check_name,
                    result=RiskCheckResult.FAILED,
                    message=f"Position would be {new_pct:.2%}, exceeds max {self._max_position_pct:.2%}",
                    details={"new_position_pct": new_pct, "max_pct": self._max_position_pct},
                )
        
        # Check 5: Daily trade limit
        if self._daily_loss_record.trades_count >= self._max_daily_trades:
            return RiskCheckReport(
                check_name=check_name,
                result=RiskCheckResult.FAILED,
                message=f"Daily trade limit reached ({self._daily_loss_record.trades_count})",
                details={"trades_count": self._daily_loss_record.trades_count},
            )
        
        # Check 6: Cash reserve
        if direction == "BUY":
            cash_reserve = portfolio_total * self._min_cash_reserve_pct
            available_cash = portfolio_total - sum(
                p.get("market_value", 0) for p in current_positions.values()
            )
            
            if available_cash - order_value < cash_reserve:
                return RiskCheckReport(
                    check_name=check_name,
                    result=RiskCheckResult.FAILED,
                    message="Order would violate cash reserve requirement",
                    details={
                        "available_cash": available_cash,
                        "order_value": order_value,
                        "required_reserve": cash_reserve,
                    },
                )
        
        # Check 7: Daily loss limit
        total_loss = self._daily_loss_record.realized_pnl + self._daily_loss_record.unrealized_pnl
        loss_pct = abs(total_loss) / portfolio_total if portfolio_total > 0 else 0
        
        if total_loss < 0 and loss_pct > self._max_daily_loss_pct:
            return RiskCheckReport(
                check_name=check_name,
                result=RiskCheckResult.BLOCKED,
                message=f"Daily loss {loss_pct:.2%} exceeds max {self._max_daily_loss_pct:.2%}",
                details={"loss_pct": loss_pct, "max_loss_pct": self._max_daily_loss_pct},
            )
        
        # All checks passed
        return RiskCheckReport(
            check_name=check_name,
            result=RiskCheckResult.PASSED,
            message="All risk checks passed",
            details={
                "order_value": order_value,
                "order_pct": order_pct,
                "trades_today": self._daily_loss_record.trades_count,
            },
        )
    
    # =========================================================================
    # Position Risk Checks
    # =========================================================================
    
    async def check_position_limits(
        self,
        positions: dict[str, Any],
        portfolio_total: float,
    ) -> list[RiskCheckReport]:
        """Check all positions against limits"""
        
        reports = []
        
        for symbol, position in positions.items():
            market_value = position.get("market_value", 0)
            weight = market_value / portfolio_total if portfolio_total > 0 else 0
            
            if weight > self._max_position_pct:
                reports.append(RiskCheckReport(
                    check_name="position_limit",
                    result=RiskCheckResult.WARNING,
                    message=f"Position {symbol} at {weight:.2%} exceeds limit",
                    details={"symbol": symbol, "weight": weight},
                ))
        
        return reports
    
    # =========================================================================
    # Loss Monitoring
    # =========================================================================
    
    async def update_daily_pnl(
        self,
        realized_pnl: float = 0,
        unrealized_pnl: float = 0,
    ):
        """Update daily PnL and circuit breaker"""
        
        # Reset if new day
        if self._daily_loss_record.date.date() != datetime.now().date():
            self._daily_loss_record = DailyLossRecord(date=datetime.now())
        
        self._daily_loss_record.realized_pnl += realized_pnl
        self._daily_loss_record.unrealized_pnl = unrealized_pnl
        self._daily_loss_record.trades_count += 1
        
        # Check circuit breaker
        if self._circuit_breaker_enabled:
            total_pnl = self._daily_loss_record.realized_pnl + unrealized_pnl
            loss_pct = abs(total_pnl) / 1000000  # Approximate portfolio value
            
            if total_pnl < 0 and loss_pct >= self._circuit_breaker_loss_pct:
                await self._trigger_circuit_breaker(
                    f"Daily loss {loss_pct:.2%} exceeds threshold"
                )
    
    async def _trigger_circuit_breaker(self, reason: str):
        """Trigger circuit breaker"""
        
        self._circuit_breaker_triggered = True
        self._circuit_breaker_triggered_at = datetime.now()
        
        logger.warning(f"CIRCUIT BREAKER TRIGGERED: {reason}")
        
        # Publish event
        await self.event_bus.publish(Event(
            type=EventTypes.CIRCUIT_BREAKER_TRIGGERED,
            payload={
                "reason": reason,
                "triggered_at": self._circuit_breaker_triggered_at.isoformat(),
                "cooldown_minutes": self._circuit_breaker_cooldown_minutes,
            },
            source="risk_guard",
        ))
    
    async def reset_circuit_breaker(self):
        """Reset circuit breaker after cooldown"""
        
        if self._circuit_breaker_triggered:
            if self._circuit_breaker_triggered_at:
                elapsed = datetime.now() - self._circuit_breaker_triggered_at
                if elapsed >= timedelta(minutes=self._circuit_breaker_cooldown_minutes):
                    self._circuit_breaker_triggered = False
                    self._circuit_breaker_triggered_at = None
                    logger.info("Circuit breaker reset")
    
    # =========================================================================
    # Symbol Management
    # =========================================================================
    
    def block_symbol(self, symbol: str, reason: str = ""):
        """Block a symbol from trading"""
        self._blocked_symbols.add(symbol)
        logger.warning(f"Symbol {symbol} blocked: {reason}")
    
    def unblock_symbol(self, symbol: str):
        """Unblock a symbol"""
        self._blocked_symbols.discard(symbol)
        logger.info(f"Symbol {symbol} unblocked")
    
    def is_symbol_blocked(self, symbol: str) -> bool:
        """Check if symbol is blocked"""
        return symbol in self._blocked_symbols
    
    # =========================================================================
    # Event Handlers
    # =========================================================================
    
    async def _on_order_approved(self, event: Event):
        """Handle order approved event"""
        logger.debug(f"Order approved: {event.payload}")
    
    async def _on_daily_cycle_complete(self, event: Event):
        """Handle daily cycle complete"""
        # Reset daily counters
        self._daily_loss_record = DailyLossRecord(date=datetime.now())
        logger.info("Daily loss record reset")
    
    # =========================================================================
    # Status
    # =========================================================================
    
    def get_status(self) -> dict[str, Any]:
        """Get Risk Guard status"""
        return {
            "circuit_breaker_triggered": self._circuit_breaker_triggered,
            "circuit_breaker_triggered_at": (
                self._circuit_breaker_triggered_at.isoformat()
                if self._circuit_breaker_triggered_at else None
            ),
            "blocked_symbols": list(self._blocked_symbols),
            "daily_trades": self._daily_loss_record.trades_count,
            "daily_realized_pnl": self._daily_loss_record.realized_pnl,
            "daily_unrealized_pnl": self._daily_loss_record.unrealized_pnl,
            "limits": {
                "max_position_pct": self._max_position_pct,
                "max_single_order_pct": self._max_single_order_pct,
                "max_daily_loss_pct": self._max_daily_loss_pct,
                "max_daily_trades": self._max_daily_trades,
            },
        }
