import requests
import os
import time
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FootyStatsClient")

load_dotenv()

class FootyStatsClient:
    BASE_URL = "https://api.football-data-api.com"
    
    def __init__(self):
        self.api_key = os.getenv("API_FOOTYSTATS_API")
        if not self.api_key:
            logger.error("API_FOOTYSTATS_API not found in environment variables.")
            raise ValueError("Missing FootyStats API Key")
        
        self.session = requests.Session()
        logger.info("FootyStats Client initialized.")

    def _request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        if params is None:
            params = {}
        
        params["key"] = self.api_key
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            logger.info(f"[FOOTYSTATS] Requesting {endpoint} with params: { {k:v for k,v in params.items() if k != 'key'} }")
            start_time = time.time()
            response = self.session.get(url, params=params, timeout=15)
            duration = time.time() - start_time
            
            logger.info(f"[FOOTYSTATS] Status: {response.status_code} | Duration: {duration:.2f}s")
            
            if response.status_code == 429:
                logger.warning("[FOOTYSTATS] Rate limit exceeded (429).")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                logger.error(f"[FOOTYSTATS] API returned success=false: {data.get('error', 'Unknown error')}")
                return None
                
            return data.get("data")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[FOOTYSTATS] Request failed: {e}")
            return None

    def get_league_list(self) -> List[Dict[str, Any]]:
        """Get list of all leagues available in the API."""
        endpoint = "/league-list"
        return self._request(endpoint) or []

    def get_league_matches(self, season_id: int) -> List[Dict[str, Any]]:
        """Get all matches for a specific league season. Used for form analysis."""
        endpoint = "/league-matches"
        params = {"season_id": season_id}
        return self._request(endpoint, params=params) or []

    def get_team_stats(self, team_id: int, season_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed stats for a team in a specific league season."""
        endpoint = "/team"
        params = {"team_id": team_id, "league_id": season_id} # FootyStats uses league_id param for season ID in /team
        return self._request(endpoint, params=params)

    def get_league_stats(self, season_id: int) -> Optional[Dict[str, Any]]:
        """Get aggregated stats for a whole league season."""
        endpoint = "/league-stats"
        params = {"league_id": season_id} # FootyStats uses league_id param for season ID in /league-stats
        return self._request(endpoint, params=params)

    def get_match_details(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Get deep match details."""
        endpoint = "/match"
        params = {"match_id": match_id}
        return self._request(endpoint, params=params)
