"""
API Client for football-data.org v4.
All data comes exclusively from https://api.football-data.org/v4/
Authentication via X-Auth-Token header.
"""
import os
import sys
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# Rate limit: 10 requests/minute on free tier → minimum 6s between requests
REQUEST_DELAY_SECONDS = 7


class APIClient:
    BASE_URL = "https://api.football-data.org/v4"

    def __init__(self):
        self.token = os.getenv("API_FOOTBALL_TOKEN")
        if not self.token:
            print("CRITICAL: API_FOOTBALL_TOKEN not set in environment.")
            sys.exit(1)

        self.headers = {
            "X-Auth-Token": self.token
        }
        self._request_count = 0

    def _make_request(self, endpoint, params=None, name="unknown"):
        """
        Execute a GET request against football-data.org.
        Includes mandatory logging, rate limiting, and error handling.
        Returns the parsed JSON response body or exits on failure.
        """
        url = f"{self.BASE_URL}/{endpoint}"
        self._request_count += 1

        print(f"\n[REQUEST #{self._request_count}] {name}")
        print(f"  URL: {url}")
        print(f"  Params: {params or '{}'}")

        start_time = time.time()

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            elapsed = time.time() - start_time
            status = response.status_code

            print(f"  Status: {status}")
            print(f"  Duration: {elapsed:.2f}s")
            print(f"  Response size: {len(response.content)} bytes")

            # Check rate limit headers
            remaining = response.headers.get("X-Requests-Available-Minute")
            if remaining is not None:
                print(f"  Rate limit remaining: {remaining}/min")

            if status == 429:
                print("  ERROR: Rate limit exceeded. Waiting 60s before retry...")
                time.sleep(60)
                return self._make_request(endpoint, params, name)

            if status == 403:
                print(f"  CRITICAL: Authentication failed (403). Check API_FOOTBALL_TOKEN.")
                print(f"  Response: {response.text[:300]}")
                sys.exit(1)

            if status != 200:
                print(f"  ERROR: Unexpected status {status}")
                print(f"  Response: {response.text[:500]}")
                sys.exit(1)

            data = response.json()

            # Check for API error messages
            if "errorCode" in data:
                print(f"  API ERROR: {data.get('message', 'Unknown error')}")
                sys.exit(1)

            return data

        except requests.exceptions.Timeout:
            print(f"  CRITICAL: Request timed out after 30s")
            sys.exit(1)
        except requests.exceptions.ConnectionError as e:
            print(f"  CRITICAL: Connection failed: {e}")
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            print(f"  CRITICAL: Request failed: {e}")
            sys.exit(1)

    def _throttle(self):
        """Enforce rate limiting between requests."""
        print(f"  Throttle: waiting {REQUEST_DELAY_SECONDS}s...")
        time.sleep(REQUEST_DELAY_SECONDS)

    def get_scheduled_matches(self, date_from=None, date_to=None):
        """
        GET /v4/matches?status=SCHEDULED
        Returns all scheduled matches across ALL available competitions.
        No league filtering — returns everything the API plan allows.
        """
        params = {"status": "SCHEDULED"}
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to

        data = self._make_request(
            "matches",
            params=params,
            name="Scheduled Matches (all competitions)"
        )
        matches = data.get("matches", [])
        print(f"  Found {len(matches)} scheduled matches total")
        return matches

    def get_standings(self, competition_code):
        """
        GET /v4/competitions/{code}/standings
        Returns standings for a specific competition.
        """
        self._throttle()
        data = self._make_request(
            f"competitions/{competition_code}/standings",
            name=f"Standings ({competition_code})"
        )
        standings = data.get("standings", [])
        print(f"  Found {len(standings)} standing types (TOTAL/HOME/AWAY)")
        return standings

    def get_finished_matches(self, competition_code, limit=100):
        """
        GET /v4/competitions/{code}/matches?status=FINISHED&limit={limit}
        Returns finished matches for calculating team statistics.
        """
        self._throttle()
        data = self._make_request(
            f"competitions/{competition_code}/matches",
            params={"status": "FINISHED", "limit": limit},
            name=f"Finished Matches ({competition_code}, limit={limit})"
        )
        matches = data.get("matches", [])
        print(f"  Found {len(matches)} finished matches")
        return matches
