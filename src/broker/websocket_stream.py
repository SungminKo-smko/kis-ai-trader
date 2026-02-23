import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Callable, Optional

from core.config import get_settings
from core.event_bus import get_event_bus, Event
from core.events import EventTypes, MarketEventType

logger = logging.getLogger("websocket")


class WebSocketClient:
    def __init__(self):
        self._ws = None
        self._running = False
        self._subscriptions: set[str] = set()
        self._reconnect_delay = 1
        self._max_reconnect_delay = 60
        
    async def connect(self):
        import websockets
        
        settings = get_settings()
        ws_url = settings.kis.websocket_url
        
        while self._running:
            try:
                self._ws = await websockets.connect(ws_url)
                self._reconnect_delay = 1
                logger.info("WebSocket connected")
                
                await self._authenticate()
                await self._resubscribe_all()
                
                await self._receive_loop()
                
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)

    async def _authenticate(self):
        from broker.kis_client import get_kis_client
        client = get_kis_client()
        await client.ensure_token()
        
        auth_data = {
            "header": {
                "appkey": "APP_KEY",
                "appsecret": "APP_SECRET",
            }
        }
        await self._ws.send(json.dumps(auth_data))

    async def _resubscribe_all(self):
        for symbol in self._subscriptions:
            await self._subscribe(symbol)

    async def subscribe_price(self, symbol: str):
        self._subscriptions.add(symbol)
        await self._subscribe(symbol)

    async def unsubscribe_price(self, symbol: str):
        self._subscriptions.discard(symbol)
        await self._unsubscribe(symbol)

    async def _subscribe(self, symbol: str):
        if not self._ws:
            return
        
        msg = {
            "mkt_tp": "0",
            "symb": symbol,
            "type": "S",
        }
        await self._ws.send(json.dumps(msg))
        logger.info(f"Subscribed to {symbol}")

    async def _unsubscribe(self, symbol: str):
        if not self._ws:
            return
        
        msg = {
            "mkt_tp": "0",
            "symb": symbol,
            "type": "U",
        }
        await self._ws.send(json.dumps(msg))
        logger.info(f"Unsubscribed from {symbol}")

    async def _receive_loop(self):
        event_bus = get_event_bus()
        
        async for message in self._ws:
            try:
                data = json.loads(message)
                
                if "evt_cd" in data:
                    if data["evt_cd"] == "5001":
                        price_data = self._parse_price(data)
                        event = Event(
                            type=EventTypes.MARKET_DATA,
                            payload=price_data,
                            source="websocket",
                        )
                        await event_bus.publish(event)
                        
            except Exception as e:
                logger.error(f"Error parsing message: {e}")

    def _parse_price(self, data: dict) -> dict:
        return {
            "type": MarketEventType.PRICE_UPDATE,
            "symbol": data.get("symb", ""),
            "price": Decimal(str(data.get("cur_pr", 0))),
            "volume": int(data.get("vol", 0)),
            "timestamp": datetime.now(),
        }

    async def start(self):
        self._running = True
        asyncio.create_task(self.connect())
        logger.info("WebSocket client started")

    async def stop(self):
        self._running = False
        if self._ws:
            await self._ws.close()
        logger.info("WebSocket client stopped")


_websocket_client: Optional[WebSocketClient] = None


def get_websocket_client() -> WebSocketClient:
    global _websocket_client
    if _websocket_client is None:
        _websocket_client = WebSocketClient()
    return _websocket_client
