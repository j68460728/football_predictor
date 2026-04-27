"""
Transformers for football-data.org v4 responses.
Calculates team statistics from match history — NO mock data, NO invented values.
"""


def build_rankings_map(standings):
    """
    Extract team rankings from standings response.
    Uses the TOTAL standing type only.
    
    Returns: dict mapping team_id -> position (int)
    """
    rankings = {}
    
    for standing in standings:
        if standing.get("type") != "TOTAL":
            continue
        table = standing.get("table", [])
        for entry in table:
            team_id = entry["team"]["id"]
            position = entry["position"]
            rankings[team_id] = position
    
    return rankings


def calculate_team_stats(finished_matches):
    """
    Calculate average goals for/against per team, split by home/away,
    from a list of FINISHED matches.
    
    Returns: dict mapping team_id -> {
        "home_goals_for": [list],
        "home_goals_against": [list],
        "away_goals_for": [list],
        "away_goals_against": [list],
    }
    """
    stats = {}
    
    for match in finished_matches:
        score = match.get("score", {})
        full_time = score.get("fullTime", {})
        
        home_goals = full_time.get("home")
        away_goals = full_time.get("away")
        
        # Skip matches without final scores
        if home_goals is None or away_goals is None:
            continue
        
        home_id = match["homeTeam"]["id"]
        away_id = match["awayTeam"]["id"]
        
        # Initialize team stats if not present
        for team_id in [home_id, away_id]:
            if team_id not in stats:
                stats[team_id] = {
                    "home_goals_for": [],
                    "home_goals_against": [],
                    "away_goals_for": [],
                    "away_goals_against": [],
                }
        
        # Home team scored home_goals at home, conceded away_goals
        stats[home_id]["home_goals_for"].append(home_goals)
        stats[home_id]["home_goals_against"].append(away_goals)
        
        # Away team scored away_goals away, conceded home_goals
        stats[away_id]["away_goals_for"].append(away_goals)
        stats[away_id]["away_goals_against"].append(home_goals)
    
    return stats


def get_team_averages(stats, team_id, location):
    """
    Calculate average goals for/against for a team at a specific location.
    
    location: "home" or "away"
    
    Returns: (avg_for, avg_against) or (None, None) if no data.
    """
    team_stats = stats.get(team_id)
    if not team_stats:
        return None, None
    
    goals_for = team_stats[f"{location}_goals_for"]
    goals_against = team_stats[f"{location}_goals_against"]
    
    if not goals_for or not goals_against:
        return None, None
    
    avg_for = round(sum(goals_for) / len(goals_for), 2)
    avg_against = round(sum(goals_against) / len(goals_against), 2)
    
    return avg_for, avg_against


def transform_scheduled_match(match, global_rankings, team_stats):
    """
    Transform a single scheduled match into the output format.
    Uses global_rankings to find domestic rank even for cup matches.
    
    Required fields for full stats — if missing, some metrics might be null:
        home_team, away_team, league_code, league_name, competition_type
    
    Returns: dict with match data, or None if team identities are missing.
    """
    home_id = match["homeTeam"]["id"]
    away_id = match["awayTeam"]["id"]
    home_name = match["homeTeam"]["name"]
    away_name = match["awayTeam"]["name"]
    comp = match["competition"]
    league_code = comp["code"]
    league_name = comp["name"]
    comp_type = comp.get("type", "LEAGUE")
    
    # Rankings from global map (domestic rank)
    rank_home = global_rankings.get(home_id)
    rank_away = global_rankings.get(away_id)
    
    # Statistics — home team playing at home, away team playing away
    # We use the team_stats which were fetched for this specific competition
    home_avg_for, home_avg_against = get_team_averages(team_stats, home_id, "home")
    away_avg_for, away_avg_against = get_team_averages(team_stats, away_id, "away")
    
    return {
        "fixture_id": match["id"],
        "date": match["utcDate"],
        "league_id": league_code,
        "league_name": league_name,
        "competition_type": comp_type,
        "home_team": home_name,
        "home_id": home_id,
        "away_team": away_name,
        "away_id": away_id,
        "rank_home": rank_home,
        "rank_away": rank_away,
        "home_avg_goals_for": home_avg_for,
        "home_avg_goals_against": home_avg_against,
        "away_avg_goals_for": away_avg_for,
        "away_avg_goals_against": away_avg_against,
        "matchday": match.get("matchday"),
        "status": match.get("status", "SCHEDULED"),
    }
