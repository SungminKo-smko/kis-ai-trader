"""
Collector Agent Factory

Collector Agent 및 각 수집기들을 쉽게 초기화할 수 있는 유틸리티입니다.
"""

from __future__ import annotations

from typing import Any

from core.config import get_settings
from core.event_bus import EventBus

from agents.collector.agent import (
    CollectorAgent,
    CollectionTask,
    DataSource,
    create_default_tasks,
)
from agents.collector.sources.kis_source import KISCollector, KISWebSocketManager
from agents.collector.sources.dart_source import DARTCollector
from agents.collector.sources.news_source import NewsCollector
from agents.collector.sources.macro_source import BOKCollector, FREDCollector


def create_collector_agent(
    event_bus: EventBus,
    universe: list[str],
    enable_realtime: bool = True,
) -> CollectorAgent:
    """Collector Agent 생성 및 설정"""
    
    settings = get_settings()
    agent = CollectorAgent(event_bus=event_bus)
    
    # KIS 수집기 등록
    ws_manager = None
    if enable_realtime:
        creds = settings.kis
        ws_manager = KISWebSocketManager(
            app_key=creds.app_key,
            app_secret=creds.app_secret,
            is_paper=settings.app.env == "paper",
        )
    
    kis_collector = KISCollector(
        event_bus=event_bus,
        ws_manager=ws_manager,
    )
    agent.register_collector(kis_collector)
    
    # DART 수집기 등록
    dart_collector = DARTCollector(
        event_bus=event_bus,
        api_key=settings.dart.api_key,
    )
    agent.register_collector(dart_collector)
    
    # 뉴스 수집기 등록
    news_collector = NewsCollector(event_bus=event_bus)
    agent.register_collector(news_collector)
    
    # BOK 수집기 등록
    bok_collector = BOKCollector(
        event_bus=event_bus,
        api_key=settings.bok.api_key,
    )
    agent.register_collector(bok_collector)
    
    # FRED 수집기 등록
    fred_collector = FREDCollector(
        event_bus=event_bus,
        api_key=settings.fred.api_key,
    )
    agent.register_collector(fred_collector)
    
    # 기본 수집 작업 등록
    tasks = create_default_tasks(universe)
    for task in tasks:
        agent.register_task(task)
    
    return agent


def get_collector_status(agent: CollectorAgent) -> dict[str, Any]:
    """Collector Agent 상태 조회"""
    return agent.get_status()
