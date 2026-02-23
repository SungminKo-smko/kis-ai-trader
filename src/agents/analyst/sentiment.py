"""
Sentiment Analysis Module

뉴스 및 소셜 미디어 감성 분석을 담당합니다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("analyst.sentiment")


@dataclass
class SentimentScore:
    news_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    avg_sentiment: float = 0.0
    sentiment_ratio: float = 0.0


class SentimentAnalyzer:
    def __init__(self):
        self._cache: dict[str, SentimentScore] = {}
    
    async def analyze(self, symbol: str) -> SentimentScore:
        if symbol in self._cache:
            return self._cache[symbol]
        
        try:
            news = await self._fetch_news(symbol)
            score = self._analyze_sentiment(news)
            
            self._cache[symbol] = score
            return score
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed for {symbol}: {e}")
            return SentimentScore()
    
    async def _fetch_news(self, symbol: str) -> list[dict]:
        try:
            return []
        except Exception as e:
            logger.error(f"Failed to fetch news for {symbol}: {e}")
            return []
    
    def _analyze_sentiment(self, news: list[dict]) -> SentimentScore:
        score = SentimentScore()
        score.news_count = len(news)
        
        if not news:
            return score
        
        keywords_positive = [
            "상승", "증가", "호조", "baik", "성장", "이익", "호가",
            "breakout", "BUY", "매수", "투자", "확대", "개선"
        ]
        
        keywords_negative = [
            "하락", "감소", "약세", "buruk", "손실", "부정",
            "breakdown", "SELL", "매도", "위험", "축소", "악화"
        ]
        
        for article in news:
            title = article.get("title", "").lower()
            content = article.get("content", "").lower()
            text = title + " " + content
            
            positive = any(k in text for k in keywords_positive)
            negative = any(k in text for k in keywords_negative)
            
            if positive and not negative:
                score.positive_count += 1
            elif negative and not positive:
                score.negative_count += 1
            else:
                score.neutral_count += 1
        
        total = score.positive_count + score.negative_count + score.neutral_count
        if total > 0:
            score.avg_sentiment = (score.positive_count - score.negative_count) / total
        
        if score.positive_count + score.negative_count > 0:
            score.sentiment_ratio = (
                score.positive_count - score.negative_count
            ) / (score.positive_count + score.negative_count)
        
        return score
