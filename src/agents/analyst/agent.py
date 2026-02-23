"""
Analyst Agent - 분석 에이전트

수집된 데이터를 다각도로 분석하여 인사이트를 생성합니다.

분석 영역:
- 기술적 분석 (RSI, MACD, Bollinger Bands, 이동평균)
- 기본적 분석 (PER, PBR, ROE, 재무비율)
- 감성 분석 (뉴스/논문 Sentiment)
- 시장 레짐 감지 (상승/하락/횡보)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from core.event_bus import Event, EventBus
from core.events import EventTypes


logger = logging.getLogger("analyst_agent")


class AnalysisType(str, Enum):
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    REGIME = "regime"
    FULL = "full"


@dataclass
class TechnicalSignals:
    rsi: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    sma_5: float | None = None
    sma_20: float | None = None
    sma_60: float | None = None
    ema_12: float | None = None
    ema_26: float | None = None
    atr: float | None = None
    adx: float | None = None
 float | None =    obv: None
    pattern: str | None = None


@dataclass
class FundamentalScore:
    per: float | None = None
    pbr: float | None = None
    roe: float | None = None
    debt_ratio: float | None = None
    current_ratio: float | None = None
    revenue_growth: float | None = None
    profit_growth: float | None = None
    dividend_yield: float | None = None
    sector_rank: int | None = None
    overall_score: float = 0.0


@dataclass
class SentimentScore:
    news_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    avg_sentiment: float = 0.0
    sentiment_ratio: float = 0.0


@dataclass
class MarketRegime:
    regime: str = "SIDEWAYS"
    confidence: float = 0.0
    volatility: float = 0.0
    trend: str = "neutral"
    indicators: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisReport:
    symbol: str
    timestamp: datetime
    technical: TechnicalSignals | None = None
    fundamental: FundamentalScore | None = None
    sentiment: SentimentScore | None = None
    regime: MarketRegime | None = None
    overall_signal: str = "HOLD"
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class AnalystAgent:
    def __init__(
        self,
        event_bus: EventBus,
        config: dict[str, Any] | None = None,
    ):
        self.event_bus = event_bus
        self.config = config or {}
        
        self._running = False
        self._tasks: dict[str, asyncio.Task] = {}
        self._subscribers: dict[str, list[Callable]] = {
            "price_tick": [],
            "daily_ohlcv": [],
            "news_article": [],
            "financial_statement": [],
        }
        self._analysis_cache: dict[str, AnalysisReport] = {}
        
        self._technical_analyzer = None
        self._fundamental_analyzer = None
        self._sentiment_analyzer = None
        self._regime_detector = None
    
    def subscribe(self, event_type: str, callback: Callable):
        if event_type in self._subscribers:
            self._subscribers[event_type].append(callback)
    
    async def start(self):
        self._running = True
        logger.info("Analyst Agent started")
        
        await self.event_bus.publish(Event(
            type=EventTypes.ANALYSIS_REPORT,
            payload={"message": "Analyst Agent started"},
            source="analyst_agent",
        ))
    
    async def stop(self):
        self._running = False
        
        for task in self._tasks.values():
            task.cancel()
        
        logger.info("Analyst Agent stopped")
    
    async def analyze_symbol(
        self,
        symbol: str,
        analysis_types: list[AnalysisType] | None = None,
    ) -> AnalysisReport:
        if analysis_types is None:
            analysis_types = [AnalysisType.FULL]
        
        report = AnalysisReport(
            symbol=symbol,
            timestamp=datetime.now(),
        )
        
        for atype in analysis_types:
            if atype == AnalysisType.TECHNICAL or atype == AnalysisType.FULL:
                report.technical = await self._analyze_technical(symbol)
            
            if atype == AnalysisType.FUNDAMENTAL or atype == AnalysisType.FULL:
                report.fundamental = await self._analyze_fundamental(symbol)
            
            if atype == AnalysisType.SENTIMENT or atype == AnalysisType.FULL:
                report.sentiment = await self._analyze_sentiment(symbol)
            
            if atype == AnalysisType.REGIME or atype == AnalysisType.FULL:
                report.regime = await self._detect_regime()
        
        report.overall_signal = self._calculate_overall_signal(report)
        report.confidence = self._calculate_confidence(report)
        
        self._analysis_cache[symbol] = report
        
        await self._publish_report(report)
        
        return report
    
    async def _analyze_technical(self, symbol: str) -> TechnicalSignals | None:
        try:
            from agents.analyst.technical import TechnicalAnalyzer
            if self._technical_analyzer is None:
                self._technical_analyzer = TechnicalAnalyzer()
            
            return await self._technical_analyzer.analyze(symbol)
        except Exception as e:
            logger.error(f"Technical analysis failed for {symbol}: {e}")
            return None
    
    async def _analyze_fundamental(self, symbol: str) -> FundamentalScore | None:
        try:
            from agents.analyst.fundamental import FundamentalAnalyzer
            if self._fundamental_analyzer is None:
                self._fundamental_analyzer = FundamentalAnalyzer()
            
            return await self._fundamental_analyzer.analyze(symbol)
        except Exception as e:
            logger.error(f"Fundamental analysis failed for {symbol}: {e}")
            return None
    
    async def _analyze_sentiment(self, symbol: str) -> SentimentScore | None:
        try:
            from agents.analyst.sentiment import SentimentAnalyzer
            if self._sentiment_analyzer is None:
                self._sentiment_analyzer = SentimentAnalyzer()
            
            return await self._sentiment_analyzer.analyze(symbol)
        except Exception as e:
            logger.error(f"Sentiment analysis failed for {symbol}: {e}")
            return None
    
    async def _detect_regime(self) -> MarketRegime:
        try:
            from agents.analyst.regime import RegimeDetector
            if self._regime_detector is None:
                self._regime_detector = RegimeDetector()
            
            return await self._regime_detector.detect()
        except Exception as e:
            logger.error(f"Regime detection failed: {e}")
            return MarketRegime()
    
    def _calculate_overall_signal(self, report: AnalysisReport) -> str:
        score = 0.0
        count = 0
        
        if report.technical:
            if report.technical.rsi:
                if report.technical.rsi < 30:
                    score += 1
                elif report.technical.rsi > 70:
                    score -= 1
                count += 1
            
            if report.technical.macd_histogram is not None:
                if report.technical.macd_histogram > 0:
                    score += 1
                else:
                    score -= 1
                count += 1
        
        if report.fundamental:
            score += report.fundamental.overall_score
            count += 1
        
        if report.sentiment:
            score += report.sentiment.sentiment_ratio * 2
            count += 1
        
        if count == 0:
            return "HOLD"
        
        avg_score = score / count
        
        if avg_score >= 0.5:
            return "BUY"
        elif avg_score <= -0.5:
            return "SELL"
        return "HOLD"
    
    def _calculate_confidence(self, report: AnalysisReport) -> float:
        factors = 0.0
        total = 0
        
        if report.technical:
            factors += 0.4
            total += 1
        
        if report.fundamental:
            factors += 0.3
            total += 1
        
        if report.sentiment:
            factors += 0.3
            total += 1
        
        if total == 0:
            return 0.0
        
        return min(factors, 1.0)
    
    async def _publish_report(self, report: AnalysisReport):
        await self.event_bus.publish(Event(
            type=EventTypes.ANALYSIS_REPORT,
            payload=report,
            source="analyst_agent",
        ))
    
    def get_report(self, symbol: str) -> AnalysisReport | None:
        return self._analysis_cache.get(symbol)
    
    def get_status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "cached_reports": len(self._analysis_cache),
            "subscribers": {k: len(v) for k, v in self._subscribers.items()},
        }
