"""
KIS 시세 수집기

KIS API를 통해 시세 데이터를 수집합니다.
- 실시간 체결가 (WebSocket)
- 호가 스냅샷 (WebSocket)
- 일봉/분봉 데이터 (REST API)
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

import aiohttp

from agents.collector.agent import BaseCollector, CollectedData, DataSource
from agents.collector.sources.kis_websocket import KISWebSocketManager
from core.event_bus import EventBus
from core.events import CollectorEventType

logger = logging.getLogger("collector.kis")


class KISCollector(BaseCollector):
    """KIS 시세 데이터 수집기"""
    
    def __init__(
        self,
        event_bus: EventBus,
        ws_manager: KISWebSocketManager | None = None,
        rest_api_url: str = "https://openapi.koreainvestment.com:9443",
        paper_url: str = "https://openapi.koreainvestment.com:9443",
    ):
        super().__init__(source=DataSource.KIS, event_bus=event_bus)
        
        self.rest_api_url = rest_api_url
        self.paper_url = paper_url
        self.ws_manager = ws_manager
        
        self._symbols: list[str] = []
        self._running = False
    
    async def collect(self, **kwargs) -> list[CollectedData]:
        """데이터 수집 실행"""
        data_type = kwargs.get("data_type", "tick")
        symbols = kwargs.get("symbols", [])
        
        if not symbols:
            logger.warning("No symbols provided for KIS collection")
            return []
        
        self._symbols = symbols
        
        match data_type:
            case "tick":
                return await self._collect_ticks(symbols)
            case "orderbook":
                return await self._collect_orderbooks(symbols)
            case "daily":
                return await self._collect_daily_ohlcv(symbols)
            case "minute":
                minute = kwargs.get("minute", 1)
                return await self._collect_minute_candles(symbols, minute)
            case _:
                logger.warning(f"Unknown data type: {data_type}")
                return []
    
    async def _collect_ticks(self, symbols: list[str]) -> list[CollectedData]:
        """실시간 체결가 수집"""
        results = []
        
        for symbol in symbols:
            try:
                from broker.kis_client import get_kis_client
                client = get_kis_client()
                
                price = client.get_current_price(symbol)
                
                data = CollectedData(
                    source=DataSource.KIS,
                    data_type="tick",
                    symbol=symbol,
                    timestamp=datetime.now(),
                    payload={
                        "price": str(price),
                        "symbol": symbol,
                    },
                )
                results.append(data)
                
            except Exception as e:
                logger.error(f"Failed to collect tick for {symbol}: {e}")
        
        return results
    
    async def _collect_orderbooks(self, symbols: list[str]) -> list[CollectedData]:
        """호가 스냅샷 수집"""
        results = []
        
        for symbol in symbols:
            try:
                from broker.kis_client import get_kis_client
                client = get_kis_client()
                
                orderbook = client.get_orderbook(symbol)
                
                data = CollectedData(
                    source=DataSource.KIS,
                    data_type="orderbook",
                    symbol=symbol,
                    timestamp=datetime.now(),
                    payload=orderbook,
                )
                results.append(data)
                
            except Exception as e:
                logger.error(f"Failed to collect orderbook for {symbol}: {e}")
        
        return results
    
    async def _collect_daily_ohlcv(
        self,
        symbols: list[str],
        days: int = 30,
    ) -> list[CollectedData]:
        """일봉 데이터 수집"""
        results = []
        
        from datetime import timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        for symbol in symbols:
            try:
                from broker.kis_client import get_kis_client
                client = get_kis_client()
                
                ohlcv = client.get_chart(
                    symbol=symbol,
                    period="D",
                    start=start_date.strftime("%Y%m%d"),
                    end=end_date.strftime("%Y%m%d"),
                    ),
                )
                
                data = CollectedData(
                    source=DataSource.KIS,
                    data_type="daily_ohlcv",
                    symbol=symbol,
                    timestamp=datetime.now(),
                    payload={
                        "candles": ohlcv,
                        "count": len(ohlcv),
                    },
                    metadata={"start_date": start_date.strftime("%Y%m%d"),
                              "end_date": end_date.strftime("%Y%m%d")},
                )
                results.append(data)
                
            except Exception as e:
                logger.error(f"Failed to collect daily OHLCV for {symbol}: {e}")
        
        return results
    
    async def _collect_minute_candles(
        self,
        symbols: list[str],
        minute: int = 1,
    ) -> list[CollectedData]:
        """분봉 데이터 수집"""
        results = []
        
        timeframe_map = {1: "1", 3: "3", 5: "5", 10: "10", 15: "15", 30: "30", 60: "60"}
        tf_code = timeframe_map.get(minute, "1")
        
        for symbol in symbols:
            try:
                from broker.kis_client import get_kis_client
                client = get_kis_client()
                
                ohlcv = client.get_chart(
                    symbol=symbol,
                    period=tf_code,
                    ),
                )
                
                data = CollectedData(
                    source=DataSource.KIS,
                    data_type="minute_candle",
                    symbol=symbol,
                    timestamp=datetime.now(),
                    payload={
                        "candles": ohlcv,
                        "count": len(ohlcv),
                        "timeframe": minute,
                    },
                )
                results.append(data)
                
            except Exception as e:
                logger.error(f"Failed to collect minute candles for {symbol}: {e}")
        
        return results
    
    async def health_check(self) -> bool:
        """KIS API 연결 상태 확인"""
        try:
            from broker.kis_client import get_kis_client
            client = get_kis_client()
            
            if self._symbols:
                client.get_current_price(self._symbols[0])
            
            return True
            
        except Exception as e:
            logger.error(f"KIS health check failed: {e}")
            return False
    
    async def start_websocket(
        self,
        symbols: list[str],
        on_price_update: callable,
        on_orderbook_update: callable | None = None,
    ):
        """WebSocket을 통한 실시간 데이터 스트리밍 시작"""
        if not self.ws_manager:
            logger.warning("WebSocket manager not configured")
            return
        
        self._running = True
        await self.ws_manager.connect()
        
        await self.ws_manager.subscribe_prices(
            symbols=symbols,
            on_update=on_price_update,
        )
        
        if on_orderbook_update:
            await self.ws_manager.subscribe_orderbooks(
                symbols=symbols,
                on_update=on_orderbook_update,
            )
    
    async def stop_websocket(self):
        """WebSocket 스트리밍 중지"""
        self._running = False
        if self.ws_manager:
            await self.ws_manager.disconnect()


class KISWebSocketManager:
    """KIS WebSocket 관리자"""
    
    def __init__(
        self,
        app_key: str,
        app_secret: str,
        is_paper: bool = True,
    ):
        self.app_key = app_key
        self.app_secret = app_secret
        self.is_paper = is_paper
        
        self._ws: aiohttp.ClientWebSocket | None = None
        self._session: aiohttp.ClientSession | None = None
        self._running = False
        self._subscribers: dict[str, set[callable]] = {
            "price": set(),
            "orderbook": set(),
        }
    
    async def connect(self):
        """WebSocket 연결"""
        url = "ws://ops.koreainvestment.com:21000/websocket"
        
        self._session = aiohttp.ClientSession()
        self._ws = await self._session.ws_connect(url)
        self._running = True
        
        asyncio.create_task(self._receive_loop())
    
    async def disconnect(self):
        """WebSocket 연결 해제"""
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._session:
            await self._session.close()
    
    async def subscribe_prices(
        self,
        symbols: list[str],
        on_update: callable,
    ):
        """가격 구독"""
        self._subscribers["price"].add(on_update)
        
        if not self._ws:
            return
        
        for symbol in symbols:
            msg = {
                "m": "subscribe",
                "t": "H0STASP0",
                "o": symbol,
            }
            await self._ws.send_json(msg)
    
    async def subscribe_orderbooks(
        self,
        symbols: list[str],
        on_update: callable,
    ):
        """호가 구독"""
        self._subscribers["orderbook"].add(on_update)
        
        if not self._ws:
            return
        
        for symbol in symbols:
            msg = {
                "m": "subscribe",
                "t": "H0STHP0",
                "o": symbol,
            }
            await self._ws.send_json(msg)
    
    async def _receive_loop(self):
        """수신 루프"""
        while self._running and self._ws:
            try:
                msg = await self._ws.receive()
                
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self._process_message(data)
                    
            except Exception as e:
                logger.error(f"WebSocket receive error: {e}")
                await asyncio.sleep(5)
    
    async def _process_message(self, data: dict):
        """수신 메시지 처리"""
        msg_type = data.get("m", "")
        
        if msg_type == "H0STASP0":  # 실시간 체결가
            for callback in self._subscribers["price"]:
                try:
                    await callback(data)
                except Exception as e:
                    logger.error(f"Price callback error: {e}")
        
        elif msg_type == "H0STHP0":  # 실시간 호가
            for callback in self._subscribers["orderbook"]:
                try:
                    await callback(data)
                except Exception as e:
                    logger.error(f"Orderbook callback error: {e}")
