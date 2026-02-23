"""
뉴스 수집기

네이버금융/한국경제 등의 뉴스 API를 통해 금융뉴스를 수집합니다.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import aiohttp

from agents.collector.agent import BaseCollector, CollectedData, DataSource
from core.event_bus import EventBus

logger = logging.getLogger("collector.news")


class NewsCollector(BaseCollector):
    """금융 뉴스 데이터 수집기"""
    
    NAVER_BASE_URL = "https://m.stock.naver.com"
    
    def __init__(
        self,
        event_bus: EventBus,
    ):
        super().__init__(source=DataSource.NAVER_NEWS, event_bus=event_bus)
    
    async def collect(self, **kwargs) -> list[CollectedData]:
        """뉴스 데이터 수집"""
        symbols = kwargs.get("symbols", [])
        
        results = []
        
        for symbol in symbols:
            try:
                news = await self._fetch_news_for_symbol(symbol)
                results.extend(news)
            except Exception as e:
                logger.error(f"Failed to fetch news for {symbol}: {e}")
        
        return results
    
    async def _fetch_news_for_symbol(self, symbol: str) -> list[CollectedData]:
        """개별종목 뉴스 조회"""
        
        url = f"{self.NAVER_BASE_URL}/api/v1/search/stock/NEWS"
        
        params = {
            "symbol": symbol,
            "page": 1,
            "pageSize": 20,
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0",
        }
        
        results = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status != 200:
                        return []
                    
                    data = await resp.json()
                    
                    articles = data.get("articles", [])
                    
                    for article in articles:
                        results.append(CollectedData(
                            source=DataSource.NAVER_NEWS,
                            data_type="news",
                            symbol=symbol,
                            timestamp=datetime.now(),
                            payload=article,
                            metadata={
                                "source": "naver",
                                "article_id": article.get("articleId"),
                            },
                        ))
        
        except Exception as e:
            logger.error(f"Naver news fetch error: {e}")
        
        return results
    
    async def fetch_market_news(self) -> list[CollectedData]:
        """시장 전체 뉴스 조회"""
        
        url = f"{self.NAVER_BASE_URL}/api/v1/search/stock/NEWS"
        
        params = {
            "page": 1,
            "pageSize": 30,
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0",
        }
        
        results = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status != 200:
                        return []
                    
                    data = await resp.json()
                    
                    articles = data.get("articles", [])
                    
                    for article in articles:
                        results.append(CollectedData(
                            source=DataSource.NAVER_NEWS,
                            data_type="news",
                            symbol=None,
                            timestamp=datetime.now(),
                            payload=article,
                            metadata={"source": "naver", "category": "market"},
                        ))
        
        except Exception as e:
            logger.error(f"Naver market news fetch error: {e}")
        
        return results
    
    async def health_check(self) -> bool:
        """네이버 뉴스 API 연결 상태 확인"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.NAVER_BASE_URL}/api/v1/search/stock/NEWS",
                    params={"page": 1, "pageSize": 1},
                    headers={"User-Agent": "Mozilla/5.0"},
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False
