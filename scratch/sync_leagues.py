import requests
import json
import os

API_KEY = "test85g57"
MAPPING_PATH = "/home/coderman/projects/docker/web_apps/football_predictor/shared/mappings/league_mapping.json"

TARGET_LEAGUES = {
    "Premier League": "PL",
    "Primera Division": "PD",
    "Bundesliga": "BL1",
    "Serie A": "SA",
    "Ligue 1": "FL1",
    "Eredivisie": "DED",
    "Primeira Liga": "PPL",
    "Campeonato Brasileiro Série A": "BSA",
    "Championship": "ELC",
    "UEFA Champions League": "CL",
    "UEFA Europa League": "EL",
    "UEFA Europa Conference League": "EC"
}

def sync():
    url = f"https://api.football-data-api.com/league-list?key={API_KEY}"
    print(f"Fetching league list from {url}...")
    res = requests.get(url)
    if res.status_code != 200:
        print(f"Error fetching leagues: {res.status_code}")
        return

    data = res.json().get("data", [])
    new_mapping = {}
    
    for league in data:
        name = league.get("league_name")
        if name in TARGET_LEAGUES:
            code = TARGET_LEAGUES[name]
            # Get the latest season ID (highest year or just the last one in list)
            seasons = league.get("season", [])
            if seasons:
                latest_season = sorted(seasons, key=lambda x: x['year'], reverse=True)[0]
                new_mapping[code] = latest_season['id']
                print(f"Mapped {name} ({code}) to Season ID {latest_season['id']} (Year {latest_season['year']})")

    if new_mapping:
        with open(MAPPING_PATH, "w") as f:
            json.dump(new_mapping, f, indent=4)
        print(f"Updated mapping saved to {MAPPING_PATH}")
    else:
        print("No matches found for target leagues.")

if __name__ == "__main__":
    sync()
