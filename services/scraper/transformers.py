def transform_match_data(fixture, standings, home_stats, away_stats):
    """
    Unifies fixture, standings and statistics into a single match record.
    """
    home_team = fixture['teams']['home']
    away_team = fixture['teams']['away']
    
    # Extract ranks from standings
    home_rank = next((s['rank'] for s in standings[0]['league']['standings'][0] if s['team']['id'] == home_team['id']), None)
    away_rank = next((s['rank'] for s in standings[0]['league']['standings'][0] if s['team']['id'] == away_team['id']), None)
    
    # Extract goals averages
    # Home team stats at home
    home_avg_for = home_stats.get('goals', {}).get('for', {}).get('average', {}).get('home', 0)
    home_avg_against = home_stats.get('goals', {}).get('against', {}).get('average', {}).get('home', 0)
    
    # Away team stats away
    away_avg_for = away_stats.get('goals', {}).get('for', {}).get('average', {}).get('away', 0)
    away_avg_against = away_stats.get('goals', {}).get('against', {}).get('average', {}).get('away', 0)
    
    return {
        "fixture_id": fixture['fixture']['id'],
        "date": fixture['fixture']['date'],
        "league_id": fixture['league']['id'],
        "league_name": fixture['league']['name'],
        "home_team": home_team['name'],
        "home_id": home_team['id'],
        "away_team": away_team['name'],
        "away_id": away_team['id'],
        "rank_home": home_rank,
        "rank_away": away_rank,
        "home_avg_goals_for": float(home_avg_for) if home_avg_for else 0.0,
        "home_avg_goals_against": float(home_avg_against) if home_avg_against else 0.0,
        "away_avg_goals_for": float(away_avg_for) if away_avg_for else 0.0,
        "away_avg_goals_against": float(away_avg_against) if away_avg_against else 0.0
    }
