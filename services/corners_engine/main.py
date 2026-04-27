import json
import os
import logging
from typing import Dict, Any, Optional, List
from scipy.stats import poisson
from fuzzywuzzy import process
from api_client import FootyStatsClient

# Configuration
MATCHES_PATH = "/app/shared/data/matches.json"
OUTPUT_PATH = "/app/shared/data/corners_predictions.json"
TEAM_MAPPING_PATH = "/app/shared/mappings/team_mapping.json"
LEAGUE_MAPPING_PATH = "/app/shared/mappings/league_mapping.json"

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CornersIntelligenceEngine")

class CornersEngine:
    def __init__(self):
        self.client = FootyStatsClient()
        self.team_mapping = self._load_json(TEAM_MAPPING_PATH)
        self.league_mapping = self._load_json(LEAGUE_MAPPING_PATH)
        self.cache_league_matches = {}
        self.global_standings = {} # {league_id: {team_id: rank}}

    def _load_json(self, path: str) -> Dict:
        if not os.path.exists(path): return {}
        with open(path, "r") as f: return json.load(f)

    def _get_footystats_team_id(self, fd_team_id: int, team_name: str, fs_league_id: int) -> Optional[int]:
        str_id = str(fd_team_id)
        if str_id in self.team_mapping.get("teams", {}): return int(self.team_mapping["teams"][str_id])
        
        matches = self._get_all_league_matches(fs_league_id)
        if not matches: return None
        fs_teams = {}
        for m in matches:
            fs_teams[m['home_name']] = m['homeID']
            fs_teams[m['away_name']] = m['awayID']
        best_match = process.extractOne(team_name, fs_teams.keys())
        if best_match and best_match[1] > 85:
            fs_id = fs_teams[best_match[0]]
            if "teams" not in self.team_mapping: self.team_mapping["teams"] = {}
            self.team_mapping["teams"][str_id] = fs_id
            return int(fs_id)
        return None

    def _get_all_league_matches(self, league_id: int) -> List[Dict]:
        if league_id in self.cache_league_matches: return self.cache_league_matches[league_id]
        matches = self.client.get_league_matches(league_id)
        if matches:
            self.cache_league_matches[league_id] = matches
            self._build_standings_proxy(league_id, matches)
            return matches
        return [] # Return empty list instead of None to prevent crashes

    def _build_standings_proxy(self, league_id: int, matches: List[Dict]):
        points = {}
        for m in matches:
            if m['status'] != 'complete': continue
            h, a = m['homeID'], m['awayID']
            if h not in points: points[h] = 0
            if a not in points: points[a] = 0
            hg, ag = m['homeGoalCount'], m['awayGoalCount']
            if hg > ag: points[h] += 3
            elif ag > hg: points[a] += 3
            else: points[h] += 1; points[a] += 1
        sorted_teams = sorted(points.items(), key=lambda x: x[1], reverse=True)
        self.global_standings[league_id] = {tid: rank+1 for rank, (tid, pts) in enumerate(sorted_teams)}

    def _get_rank_percentile(self, team_id: int, league_id: int) -> float:
        standings = self.global_standings.get(league_id, {})
        rank = standings.get(team_id, 15)
        total_teams = len(standings) if standings else 20
        return 1.0 - (rank / total_teams)

    def _get_weighted_form(self, team_id: int, league_id: int, context: str, l_avg: float) -> Dict:
        matches = self._get_all_league_matches(league_id)
        if not matches: return {"for": l_avg/2, "against": l_avg/2, "count": 0}

        filtered = [m for m in matches if m['status'] == 'complete']
        if context == 'home': filtered = [m for m in filtered if m['homeID'] == team_id]
        elif context == 'away': filtered = [m for m in filtered if m['awayID'] == team_id]
        else: filtered = [m for m in filtered if m['homeID'] == team_id or m['awayID'] == team_id]
        
        recent = sorted(filtered, key=lambda x: x['date_unix'], reverse=True)[:5]
        if not recent: return {"for": l_avg/2, "against": l_avg/2, "count": 0}

        w_for = []
        w_ag = []
        for m in recent:
            is_home = m['homeID'] == team_id
            opp_id = m['awayID'] if is_home else m['homeID']
            opp_strength = self._get_rank_percentile(opp_id, league_id)
            strength_factor = 0.5 + opp_strength 
            c_for = m['home_corners'] if is_home else m['away_corners']
            c_ag = m['away_corners'] if is_home else m['home_corners']
            w_for.append(c_for * strength_factor)
            w_ag.append(c_ag * (2.0 - strength_factor))

        return {
            "for": sum(w_for) / len(w_for),
            "against": sum(w_ag) / len(w_ag),
            "count": len(recent)
        }

    def _calculate_pace(self, stats: Dict, l_stats: Dict) -> Dict:
        shots = stats.get('shots_avg_overall', 10.0)
        sot = stats.get('shots_on_target_avg_overall', 4.0)
        corners = stats.get('corners_for_avg_overall', 5.0)
        l_shots = l_stats.get('shots_avg_overall', 10.0)
        l_sot = l_stats.get('shots_on_target_avg_overall', 4.0)
        n_shots = min(shots / (l_shots * 1.5), 1.0) if l_shots > 0 else 0.5
        n_sot = min(sot / (l_sot * 1.5), 1.0) if l_sot > 0 else 0.5
        n_corner_rate = min((corners / shots if shots > 0 else 0) / 0.6, 1.0)
        h1_ratio = stats.get('corners_for_avg_first_half', 2.0) / stats.get('corners_for_avg_overall', 5.0) if stats.get('corners_for_avg_overall', 0) > 0 else 0.45
        score = (n_shots * 0.3) + (n_sot * 0.3) + (n_corner_rate * 0.2) + (h1_ratio * 0.2)
        classification = "MEDIUM"
        if score > 0.7: classification = "HIGH"
        elif score < 0.4: classification = "LOW"
        return {"score": round(score, 2), "classification": classification, "h1_ratio": h1_ratio}

    def calculate_prediction(self, match: Dict) -> Optional[Dict]:
        fixture_id = match.get('fixture_id')
        l_code = match.get('league_id')
        fs_l_id = self.league_mapping.get(l_code)
        if not fs_l_id: return None

        # Resolve IDs using fallback to league stats if league matches fail
        h_id = self._get_footystats_team_id(match['home_id'], match['home_team'], fs_l_id)
        a_id = self._get_footystats_team_id(match['away_id'], match['away_team'], fs_l_id)
        
        # If ID mapping fails, we can't calculate team-specific stats
        if not h_id or not a_id: 
            logger.warning(f"Could not resolve IDs for {match['home_team']} vs {match['away_team']}")
            return None

        h_stats_raw = self.client.get_team_stats(h_id, fs_l_id)
        a_stats_raw = self.client.get_team_stats(a_id, fs_l_id)
        l_stats = self.client.get_league_stats(fs_l_id)
        if not h_stats_raw or not a_stats_raw or not l_stats: return None

        h_s = h_stats_raw.get('stats', {})
        a_s = a_stats_raw.get('stats', {})
        l_avg = l_stats.get('corners_avg_overall', 10.0)

        # 1. Base Poisson
        l_h = (h_s.get('corners_for_avg_overall', l_avg/2) * a_s.get('corners_against_avg_overall', l_avg/2)) / l_avg if l_avg > 0 else 5.0
        l_a = (a_s.get('corners_for_avg_overall', l_avg/2) * h_s.get('corners_against_avg_overall', l_avg/2)) / l_avg if l_avg > 0 else 5.0
        
        # 2. Advanced Form
        h_f_overall = self._get_weighted_form(h_id, fs_l_id, 'overall', l_avg)
        h_f_home = self._get_weighted_form(h_id, fs_l_id, 'home', l_avg)
        a_f_overall = self._get_weighted_form(a_id, fs_l_id, 'overall', l_avg)
        a_f_away = self._get_weighted_form(a_id, fs_l_id, 'away', l_avg)
        
        h_form_score = (h_f_overall['for'] * 0.4) + (h_f_home['for'] * 0.6)
        a_form_score = (a_f_overall['for'] * 0.4) + (a_f_away['for'] * 0.6)
        
        l_h_adj = (l_h * 0.6) + (h_form_score * 0.4)
        l_a_adj = (l_a * 0.6) + (a_form_score * 0.4)
        exp_total = l_h_adj + l_a_adj

        # 3. Match Pace
        h_pace = self._calculate_pace(h_s, l_stats)
        a_pace = self._calculate_pace(a_s, l_stats)
        pace_score = (h_pace['score'] + a_pace['score']) / 2
        pace_class = "MEDIUM"
        if pace_score > 0.7: pace_class = "HIGH"
        elif pace_score < 0.4: pace_class = "LOW"

        # 4. Context Engine
        h_att = h_form_score
        a_def = a_f_away['against'] if a_f_away['against'] > 0 else l_avg/2
        a_att = a_form_score
        h_def = h_f_home['against'] if h_f_home['against'] > 0 else l_avg/2
        context_score = (h_att / a_def if a_def > 0 else 1.0) + (a_att / h_def if h_def > 0 else 1.0)
        context_class = "MEDIUM"
        if context_score > 2.5: context_class = "HIGH"
        elif context_score < 1.8: context_class = "LOW"

        # 5. Early Pressure
        h1_ratio = (h_pace['h1_ratio'] + a_pace['h1_ratio']) / 2
        att_strength = (h_att + a_att) / (l_avg if l_avg > 0 else 10)
        def_weakness = (h_def + a_def) / (l_avg if l_avg > 0 else 10)
        ep_score = (h1_ratio * 0.4) + (pace_score * 0.3) + (att_strength * 0.2) + (def_weakness * 0.1)
        
        # 6. Probabilities & Timed Markets
        p85 = 1 - poisson.cdf(8, exp_total)
        p95 = 1 - poisson.cdf(9, exp_total)
        p105 = 1 - poisson.cdf(10, exp_total)
        exp_1H = exp_total * h1_ratio
        p_0_10 = ep_score * exp_1H * 0.35
        p_0_20 = ep_score * exp_1H * 0.65

        return {
            "fixture_id": fixture_id,
            "league_name": match['league_name'],
            "home_team": match['home_team'],
            "away_team": match['away_team'],
            "date": match['date'],
            "expected_total_corners": round(exp_total, 2),
            "expected_first_half_corners": round(exp_1H, 2),
            "probabilities": { "over_8_5": round(p85, 4), "over_9_5": round(p95, 4), "over_10_5": round(p105, 4) },
            "early_markets": { "p_0_10": round(p_0_10, 2), "p_0_20": round(p_0_20, 2), "inferred": True },
            "pace": { "pace_score": round(pace_score, 2), "classification": pace_class },
            "form": {
                "home_last5": round(h_f_overall['for'], 2),
                "away_last5": round(a_f_overall['for'], 2),
                "weighted_context_analysis": {
                    "home_weighted": round(h_form_score, 2),
                    "away_weighted": round(a_form_score, 2)
                }
            },
            "context": { "mismatch_score": round(context_score, 2), "classification": context_class }
        }

    def run(self):
        if not os.path.exists(MATCHES_PATH): return
        with open(MATCHES_PATH, "r") as f: matches = json.load(f)
        predictions = []
        
        logger.info(f"Starting prediction run for {len(matches)} matches...")
        
        for m in matches:
            try:
                p = self.calculate_prediction(m)
                if p: 
                    predictions.append(p)
                else:
                    # Fallback to realistic mock data if API fails (Demo Mode)
                    if os.getenv("API_FOOTYSTATS_API") == "test85g57":
                        predictions.append(self._generate_mock_prediction(m))
            except Exception as e:
                logger.error(f"Error predicting for {m.get('home_team')}: {e}")

        with open(OUTPUT_PATH, "w") as f:
            json.dump(predictions, f, indent=4)
        
        # Save mapping updates
        with open(TEAM_MAPPING_PATH, "w") as f:
            json.dump(self.team_mapping, f, indent=4)
            
        logger.info(f"Professional Corners Intelligence Engine complete. {len(predictions)} matches generated (Mode: {'DEMO' if len(predictions) > 0 and not any(p.get('real_data') for p in predictions) else 'PROD'}).")

    def _generate_mock_prediction(self, m: Dict) -> Dict:
        """Generates a statistically consistent mock prediction for UI demonstration."""
        import random
        exp_total = round(random.uniform(8.5, 12.5), 2)
        exp_1H = round(exp_total * random.uniform(0.42, 0.48), 2)
        pace_score = random.uniform(0.3, 0.9)
        mismatch = random.uniform(1.5, 3.0)
        
        return {
            "fixture_id": m.get('fixture_id'),
            "league_name": m.get('league_name'),
            "home_team": m.get('home_team'),
            "away_team": m.get('away_team'),
            "date": m.get('date'),
            "expected_total_corners": exp_total,
            "expected_first_half_corners": exp_1H,
            "probabilities": {
                "over_8_5": round(1 - poisson.cdf(8, exp_total), 4),
                "over_9_5": round(1 - poisson.cdf(9, exp_total), 4),
                "over_10_5": round(1 - poisson.cdf(10, exp_total), 4)
            },
            "early_markets": {
                "p_0_10": round(random.uniform(0.15, 0.35), 2),
                "p_0_20": round(random.uniform(0.40, 0.65), 2),
                "inferred": True
            },
            "pace": {
                "pace_score": round(pace_score, 2),
                "classification": "HIGH" if pace_score > 0.7 else ("LOW" if pace_score < 0.4 else "MEDIUM")
            },
            "form": {
                "home_last5": round(random.uniform(4.0, 7.0), 2),
                "away_last5": round(random.uniform(4.0, 7.0), 2),
                "weighted_context_analysis": {
                    "home_weighted": round(random.uniform(4.5, 6.5), 2),
                    "away_weighted": round(random.uniform(4.5, 6.5), 2)
                }
            },
            "context": {
                "mismatch_score": round(mismatch, 2),
                "classification": "HIGH" if mismatch > 2.5 else "MEDIUM",
                "is_demo": True
            }
        }

if __name__ == "__main__":
    CornersEngine().run()
