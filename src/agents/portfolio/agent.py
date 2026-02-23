"""
Portfolio Manager Agent - Portfolio Management Agent

Portfolio Manager Agent is in charge of managing the portfolio,
including position sizing, rebalancing, risk management, and more.

Role:
- Position sizing based on signals and risk
- Portfolio rebalancing
- Risk management (max position, sector limits)
- Order proposal generation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from core.event_bus import Event, EventBus
from core.events import EventTypes


logger = logging.getLogger("portfolio_manager")


class RebalanceTrigger(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    SIGNAL = "signal"
    THRESHOLD = "threshold"
    EMERGENCY = "emergency"


@dataclass
class Position:
    symbol: str
    quantity: int = 0
    avg_price: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    weight: float = 0.0


@dataclass
class Portfolio:
    total_value: float = 0.0
    cash: float = 0.0
    positions: dict[str, Position] = field(default_factory=dict)
    last_rebalance: datetime | None = None


@dataclass
class OrderProposal:
    symbol: str
    direction: str
    quantity: int
    price: float | None = None
    order_type: str = "MARKET"
    reason: str = ""
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class PortfolioManager:
    def __init__(
        self,
        event_bus: EventBus,
        config: dict[str, Any] | None = None,
    ):
        self.event_bus = event_bus
        self.config = config or {}
        
        self._running = False
        self._portfolio = Portfolio()
        self._max_position_pct = self.config.get("max_position_pct", 0.10)
        self._max_sector_pct = self.config.get("max_sector_pct", 0.30)
        self._cash_reserve_pct = self.config.get("cash_reserve_pct", 0.10)
        self._rebalance_threshold = self.config.get("rebalance_threshold", 0.05)
    
    async def start(self):
        self._running = True
        await self._load_portfolio()
        logger.info("Portfolio Manager started")
        
        await self.event_bus.publish(Event(
            type=EventTypes.PORTFOLIO_UPDATED,
            payload={"message": "Portfolio Manager started"},
            source="portfolio_manager",
        ))
    
    async def stop(self):
        self._running = False
        await self._save_portfolio()
        logger.info("Portfolio Manager stopped")
    
    async def update_positions(self, prices: dict[str, float]):
        for symbol, price in prices.items():
            if symbol in self._portfolio.positions:
                pos = self._portfolio.positions[symbol]
                pos.current_price = price
                pos.market_value = pos.quantity * price
                pos.unrealized_pnl = (price - pos.avg_price) * pos.quantity
        
        self._update_portfolio_value()
    
    def _update_portfolio_value(self):
        total_market_value = sum(p.market_value for p in self._portfolio.positions.values())
        self._portfolio.total_value = self._portfolio.cash + total_market_value
        
        for pos in self._portfolio.positions.values():
            if self._portfolio.total_value > 0:
                pos.weight = pos.market_value / self._portfolio.total_value
    
    async def generate_order_proposals(
        self,
        signals: list,
        available_cash: float | None = None,
    ) -> list[OrderProposal]:
        proposals = []
        
        if available_cash:
            self._portfolio.cash = available_cash
            self._update_portfolio_value()
        
        for signal in signals:
            proposal = await self._evaluate_signal(signal)
            if proposal:
                proposals.append(proposal)
        
        proposals = self._rank_proposals(proposals)
        
        return proposals
    
    async def _evaluate_signal(self, signal) -> OrderProposal | None:
        symbol = signal.symbol
        direction = signal.direction
        strength = signal.strength
        
        if direction == "HOLD":
            return None
        
        current_position = self._portfolio.positions.get(symbol)
        
        if direction == "BUY":
            return await self._evaluate_buy(signal, current_position)
        elif direction == "SELL":
            return await self._evaluate_sell(signal, current_position)
        
        return None
    
    async def _evaluate_buy(self, signal, current_position) -> OrderProposal | None:
        symbol = signal.symbol
        strength = signal.strength
        
        current_weight = 0.0
        if current_position:
            current_weight = current_position.weight
        
        max_new_weight = self._max_position_pct
        
        if current_weight >= max_new_weight:
            return None
        
        available_weight = max_new_weight - current_weight
        
        target_value = self._portfolio.total_value * available_weight * strength
        
        target_value = min(target_value, self._portfolio.cash * 0.8)
        
        if target_value < 10000:
            return None
        
        from broker.kis_client import get_kis_client
        try:
            client = get_kis_client()
            price = float(client.get_current_price(symbol))
        except:
            price = signal.target_price or 50000
        
        quantity = int(target_value / price)
        quantity = quantity - (quantity % 10)
        
        if quantity <= 0:
            return None
        
        return OrderProposal(
            symbol=symbol,
            direction="BUY",
            quantity=quantity,
            price=price,
            reason=f"Buy signal: {signal.strategy_name}",
            priority=int(strength * 10),
            metadata={
                "strategy": signal.strategy_name,
                "target_price": signal.target_price,
                "stop_loss": signal.stop_loss_price,
            },
        )
    
    async def _evaluate_sell(self, signal, current_position) -> OrderProposal | None:
        if not current_position or current_position.quantity == 0:
            return None
        
        if current_position.unrealized_pnl < 0 and signal.strength < 0.8:
            return None
        
        quantity = int(current_position.quantity * signal.strength)
        quantity = quantity - (quantity % 10)
        
        if quantity < 10:
            return None
        
        from broker.kis_client import get_kis_client
        try:
            client = get_kis_client()
            price = float(client.get_current_price(signal.symbol))
        except:
            price = signal.target_price or current_position.current_price
        
        return OrderProposal(
            symbol=signal.symbol,
            direction="SELL",
            quantity=quantity,
            price=price,
            reason=f"Sell signal: {signal.strategy_name}",
            priority=int(signal.strength * 10),
            metadata={
                "strategy": signal.strategy_name,
                "unrealized_pnl": current_position.unrealized_pnl,
            },
        )
    
    def _rank_proposals(self, proposals: list[OrderProposal]) -> list[OrderProposal]:
        return sorted(proposals, key=lambda p: p.priority, reverse=True)
    
    async def rebalance(self) -> list[OrderProposal]:
        proposals = []
        
        for symbol, position in self._portfolio.positions.items():
            target_weight = self._max_position_pct * 0.5
            diff = position.weight - target_weight
            
            if abs(diff) > self._rebalance_threshold and diff > 0:
                quantity = int(position.quantity * diff * 0.5)
                quantity = quantity - (quantity % 10)
                
                if quantity >= 10:
                    proposals.append(OrderProposal(
                        symbol=symbol,
                        direction="SELL",
                        quantity=quantity,
                        reason="Rebalance: reduce position",
                        priority=5,
                    ))
        
        return proposals
    
    def check_risk_limits(self, proposal: OrderProposal) -> tuple[bool, str]:
        if proposal.direction == "BUY":
            position = self._portfolio.positions.get(proposal.symbol)
            current_weight = position.weight if position else 0.0
            
            new_value = proposal.quantity * (proposal.price or 0)
            new_weight = new_value / self._portfolio.total_value if self._portfolio.total_value > 0 else 0
            
            if current_weight + new_weight > self._max_position_pct:
                return False, "Exceeds max position limit"
        
        total_equity = self._portfolio.cash + sum(
            p.market_value for p in self._portfolio.positions.values()
        )
        
        if self._portfolio.cash < total_equity * self._cash_reserve_pct:
            return False, "Cash reserve below minimum"
        
        return True, "OK"
    
    async def execute_order(self, order: OrderProposal):
        if order.direction == "BUY":
            cost = order.quantity * (order.price or 0)
            if cost <= self._portfolio.cash:
                self._portfolio.cash -= cost
                
                if order.symbol in self._portfolio.positions:
                    pos = self._portfolio.positions[order.symbol]
                    total_cost = pos.avg_price * pos.quantity + cost
                    pos.quantity += order.quantity
                    pos.avg_price = total_cost / pos.quantity if pos.quantity > 0 else 0
                else:
                    self._portfolio.positions[order.symbol] = Position(
                        symbol=order.symbol,
                        quantity=order.quantity,
                        avg_price=order.price or 0,
                        current_price=order.price or 0,
                        market_value=order.quantity * (order.price or 0),
                    )
        
        elif order.direction == "SELL":
            position = self._portfolio.positions.get(order.symbol)
            if position and position.quantity >= order.quantity:
                proceeds = order.quantity * (order.price or 0)
                self._portfolio.cash += proceeds
                position.quantity -= order.quantity
                
                if position.quantity == 0:
                    del self._portfolio.positions[order.symbol]
        
        self._update_portfolio_value()
    
    async def _load_portfolio(self):
        pass
    
    async def _save_portfolio(self):
        pass
    
    def get_portfolio(self) -> Portfolio:
        return self._portfolio
    
    def get_position(self, symbol: str) -> Position | None:
        return self._portfolio.positions.get(symbol)
    
    def get_status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "total_value": self._portfolio.total_value,
            "cash": self._portfolio.cash,
            "positions": len(self._portfolio.positions),
            "max_position_pct": self._max_position_pct,
        }
