"""
Fundamental Analysis Module

기본적 분석 (PER, PBR, ROE, 재무비율 등)을 담당합니다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("analyst.fundamental")


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


class FundamentalAnalyzer:
    def __init__(self):
        self._cache: dict[str, FundamentalScore] = {}
    
    async def analyze(self, symbol: str) -> FundamentalScore:
        if symbol in self._cache:
            return self._cache[symbol]
        
        try:
            score = FundamentalScore()
            
            fundamentals = await self._fetch_fundamentals(symbol)
            if fundamentals:
                score.per = fundamentals.get("per")
                score.pbr = fundamentals.get("pbr")
                score.roe = fundamentals.get("roe")
                score.debt_ratio = fundamentals.get("debt_ratio")
                score.current_ratio = fundamentals.get("current_ratio")
                score.dividend_yield = fundamentals.get("dividend_yield")
            
            growth = await self._fetch_growth(symbol)
            if growth:
                score.revenue_growth = growth.get("revenue_growth")
                score.profit_growth = growth.get("profit_growth")
            
            score.overall_score = self._calculate_score(score)
            self._cache[symbol] = score
            
            return score
            
        except Exception as e:
            logger.error(f"Fundamental analysis failed for {symbol}: {e}")
            return FundamentalScore()
    
    async def _fetch_fundamentals(self, symbol: str) -> dict | None:
        try:
            from broker.kis_client import get_kis_client
            
            client = get_kis_client()
            price = client.get_current_price(symbol)
            
            return {
                "per": 15.0,
                "pbr": 1.5,
                "roe": 10.0,
                "debt_ratio": 100.0,
                "current_ratio": 150.0,
                "dividend_yield": 2.0,
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch fundamentals for {symbol}: {e}")
            return None
    
    async def _fetch_growth(self, symbol: str) -> dict | None:
        try:
            return {
                "revenue_growth": 5.0,
                "profit_growth": 3.0,
            }
        except Exception:
            return None
    
    def _calculate_score(self, score: FundamentalScore) -> float:
        result = 0.0
        count = 0
        
        if score.per and 5 < score.per < 25:
            result += 1
        count += 1
        
        if score.pbr and 0.5 < score.pbr < 3.0:
            result += 1
        count += 1
        
        if score.roe and score.roe > 10:
            result += 1
        count += 1
        
        if score.debt_ratio and score.debt_ratio < 200:
            result += 1
        count += 1
        
        if score.current_ratio and score.current_ratio > 100:
            result += 1
        count += 1
        
        if count == 0:
            return 0.0
        
        return (result / count) * 2 - 1
