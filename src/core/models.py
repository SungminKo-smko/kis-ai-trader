from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from core.events import (
    OrderSide,
    OrderStatus,
    OrderType,
    SignalDirection,
    TimeInForce,
    MarketRegime,
)


@dataclass
class OHLCV:
    time: datetime
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    timeframe: str


@dataclass
class TickData:
    time: datetime
    symbol: str
    price: Decimal
    volume: int
    side: str


@dataclass
class OrderbookLevel:
    price: Decimal
    size: int


@dataclass
class OrderbookSnapshot:
    time: datetime
    symbol: str
    bid_prices: list[Decimal]
    bid_sizes: list[int]
    ask_prices: list[Decimal]
    ask_sizes: list[int]


@dataclass
class TradeSignal:
    id: UUID = field(default_factory=uuid4)
    symbol: str = ""
    direction: SignalDirection = SignalDirection.HOLD
    strength: float = 0.0
    target_price: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = None
    strategy_name: str = ""
    reasoning: str = ""
    max_position_pct: float = 0.0
    urgency: str = "THIS_WEEK"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class OrderProposal:
    id: UUID = field(default_factory=uuid4)
    signal_id: UUID = field(default_factory=uuid4)
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: int = 0
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    split_count: int = 1
    time_in_force: TimeInForce = TimeInForce.DAY
    reasoning: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ApprovedOrder:
    id: UUID = field(default_factory=uuid4)
    proposal_id: UUID = field(default_factory=uuid4)
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: int = 0
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    approved_at: datetime = field(default_factory=datetime.now)


@dataclass
class OrderExecution:
    id: UUID = field(default_factory=uuid4)
    order_id: UUID = field(default_factory=uuid4)
    status: OrderStatus = OrderStatus.SUBMITTED
    kis_order_no: Optional[str] = None
    filled_quantity: int = 0
    filled_price: Optional[Decimal] = None
    rejection_reason: Optional[str] = None
    executed_at: Optional[datetime] = None


@dataclass
class Holding:
    symbol: str
    name: str
    quantity: int
    avg_price: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_pct: float


@dataclass
class Portfolio:
    total_value: Decimal
    cash: Decimal
    invested: Decimal
    daily_pnl: Decimal
    daily_pnl_pct: float
    holdings: list[Holding] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class AnalysisReport:
    id: UUID = field(default_factory=uuid4)
    symbol: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    technical_score: float = 0.0
    fundamental_score: float = 0.0
    sentiment_score: float = 0.0
    regime: MarketRegime = MarketRegime.SIDEWAYS
    overall_signal: SignalDirection = SignalDirection.HOLD
    confidence: float = 0.0
    details: dict = field(default_factory=dict)


@dataclass
class NewsArticle:
    id: UUID = field(default_factory=uuid4)
    symbol: Optional[str] = None
    source: str = ""
    title: str = ""
    content: str = ""
    url: str = ""
    sentiment_score: float = 0.0
    published_at: Optional[datetime] = None
    analyzed_at: datetime = field(default_factory=datetime.now)


@dataclass
class MacroIndicator:
    indicator_name: str
    value: float
    previous_value: float
    change_pct: float
    unit: str
    date: datetime


@dataclass
class FinancialStatement:
    corp_code: str
    corp_name: str
    report_date: str
    revenue: Decimal
    operating_income: Decimal
    net_income: Decimal
    total_assets: Decimal
    total_equity: Decimal
    debt_ratio: float
    roe: float
    per: float
    pbr: float
