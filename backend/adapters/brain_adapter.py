"""
BRAIN Adapter - WorldQuant BRAIN Platform API Integration
Refactored based on ace_lib.py best practices:
- Singleton Session (httpx.AsyncClient)
- Active Token Expiry Checking
- Basic Authentication
- Retry-After Handling
"""

import os
import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import httpx
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from sqlalchemy import select

from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models import BrainAuthToken

# Singleton Client Storage (Loop-aware)
_GLOBAL_CLIENT: Optional[httpx.AsyncClient] = None
_GLOBAL_CLIENT_LOOP: Optional[asyncio.AbstractEventLoop] = None

class BrainAdapter:
    """
    Adapter for WorldQuant BRAIN platform.
    Uses a singleton AsyncClient for persistent session management within the same event loop.
    """
    
    BASE_URL = "https://api.worldquantbrain.com"
    SESSION_BUFFER_SECONDS = 300  # Re-auth if expiring in < 5 mins
    REDIS_SESSION_KEY = "brain_session:cookies"
    
    def __init__(self, email: str = None, password: str = None):
        self.email = email or settings.BRAIN_EMAIL
        self.password = password or settings.BRAIN_PASSWORD
        self.session_token = None
    
    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        """Get or create the global singleton client for the current event loop."""
        global _GLOBAL_CLIENT, _GLOBAL_CLIENT_LOOP
        
        current_loop = asyncio.get_running_loop()
        
        # If client exists but loop doesn't match (or loop closed), reset it
        if _GLOBAL_CLIENT:
            if _GLOBAL_CLIENT.is_closed or _GLOBAL_CLIENT_LOOP != current_loop:
                logger.debug("Event loop changed or client closed, resetting BrainAdapter client")
                # Try to close old one if loop still open (unlikely if loop changed) 
                # but we can't await on old loop easily. Just drop ref.
                _GLOBAL_CLIENT = None
                _GLOBAL_CLIENT_LOOP = None

        if _GLOBAL_CLIENT is None:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Origin": "https://platform.worldquantbrain.com",
                "Referer": "https://platform.worldquantbrain.com/",
                "Accept": "application/json;version=2.0"
            }
            _GLOBAL_CLIENT = httpx.AsyncClient(
                timeout=60.0, 
                headers=headers,
                follow_redirects=True
            )
            _GLOBAL_CLIENT_LOOP = current_loop
            
        return _GLOBAL_CLIENT

    async def __aenter__(self):
        self.client = await self.get_client()
        await self.ensure_session()
        return self

    async def __aexit__(self, *args):
        # Do not close the global client here; it persists.
        pass
    
    @classmethod
    async def close(cls):
        """Explicitly close the global client (app shutdown)."""
        global _GLOBAL_CLIENT
        if _GLOBAL_CLIENT:
            await _GLOBAL_CLIENT.aclose()
            _GLOBAL_CLIENT = None

    async def _get_redis(self):
        """Get redis connection"""
        return redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def _load_session_from_redis(self) -> bool:
        """Load cookies from Redis if they exist."""
        try:
            r = await self._get_redis()
            cookies_json = await r.get(self.REDIS_SESSION_KEY)
            await r.aclose()
            
            if cookies_json:
                cookies = json.loads(cookies_json)
                self.client.cookies.update(cookies)
                logger.debug("Loaded session cookies from Redis")
                # When loaded from Redis, we trust it aligns with expiry.
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to load session from Redis: {e}")
            return False

    async def _save_session_to_redis(self, expiry_seconds: int):
        """Save current cookies to Redis with TTL."""
        try:
            cookies = dict(self.client.cookies)
            if not cookies:
                return
                
            r = await self._get_redis()
            # Set TTL slightly less than actual expiry to be safe (e.g. 5 min buffer logic already in caller or here)
            # If expiry_seconds is "seconds remaining", we use it as TTL directly.
            # If it's a timestamp, we calculate diff? 
            # Brain API returns "expiry": 14400 (seconds remaining). So use directly.
            ttl = max(60, int(expiry_seconds) - 60) # Reduce by 1 min to be safe
            await r.set(self.REDIS_SESSION_KEY, json.dumps(cookies), ex=ttl)
            await r.aclose()
            logger.debug(f"Saved session to Redis (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Failed to save session to Redis: {e}")

    async def ensure_session(self):
        """Ensure valid session exists, refreshing if needed. Prefer Redis cache."""
        # 1. Try to load from Redis first
        if await self._load_session_from_redis():
            # If loaded from Redis, we assume it is valid for now (TTL handles expiry)
            # We could do a lightweight check, but to save requests, we trust Redis.
            return

        # 2. If no Redis session, check active client state
        if not await self._is_session_valid():
            logger.info("Session invalid or expiring, re-authenticating...")
            await self.authenticate()

    async def _is_session_valid(self) -> bool:
        """
        Check if current session is valid by querying API.
        Reference: ace_lib.py `check_session_timeout`
        """
        try:
            # We need to use the client directly to check
            response = await self.client.get(f"{self.BASE_URL}/authentication")
            
            if response.status_code == 200:
                data = response.json()
                expiry = data.get("token", {}).get("expiry", 0)
                logger.debug(f"Session check: expiry={expiry}, buffer={self.SESSION_BUFFER_SECONDS}")
                # expiry is seconds remaining
                if expiry > self.SESSION_BUFFER_SECONDS:
                    return True
                else:
                    logger.debug(f"Session expiring soon: {expiry}s remaining")
                    return False
            return False
        except Exception:
            return False

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=60))
    async def authenticate(self) -> bool:
        """
        Authenticate using Basic Auth.
        Reference: ace_lib.py `start_session` uses Basic Auth (via requests.auth).
        """
        try:
            response = await self.client.post(
                f"{self.BASE_URL}/authentication",
                auth=(self.email, self.password)
            )
            
            if response.status_code == 201:
                logger.info("BRAIN authentication successful")
                
                # Save session to Redis
                data = response.json()
                expiry = data.get("token", {}).get("expiry", 3600*4) # Default 4h if missing
                await self._save_session_to_redis(expiry)
                
                return True
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                     logger.warning(f"Rate limited. Sleeping {retry_after}s")
                     await asyncio.sleep(float(retry_after))
                raise Exception("Rate limit exceeded")
            else:
                logger.error(f"Auth failed: {response.status_code} - {response.text}")
                raise Exception(f"Auth failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise

    # ... Methods (simulate_alpha, get_datasets, etc.) need to use self.client ...
    # I will replicate them below, ensuring they use self.client and handle errors.
    
    async def simulate_alpha(self, expression: str, region: str = "USA", universe: str = "TOP3000", delay: int = 1, decay: int = 4, neutralization: str = "SUBINDUSTRY", truncation: float = 0.08, test_period: str = "P0Y0M") -> Dict:
        # Construct payload
        sim_payload = {
            "type": "REGULAR",
            "settings": {
                "instrumentType": "EQUITY", "region": region, "universe": universe, "delay": delay,
                "decay": decay, "neutralization": neutralization, "truncation": truncation,
                "testPeriod": test_period, "nanHandling": "OFF", "unitHandling": "VERIFY", "pasteurization": "ON"
            },
            "regular": expression
        }
        
        try:
            response = await self.client.post(f"{self.BASE_URL}/simulations", json=sim_payload)
            if response.status_code not in [200, 201, 202]:
                return {"success": False, "error": f"Creation failed: {response.text}"}
            
            location = response.headers.get("Location")
            if not location:
                 location = f"/simulations/{response.json().get('id')}"
                 
            return await self._wait_for_simulation(location)
        except Exception as e:
            logger.error(f"Simulate error: {e}")
            return {"success": False, "error": str(e)}

    async def _wait_for_simulation(self, location: str, max_wait: int = 300) -> Dict:
        start_time = datetime.now()
        while (datetime.now() - start_time).seconds < max_wait:
            try:
                 response = await self.client.get(f"{self.BASE_URL}{location}")
                 if response.headers.get("Retry-After"):
                     await asyncio.sleep(float(response.headers["Retry-After"]))
                     continue
                     
                 if response.status_code != 200:
                     await asyncio.sleep(3)
                     continue
                     
                 data = response.json()
                 status = data.get("status", "")
                 
                 if status == "DONE":
                     alpha = data.get("alpha", {})
                     return {
                         "success": True, 
                         "alpha_id": alpha.get("id"),
                         "metrics": {
                             "sharpe": alpha.get("is", {}).get("sharpe"),
                             "returns": alpha.get("is", {}).get("returns"),
                             "turnover": alpha.get("is", {}).get("turnover"),
                             "fitness": alpha.get("is", {}).get("fitness"),
                             "max_dd": alpha.get("is", {}).get("drawdown")
                         }
                     }
                 elif status == "ERROR":
                     return {"success": False, "error": data.get("message")}
                 
                 await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(2)
        return {"success": False, "error": "Timeout"}

    async def _safe_api_call(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """
        Execute API call with auto-reauth on 401 and retry on 429/5xx.
        """
        url = f"{self.BASE_URL}{endpoint}"
        retries = 0
        max_retries = 5
        
        while retries < max_retries:
            try:
                response = await getattr(self.client, method.lower())(url, **kwargs)
                
                # 1. Handle 401 Unauthorized (Token Expiry)
                if response.status_code == 401:
                    logger.warning(f"401 Unauthorized for {endpoint}, re-authenticating...")
                    if await self.authenticate():
                        # Retry immediately with new token
                        response = await getattr(self.client, method.lower())(url, **kwargs)
                
                # 2. Handle 429 Too Many Requests (Rate Limit)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait_time = float(retry_after) if retry_after else (2 ** (retries + 1))
                    logger.warning(f"429 Rate Limit for {endpoint}. Sleeping {wait_time}s (Attempt {retries+1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    retries += 1
                    continue
                
                # 3. Handle 5xx Server Errors (Temporary Glitch)
                if 500 <= response.status_code < 600:
                    wait_time = 2 ** (retries + 1)
                    logger.warning(f"Server Error {response.status_code} for {endpoint}. Sleeping {wait_time}s")
                    await asyncio.sleep(wait_time)
                    retries += 1
                    continue
                
                return response
                
            except (httpx.RequestError, httpx.TimeoutException) as e:
                # Network level errors
                wait_time = 2 ** (retries + 1)
                logger.error(f"Network error {endpoint}: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                retries += 1
                
        # If exhausted retries, return the last response or raise
        logger.error(f"Max retries exceeded for {endpoint}")
        if 'response' in locals():
            return response
        raise Exception(f"Failed to connect to {endpoint} after {max_retries} attempts")

    async def get_datasets(self, region: str = "USA", delay: int = 1, universe: str = "TOP3000") -> List[Dict]:
        try:
            response = await self._safe_api_call(
                "GET", "/data-sets",
                params={"region": region, "delay": delay, "universe": universe, "instrumentType": "EQUITY"}
            )
            return response.json().get("results", []) if response.status_code == 200 else []
        except Exception:
            return []

    async def get_datafields(self, dataset_id: str, region: str = "USA", delay: int = 1, universe: str = "TOP3000") -> List[Dict]:
        all_results = []
        offset = 0
        limit = 50
        
        while True:
            try:
                response = await self._safe_api_call(
                    "GET", "/data-fields",
                    params={
                        "dataset.id": dataset_id, 
                        "region": region, 
                        "delay": delay, 
                        "universe": universe, 
                        "instrumentType": "EQUITY",
                        "limit": limit,
                        "offset": offset
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Get fields failed: {response.status_code} - {response.text}")
                    break
                    
                data = response.json()
                results = data.get("results", [])
                
                if not results:
                    break
                    
                all_results.extend(results)
                
                if len(results) < limit:
                    break
                    
                offset += limit
                
            except Exception as e:
                logger.error(f"Get fields error: {e}")
                break
                
        return all_results

    async def get_operators(self, detailed: bool = False) -> List[Any]:
        try:
            response = await self._safe_api_call("GET", "/operators")
            if response.status_code == 200:
                data = response.json()
                results = data if isinstance(data, list) else data.get("results", [])
                return results if detailed else [op.get("name") for op in results]
            return self._get_common_operators()
        except Exception:
            return self._get_common_operators()

    async def get_alpha_pnl(self, alpha_id: str) -> Dict:
        try:
            response = await self.client.get(f"{self.BASE_URL}/alphas/{alpha_id}/recordsets/pnl")
            return response.json() if response.status_code == 200 else {}
        except Exception:
            return {}

    async def check_correlation(self, alpha_id: str, check_type: str = "PROD") -> Dict:
        try:
            response = await self.client.get(f"{self.BASE_URL}/alphas/{alpha_id}/correlations/{check_type}")
            return response.json() if response.status_code == 200 else {}
        except Exception:
            return {}

    async def get_user_alphas(self, limit: int = 100, offset: int = 0, stage: str = None, search: str = None, start_date: str = None) -> Dict:
        """
        Get user's alphas with pagination.
        endpoint: /users/self/alphas
        """
        try:
            params = {
                "limit": limit, 
                "offset": offset,
                "hidden": False,
                "order": "-dateCreated"
            }
            if stage:
                params["stage"] = stage
            if search:
                params["search"] = search
            if start_date:
                # Brain API often uses 'startDate' for filtering creation date
                params["startDate"] = start_date
                
            response = await self._safe_api_call("GET", "/users/self/alphas", params=params)
            
            if response.status_code == 200:
                return response.json()
            return {"results": [], "count": 0}
        except Exception as e:
            logger.error(f"Failed to get user alphas: {e}")
            return {"results": [], "count": 0}

    def _get_common_operators(self) -> List[str]:
        return ["rank", "ts_rank", "ts_zscore", "ts_mean", "ts_delay", "ts_corr", "ts_max", "ts_min", "abs", "log", "sign"]
