import json
import os

DATA_PATH = "/app/shared/data/matches.json"

def calculate_flags(match):
    rank_home = match.get('rank_home')
    rank_away = match.get('rank_away')
    
    if rank_home is None or rank_away is None:
        match['is_goliath_vs_david'] = False
        return match
    
    # Goliath vs David Logic:
    # (rank_home <= 4 AND rank_away >= 14) OR (rank_away <= 4 AND rank_home >= 14)
    is_goliath_vs_david = (
        (rank_home <= 4 and rank_away >= 14) or
        (rank_away <= 4 and rank_home >= 14)
    )
    
    match['is_goliath_vs_david'] = is_goliath_vs_david
    
    # Identify who is the Goliath
    match['goliath_team'] = "home" if rank_home <= 4 else ("away" if rank_away <= 4 else None)
    
    return match

def main():
    if not os.path.exists(DATA_PATH):
        print(f"File {DATA_PATH} not found. Skipping engine.")
        return
        
    with open(DATA_PATH, "r") as f:
        matches = json.load(f)
        
    processed_matches = [calculate_flags(m) for m in matches]
    
    with open(DATA_PATH, "w") as f:
        json.dump(processed_matches, f, indent=4)
        
    print(f"Processed {len(processed_matches)} matches with engine flags.")

if __name__ == "__main__":
    main()
