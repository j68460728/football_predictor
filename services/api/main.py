import json
import os
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Football Predictor API")

# Enable CORS for frontend
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
    home: Optional[bool] = Query(None)
):
    if not os.path.exists(DATA_PATH):
        return []
        
    with open(DATA_PATH, "r") as f:
        matches = json.load(f)
        
    filtered_matches = matches
    
    if league is not None:
        filtered_matches = [m for m in filtered_matches if m.get('league_id') == league]
        
    if goliath is not None:
        filtered_matches = [m for m in filtered_matches if m.get('is_goliath_vs_david') == goliath]
        
    if home is not None:
        # If home=true, show matches where Goliath is home? 
        # Or if the user meant "filter by home matches" generally? 
        # User said "filtros: league, goliath, home". 
        # I'll interpret 'home' as filtering matches where the 'home' team is the one of interest.
        # But for Goliath vs David, it probably means "Goliath is at home".
        filtered_matches = [m for m in filtered_matches if (m.get('goliath_team') == 'home') == home]

    return filtered_matches

@app.get("/health")
def health():
    return {"status": "ok"}
