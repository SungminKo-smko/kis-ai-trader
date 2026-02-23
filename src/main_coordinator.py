"""
Main Coordinator - Trading System Orchestrator

The Main Coordinator is the heart of the AI trading system.
It orchestrates all agents and manages the trading lifecycle.

Responsibilities:
- Agent lifecycle management (start/stop)
- Event routing between agents
- Daily trading cycle execution
- Error handling and recovery
- System health monitoring
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from core.event_bus import Event, EventBus
from core.events import EventTypes

from agents.collector import CollectorAgent, create_collector_agent
from agents.analyst import AnalystAgent
from agents.strategist import StrategistAgent, StrategyType
from agents.strategist.strategies.composite import CompositeStrategy
from agents.portfolio import PortfolioManager
from agents.cio import CIOAgent, EmergencyLevel


logger = logging.getLogger("main_coordinator")


class SystemState(str, Enum):
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    ERROR = "ERROR"


@dataclass
class CycleResult:
    cycle_type: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float = 0.0
    success: bool = False
    error_message: str = ""
    trades_executed: int = 0
    signals_generated: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemStatus:
    state: SystemState
    started_at: datetime | None = None
    last_cycle: CycleResult | None = None
    agents_running: dict[str, bool] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class MainCoordinator:
    """
    Main Coordinator - AI Trading System Orchestrator
    
    This is the central nervous system of the trading bot.
    It coordinates all agents and manages the trading lifecycle.
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        universe: list[str],
        config: dict[str, Any] | None = None,
    ):
        self.event_bus = event_bus
        self.universe = universe
        self.config = config or {}
        
        # System state
        self._state = SystemState.INITIALIZING
        self._started_at: datetime | None = None
        self._last_cycle_result: CycleResult | None = None
        self._errors: list[str] = []
        
        # Agents
        self.collector: CollectorAgent | None = None
        self.analyst: AnalystAgent | None = None
        self.strategist: StrategistAgent | None = None
        self.portfolio_manager: PortfolioManager | None = None
        self.cio: CIOAgent | None = None
        
        # Subscriptions
        self._event_subscriptions: dict[str, list[callable]] = {}
        self._running = False
        self._cycle_task: asyncio.Task | None = None
    
    async def initialize(self):
        """Initialize all agents"""
        logger.info("Initializing Main Coordinator...")
        self._state = SystemState.INITIALIZING
        
        try:
            # Create agents
            self.collector = create_collector_agent(
                event_bus=self.event_bus,
                universe=self.universe,
                enable_realtime=self.config.get("enable_realtime", True),
            )
            
            self.analyst = AnalystAgent(
                event_bus=self.event_bus,
                config=self.config.get("analyst", {}),
            )
            
            self.strategist = StrategistAgent(
                event_bus=self.event_bus,
                config=self.config.get("strategist", {}),
            )
            self.strategist.register_strategy(
                StrategyType.COMPOSITE,
                CompositeStrategy(),
            )
            
            self.portfolio_manager = PortfolioManager(
                event_bus=self.event_bus,
                config=self.config.get("portfolio", {}),
            )
            
            self.cio = CIOAgent(
                event_bus=self.event_bus,
                config=self.config.get("cio", {}),
            )
            
            # Subscribe to events
            self._subscribe_events()
            
            logger.info("Main Coordinator initialized successfully")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            self._state = SystemState.ERROR
            self._errors.append(str(e))
            raise
    
    def _subscribe_events(self):
        """Subscribe to events from other agents"""
        
        # Collector -> Analyst
        async def on_price_tick(event: Event):
            if self.analyst and self._state == SystemState.RUNNING:
                symbol = event.payload.get("symbol")
                if symbol:
                    await self.analyst.analyze_symbol(symbol)
        
        # Analyst -> Strategist
        async def on_analysis_report(event: Event):
            if self.strategist and self._state == SystemState.RUNNING:
                report = event.payload
                if hasattr(report, "symbol"):
                    await self.strategist.generate_signal(
                        {"symbol": report.symbol, "technical": {}, "fundamental": {}, "sentiment": {}}
                    )
        
        # Strategist -> Portfolio Manager
        async def on_trade_signal(event: Event):
            if self.portfolio_manager and self._state == SystemState.RUNNING:
                signal = event.payload
                proposals = await self.portfolio_manager.generate_order_proposals([signal])
                for proposal in proposals[:3]:
                    if self.cio:
                        decision = await self.cio.review_order(proposal)
                        if decision.status.value == "APPROVED":
                            await self.portfolio_manager.execute_order(proposal)
        
        # Subscribe to EventBus
        self.event_bus.subscribe(EventTypes.PRICE_TICK.value, on_price_tick)
        self.event_bus.subscribe(EventTypes.ANALYSIS_REPORT.value, on_analysis_report)
        self.event_bus.subscribe(EventTypes.TRADE_SIGNAL.value, on_trade_signal)
    
    async def start(self):
        """Start the trading system"""
        if self._state == SystemState.RUNNING:
            logger.warning("System already running")
            return
        
        logger.info("Starting AI Trading System...")
        self._started_at = datetime.now()
        self._running = True
        
        try:
            # Start all agents
            if self.collector:
                await self.collector.start()
            
            if self.analyst:
                await self.analyst.start()
            
            if self.strategist:
                await self.strategist.start()
            
            if self.portfolio_manager:
                await self.portfolio_manager.start()
            
            if self.cio:
                await self.cio.start()
            
            self._state = SystemState.RUNNING
            
            # Start daily cycle if configured
            if self.config.get("auto_start_cycle", True):
                self._cycle_task = asyncio.create_task(self._run_daily_cycle_loop())
            
            logger.info("AI Trading System started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start system: {e}", exc_info=True)
            self._state = SystemState.ERROR
            self._errors.append(str(e))
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the trading system"""
        logger.info("Stopping AI Trading System...")
        self._state = SystemState.STOPPING
        self._running = False
        
        # Stop cycle task
        if self._cycle_task:
            self._cycle_task.cancel()
            try:
                await self._cycle_task
            except asyncio.CancelledError:
                pass
        
        # Stop all agents
        if self.cio:
            await self.cio.stop()
        
        if self.portfolio_manager:
            await self.portfolio_manager.stop()
        
        if self.strategist:
            await self.strategist.stop()
        
        if self.analyst:
            await self.analyst.stop()
        
        if self.collector:
            await self.collector.stop()
        
        self._state = SystemState.INITIALIZING
        logger.info("AI Trading System stopped")
    
    async def _run_daily_cycle_loop(self):
        """Run daily trading cycles"""
        while self._running and self._state == SystemState.RUNNING:
            try:
                now = datetime.now()
                
                # Run cycle at market open (9:00) or custom time
                cycle_time = self.config.get("cycle_time", "09:00")
                hour, minute = map(int, cycle_time.split(":"))
                
                next_cycle = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if now.hour >= hour:
                    next_cycle = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    from datetime import timedelta
                    next_cycle += timedelta(days=1)
                
                wait_seconds = (next_cycle - now).total_seconds()
                
                logger.info(f"Next daily cycle in {wait_seconds/3600:.1f} hours")
                await asyncio.sleep(wait_seconds)
                
                if self._running:
                    await self.run_daily_cycle()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Daily cycle loop error: {e}", exc_info=True)
                self._errors.append(str(e))
                await asyncio.sleep(60)
    
    async def run_daily_cycle(self):
        """Execute a complete daily trading cycle"""
        cycle_result = CycleResult(
            cycle_type="DAILY",
            started_at=datetime.now(),
        )
        
        logger.info("Starting daily trading cycle...")
        
        try:
            # Step 1: Start daily cycle in CIO
            if self.cio:
                await self.cio.start_daily_cycle()
            
            # Step 2: Collect data
            if self.collector:
                for symbol in self.universe:
                    await self.collector.trigger_collection(
                        source="kis",
                        symbols=[symbol],
                        data_type="daily",
                    )
                cycle_result.metadata["collection_complete"] = True
            
            # Step 3: Analyze all symbols
            signals_generated = 0
            if self.analyst and self.strategist:
                for symbol in self.universe:
                    report = await self.analyst.analyze_symbol(symbol)
                    signal = await self.strategist.generate_signal(
                        {"symbol": symbol, "technical": {}, "fundamental": {}, "sentiment": {}}
                    )
                    if signal and signal.direction != "HOLD":
                        signals_generated += 1
            
            cycle_result.signals_generated = signals_generated
            
            # Step 4: Generate order proposals
            if self.strategist and self.portfolio_manager:
                active_signals = list(self.strategist.get_active_signals().values())
                proposals = await self.portfolio_manager.generate_order_proposals(
                    active_signals
                )
                
                # Step 5: Review and execute orders
                trades_executed = 0
                for proposal in proposals[:self.config.get("max_daily_trades", 10)]:
                    if self.cio:
                        decision = await self.cio.review_order(proposal)
                        if decision.status.value == "APPROVED":
                            await self.portfolio_manager.execute_order(proposal)
                            trades_executed += 1
                
                cycle_result.trades_executed = trades_executed
            
            # Step 6: End daily cycle
            if self.cio:
                await self.cio.end_daily_cycle()
            
            # Step 7: Rebalance if needed
            if self.portfolio_manager:
                rebalance_proposals = await self.portfolio_manager.rebalance()
                for proposal in rebalance_proposals[:5]:
                    if self.cio:
                        decision = await self.cio.review_order(proposal)
                        if decision.status.value == "APPROVED":
                            await self.portfolio_manager.execute_order(proposal)
            
            cycle_result.success = True
            cycle_result.completed_at = datetime.now()
            cycle_result.duration_seconds = (
                cycle_result.completed_at - cycle_result.started_at
            ).total_seconds()
            
            logger.info(
                f"Daily cycle completed: {signals_generated} signals, "
                f"{cycle_result.trades_executed} trades, "
                f"{cycle_result.duration_seconds:.1f}s"
            )
            
        except Exception as e:
            logger.error(f"Daily cycle failed: {e}", exc_info=True)
            cycle_result.success = False
            cycle_result.error_message = str(e)
            cycle_result.completed_at = datetime.now()
            self._errors.append(f"Cycle error: {e}")
        
        self._last_cycle_result = cycle_result
    
    async def trigger_signal_generation(self, symbol: str):
        """Manually trigger signal generation for a symbol"""
        if self._state != SystemState.RUNNING:
            logger.warning("System not running")
            return None
        
        try:
            # Analyze
            if self.analyst:
                report = await self.analyst.analyze_symbol(symbol)
            
            # Generate signal
            if self.strategist:
                signal = await self.strategist.generate_signal(
                    {"symbol": symbol, "technical": {}, "fundamental": {}, "sentiment": {}}
                )
                return signal
            
            return None
            
        except Exception as e:
            logger.error(f"Signal generation failed: {e}")
            self._errors.append(str(e))
            return None
    
    async def trigger_emergency(self, level: EmergencyLevel, reason: str):
        """Trigger emergency mode"""
        logger.warning(f"Emergency triggered: {level.value} - {reason}")
        
        if self.cio:
            await self.cio.set_emergency(level, reason)
        
        if level == EmergencyLevel.CRITICAL:
            await self.stop()
    
    def get_status(self) -> SystemStatus:
        """Get current system status"""
        return SystemStatus(
            state=self._state,
            started_at=self._started_at,
            last_cycle=self._last_cycle_result,
            agents_running={
                "collector": self.collector is not None,
                "analyst": self.analyst is not None,
                "strategist": self.strategist is not None,
                "portfolio_manager": self.portfolio_manager is not None,
                "cio": self.cio is not None,
            },
            errors=self._errors[-10:],
        )
    
    def get_portfolio_status(self) -> dict[str, Any]:
        """Get portfolio status"""
        if self.portfolio_manager:
            portfolio = self.portfolio_manager.get_portfolio()
            return {
                "total_value": portfolio.total_value,
                "cash": portfolio.cash,
                "positions": len(portfolio.positions),
                "positions_detail": [
                    {
                        "symbol": p.symbol,
                        "quantity": p.quantity,
                        "market_value": p.market_value,
                        "weight": p.weight,
                    }
                    for p in portfolio.positions.values()
                ],
            }
        return {}
    
    def get_active_signals(self) -> list[dict]:
        """Get all active trade signals"""
        if self.strategist:
            signals = self.strategist.get_active_signals()
            return [
                {
                    "symbol": s.symbol,
                    "direction": s.direction,
                    "strength": s.strength,
                    "reasoning": s.reasoning,
                }
                for s in signals.values()
            ]
        return []
