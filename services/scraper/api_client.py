import os
import requests
from dotenv import load_dotenv

load_dotenv()

class APIClient:
    BASE_URL = "https://v3.football.api-sports.io"
    
    def __init__(self):
        self.api_key = os.getenv("API_FOOTBALL_KEY")
        self.headers = {
            'x-rapidapi-host': "v3.football.api-sports.io",
            'x-rapidapi-key': self.api_key
        }

    def get_fixtures(self, date, league_id):
        url = f"{self.BASE_URL}/fixtures"
        params = {"date": date, "league": league_id}
        response = requests.get(url, headers=self.headers, params=params)
        return response.json().get("response", [])

    def get_standings(self, league_id, season=2024):
        url = f"{self.BASE_URL}/standings"
        params = {"league": league_id, "season": season}
        response = requests.get(url, headers=self.headers, params=params)
        return response.json().get("response", [])

    def get_team_statistics(self, league_id, team_id, season=2024):
        url = f"{self.BASE_URL}/teams/statistics"
        params = {"league": league_id, "team": team_id, "season": season}
        response = requests.get(url, headers=self.headers, params=params)
        return response.json().get("response", {})
