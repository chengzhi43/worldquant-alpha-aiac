import os
import json
import time
import logging
import threading
import requests
from typing import Optional, List, Dict, Union, Literal
from urllib.parse import urljoin
from backend.config import settings

logger = logging.getLogger("brain_adapter")

class BrainAdapter:
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        self.base_url = "https://api.worldquantbrain.com"
        self.session = requests.Session()
        self.authenticated = False 
        self._relogin_lock = threading.Lock()
        
    def authenticate(self):
        """Authenticates with BRAIN Platform using credentials from settings."""
        if not settings.BRAIN_EMAIL or not settings.BRAIN_PASSWORD:
            logger.error("BRAIN credentials not set.")
            raise ValueError("BRAIN_EMAIL and BRAIN_PASSWORD must be set.")

        auth_payload = {
            "email": settings.BRAIN_EMAIL,
            "password": settings.BRAIN_PASSWORD
        }
        
        try:
            r = self.session.post(f"{self.base_url}/authentication", json=auth_payload)
            r.raise_for_status()
            self.authenticated = True
            logger.info("Successfully authenticated with BRAIN.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # Handle 2FA/Biometrics check if needed (simplified for now)
                if "WWW-Authenticate" in e.response.headers:
                     logger.warning("Biometric/2FA required. Please run the CLI tool for initial setup.")
            logger.error(f"Authentication failed: {e}")
            raise

    def check_session(self):
        """Checks if session is valid, re-logins if needed."""
        try:
            r = self.session.get(f"{self.base_url}/authentication")
            if r.status_code == 200:
                expiry = r.json().get("token", {}).get("expiry", 0)
                if expiry < 300: # Less than 5 mins
                    logger.info("Session expanding/refreshing...")
                    self.authenticate()
            else:
                self.authenticate()
        except Exception:
            self.authenticate()

    def get_datasets(self, region: str = "USA", universe: str = "TOP3000", delay: int = 1) -> List[Dict]:
        """Fetches available datasets."""
        self.check_session()
        params = {
            "region": region,
            "delay": delay,
            "universe": universe,
            "instrumentType": "EQUITY"
        }
        try:
            r = self.session.get(f"{self.base_url}/data-sets", params=params)
            r.raise_for_status()
            return r.json().get("results", [])
        except Exception as e:
            logger.error(f"Failed to fetch datasets: {e}")
            return []

    def get_datafields(self, dataset_id: str, region: str = "USA", universe: str = "TOP3000", delay: int = 1) -> List[Dict]:
        """Fetches datafields for a dataset."""
        self.check_session()
        params = {
            "region": region,
            "delay": delay,
            "universe": universe,
            "datasetId": dataset_id,
            "instrumentType": "EQUITY",
            "limit": 50
        }
        try:
            r = self.session.get(f"{self.base_url}/data-fields", params=params)
            r.raise_for_status()
            return r.json().get("results", [])
        except Exception as e:
            logger.error(f"Failed to fetch datafields: {e}")
            return []
            
    def get_operators(self) -> List[Dict]:
        """Fetches available operators."""
        self.check_session()
        try:
            r = self.session.get(f"{self.base_url}/operators")
            r.raise_for_status()
            return r.json().get("results", [])
        except Exception as e:
            logger.error(f"Failed to fetch operators: {e}")
            return []

    def simulate_batch(self, configs: List[Dict], concurrency: int = 5) -> List[Dict]:
        """
        Simulates a batch of alphas. 
        Note: This uses the multisimulation endpoint for efficiency.
        """
        self.check_session()
        
        # Split into chunks if too large (Brain has limits)
        results = []
        chunk_size = 10 # Brain supports up to 10-20 usually
        
        for i in range(0, len(configs), chunk_size):
            chunk = configs[i:i+chunk_size]
            try:
                # Construct multisimulation payload
                # Note: Brain API for creating simulations is singular, 
                # but we can use concurrent/async calls or loop.
                # 'ace_lib' used 'simulate_alpha_list_multi' which likely manages threads.
                # For simplicity in this v1, we will loop sequentially or use ThreadPool in future.
                # OR we use the actual /simulations endpoint which might support batch? 
                # Ace_lib suggests creating individual simulations and tracking them.
                
                # Let's use simple sequential for safety in this MVP step, 
                # or implement a simple loop.
                for config in chunk:
                    res = self.simulate_single(config)
                    results.append(res)
                    time.sleep(1) # Rate limit protection
            except Exception as e:
                logger.error(f"Batch simulation error: {e}")
        
        return results

    def simulate_single(self, config: Dict) -> Dict:
        """Simulates a single alpha configuration."""
        try:
            r = self.session.post(f"{self.base_url}/simulations", json=config)
            r.raise_for_status()
            
            # Polling for result
            loc = r.headers.get("Location")
            if not loc:
                return {"status": "ERROR", "message": "No location header"}
            
            while True:
                prog_res = self.session.get(loc)
                if prog_res.status_code == 200:
                    data = prog_res.json()
                    status = data.get("status")
                    if status == "COMPLETED":
                        alpha_id = data.get("alpha")
                        # Fetch full results
                        detail_res = self.session.get(f"{self.base_url}/alphas/{alpha_id}")
                        return {"status": "SUCCESS", "alpha_id": alpha_id, "detail": detail_res.json()}
                    elif status == "ERROR":
                        return {"status": "ERROR", "message": data.get("message", "Unknown error")}
                    
                    # Wait and retry
                    retry_after = float(prog_res.headers.get("Retry-After", 2))
                    time.sleep(retry_after)
                else:
                    time.sleep(2)
                    
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

brain_client = BrainAdapter()
