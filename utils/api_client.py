import os
import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger('archie-bot')

STEVE_HEAD_URL = "https://mc-heads.net/avatar/MHF_Steve/80"

_http_session: Optional[aiohttp.ClientSession] = None

async def get_http_session() -> aiohttp.ClientSession:
    """Get or create global HTTP session."""
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=5),
            connector=aiohttp.TCPConnector(limit=20, ttl_dns_cache=300)
        )
    return _http_session

async def fetch_player_head(uuid: str) -> Optional[bytes]:
    """Async fetch player head with timeout protection."""
    head_urls = [f"https://mc-heads.net/avatar/{uuid}/80", STEVE_HEAD_URL]
    session = await get_http_session()
    for url in head_urls:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    if len(data) > 100:
                        return data
        except:
            continue
    return None


class AsyncPIGDIClient:
    """Async API client - prevents blocking the event loop."""
    BASE_URL = "https://api.arch.mc"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(
                headers={"X-API-KEY": self.api_key},
                timeout=timeout
            )
        return self._session

    async def _request(self, method: str, path: str) -> Any:
        session = await self._get_session()
        url = f"{self.BASE_URL}{path}"
        try:
            async with session.request(method, url) as resp:
                if resp.status != 200:
                    return None
                if resp.content_type and resp.content_type.startswith("application/json"):
                    return await resp.json()
                return await resp.text()
        except asyncio.TimeoutError:
            logger.warning(f"API timeout: {path}")
            return None
        except Exception as e:
            logger.error(f"API error: {e}")
            return None

    async def get_ugc_player_stats_by_username(self, gamemode: str, username: str) -> Optional[Dict]:
        path = f"/v1/ugc/{gamemode}/players/username/{username}/statistics"
        return await self._request("GET", path)

    async def get_ugc_leaderboard(self, gamemode: str, stat_type: str, page: int = 0, size: int = 10) -> Optional[Dict]:
        path = f"/v1/ugc/{gamemode}/leaderboard/{stat_type}?page={page}&size={size}"
        return await self._request("GET", path)

    async def get(self, path: str) -> Optional[Dict]:
        return await self._request("GET", path)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


_api_client: Optional[AsyncPIGDIClient] = None

def get_api_client() -> AsyncPIGDIClient:
    global _api_client
    if _api_client is None:
        API_KEY = os.getenv("ARCH_API_KEY") or "your-api-key-here"
        _api_client = AsyncPIGDIClient(API_KEY)
    return _api_client
