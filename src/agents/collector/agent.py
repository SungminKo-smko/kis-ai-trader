"""
Collector Agent - 정보수집 에이전트

모든 외부 데이터 수집, 정규화, 저장을 담당하는 에이전트입니다.

수집 대상:
- KIS 시세 데이터 (실시간 체결가, 호가, 일봉, 분봉)
- DART 재무제표
- 뉴스 데이터 (네이버금융, 한국경제 등)
- 경제지표 (한국은행, FRED)
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from core.event_bus import Event, EventBus
from core.events import CollectorEventType


logger = logging.getLogger(__name__)


class CollectionFrequency(str, Enum):
    REALTIME = "realtime"
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    HOURLY = "1h"
    DAILY = "1d"
    WEEKLY = "1w"


class DataSource(str, Enum):
    KIS = "kis"
    DART = "dart"
    NAVER_NEWS = "naver_news"
    BOK = "bok"
    FRED = "fred"


@dataclass
class CollectionTask:
    id: str
    source: DataSource
    frequency: CollectionFrequency
    symbols: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    last_run: datetime | None = None
    next_run: datetime | None = None


@dataclass
class CollectedData:
    source: DataSource
    data_type: str
    symbol: str | None
    timestamp: datetime
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseCollector(ABC):
    def __init__(self, source: DataSource, event_bus: EventBus):
        self.source = source
        self.event_bus = event_bus
        self._running = False
    
    @abstractmethod
    async def collect(self, **kwargs) -> list[CollectedData]:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass
    
    async def publish_event(self, event_type: CollectorEventType, data: CollectedData):
        event = Event(
            type=event_type.value,
            payload=data,
            source=f"collector:{self.source.value}",
            timestamp=datetime.now(),
        )
        await self.event_bus.publish(event)
    
    async def start(self):
        self._running = True
        logger.info(f"[{self.source.value}] Collector started")
    
    async def stop(self):
        self._running = False
        logger.info(f"[{self.source.value}] Collector stopped")


class CollectorAgent:
    def __init__(self, event_bus: EventBus, config: dict[str, Any] | None = None):
        self.event_bus = event_bus
        self.config = config or {}
        
        self._collectors: dict[DataSource, BaseCollector] = {}
        self._tasks: dict[str, CollectionTask] = {}
        self._running = False
        self._scheduler_task: asyncio.Task | None = None
        self._on_collection_complete: Callable | None = None
    
    def register_collector(self, collector: BaseCollector):
        self._collectors[collector.source] = collector
        logger.info(f"Registered collector: {collector.source.value}")
    
    def register_task(self, task: CollectionTask):
        self._tasks[task.id] = task
        logger.info(f"Registered collection task: {task.id} ({task.frequency.value})")
    
    def remove_task(self, task_id: str):
        self._tasks.pop(task_id, None)
        logger.info(f"Removed collection task: {task_id}")
    
    async def start(self):
        self._running = True
        
        for collector in self._collectors.values():
            await collector.start()
        
        self._scheduler_task = asyncio.create_task(self._run_scheduler())
        
        logger.info("Collector Agent started")
        
        await self.event_bus.publish(Event(
            type=CollectorEventType.COLLECTION_STARTED.value,
            payload={"message": "Collector Agent started"},
            source="collector_agent",
        ))
    
    async def stop(self):
        self._running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        for collector in self._collectors.values():
            await collector.stop()
        
        logger.info("Collector Agent stopped")
        
        await self.event_bus.publish(Event(
            type=CollectorEventType.COLLECTION_COMPLETE.value,
            payload={"message": "Collector Agent stopped"},
            source="collector_agent",
        ))
    
    async def trigger_collection(self, source: DataSource, **kwargs) -> list[CollectedData]:
        collector = self._collectors.get(source)
        if not collector:
            raise ValueError(f"No collector registered for {source}")
        
        if not await collector.health_check():
            await self.event_bus.publish(Event(
                type=CollectorEventType.COLLECTION_ERROR.value,
                payload={"source": source.value, "error": "Health check failed"},
                source="collector_agent",
            ))
            return []
        
        data = await collector.collect(**kwargs)
        
        for item in data:
            event_type = self._get_event_type_for_data(item)
            await collector.publish_event(event_type, item)
        
        return data
    
    def _get_event_type_for_data(self, data: CollectedData) -> CollectorEventType:
        if data.source == DataSource.KIS:
            if data.data_type == "tick":
                return CollectorEventType.PRICE_TICK
            elif data.data_type == "orderbook":
                return CollectorEventType.ORDERBOOK_SNAPSHOT
            elif data.data_type == "daily_ohlcv":
                return CollectorEventType.DAILY_OHLCV
            elif data.data_type == "minute_candle":
                return CollectorEventType.MINUTE_CANDLES
        elif data.source == DataSource.DART:
            return CollectorEventType.FINANCIAL_STATEMENT_UPDATE
        elif data.source == DataSource.NAVER_NEWS:
            return CollectorEventType.NEWS_ARTICLE
        elif data.source in (DataSource.BOK, DataSource.FRED):
            return CollectorEventType.MACRO_INDICATOR_UPDATE
        
        return CollectorEventType.DAILY_OHLCV
    
    async def _run_scheduler(self):
        while self._running:
            try:
                now = datetime.now()
                
                for task_id, task in self._tasks.items():
                    if not task.enabled:
                        continue
                    
                    if task.next_run and now >= task.next_run:
                        await self._execute_task(task)
                        
                        task.last_run = now
                        task.next_run = self._calculate_next_run(task.frequency)
                
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)
                await asyncio.sleep(60)
    
    async def _execute_task(self, task: CollectionTask):
        collector = self._collectors.get(task.source)
        if not collector:
            logger.warning(f"No collector for task {task.id}")
            return
        
        try:
            logger.info(f"Executing collection task: {task.id}")
            
            params = {"symbols": task.symbols, **task.params}
            
            data = await collector.collect(**params)
            
            for item in data:
                event_type = self._get_event_type_for_data(item)
                await collector.publish_event(event_type, item)
            
            if self._on_collection_complete:
                await self._on_collection_complete(task, data)
                
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}", exc_info=True)
            await self.event_bus.publish(Event(
                type=CollectorEventType.COLLECTION_ERROR.value,
                payload={"task_id": task.id, "error": str(e)},
                source="collector_agent",
            ))
    
    def _calculate_next_run(self, frequency: CollectionFrequency) -> datetime:
        now = datetime.now()
        
        match frequency:
            case CollectionFrequency.MINUTE_1:
                return now + timedelta(minutes=1)
            case CollectionFrequency.MINUTE_5:
                return now + timedelta(minutes=5)
            case CollectionFrequency.MINUTE_15:
                return now + timedelta(minutes=15)
            case CollectionFrequency.HOURLY:
                return now + timedelta(hours=1)
            case CollectionFrequency.DAILY:
                next_run = now.replace(hour=15, minute=40, second=0, microsecond=0)
                if now.hour >= 15:
                    next_run += timedelta(days=1)
                return next_run
            case CollectionFrequency.WEEKLY:
                days_until_monday = (7 - now.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7
                return (now + timedelta(days=days_until_monday)).replace(
                    hour=9, minute=0, second=0, microsecond=0
                )
            case _:
                return now + timedelta(hours=1)
    
    def get_status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "collectors": list(self._collectors.keys()),
            "tasks": {
                tid: {
                    "source": t.source.value,
                    "frequency": t.frequency.value,
                    "enabled": t.enabled,
                    "last_run": t.last_run.isoformat() if t.last_run else None,
                    "next_run": t.next_run.isoformat() if t.next_run else None,
                }
                for tid, t in self._tasks.items()
            },
        }
    
    def set_on_collection_complete(self, callback: Callable):
        self._on_collection_complete = callback


def create_default_tasks(universe: list[str]) -> list[CollectionTask]:
    tasks = [
        CollectionTask(
            id="realtime_prices",
            source=DataSource.KIS,
            frequency=CollectionFrequency.REALTIME,
            symbols=universe,
            params={"data_type": "tick"},
        ),
        CollectionTask(
            id="minute_candles_1m",
            source=DataSource.KIS,
            frequency=CollectionFrequency.MINUTE_1,
            symbols=universe,
            params={"data_type": "minute", "minute": 1},
        ),
        CollectionTask(
            id="daily_ohlcv",
            source=DataSource.KIS,
            frequency=CollectionFrequency.DAILY,
            symbols=universe,
            params={"data_type": "daily"},
        ),
        CollectionTask(
            id="dart_financials",
            source=DataSource.DART,
            frequency=CollectionFrequency.WEEKLY,
            symbols=universe,
        ),
        CollectionTask(
            id="news",
            source=DataSource.NAVER_NEWS,
            frequency=CollectionFrequency.HOURLY,
            symbols=universe,
        ),
        CollectionTask(
            id="bok_indicators",
            source=DataSource.BOK,
            frequency=CollectionFrequency.DAILY,
        ),
        CollectionTask(
            id="fred_indicators",
            source=DataSource.FRED,
            frequency=CollectionFrequency.DAILY,
        ),
    ]
    
    return tasks
