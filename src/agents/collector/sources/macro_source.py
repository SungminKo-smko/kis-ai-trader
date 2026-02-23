"""
경제지표 수집기

한국은행(BOK) 및 FRED(연준) 경제지표를 수집합니다.
"""

from __future__ import annotations

import logging
from datetime import datetime

import aiohttp

from agents.collector.agent import BaseCollector, CollectedData, DataSource
from core.event_bus import EventBus

logger = logging.getLogger("collector.macro")


class BOKCollector(BaseCollector):
    BASE_URL = "https://ecos.bok.or.kr/api"
    
    def __init__(self, event_bus: EventBus, api_key: str):
        super().__init__(source=DataSource.BOK, event_bus=event_bus)
        self.api_key = api_key
    
    async def collect(self, **kwargs) -> list[CollectedData]:
        indicators = kwargs.get("indicators", [
            "M0101000M",
            "036010000M",
            "060100000M",
            "010100000M",
        ])
        
        results = []
        for indicator in indicators:
            try:
                data = await self._fetch_indicator(indicator)
                if data:
                    results.append(data)
            except Exception as e:
                logger.error(f"Failed to fetch BOK indicator {indicator}: {e}")
        
        return results
    
    async def _fetch_indicator(self, stat_code: str) -> CollectedData | None:
        url = f"{self.BASE_URL}/StatisticSearch.json"
        
        params = {
            "authkey": self.api_key,
            "stat_code": stat_code,
            "cycle": "M",
            "start_date": "202001",
            "end_date": datetime.now().strftime("%Y%m"),
            "format": "json",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    
                    if data.get("StatisticSearch"):
                        return CollectedData(
                            source=DataSource.BOK,
                            data_type="macro_indicator",
                            symbol=stat_code,
                            timestamp=datetime.now(),
                            payload=data,
                            metadata={"stat_code": stat_code},
                        )
        except Exception as e:
            logger.error(f"BOK indicator fetch error: {e}")
        
        return None
    
    async def health_check(self) -> bool:
        try:
            url = f"{self.BASE_URL}/StatisticSearch.json"
            params = {
                "authkey": self.api_key,
                "stat_code": "010100000M",
                "cycle": "M",
                "start_date": "202001",
                "end_date": "202001",
                "format": "json",
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    return resp.status == 200
        except Exception:
            return False


class FREDCollector(BaseCollector):
    BASE_URL = "https://api.stlouisfed.org/fred"
    
    def __init__(self, event_bus: EventBus, api_key: str):
        super().__init__(source=DataSource.FRED, event_bus=event_bus)
        self.api_key = api_key
    
    async def collect(self, **kwargs) -> list[CollectedData]:
        series_ids = kwargs.get("series", [
            "DFF",
            "DGS10",
            "UNRATE",
            "CPIAUCSL",
            "GDPC1",
        ])
        
        results = []
        for sid in series_ids:
            try:
                data = await self._fetch_series(sid)
                if data:
                    results.append(data)
            except Exception as e:
                logger.error(f"Failed to fetch FRED series {sid}: {e}")
        
        return results
    
    async def _fetch_series(self, series_id: str) -> CollectedData | None:
        url = f"{self.BASE_URL}/series/observations"
        
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "observation_start": "2020-01-01",
            "observation_end": datetime.now().strftime("%Y-%m-%d"),
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    
                    if "observations" in data:
                        return CollectedData(
                            source=DataSource.FRED,
                            data_type="macro_indicator",
                            symbol=series_id,
                            timestamp=datetime.now(),
                            payload=data,
                            metadata={"series_id": series_id},
                        )
        except Exception as e:
            logger.error(f"FRED series fetch error: {e}")
        
        return None
    
    async def fetch_latest(self, series_id: str) -> dict | None:
        url = f"{self.BASE_URL}/series/observations"
        
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "limit": 1,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    
                    if data.get("observations"):
                        return data["observations"][-1]
        except Exception:
            pass
        
        return None
    
    async def health_check(self) -> bool:
        try:
            url = f"{self.BASE_URL}/series/observations"
            params = {
                "series_id": "DFF",
                "api_key": self.api_key,
                "file_type": "json",
                "limit": 1,
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    return resp.status == 200
        except Exception:
            return False
