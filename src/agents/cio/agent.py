"""
CIO Agent - Chief Investment Officer Agent

The CIO Agent is the supreme decision-maker in the trading system.
This agent is in charge of final decision-making, order approval, emergency response, and more.

Role:
- Final decision making on all orders
- Order approval and rejection
- Emergency response (circuit breaker, market panic)
- System-wide risk management
- Daily cycle management
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from core.event_bus import Event, EventBus
from core.events import EventTypes


logger = logging.getLogger("cio_agent")


class ApprovalStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class EmergencyLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class OrderDecision:
    proposal_id: str
    status: ApprovalStatus
    approved_quantity: int | None = None
    approved_price: float | None = None
    reason: str = ""
    conditions: list[str] = field(default_factory=list)
    reviewed_at: datetime = field(default_factory=datetime.now)


@dataclass
class DailyPlan:
    date: datetime
    target_trades: int = 0
    approved_orders: list[OrderDecision] = field(default_factory=list)
    rejected_orders: list[OrderDecision] = field(default_factory=list)
    total_buy_value: float = 0.0
    total_sell_value: float = 0.0


class CIOAgent:
    def __init__(
        self,
        event_bus: EventBus,
        config: dict[str, Any] | None = None,
    ):
        self.event_bus = event_bus
        self.config = config or {}
        
        self._running = False
        self._emergency_level = EmergencyLevel.NONE
        self._daily_plan: DailyPlan | None = None
        self._order_history: list[OrderDecision] = []
        self._max_daily_trades = self.config.get("max_daily_trades", 20)
        self._max_single_order_value = self.config.get("max_single_order_value", 10000000)
        self._require_manual_review_threshold = self.config.get("require_manual_review_threshold", 5000000)
    
    async def start(self):
        self._running = True
        self._emergency_level = EmergencyLevel.NONE
        
        logger.info("CIO Agent started")
        
        await self.event_bus.publish(Event(
            type=EventTypes.ORDER_APPROVED,
            payload={"message": "CIO Agent started"},
            source="cio_agent",
        ))
    
    async def stop(self):
        self._running = False
        logger.info("CIO Agent stopped")
    
    async def start_daily_cycle(self, date: datetime | None = None):
        if date is None:
            date = datetime.now()
        
        self._daily_plan = DailyPlan(date=date)
        
        logger.info(f"Daily cycle started: {date.strftime('%Y-%m-%d')}")
        
        await self.event_bus.publish(Event(
            type=EventTypes.DAILY_CYCLE_START,
            payload={"date": date.isoformat()},
            source="cio_agent",
        ))
    
    async def end_daily_cycle(self):
        if self._daily_plan:
            logger.info(f"Daily cycle ended. Trades: {len(self._daily_plan.approved_orders)}")
            
            await self.event_bus.publish(Event(
                type=EventTypes.DAILY_CYCLE_COMPLETE,
                payload={
                    "date": self._daily_plan.date.isoformat(),
                    "total_trades": len(self._daily_plan.approved_orders),
                    "buy_value": self._daily_plan.total_buy_value,
                    "sell_value": self._daily_plan.total_sell_value,
                },
                source="cio_agent",
            ))
            
            self._daily_plan = None
    
    async def review_order(self, proposal) -> OrderDecision:
        proposal_id = f"{proposal.symbol}_{proposal.direction}_{datetime.now().timestamp()}"
        
        if self._emergency_level == EmergencyLevel.CRITICAL:
            return OrderDecision(
                proposal_id=proposal_id,
                status=ApprovalStatus.REJECTED,
                reason="System in critical emergency mode",
            )
        
        if self._daily_plan and len(self._daily_plan.approved_orders) >= self._max_daily_trades:
            return OrderDecision(
                proposal_id=proposal_id,
                status=ApprovalStatus.REJECTED,
                reason="Maximum daily trades limit reached",
            )
        
        order_value = proposal.quantity * (proposal.price or 0)
        
        if order_value > self._max_single_order_value:
            return OrderDecision(
                proposal_id=proposal_id,
                status=ApprovalStatus.REQUIRES_REVIEW,
                reason=f"Order value {order_value} exceeds maximum",
                conditions=["Manual approval required"],
            )
        
        if order_value > self._require_manual_review_threshold:
            return OrderDecision(
                proposal_id=proposal_id,
                status=ApprovalStatus.PENDING,
                reason="Order requires manual review",
                conditions=["Awaiting manual approval"],
            )
        
        risk_check = await self._check_risk(proposal, order_value)
        if not risk_check[0]:
            return OrderDecision(
                proposal_id=proposal_id,
                status=ApprovalStatus.REJECTED,
                reason=risk_check[1],
            )
        
        decision = OrderDecision(
            proposal_id=proposal_id,
            status=ApprovalStatus.APPROVED,
            approved_quantity=proposal.quantity,
            approved_price=proposal.price,
            reason="Approved by automated system",
        )
        
        if self._daily_plan:
            self._daily_plan.approved_orders.append(decision)
            
            if proposal.direction == "BUY":
                self._daily_plan.total_buy_value += order_value
            else:
                self._daily_plan.total_sell_value += order_value
        
        self._order_history.append(decision)
        
        await self._publish_decision(decision, proposal)
        
        return decision
    
    async def _check_risk(self, proposal, order_value: float) -> tuple[bool, str]:
        if self._emergency_level in (EmergencyLevel.HIGH, EmergencyLevel.CRITICAL):
            if proposal.direction == "BUY":
                return False, "Buying not allowed during high emergency"
        
        if order_value > self._max_single_order_value:
            return False, "Exceeds maximum order value"
        
        return True, "OK"
    
    async def _publish_decision(self, decision: OrderDecision, proposal):
        event_type = EventTypes.ORDER_APPROVED if decision.status == ApprovalStatus.APPROVED else EventTypes.ORDER_REJECTED
        
        await self.event_bus.publish(Event(
            type=event_type,
            payload={
                "decision": decision,
                "proposal": proposal,
            },
            source="cio_agent",
        ))
    
    async def set_emergency(self, level: EmergencyLevel, reason: str = ""):
        old_level = self._emergency_level
        self._emergency_level = level
        
        logger.warning(f"Emergency level changed: {old_level} -> {level}. Reason: {reason}")
        
        await self.event_bus.publish(Event(
            type=EventTypes.EMERGENCY_HALT if level == EmergencyLevel.CRITICAL else EventTypes.CIRCUIT_BREAKER_TRIGGERED,
            payload={
                "level": level.value,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            },
            source="cio_agent",
        ))
        
        if level == EmergencyLevel.CRITICAL:
            await self._handle_critical_emergency()
    
    async def _handle_critical_emergency(self):
        logger.critical("Critical emergency: halting all trading operations")
        
        await self.event_bus.publish(Event(
            type=EventTypes.EMERGENCY_HALT,
            payload={"message": "All trading halted due to critical emergency"},
            source="cio_agent",
        ))
    
    async def trigger_circuit_breaker(self, reason: str):
        if self._emergency_level == EmergencyLevel.NONE:
            await self.set_emergency(EmergencyLevel.MEDIUM, reason)
    
    def get_daily_plan(self) -> DailyPlan | None:
        return self._daily_plan
    
    def get_order_history(self, limit: int = 100) -> list[OrderDecision]:
        return self._order_history[-limit:]
    
    def get_emergency_level(self) -> EmergencyLevel:
        return self._emergency_level
    
    def get_status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "emergency_level": self._emergency_level.value,
            "daily_trades": len(self._daily_plan.approved_orders) if self._daily_plan else 0,
            "total_order_history": len(self._order_history),
            "max_daily_trades": self._max_daily_trades,
        }
