from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal
import logging

try:
    import pykis
    from pykis import KIS, Order, Market, Crypto
    from pykis.api.market import KISMarket
    from pykis.api.order import KISOrder
    from pykis.types import OrderType, OrderSide, TimeInForce
    PYKIS_AVAILABLE = True
except ImportError:
    PYKIS_AVAILABLE = False

from core.config import get_settings, get_kis_credentials

logger = logging.getLogger("kis_client")


class KISClient:
    def __init__(self):
        if not PYKIS_AVAILABLE:
            raise ImportError("pykis not installed. Run: pip install pykis")
        
        creds = get_kis_credentials()
        settings = get_settings()
        
        self._kis = KIS(
            appkey=creds.app_key,
            appsecret=creds.app_secret,
            account_no=creds.account_no,
            is_paper=(settings.app.env == "paper"),
        )
        self._is_paper = settings.app.env == "paper"
        self._token_expires: Optional[datetime] = None
        logger.info(f"KIS Client initialized (paper={self._is_paper})")

    async def ensure_token(self):
        if self._token_expires and datetime.now() < self._token_expires:
            return
        
        self._kis.get_token()
        self._token_expires = datetime.now() + timedelta(hours=23)
        logger.info("KIS token refreshed")

    def get_account_info(self) -> dict:
        self._kis.get_token()
        return self._kis.Account.account_info()

    def get_balance(self) -> dict:
        self._kis.get_token()
        return self._kis.Account.balance()

    def get_today_orders(self) -> list[dict]:
        self._kis.get_token()
        return self._kis.Account.today_orders()

    def get_today_executions(self) -> list[dict]:
        self._kis.get_token()
        return self._kis.Account.today_executions()

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "D",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        self._kis.get_token()
        market = Market(self._kis)
        return market.ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    def get_current_price(self, symbol: str) -> Decimal:
        self._kis.get_token()
        market = Market(self._kis)
        price = market.current_price(symbol)
        return Decimal(str(price))

    def get_orderbook(self, symbol: str) -> dict:
        self._kis.get_token()
        market = Market(self._kis)
        return market.orderbook(symbol)

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: int,
        price: Optional[Decimal] = None,
        order_type_detail: str = "0",
    ) -> dict:
        self._kis.get_token()
        
        side_map = {"BUY": "buy", "SELL": "sell"}
        type_map = {
            "MARKET": "01",
            "LIMIT": "00",
            "STOP_LIMIT": "03",
        }
        
        order = Order(
            symbol=symbol,
            side=side_map.get(side, "buy"),
            order_type_code=type_map.get(order_type, "01"),
            order_type_detail=order_type_detail,
            quantity=quantity,
            price=str(price) if price else None,
        )
        
        result = self._kis.Order.order(order)
        logger.info(f"Order placed: {side} {quantity} {symbol} @ {price}")
        return result

    def cancel_order(self, order_no: str, order_id: str) -> dict:
        self._kis.get_token()
        return self._kis.Order.cancel(order_no, order_id)

    def modify_order(
        self,
        order_no: str,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[Decimal] = None,
    ) -> dict:
        self._kis.get_token()
        return self._kis.Order.modify(order_no, order_id, quantity, str(price) if price else None)

    def get_order_detail(self, order_no: str) -> dict:
        self._kis.get_token()
        return self._kis.Order.detail(order_no)


_kis_client: Optional[KISClient] = None


def get_kis_client() -> KISClient:
    global _kis_client
    if _kis_client is None:
        _kis_client = KISClient()
    return _kis_client
