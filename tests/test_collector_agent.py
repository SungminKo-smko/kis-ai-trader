"""
Tests for Collector Agent
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents.collector.agent import (
    CollectorAgent,
    CollectionTask,
    CollectedData,
    DataSource,
    CollectionFrequency,
)
from core.event_bus import EventBus


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def collector_agent(event_bus):
    return CollectorAgent(event_bus=event_bus)


class TestCollectorAgent:
    @pytest.mark.asyncio
    async def test_collector_agent_creation(self, collector_agent):
        assert collector_agent is not None
        assert collector_agent._running is False
        assert len(collector_agent._collectors) == 0
        assert len(collector_agent._tasks) == 0

    @pytest.mark.asyncio
    async def test_register_collector(self, collector_agent):
        mock_collector = MagicMock()
        mock_collector.source = DataSource.KIS
        
        collector_agent.register_collector(mock_collector)
        
        assert DataSource.KIS in collector_agent._collectors
        mock_collector.start.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_task(self, collector_agent):
        task = CollectionTask(
            id="test_task",
            source=DataSource.KIS,
            frequency=CollectionFrequency.DAILY,
            symbols=["005930"],
        )
        
        collector_agent.register_task(task)
        
        assert "test_task" in collector_agent._tasks
        assert collector_agent._tasks["test_task"].id == "test_task"

    @pytest.mark.asyncio
    async def test_remove_task(self, collector_agent):
        task = CollectionTask(
            id="test_task",
            source=DataSource.KIS,
            frequency=CollectionFrequency.DAILY,
        )
        
        collector_agent.register_task(task)
        collector_agent.remove_task("test_task")
        
        assert "test_task" not in collector_agent._tasks

    @pytest.mark.asyncio
    async def test_start_and_stop(self, collector_agent):
        mock_collector = MagicMock()
        mock_collector.source = DataSource.KIS
        collector_agent.register_collector(mock_collector)
        
        await collector_agent.start()
        
        assert collector_agent._running is True
        mock_collector.start.assert_called_once()
        
        await collector_agent.stop()
        
        assert collector_agent._running is False
        mock_collector.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_status(self, collector_agent):
        mock_collector = MagicMock()
        mock_collector.source = DataSource.KIS
        collector_agent.register_collector(mock_collector)
        
        status = collector_agent.get_status()
        
        assert "running" in status
        assert "collectors" in status
        assert "tasks" in status
        assert status["running"] is False


class TestCollectionTask:
    def test_collection_task_creation(self):
        task = CollectionTask(
            id="test_task",
            source=DataSource.KIS,
            frequency=CollectionFrequency.MINUTE_1,
            symbols=["005930", "000660"],
            enabled=True,
        )
        
        assert task.id == "test_task"
        assert task.source == DataSource.KIS
        assert task.frequency == CollectionFrequency.MINUTE_1
        assert task.symbols == ["005930", "000660"]
        assert task.enabled is True

    def test_collection_task_defaults(self):
        task = CollectionTask(
            id="test_task",
            source=DataSource.KIS,
            frequency=CollectionFrequency.DAILY,
        )
        
        assert task.symbols == []
        assert task.params == {}
        assert task.enabled is True
        assert task.last_run is None
        assert task.next_run is None


class TestCollectedData:
    def test_collected_data_creation(self):
        from datetime import datetime
        
        data = CollectedData(
            source=DataSource.KIS,
            data_type="tick",
            symbol="005930",
            timestamp=datetime.now(),
            payload={"price": "75000"},
            metadata={"source": "kis"},
        )
        
        assert data.source == DataSource.KIS
        assert data.data_type == "tick"
        assert data.symbol == "005930"
        assert data.payload == {"price": "75000"}
        assert data.metadata == {"source": "kis"}


class TestDataSource:
    def test_data_source_values(self):
        assert DataSource.KIS.value == "kis"
        assert DataSource.DART.value == "dart"
        assert DataSource.NAVER_NEWS.value == "naver_news"
        assert DataSource.BOK.value == "bok"
        assert DataSource.FRED.value == "fred"


class TestCollectionFrequency:
    def test_collection_frequency_values(self):
        assert CollectionFrequency.REALTIME.value == "realtime"
        assert CollectionFrequency.MINUTE_1.value == "1m"
        assert CollectionFrequency.MINUTE_5.value == "5m"
        assert CollectionFrequency.HOURLY.value == "1h"
        assert CollectionFrequency.DAILY.value == "1d"
        assert CollectionFrequency.WEEKLY.value == "1w"
