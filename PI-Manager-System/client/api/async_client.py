# -*- coding: utf-8 -*-
import asyncio
import aiohttp
from typing import Optional, List, Dict, Any
from config import Config

class AsyncApiClient:
    def __init__(self, base_url: str = None):
        self.base_url = (base_url or Config.API_BASE_URL).rstrip("/")
        self.session = None
        self.db_config = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        if self.db_config:
            self.session.headers.update({
                "Content-Type": "application/json",
                "X-DB-Host": self.db_config.get("db_host", ""),
                "X-DB-Port": str(self.db_config.get("db_port", 3306)),
                "X-DB-User": self.db_config.get("db_user", ""),
                "X-DB-Password": self.db_config.get("db_password", ""),
                "X-DB-Name": self.db_config.get("db_name", "")
            })
        else:
            self.session.headers.update({"Content-Type": "application/json"})
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    def set_db_config(self, db_config: Dict):
        self.db_config = db_config

    def _build_url(self, endpoint: str) -> str:
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]
        return f"{self.base_url}/api/{endpoint}"

    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()

    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        async with self.session.post(url, json=data) as response:
            response.raise_for_status()
            return await response.json()

    async def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        async with self.session.put(url, json=data) as response:
            response.raise_for_status()
            return await response.json()

    async def delete(self, endpoint: str) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        async with self.session.delete(url) as response:
            response.raise_for_status()
            return await response.json()

    async def get_suppliers(self) -> List[Dict]:
        return await self.get("/suppliers")

    async def create_supplier(self, data: Dict) -> Dict:
        return await self.post("/suppliers", data)

    async def batch_create_suppliers(self, data: List[Dict]) -> Dict:
        return await self.post("/suppliers/batch", {"suppliers": data})

    async def get_provinces(self) -> List[str]:
        return await self.get("/suppliers/provinces")

    async def get_cities(self, province: str) -> List[str]:
        return await self.get(f"/suppliers/cities/{province}")