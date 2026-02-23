import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from broker.kis_client import get_kis_client
from core.models import ApprovedOrder, OrderExecution
from core.events import OrderStatus, EventTypes
from core.event_bus import get_event_bus, Event

logger = logging.getLogger("order_executor")


class OrderExecutor:
    def __init__(self):
        self._client = get_kis_client()
        self._event_bus = get_event_bus()

    async def execute(self, order: ApprovedOrder) -> OrderExecution:
        execution = OrderExecution(
            id=uuid4(),
            order_id=order.id,
            status=OrderStatus.SUBMITTED,
        )
        
        try:
            result = self._client.place_order(
                symbol=order.symbol,
                side=order.side.value,
                order_type=order.order_type.value,
                quantity=order.quantity,
                price=order.price,
            )
            
            execution.kis_order_no = result.get("ODNO", "")
            execution.status = OrderStatus.FILLED
            
            event = Event(
                type=EventTypes.ORDER_EXECUTED,
                payload=execution,
                source="order_executor",
            )
            await self._event_bus.publish(event)
            
            logger.info(f"Order executed: {order.side.value} {order.quantity} {order.symbol}")
            
        except Exception as e:
            execution.status = OrderStatus.FAILED
            execution.rejection_reason = str(e)
            
            event = Event(
                type=EventTypes.ORDER_FAILED,
                payload=execution,
                source="order_executor",
            )
            await self._event_bus.publish(event)
            
            logger.error(f"Order failed: {order.symbol} - {e}")
        
        return execution

    async def cancel(self, order_no: str) -> dict:
        result = self._client.cancel_order(order_no, "")
        return result


_order_executor: Optional[OrderExecutor] = None


def get_order_executor() -> OrderExecutor:
    global _order_executor
    if _order_executor is None:
        _order_executor = OrderExecutor()
    return _order_executor
