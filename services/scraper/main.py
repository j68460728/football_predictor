"""
Football Predictor Scraper — League & Cup Dynamic Integration
============================================================
Pipeline:
  1. Fetch ALL scheduled matches (today/tomorrow).
  2. Detect all involved competitions (Leagues & Cups).
  3. Pre-fetch domestic rankings for CORE_LEAGUES to build a global map.
  4. Fetch historical matches for stats for EVERY detected competition.
  5. Transform matches using the global ranking map as a baseline.
  6. Write matches.json.

NO mock data. NO invented values.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

from api_client import APIClient
from transformers import (
    build_rankings_map,
    calculate_team_stats,
    transform_scheduled_match,
)

DATA_PATH = "/app/shared/data/matches.json"

# All domestic leagues included in the Tier One (free) plan
CORE_LEAGUES = ["PL", "PD", "SA", "BL1", "FL1", "PPL", "DED", "BSA", "ELC"]


def main():
    start_time = time.time()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    range_end = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")

    print("=" * 60)
    print("FOOTBALL PREDICTOR SCRAPER — LEAGUE & CUP MODE")
    print("Source: football-data.org v4")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print(f"Date range: {today} → {range_end} (7 days)")
    print("=" * 60)

    client = APIClient()

    # ─── Step 1: Pre-fetch Global Rankings ───
    print("\n" + "─" * 40)
    print("STEP 1: Building global ranking map from core leagues")
    print("─" * 40)
    
    global_rankings = {}
    for code in CORE_LEAGUES:
        print(f"  Fetching standings for {code}...")
        try:
            standings = client.get_standings(code)
            if standings:
                league_map = build_rankings_map(standings)
                global_rankings.update(league_map)
                print(f"    Added {len(league_map)} teams to global map.")
        except SystemExit:
            print(f"    WARNING: Could not fetch standings for {code}. Skipping.")

    print(f"\nGlobal ranking map contains {len(global_rankings)} teams.")

    # ─── Step 2: Get all scheduled matches ───
    print("\n" + "─" * 40)
    print("STEP 2: Fetching ALL scheduled matches")
    print("─" * 40)

    all_scheduled = client.get_scheduled_matches(
        date_from=today,
        date_to=range_end
    )

    if not all_scheduled:
        print("\nNo scheduled matches returned by API.")
        _write_output([], start_time)
        return

    # ─── Step 3: Detect and fetch stats for all competitions ───
    print("\n" + "─" * 40)
    print("STEP 3: Processing detected competitions")
    print("─" * 40)

    league_matches = {}
    for match in all_scheduled:
        comp = match.get("competition", {})
        code = comp.get("code")
        name = comp.get("name", code)
        comp_type = comp.get("type", "LEAGUE")

        if not code: continue

        if code not in league_matches:
            league_matches[code] = {"name": name, "type": comp_type, "matches": []}
        league_matches[code]["matches"].append(match)

    detected_codes = list(league_matches.keys())
    print(f"Detected {len(detected_codes)} competitions.")

    league_stats = {}
    for i, code in enumerate(detected_codes):
        lg = league_matches[code]
        print(f"\n--- [{i+1}/{len(detected_codes)}] {code} ({lg['name']}) [{lg['type']}] ---")

        try:
            finished = client.get_finished_matches(code, limit=100)
            if finished:
                stats = calculate_team_stats(finished)
                print(f"  Stats calculated for {len(stats)} teams.")
                league_stats[code] = stats
            else:
                print(f"  WARNING: No match history found.")
                league_stats[code] = {}
        except SystemExit:
            print(f"  WARNING: Failed to fetch history for {code}.")
            league_stats[code] = {}

    # ─── Step 4: Transform matches ───
    print("\n" + "─" * 40)
    print("STEP 4: Transforming matches")
    print("─" * 40)

    all_matches = []
    skipped = 0

    for code in detected_codes:
        lg = league_matches[code]
        stats = league_stats.get(code, {})

        print(f"\n  Processing {len(lg['matches'])} matches in {code}...")

        for match in lg["matches"]:
            result = transform_scheduled_match(match, global_rankings, stats)
            if result:
                all_matches.append(result)
            else:
                skipped += 1

    # ─── Step 5: Write output ───
    _write_output(all_matches, start_time, skipped, len(detected_codes), client._request_count)


def _write_output(all_matches, start_time, skipped, league_count, request_count):
    """Validate and write the final matches.json."""
    print("\n" + "─" * 40)
    print("STEP 5: Output and Summary")
    print("─" * 40)

    # Note: We are now more relaxed about missing ranks/stats to show all matches
    # but the engine will naturally ignore those for Goliath logic.
    valid_matches = []
    for match in all_matches:
        # We still need team names and basic info
        if match.get("home_team") and match.get("away_team"):
            valid_matches.append(match)

    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump(valid_matches, f, indent=4)

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print("SCRAPER COMPLETE")
    print(f"  Total matches saved: {len(valid_matches)}")
    print(f"  API requests: {request_count}")
    print(f"  Duration: {elapsed:.1f}s")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
