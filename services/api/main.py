import json
import os
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Football Predictor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = "/app/shared/data/matches.json"

@app.get("/matches")
def get_matches(
    league: Optional[int] = Query(None),
    goliath: Optional[bool] = Query(None),
    goliath_home: Optional[bool] = Query(None),
    goliath_away: Optional[bool] = Query(None)
):
    if not os.path.exists(DATA_PATH):
        return []
        
    try:
        with open(DATA_PATH, "r") as f:
            matches = json.load(f)
    except Exception:
        return []
        
    filtered_matches = matches
    
    if league is not None:
        filtered_matches = [m for m in filtered_matches if m.get('league_id') == league]
        
    if goliath is not None:
        filtered_matches = [m for m in filtered_matches if m.get('is_goliath_vs_david') == goliath]
        
    if goliath_home is not None:
        filtered_matches = [m for m in filtered_matches if (m.get('goliath_team') == 'home') == goliath_home]

    if goliath_away is not None:
        filtered_matches = [m for m in filtered_matches if (m.get('goliath_team') == 'away') == goliath_away]

    return filtered_matches

@app.get("/health")
def health():
    return {"status": "ok"}
