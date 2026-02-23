from datetime import datetime
from decimal import Decimal
from typing import Optional
import logging

from broker.kis_client import get_kis_client
from core.models import OHLCV, OrderbookSnapshot

logger = logging.getLogger("market_data")


class MarketDataService:
    def __init__(self):
        self._client = get_kis_client()

    async def get_current_price(self, symbol: str) -> Decimal:
        return self._client.get_current_price(symbol)

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "D",
        days: int = 100,
    ) -> list[OHLCV]:
        end_date = datetime.now()
        start_date = end_date.replace(day=end_date.day - days)
        
        data = self._client.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date.strftime("%Y%m%d"),
            limit=days,
        )
        
        ohlcvs = []
        for item in data:
            ohlcvs.append(OHLCV(
                time=datetime.strptime(item.get("stk_cd_mkt_dt", ""), "%Y%m%d"),
                symbol=item.get("stk_cd", ""),
                open=Decimal(str(item.get("oprc", 0))),
                high=Decimal(str(item.get("hgpr", 0))),
                low=Decimal(str(item.get("lwpr", 0))),
                close=Decimal(str(item.get("clpr", 0))),
                volume=int(item.get("vol", 0)),
                timeframe=timeframe,
            ))
        
        return ohlcvs

    async def get_minute_candles(
        self,
        symbol: str,
        minutes: int = 1,
        count: int = 100,
    ) -> list[OHLCV]:
        timeframe_map = {1: "1", 3: "3", 5: "5", 10: "10", 15: "15", 30: "30", 60: "60"}
        tf = timeframe_map.get(minutes, "1")
        
        data = self._client.get_ohlcv(
            symbol=symbol,
            timeframe=tf,
            limit=count,
        )
        
        ohlcvs = []
        for item in data:
            ohlcvs.append(OHLCV(
                time=datetime.strptime(
                    f"{item.get('stk_cd_mkt_dt', '')} {item.get('stk_cd_mkt_tm', '')}",
                    "%Y%m%d %H%M%S"
                ),
                symbol=item.get("stk_cd", ""),
                open=Decimal(str(item.get("oprc", 0))),
                high=Decimal(str(item.get("hgpr", 0))),
                low=Decimal(str(item.get("lwpr", 0))),
                close=Decimal(str(item.get("clpr", 0))),
                volume=int(item.get("vol", 0)),
                timeframe=f"{minutes}m",
            ))
        
        return ohlcvs

    async def get_orderbook(self, symbol: str) -> OrderbookSnapshot:
        data = self._client.get_orderbook(symbol)
        
        bid_prices, bid_sizes = [], []
        ask_prices, ask_sizes = [], []
        
        for i in range(1, 6):
            bid_prices.append(Decimal(str(data.get(f"bid_p{i}", 0))))
            bid_sizes.append(int(data.get(f"bid_q{i}", 0)))
            ask_prices.append(Decimal(str(data.get(f"ask_p{i}", 0))))
            ask_sizes.append(int(data.get(f"ask_q{i}", 0)))
        
        return OrderbookSnapshot(
            time=datetime.now(),
            symbol=symbol,
            bid_prices=bid_prices,
            bid_sizes=bid_sizes,
            ask_prices=ask_prices,
            ask_sizes=ask_sizes,
        )


_market_data_service: Optional[MarketDataService] = None


def get_market_data_service() -> MarketDataService:
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService()
    return _market_data_service
