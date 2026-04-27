import json
import sys
from api_client import FootyStatsClient

def main():
    if len(sys.argv) < 2:
        print("Usage: python mapping_helper.py <footystats_league_id>")
        return

    league_id = int(sys.argv[1])
    client = FootyStatsClient()
    
    print(f"Fetching matches for league {league_id} to identify teams...")
    matches = client.get_league_matches(league_id)
    
    teams = {}
    for m in matches:
        teams[m['homeID']] = m['home_name']
        teams[m['awayID']] = m['away_name']
        
    print("\nDetected Teams (ID: Name):")
    for tid, name in sorted(teams.items(), key=lambda x: x[1]):
        print(f"{tid}: {name}")

if __name__ == "__main__":
    main()
