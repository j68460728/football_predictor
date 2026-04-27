import json
import os
from datetime import datetime
from api_client import APIClient
from transformers import transform_match_data

TOP_LEAGUES = [39, 140, 135, 78, 61]
DATA_PATH = "/app/shared/data/matches.json"

def main():
    client = APIClient()
    today = datetime.now().strftime("%Y-%m-%d")
    season = 2025  # Corresponding to 2025/26 season
    
    all_matches = []
    
    for league_id in TOP_LEAGUES:
        print(f"Processing league {league_id}...")
        fixtures = client.get_fixtures(today, league_id)
        if not fixtures:
            continue
            
        standings = client.get_standings(league_id, season)
        if not standings:
            continue
            
        for fixture in fixtures:
            home_id = fixture['teams']['home']['id']
            away_id = fixture['teams']['away']['id']
            
            print(f"  Fetching stats for {fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}")
            home_stats = client.get_team_statistics(league_id, home_id, season)
            away_stats = client.get_team_statistics(league_id, away_id, season)
            
            # 1. Scraper Robustness: Discard matches without stats
            if not home_stats or not away_stats:
                print(f"    Skipping match: Missing statistics.")
                continue
                
            match_data = transform_match_data(fixture, standings, home_stats, away_stats)
            
            # 1. Scraper Robustness: Discard matches without standings
            if match_data.get('rank_home') is None or match_data.get('rank_away') is None:
                print(f"    Skipping match: Missing standings.")
                continue

            all_matches.append(match_data)
            
    # Ensure directory exists
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    
    with open(DATA_PATH, "w") as f:
        json.dump(all_matches, f, indent=4)
        
    print(f"Successfully saved {len(all_matches)} matches to {DATA_PATH}")

if __name__ == "__main__":
    main()
