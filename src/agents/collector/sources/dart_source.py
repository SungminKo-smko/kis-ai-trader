"""
DART 재무제표 수집기

DART 전자공시 OPEN API를 통해 재무제표 데이터를 수집합니다.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import aiohttp

from agents.collector.agent import BaseCollector, CollectedData, DataSource
from core.event_bus import EventBus

logger = logging.getLogger("collector.dart")


class DARTCollector(BaseCollector):
    """DART 재무제표 데이터 수집기"""
    
    BASE_URL = "https://opendart.fss.or.kr/api"
    
    def __init__(
        self,
        event_bus: EventBus,
        api_key: str,
    ):
        super().__init__(source=DataSource.DART, event_bus=event_bus)
        self.api_key = api_key
    
    async def collect(self, **kwargs) -> list[CollectedData]:
        """재무제표 데이터 수집"""
        symbols = kwargs.get("symbols", [])
        
        if not symbols:
            return []
        
        results = []
        
        for symbol in symbols:
            try:
                data = await self._fetch_financial_statement(symbol)
                if data:
                    results.append(data)
            except Exception as e:
                logger.error(f"Failed to fetch financial data for {symbol}: {e}")
        
        return results
    
    async def _fetch_financial_statement(self, corp_code: str) -> CollectedData | None:
        """개별기업 재무제표 조회"""
        
        url = f"{self.BASE_URL}/fnlttSinglAcnt.json"
        
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bsns_year": datetime.now().year,
            "reprt_code": "11011",  # annual
            "fs_div": "OFS",  # separate financial statements
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"DART API error: {resp.status}")
                    return None
                
                data = await resp.json()
                
                if data.get("status") != "000":
                    logger.warning(f"DART API warning: {data.get('message')}")
                    return None
                
                return CollectedData(
                    source=DataSource.DART,
                    data_type="financial_statement",
                    symbol=corp_code,
                    timestamp=datetime.now(),
                    payload=data,
                    metadata={"bsns_year": params["bsns_year"]},
                )
    
    async def fetch_company_info(self, corp_code: str) -> dict | None:
        """회사 기본정보 조회"""
        
        url = f"{self.BASE_URL}/company.json"
        
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                
                if data.get("status") != "000":
                    return None
                
                return data.get("result", {})
    
    async def fetch_listing_company(self) -> list[dict]:
        """상장사 목록 조회"""
        
        url = f"{self.BASE_URL}/companyList.json"
        
        params = {
            "crtfc_key": self.api_key,
            "last_reprt_at": "Y",
            "capital": "",
            "status": "",
        }
        
        results = []
        
        async with aiohttp.ClientSession() as session:
            page = 1
            
            while True:
                params["page_no"] = page
                
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        break
                    
                    data = await resp.json()
                    
                    if data.get("status") != "000":
                        break
                    
                    companies = data.get("list", [])
                    
                    if not companies:
                        break
                    
                    results.extend(companies)
                    page += 1
                    
                    if page > data.get("total_page", 1):
                        break
        
        return results
    
    async def health_check(self) -> bool:
        """DART API 연결 상태 확인"""
        
        url = f"{self.BASE_URL}/companyList.json"
        
        params = {
            "crtfc_key": self.api_key,
            "page_no": 1,
            "page_count": 1,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    return resp.status == 200
        except Exception:
            return False
