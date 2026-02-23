"""
KIS AI Trader - Main Entry Point

This is the main entry point for the AI-powered stock trading system.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.event_bus import EventBus
from main_coordinator import MainCoordinator, SystemState


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Global instances
event_bus: EventBus | None = None
coordinator: MainCoordinator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global event_bus, coordinator
    
    settings = get_settings()
    logger.info(f"Starting KIS AI Trader (env: {settings.app.env})")
    
    # Trading universe
    universe = [
        "005930",  # Samsung Electronics
        "000660",  # SK Hynix
        "035420",  # NAVER
        "051910",  # LG Chem
        "006400",  # Samsung SDI
        "035900",  # JYP Ent.
        "012330",  # Myoung Industrial
        "096770",  # SK Innovation
    ]
    
    # Create event bus
    event_bus = EventBus()
    
    # Create coordinator
    coordinator = MainCoordinator(
        event_bus=event_bus,
        universe=universe,
        config={
            "enable_realtime": settings.app.env != "paper",
            "cycle_time": "09:00",
            "auto_start_cycle": True,
            "max_daily_trades": 10,
            "portfolio": {
                "max_position_pct": 0.10,
                "cash_reserve_pct": 0.10,
                "rebalance_threshold": 0.05,
            },
            "cio": {
                "max_daily_trades": 20,
                "max_single_order_value": 10000000,
                "require_manual_review_threshold": 5000000,
            },
        },
    )
    
    # Initialize and start
    await coordinator.initialize()
    await coordinator.start()
    
    logger.info("KIS AI Trader started successfully")
    
    yield
    
    # Shutdown
    if coordinator:
        await coordinator.stop()
    
    logger.info("KIS AI Trader shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="KIS AI Trader",
    description="AI-powered multi-agent stock trading system",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
async def health_check():
    if coordinator:
        status = coordinator.get_status()
        return {
            "status": status.state.value,
            "started_at": status.started_at.isoformat() if status.started_at else None,
            "last_cycle": status.last_cycle.success if status.last_cycle else None,
        }
    return {"status": "initializing"}


# System status
@app.get("/api/v1/system/status")
async def get_system_status():
    if coordinator:
        status = coordinator.get_status()
        return {
            "state": status.state.value,
            "started_at": status.started_at.isoformat() if status.started_at else None,
            "last_cycle": {
                "success": status.last_cycle.success,
                "signals_generated": status.last_cycle.signals_generated,
                "trades_executed": status.last_cycle.trades_executed,
                "duration_seconds": status.last_cycle.duration_seconds,
            } if status.last_cycle else None,
            "errors": status.errors,
        }
    return {"error": "System not initialized"}


# Portfolio status
@app.get("/api/v1/portfolio")
async def get_portfolio():
    if coordinator:
        return coordinator.get_portfolio_status()
    return {"error": "System not initialized"}


# Active signals
@app.get("/api/v1/signals")
async def get_signals():
    if coordinator:
        return {"signals": coordinator.get_active_signals()}
    return {"error": "System not initialized"}


# Trigger daily cycle manually
@app.post("/api/v1/cycle/trigger")
async def trigger_daily_cycle():
    if coordinator:
        status = coordinator.get_status()
        if status.state == SystemState.RUNNING:
            await coordinator.run_daily_cycle()
            return {"message": "Daily cycle triggered"}
        return {"error": "System not running"}
    return {"error": "System not initialized"}


# Trigger emergency stop
@app.post("/api/v1/emergency/stop")
async def trigger_emergency_stop(reason: str = "Manual emergency stop"):
    if coordinator:
        from agents.cio import EmergencyLevel
        await coordinator.trigger_emergency(EmergencyLevel.CRITICAL, reason)
        return {"message": "Emergency stop triggered"}
    return {"error": "System not initialized"}


# Analyze symbol
@app.get("/api/v1/analyze/{symbol}")
async def analyze_symbol(symbol: str):
    if coordinator:
        signal = await coordinator.trigger_signal_generation(symbol)
        if signal:
            return {
                "symbol": symbol,
                "direction": signal.direction,
                "strength": signal.strength,
                "reasoning": signal.reasoning,
            }
        return {"symbol": symbol, "message": "No signal generated"}
    return {"error": "System not initialized"}


# Get account info
@app.get("/api/v1/account")
async def get_account():
    from broker.account import get_account_service
    account = get_account_service()
    portfolio = account.get_portfolio()
    return {
        "total_value": float(portfolio.total_value),
        "cash": float(portfolio.cash),
        "invested": float(portfolio.invested),
    }


# Get price
@app.get("/api/v1/price/{symbol}")
async def get_price(symbol: str):
    from broker.market_data import get_market_data_service
    service = get_market_data_service()
    price = await service.get_current_price(symbol)
    return {"symbol": symbol, "price": float(price)}


# Get OHLCV data
@app.get("/api/v1/ohlcv/{symbol}")
async def get_ohlcv(symbol: str, timeframe: str = "D", days: int = 100):
    from broker.market_data import get_market_data_service
    service = get_market_data_service()
    data = await service.get_ohlcv(symbol, timeframe, days)
    return {
        "symbol": symbol,
        "data": [
            {
                "time": o.time.isoformat(),
                "open": float(o.open),
                "high": float(o.high),
                "low": float(o.low),
                "close": float(o.close),
                "volume": o.volume,
            }
            for o in data
        ],
    }


# Place order
@app.post("/api/v1/orders")
async def place_order(
    symbol: str,
    side: str,
    order_type: str = "MARKET",
    quantity: int = 0,
    price: float | None = None,
):
    from broker.order_executor import get_order_executor
    from core.models import ApprovedOrder, OrderSide, OrderType
    from decimal import Decimal
    
    executor = get_order_executor()
    order = ApprovedOrder(
        symbol=symbol,
        side=OrderSide(side),
        order_type=OrderType(order_type),
        quantity=quantity,
        price=Decimal(str(price)) if price else None,
    )
    
    result = await executor.execute(order)
    return {
        "order_id": str(result.id),
        "status": result.status.value,
        "kis_order_no": result.kis_order_no,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
