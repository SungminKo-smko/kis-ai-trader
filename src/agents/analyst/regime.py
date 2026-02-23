"""
Market Regime Detection Module

시장 레짐 (상승/하락/횡보) 감지를 담당합니다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("analyst.regime")


@dataclass
class MarketRegime:
    regime: str = "SIDEWAYS"
    confidence: float = 0.0
    volatility: float = 0.0
    trend: str = "neutral"
    indicators: dict[str, Any] = field(default_factory=dict)


class RegimeDetector:
    def __init__(self):
        self._cache: MarketRegime | None = None
    
    async def detect(self) -> MarketRegime:
        try:
            df = await self._fetch_market_data()
            if df is None or df.empty:
                return MarketRegime()
            
            regime = self._analyze_regime(df)
            self._cache = regime
            return regime
            
        except Exception as e:
            logger.error(f"Regime detection failed: {e}")
            return MarketRegime()
    
    async def _fetch_market_data(self):
        try:
            import pandas as pd
            from broker.kis_client import get_kis_client
            from datetime import timedelta
            
            client = get_kis_client()
            
            kospi = client.get_ohlcv(
                symbol="000001",
                timeframe="D",
                start_date=(pd.Timestamp.now() - timedelta(days=60)).strftime("%Y%m%d"),
                limit=60,
            )
            
            if not kospi:
                return None
            
            df = pd.DataFrame(kospi)
            df = df.rename(columns={
                "stck_clpr": "close",
                "stck_oprc": "open",
                "stck_hgpr": "high",
                "stck_lwpr": "low",
            })
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            return None
    
    def _analyze_regime(self, df) -> MarketRegime:
        import pandas as pd
        
        regime = MarketRegime()
        
        try:
            close = pd.to_numeric(df["close"], errors="coerce")
            high = pd.to_numeric(df["high"], errors="coerce")
            low = pd.to_numeric(df["low"], errors="coerce")
            
            returns = close.pct_change().dropna()
            
            regime.volatility = float(returns.std() * (252 ** 0.5))
            
            sma_20 = close.rolling(20).mean()
            sma_60 = close.rolling(60).mean() if len(close) >= 60 else sma_20
            
            current_price = close.iloc[-1]
            ma_20 = sma_20.iloc[-1]
            ma_60 = sma_60.iloc[-1] if len(sma_60) > 0 else ma_20
            
            if current_price > ma_20 and current_price > ma_60:
                regime.trend = "up"
                regime.regime = "BULL"
                regime.confidence = 0.7
            elif current_price < ma_20 and current_price < ma_60:
                regime.trend = "down"
                regime.regime = "BEAR"
                regime.confidence = 0.7
            else:
                regime.trend = "sideways"
                regime.regime = "SIDEWAYS"
                regime.confidence = 0.5
            
            regime.indicators = {
                "price": float(current_price),
                "ma20": float(ma_20),
                "ma60": float(ma_60),
                "volatility": regime.volatility,
                "return_20d": float((current_price / close.iloc[-20] - 1)) if len(close) >= 20 else 0.0,
            }
            
        except Exception as e:
            logger.error(f"Regime analysis error: {e}")
        
        return regime
