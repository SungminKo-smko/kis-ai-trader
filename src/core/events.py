from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class EventTypes:
    MARKET_DATA = "market_data"
    NEWS = "news"
    MACRO_INDICATOR = "macro_indicator"
    FINANCIAL_STATEMENT = "financial_statement"
    ANALYSIS_REPORT = "analysis_report"
    TRADE_SIGNAL = "trade_signal"
    ORDER_PROPOSAL = "order_proposal"
    ORDER_APPROVED = "order_approved"
    ORDER_REJECTED = "order_rejected"
    ORDER_EXECUTED = "order_executed"
    ORDER_FAILED = "order_failed"
    PORTFOLIO_UPDATED = "portfolio_updated"
    CIRCUIT_BREAKER_TRIGGERED = "circuit_breaker_triggered"
    DAILY_CYCLE_START = "daily_cycle_start"
    DAILY_CYCLE_COMPLETE = "daily_cycle_complete"
    EMERGENCY_HALT = "emergency_halt"


class MarketEventType(str, Enum):
    PRICE_UPDATE = "price_update"
    ORDERBOOK_UPDATE = "orderbook_update"
    TRADE_EXECUTION = "trade_execution"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"


class SignalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TradingMode(str, Enum):
    AGGRESSIVE = "AGGRESSIVE"
    NEUTRAL = "NEUTRAL"
    DEFENSIVE = "DEFENSIVE"
    HALT = "HALT"


class MarketRegime(str, Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"
class MarketRegime(str, Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"


# ============================================================================
# Collector Agent Events
# ============================================================================


class CollectorEventType(str, Enum):
    # 실시간 데이터
    PRICE_TICK = "price_tick"              # 실시간 체결가
    ORDERBOOK_SNAPSHOT = "orderbook_snapshot"  # 호가 스냅샷
    
    # 배치 수집
    DAILY_OHLCV = "daily_ohlcv"            # 일봉 데이터
    MINUTE_CANDLES = "minute_candles"      # 분봉 데이터
    
    # 외부 데이터
    FINANCIAL_STATEMENT_UPDATE = "financial_statement_update"  # DART 재무제표
    NEWS_ARTICLE = "news_article"          # 뉴스 기사
    MACRO_INDICATOR_UPDATE = "macro_indicator_update"  # 경제지표
    
    # 시스템
    COLLECTION_STARTED = "collection_started"
    COLLECTION_COMPLETE = "collection_complete"
    COLLECTION_ERROR = "collection_error"
