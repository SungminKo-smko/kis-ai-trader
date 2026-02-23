"""
Tests for Analyst Agent
"""

import pytest
from unittest.mock import MagicMock, patch

from agents.analyst.agent import (
    AnalystAgent,
    AnalysisType,
    AnalysisReport,
    TechnicalSignals,
    FundamentalScore,
    SentimentScore,
)
from core.event_bus import EventBus


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def analyst_agent(event_bus):
    return AnalystAgent(event_bus=event_bus)


class TestAnalystAgent:
    @pytest.mark.asyncio
    async def test_analyst_agent_creation(self, analyst_agent):
        assert analyst_agent is not None
        assert analyst_agent._running is False
        assert analyst_agent._analysis_cache == {}

    @pytest.mark.asyncio
    async def test_start_and_stop(self, analyst_agent):
        await analyst_agent.start()
        assert analyst_agent._running is True
        
        await analyst_agent.stop()
        assert analyst_agent._running is False

    @pytest.mark.asyncio
    async def test_get_status(self, analyst_agent):
        status = analyst_agent.get_status()
        
        assert "running" in status
        assert "cached_reports" in status
        assert "subscribers" in status
        assert status["running"] is False

    @pytest.mark.asyncio
    async def test_subscribe(self, analyst_agent):
        callback = MagicMock()
        analyst_agent.subscribe("price_tick", callback)
        
        assert "price_tick" in analyst_agent._subscribers
        assert callback in analyst_agent._subscribers["price_tick"]

    @pytest.mark.asyncio
    async def test_get_report_not_found(self, analyst_agent):
        report = analyst_agent.get_report("005930")
        assert report is None


class TestAnalysisType:
    def test_analysis_type_values(self):
        assert AnalysisType.TECHNICAL.value == "technical"
        assert AnalysisType.FUNDAMENTAL.value == "fundamental"
        assert AnalysisType.SENTIMENT.value == "sentiment"
        assert AnalysisType.REGIME.value == "regime"
        assert AnalysisType.FULL.value == "full"


class TestTechnicalSignals:
    def test_technical_signals_creation(self):
        signals = TechnicalSignals(
            rsi=45.5,
            macd=150.0,
            macd_signal=140.0,
            macd_histogram=10.0,
            bb_upper=80000,
            bb_middle=75000,
            bb_lower=70000,
            sma_5=74000,
            sma_20=72000,
            ema_12=74500,
            ema_26=73000,
            atr=1500.0,
            adx=25.0,
            pattern="UPTREND",
        )
        
        assert signals.rsi == 45.5
        assert signals.macd == 150.0
        assert signals.macd_histogram == 10.0
        assert signals.pattern == "UPTREND"

    def test_technical_signals_defaults(self):
        signals = TechnicalSignals()
        
        assert signals.rsi is None
        assert signals.macd is None
        assert signals.pattern is None


class TestFundamentalScore:
    def test_fundamental_score_creation(self):
        score = FundamentalScore(
            per=12.5,
            pbr=1.2,
            roe=15.0,
            debt_ratio=150.0,
            current_ratio=180.0,
            revenue_growth=10.0,
            profit_growth=5.0,
            dividend_yield=2.5,
            sector_rank=3,
            overall_score=0.7,
        )
        
        assert score.per == 12.5
        assert score.pbr == 1.2
        assert score.roe == 15.0
        assert score.overall_score == 0.7

    def test_fundamental_score_defaults(self):
        score = FundamentalScore()
        
        assert score.per is None
        assert score.pbr is None
        assert score.overall_score == 0.0


class TestSentimentScore:
    def test_sentiment_score_creation(self):
        score = SentimentScore(
            news_count=20,
            positive_count=12,
            negative_count=3,
            neutral_count=5,
            avg_sentiment=0.45,
            sentiment_ratio=0.6,
        )
        
        assert score.news_count == 20
        assert score.positive_count == 12
        assert score.negative_count == 3
        assert score.sentiment_ratio == 0.6

    def test_sentiment_score_defaults(self):
        score = SentimentScore()
        
        assert score.news_count == 0
        assert score.positive_count == 0
        assert score.avg_sentiment == 0.0


class TestAnalysisReport:
    def test_analysis_report_creation(self):
        from datetime import datetime
        
        report = AnalysisReport(
            symbol="005930",
            timestamp=datetime.now(),
            technical=TechnicalSignals(rsi=45.0),
            fundamental=FundamentalScore(per=10.0),
            sentiment=SentimentScore(sentiment_ratio=0.5),
            overall_signal="BUY",
            confidence=0.8,
            reasoning="Strong technical and sentiment",
        )
        
        assert report.symbol == "005930"
        assert report.overall_signal == "BUY"
        assert report.confidence == 0.8

    def test_analysis_report_defaults(self):
        from datetime import datetime
        
        report = AnalysisReport(
            symbol="005930",
            timestamp=datetime.now(),
        )
        
        assert report.technical is None
        assert report.fundamental is None
        assert report.overall_signal == "HOLD"
        assert report.confidence == 0.0
