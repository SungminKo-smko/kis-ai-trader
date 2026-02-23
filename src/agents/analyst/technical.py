"""
Technical Analysis Module

기술적 지표 계산 및 패턴 인식을 담당합니다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("analyst.technical")


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
    obv: float | None = None
    pattern: str | None = None


class TechnicalAnalyzer:
    def __init__(self):
        self._cache: dict[str, TechnicalSignals] = {}
    
    async def analyze(self, symbol: str) -> TechnicalSignals:
        if symbol in self._cache:
            return self._cache[symbol]
        
        try:
            df = await self._fetch_ohlcv(symbol)
            if df is None or df.empty:
                return TechnicalSignals()
            
            signals = self._calculate_indicators(df)
            self._cache[symbol] = signals
            return signals
            
        except Exception as e:
            logger.error(f"Technical analysis failed for {symbol}: {e}")
            return TechnicalSignals()
    
    async def _fetch_ohlcv(self, symbol: str):
        try:
            from broker.kis_client import get_kis_client
            from datetime import timedelta
            
            client = get_kis_client()
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            ohlcv = client.get_ohlcv(
                symbol=symbol,
                timeframe="D",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                limit=90,
            )
            
            if not ohlcv:
                return None
            
            import pandas as pd
            df = pd.DataFrame(ohlcv)
            
            if "stck_clpr" in df.columns:
                df = df.rename(columns={
                    "stck_clpr": "close",
                    "stck_oprc": "open",
                    "stck_hgpr": "high",
                    "stck_lwpr": "low",
                    "acml_vol": "volume",
                })
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            return None
    
    def _calculate_indicators(self, df) -> TechnicalSignals:
        signals = TechnicalSignals()
        
        try:
            import pandas as pd
            try:
                import pandas_ta as ta
                ta_available = True
            except ImportError:
                ta_available = False
            
            close = pd.to_numeric(df["close"], errors="coerce")
            high = pd.to_numeric(df["high"], errors="coerce")
            low = pd.to_numeric(df["low"], errors="coerce")
            volume = pd.to_numeric(df["volume"], errors="coerce")
            
            if ta_available:
                signals.rsi = float(ta.rsi(close, length=14).iloc[-1]) if len(close) >= 14 else None
                
                macd = ta.macd(close)
                if macd is not None and len(macd) > 0:
                    signals.macd = float(macd.iloc[-1, 0]) if macd.shape[1] >= 1 else None
                    signals.macd_signal = float(macd.iloc[-1, 1]) if macd.shape[1] >= 2 else None
                    signals.macd_histogram = float(macd.iloc[-1, 2]) if macd.shape[1] >= 3 else None
                
                bbands = ta.bbands(close, length=20)
                if bbands is not None and len(bbands) > 0:
                    signals.bb_upper = float(bbands.iloc[-1, 0])
                    signals.bb_middle = float(bbands.iloc[-1, 1])
                    signals.bb_lower = float(bbands.iloc[-1, 2])
                
                signals.sma_5 = float(ta.sma(close, length=5).iloc[-1]) if len(close) >= 5 else None
                signals.sma_20 = float(ta.sma(close, length=20).iloc[-1]) if len(close) >= 20 else None
                signals.sma_60 = float(ta.sma(close, length=60).iloc[-1]) if len(close) >= 60 else None
                
                signals.ema_12 = float(ta.ema(close, length=12).iloc[-1]) if len(close) >= 12 else None
                signals.ema_26 = float(ta.ema(close, length=26).iloc[-1]) if len(close) >= 26 else None
                
                signals.atr = float(ta.atr(high, low, close, length=14).iloc[-1]) if len(close) >= 14 else None
                signals.adx = float(ta.adx(high, low, close, length=14).iloc[-1]) if len(close) >= 14 else None
                
                signals.obv = float(ta.obv(close, volume).iloc[-1]) if len(close) > 0 else None
            else:
                signals.rsi = self._calculate_rsi(close, 14)
                signals.sma_5 = self._calculate_sma(close, 5)
                signals.sma_20 = self._calculate_sma(close, 20)
                signals.sma_60 = self._calculate_sma(close, 60)
            
            signals.pattern = self._detect_pattern(close, high, low)
            
        except Exception as e:
            logger.error(f"Indicator calculation error: {e}")
        
        return signals
    
    def _calculate_rsi(self, series, period: int = 14) -> float | None:
        try:
            import pandas as pd
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1])
        except:
            return None
    
    def _calculate_sma(self, series, period: int) -> float | None:
        try:
            return float(series.rolling(window=period).mean().iloc[-1])
        except:
            return None
    
    def _detect_pattern(self, close, high, low) -> str | None:
        try:
            if len(close) < 5:
                return None
            
            recent = close.tail(5).values
            current = close.iloc[-1]
            high_20 = high.tail(20).max()
            low_20 = low.tail(20).min()
            
            if current > high_20 * 0.98:
                return "NEAR_HIGH"
            elif current < low_20 * 1.02:
                return "NEAR_LOW"
            elif all(recent[i] < recent[i+1] for i in range(len(recent)-1)):
                return "UPTREND"
            elif all(recent[i] > recent[i+1] for i in range(len(recent)-1)):
                return "DOWNTREND"
            
            return "SIDEWAYS"
            
        except Exception as e:
            logger.error(f"Pattern detection error: {e}")
            return None


from datetime import datetime
