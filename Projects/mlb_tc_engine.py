#!/usr/bin/env python3

# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""
MLB Triple Conservative Engine v1.0
====================================
Player prop projections for batting and pitching stats using ESPN season averages
and The Odds API for live DK lines.

TC Formulas (MLB):
  Batter TC = stat_avg × 0.85 (ACTIVE) | × 0.85 × 0.55 (Q/questionable) | × 0 (OUT)
  Pitcher TC = stat_avg × 0.80 (ACTIVE) | × 0.80 × 0.55 (Q) | × 0 (OUT)

  LINE = floor(TC × 0.88)
  EDGE = TC - LINE
  SIGNAL: edge > 2.0 → OVER | edge < -2.0 → UNDER | else → PASS

Usage:
  python3 mlb_tc_engine.py --game "MIA@PHI" --report
  python3 mlb_tc_engine.py --slate
  python3 mlb_tc_engine.py --backtest 2026-06-14

Author: Tyson | Zo Computer | TC Pipeline
"""

import argparse, csv, datetime, json, math, os, requests, sys
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# TC Constants (MLB-specific)
# ═══════════════════════════════════════════════════════════════════════════════
LINE_FACTOR = 0.88
Q_FACTOR = 0.55
OUT_FACTOR = 0.0
EDGE_THRESH = 2.0
EDGE_THRESH_SELF = 1.0
EDGE_THRESH_MLB_SDIO = 0.5

BATTER_WEIGHT = 0.85
PITCHER_WEIGHT = 0.80
GAP_BATTER = 0.0
GAP_PITCHER = -0.5

# Markets we track - map stat name to odds API market key
BATTER_MARKETS = {
    "hits": "batter_hits",
    "rbi": "batter_rbis",
    "runs": "batter_runs_scored",
    "hr": "batter_home_runs",
    "total_bases": "batter_total_bases",
    "sb": "batter_stolen_bases",
    "singles": "batter_singles",
    "doubles": "batter_doubles",
    "walks": "batter_walks",
}

PITCHER_MARKETS = {
    "strikeouts": "pitcher_strikeouts",
    "hits_allowed": "pitcher_hits_allowed",
    "walks": "pitcher_walks",
    "earned_runs": "pitcher_earned_runs",
    "outs": "pitcher_outs",
}

# MLB Team ID mapping (ESPN IDs)
MLB_TEAM_IDS = {
    "ARI": 29, "ATH": 11, "ATL": 15, "BAL": 1, "BOS": 2,
    "CHC": 16, "CHW": 4, "CIN": 17, "CLE": 5, "COL": 27,
    "DET": 6, "HOU": 18, "KC": 7, "LAA": 3, "LAD": 19,
    "MIA": 28, "MIL": 8, "MIN": 9, "NYM": 21, "NYY": 10,
    "PIT": 23, "PHI": 22, "SD": 25, "SEA": 12, "SF": 26,
    "STL": 24, "TB": 30, "TEX": 13, "TOR": 14, "WSH": 20,
}

MLB_TEAM_NAMES = {
    "ARI": "Arizona Diamondbacks", "ATH": "Athletics", "ATL": "Atlanta Braves",
    "BAL": "Baltimore Orioles", "BOS": "Boston Red Sox", "CHC": "Chicago Cubs",
    "CHW": "Chicago White Sox", "CIN": "Cincinnati Reds", "CLE": "Cleveland Guardians",
    "COL": "Colorado Rockies", "DET": "Detroit Tigers", "HOU": "Houston Astros",
    "KC": "Kansas City Royals", "LAA": "Los Angeles Angels", "LAD": "Los Angeles Dodgers",
    "MIA": "Miami Marlins", "MIL": "Milwaukee Brewers", "MIN": "Minnesota Twins",
    "NYM": "New York Mets", "NYY": "New York Yankees", "PIT": "Pittsburgh Pirates",
    "PHI": "Philadelphia Phillies", "SD": "San Diego Padres", "SEA": "Seattle Mariners",
    "SF": "San Francisco Giants", "STL": "St. Louis Cardinals", "TB": "Tampa Bay Rays",
    "TEX": "Texas Rangers", "TOR": "Toronto Blue Jays", "WSH": "Washington Nationals",
}

# Odds API team name mapping
ODDS_TO_ESPN_TEAM = {
    "Miami Marlins": "MIA", "Philadelphia Phillies": "PHI",
    "Kansas City Royals": "KC", "Washington Nationals": "WSH",
    "New York Mets": "NYM", "Cincinnati Reds": "CIN",
    "San Diego Padres": "SD", "St. Louis Cardinals": "STL",
    "Colorado Rockies": "COL", "Chicago Cubs": "CHC",
    "Minnesota Twins": "MIN", "Texas Rangers": "TEX",
    "Detroit Tigers": "DET", "Houston Astros": "HOU",
    "Los Angeles Angels": "LAA", "Arizona Diamondbacks": "ARI",
    "Pittsburgh Pirates": "PIT", "Athletics": "ATH",
    "Tampa Bay Rays": "TB", "Los Angeles Dodgers": "LAD",
    "Atlanta Braves": "ATL", "Boston Red Sox": "BOS",
    "Baltimore Orioles": "BAL", "Cleveland Guardians": "CLE",
    "Chicago White Sox": "CHW", "Milwaukee Brewers": "MIL",
    "New York Yankees": "NYY", "Toronto Blue Jays": "TOR",
    "San Francisco Giants": "SF", "Seattle Mariners": "SEA",
}

@dataclass
class MLBPlayer:
    name: str
    pos: str
    team: str
    status: str = "ACTIVE"

    # Batting season averages (per game)
    hits_avg: float = 0.0
    rbi_avg: float = 0.0
    runs_avg: float = 0.0
    hr_avg: float = 0.0
    total_bases_avg: float = 0.0
    sb_avg: float = 0.0
    singles_avg: float = 0.0
    doubles_avg: float = 0.0
    walks_avg: float = 0.0
    avg_batting: float = 0.0
    games_played: int = 0

    # Pitching season averages (per start/appearance)
    strikeouts_avg: float = 0.0
    hits_allowed_avg: float = 0.0
    walks_allowed_avg: float = 0.0
    earned_runs_avg: float = 0.0
    outs_avg: float = 0.0
    era: float = 0.0
    appearances: int = 0

    # TC computed values
    tc_hits: float = 0.0
    tc_rbi: float = 0.0
    tc_runs: float = 0.0
    tc_hr: float = 0.0
    tc_total_bases: float = 0.0
    tc_sb: float = 0.0
    tc_singles: float = 0.0
    tc_doubles: float = 0.0
    tc_walks: float = 0.0
    tc_strikeouts: float = 0.0
    tc_hits_allowed: float = 0.0
    tc_walks_allowed: float = 0.0
    tc_earned_runs: float = 0.0
    tc_outs: float = 0.0

    # Market lines
    lines: Dict[str, float] = field(default_factory=dict)
    edges: Dict[str, float] = field(default_factory=dict)

    def sf(self) -> float:
        s = self.status.upper()
        if s in ("OUT", "DNP", "INJURED"):
            return OUT_FACTOR
        if any(x in s for x in ("Q", "QUESTIONABLE", "DOUBTFUL", "GTD")):
            return Q_FACTOR
        return 1.0

    def compute_batter(self):
        sf = self.sf()
        w = BATTER_WEIGHT
        self.tc_hits = round(max(0.0, self.hits_avg * w * sf + GAP_BATTER), 1)
        self.tc_rbi = round(max(0.0, self.rbi_avg * w * sf + GAP_BATTER), 1)
        self.tc_runs = round(max(0.0, self.runs_avg * w * sf + GAP_BATTER), 1)
        self.tc_hr = round(max(0.0, self.hr_avg * w * sf + GAP_BATTER), 1)
        self.tc_total_bases = round(max(0.0, self.total_bases_avg * w * sf + GAP_BATTER), 1)
        self.tc_sb = round(max(0.0, self.sb_avg * w * sf + GAP_BATTER), 1)
        self.tc_singles = round(max(0.0, self.singles_avg * w * sf + GAP_BATTER), 1)
        self.tc_doubles = round(max(0.0, self.doubles_avg * w * sf + GAP_BATTER), 1)
        self.tc_walks = round(max(0.0, self.walks_avg * w * sf + GAP_BATTER), 1)

    def compute_pitcher(self):
        sf = self.sf()
        w = PITCHER_WEIGHT
        self.tc_strikeouts = round(max(0.0, self.strikeouts_avg * w * sf + GAP_PITCHER), 1)
        self.tc_hits_allowed = round(max(0.0, self.hits_allowed_avg * w * sf - GAP_PITCHER), 1)
        self.tc_walks_allowed = round(max(0.0, self.walks_allowed_avg * w * sf - GAP_PITCHER), 1)
        self.tc_earned_runs = round(max(0.0, self.earned_runs_avg * w * sf - GAP_PITCHER), 1)
        self.tc_outs = round(max(0.0, self.outs_avg * w * sf + GAP_PITCHER), 1)

    def compute_all(self):
        self.compute_batter()
        self.compute_pitcher()

    def dict(self) -> dict:
        return {
            "name": self.name, "pos": self.pos, "team": self.team,
            "status": self.status,
            "batting": {
                "hits_avg": self.hits_avg, "rbi_avg": self.rbi_avg,
                "runs_avg": self.runs_avg, "hr_avg": self.hr_avg,
                "total_bases_avg": self.total_bases_avg, "sb_avg": self.sb_avg,
                "singles_avg": self.singles_avg, "doubles_avg": self.doubles_avg,
                "walks_avg": self.walks_avg, "avg": self.avg_batting,
                "games": self.games_played,
            },
            "pitching": {
                "strikeouts_avg": self.strikeouts_avg, "hits_allowed_avg": self.hits_allowed_avg,
                "walks_allowed_avg": self.walks_allowed_avg, "earned_runs_avg": self.earned_runs_avg,
                "outs_avg": self.outs_avg, "era": self.era,
                "appearances": self.appearances,
            },
            "tc_batting": {
                "hits": self.tc_hits, "rbi": self.tc_rbi, "runs": self.tc_runs,
                "hr": self.tc_hr, "total_bases": self.tc_total_bases,
                "sb": self.tc_sb, "singles": self.tc_singles,
                "doubles": self.tc_doubles, "walks": self.tc_walks,
            },
            "tc_pitching": {
                "strikeouts": self.tc_strikeouts, "hits_allowed": self.tc_hits_allowed,
                "walks_allowed": self.tc_walks_allowed, "earned_runs": self.tc_earned_runs,
                "outs": self.tc_outs,
            },
            "lines": self.lines,
            "edges": self.edges,
        }

# ═══════════════════════════════════════════════════════════════════════════════
# ESPN STATS FETCH
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_espn_mlb_stats(team_abbr: str, lookback_days: int = 30) -> List[MLBPlayer]:
    """
    Fetch MLB player stats by aggregating recent ESPN boxscores.
    Returns a list of MLBPlayer with season averages computed from recent games.
    """
    # For now, fetch the most recent completed game boxscore and use those stats
    # as a snapshot. Full season averaging would require multiple boxscore pulls.
    team_id = MLB_TEAM_IDS.get(team_abbr)
    if not team_id:
        print(f"Unknown team: {team_abbr}")
        return []

    players = []

    try:
        # Try to get recent completed games for this team
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        date_str = start_date.strftime("%Y%m%d")

        scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={date_str}&limit=100"
        r = requests.get(scoreboard_url, timeout=15)

        if r.status_code != 200:
            print(f"  Error fetching scoreboard: {r.status_code}")
            return []

        data = r.json()
        events = data.get("events", [])

        # Find games involving our team that are completed
        team_games = []
        for evt in events:
            competitions = evt.get("competitions", [])
            for comp in competitions:
                competitors = comp.get("competitors", [])
                abbrs = [c.get("team", {}).get("abbreviation", "") for c in competitors]
                status = comp.get("status", {}).get("type", {}).get("name", "")
                if team_abbr in abbrs and status == "STATUS_FINAL":
                    team_games.append(evt)

        if not team_games:
            # Fall back to the most recent game even if pending
            for evt in events:
                competitions = evt.get("competitions", [])
                for comp in competitions:
                    competitors = comp.get("competitors", [])
                    abbrs = [c.get("team", {}).get("abbreviation", "") for c in competitors]
                    if team_abbr in abbrs:
                        team_games.append(evt)
                        break

        # Process each game's boxscore
        hitter_stats: Dict[str, Dict[str, List[float]]] = {}
        pitcher_stats: Dict[str, Dict[str, List[float]]] = {}

        for game in team_games[:min(len(team_games), 10)]:  # max 10 games for now
            game_id = game.get("id")
            summary_url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary?event={game_id}"
            sr = requests.get(summary_url, timeout=15)

            if sr.status_code != 200:
                continue

            sd = sr.json()
            bs = sd.get("boxscore", {})
            players_by_team = bs.get("players", [])

            for pt in players_by_team:
                pt_team = pt.get("team", {}).get("abbreviation", "")
                if pt_team != team_abbr:
                    continue

                stats_groups = pt.get("statistics", [])
                for sg in stats_groups:
                    stype = sg.get("type") or sg.get("name", "")
                    athletes = sg.get("athletes", [])

                    for a in athletes:
                        if not isinstance(a, dict):
                            continue
                        athlete = a.get("athlete", {})
                        player_name = athlete.get("displayName") or athlete.get("fullName") or ""
                        if not player_name:
                            continue

                        pos = athlete.get("position", {})
                        pos_abbr = pos.get("abbreviation", "") if isinstance(pos, dict) else str(pos)
                        stats_vals = a.get("stats", [])

                        if stype == "batting" and len(stats_vals) >= 12:
                            # keys: hits-atBats, atBats, runs, hits, RBIs, homeRuns, walks, strikeouts, pitches, avg, onBasePct, slugAvg
                            key = player_name
                            if key not in hitter_stats:
                                hitter_stats[key] = {"pos": pos_abbr, "vals": {k: [] for k in BATTER_MARKETS}}
                                hitter_stats[key]["vals"]["avg"] = []
                                hitter_stats[key]["vals"]["games"] = []

                            try:
                                runs_v = float(stats_vals[2]) if stats_vals[2] else 0.0
                                hits_v = float(stats_vals[3]) if stats_vals[3] else 0.0
                                rbi_v = float(stats_vals[4]) if stats_vals[4] else 0.0
                                hr_v = float(stats_vals[5]) if stats_vals[5] else 0.0
                                walks_v = float(stats_vals[6]) if stats_vals[6] else 0.0
                                so_v = float(stats_vals[7]) if stats_vals[7] else 0.0
                                avg_v = float(stats_vals[9]) if stats_vals[9] else 0.0
                                slug_v = float(stats_vals[11]) if len(stats_vals) > 11 and stats_vals[11] else 0.0
                            except (ValueError, IndexError):
                                continue

                            # Estimate total bases from slugging: SLG = TB / AB, so TB ≈ SLG * AB
                            at_bats_raw = stats_vals[1]
                            try:
                                at_bats = float(at_bats_raw) if at_bats_raw else 0.0
                            except (ValueError, IndexError):
                                at_bats = 0.0

                            total_bases_v = slug_v * at_bats if at_bats > 0 else 0.0

                            # Estimate singles and doubles from hits and TB: 
                            # TB = singles + 2*doubles + 3*triples + 4*HR
                            # Simplified: use the boxscore hits-atBats (e.g. "2-4") to get single-game hits
                            # For now use hits as proxy for singles (we'll build better later)
                            hits_at_bats_raw = stats_vals[0]
                            try:
                                game_hits = int(hits_at_bats_raw.split("-")[0]) if hits_at_bats_raw else 0
                            except (ValueError, IndexError):
                                game_hits = int(hits_v)

                            hitter_stats[key]["vals"]["hits"].append(hits_v)
                            hitter_stats[key]["vals"]["runs"].append(runs_v)
                            hitter_stats[key]["vals"]["rbi"].append(rbi_v)
                            hitter_stats[key]["vals"]["hr"].append(hr_v)
                            hitter_stats[key]["vals"]["total_bases"].append(total_bases_v)
                            hitter_stats[key]["vals"]["walks"].append(walks_v)
                            hitter_stats[key]["vals"]["singles"].append(game_hits)  # simplified
                            hitter_stats[key]["vals"]["doubles"].append(0.0)  # to refine
                            hitter_stats[key]["vals"]["sb"].append(0.0)  # not in basic boxscore
                            hitter_stats[key]["vals"]["avg"].append(avg_v)
                            hitter_stats[key]["vals"]["games"].append(1)

                        elif stype == "pitching" and len(stats_vals) >= 10:
                            key = player_name
                            if key not in pitcher_stats:
                                pitcher_stats[key] = {"pos": pos_abbr, "vals": {k: [] for k in PITCHER_MARKETS}}
                                pitcher_stats[key]["vals"]["era"] = []
                                pitcher_stats[key]["vals"]["appearances"] = []

                            try:
                                so_v = float(stats_vals[5]) if stats_vals[5] else 0.0
                                hits_v = float(stats_vals[1]) if stats_vals[1] else 0.0
                                era_v = float(stats_vals[8]) if stats_vals[8] else 0.0
                            except (ValueError, IndexError):
                                continue

                            # For outs: innings pitched * 3
                            inn_raw = stats_vals[0]
                            try:
                                inn = float(inn_raw) if inn_raw else 0.0
                            except (ValueError, IndexError):
                                inn = 0.0
                            outs_v = inn * 3

                            try:
                                walks_v = float(stats_vals[4]) if stats_vals[4] else 0.0
                                er_v = float(stats_vals[3]) if stats_vals[3] else 0.0
                            except (ValueError, IndexError):
                                walks_v = 0.0
                                er_v = 0.0

                            pitcher_stats[key]["vals"]["strikeouts"].append(so_v)
                            pitcher_stats[key]["vals"]["hits_allowed"].append(hits_v)
                            pitcher_stats[key]["vals"]["walks"].append(walks_v)
                            pitcher_stats[key]["vals"]["earned_runs"].append(er_v)
                            pitcher_stats[key]["vals"]["outs"].append(outs_v)
                            pitcher_stats[key]["vals"]["era"].append(era_v)
                            pitcher_stats[key]["vals"]["appearances"].append(1)

        # Convert aggregated stats to players
        all_names = set(list(hitter_stats.keys()) + list(pitcher_stats.keys()))
        for name in all_names:
            p = MLBPlayer(name=name, pos="", team=team_abbr)

            if name in hitter_stats:
                p.pos = hitter_stats[name]["pos"]
                v = hitter_stats[name]["vals"]
                ng = len(v.get("games", [1]))
                if ng > 0:
                    p.hits_avg = round(sum(v["hits"]) / ng, 2)
                    p.rbi_avg = round(sum(v["rbi"]) / ng, 2)
                    p.runs_avg = round(sum(v["runs"]) / ng, 2)
                    p.hr_avg = round(sum(v["hr"]) / ng, 2)
                    p.total_bases_avg = round(sum(v["total_bases"]) / ng, 2)
                    p.sb_avg = round(sum(v["sb"]) / ng, 2)
                    p.singles_avg = round(sum(v["singles"]) / ng, 2)
                    p.doubles_avg = round(sum(v["doubles"]) / ng, 2)
                    p.walks_avg = round(sum(v["walks"]) / ng, 2)
                    p.avg_batting = round(sum(v["avg"]) / ng, 3)
                    p.games_played = ng

            if name in pitcher_stats:
                if not p.pos:
                    p.pos = pitcher_stats[name]["pos"]
                v = pitcher_stats[name]["vals"]
                na = len(v.get("appearances", [1]))
                if na > 0:
                    p.strikeouts_avg = round(sum(v["strikeouts"]) / na, 1)
                    p.hits_allowed_avg = round(sum(v["hits_allowed"]) / na, 1)
                    p.walks_allowed_avg = round(sum(v["walks"]) / na, 1)
                    p.earned_runs_avg = round(sum(v["earned_runs"]) / na, 1)
                    p.outs_avg = round(sum(v["outs"]) / na, 1)
                    p.era = round(sum(v["era"]) / na, 2)
                    p.appearances = na

            p.compute_all()
            players.append(p)

    except Exception as e:
        print(f"  Error fetching stats for {team_abbr}: {e}")
        return []

    return players

# ═══════════════════════════════════════════════════════════════════════════════
# ODDS API FETCH
# ═══════════════════════════════════════════════════════════════════════════════

def load_api_key() -> str:
    """Load and return The Odds API key from env or secrets file."""
    # Check env first
    for name in ('ODDS_API_KEY', 'THEODDSAPI', 'THEODDSAPI_KEY'):
        val = os.environ.get(name, '')
        if val and len(val) > 10:
            return val
    # Fallback: read secrets file
    secrets_file = "/root/.zo/secrets.env"
    if os.path.exists(secrets_file):
        with open(secrets_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if 'ODDS' in k.upper() and len(v) > 10:
                        os.environ.setdefault(k, v)
                        return v
    return ""

ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports"

def _odds_url(sport_key: str, event_id: str = "") -> str:
    if event_id:
        return f"{ODDS_API_BASE}/{sport_key}/events/{event_id}/odds"
    return f"{ODDS_API_BASE}/{sport_key}/odds"

def fetch_mlb_player_lines(game_id: str) -> Dict[str, Dict[str, float]]:
    """
    Fetch DK player prop lines for an MLB game.
    Returns {player_name: {stat_key: line_value}}
    """
    key = load_api_key()
    if not key:
        return {}

    player_lines: Dict[str, Dict[str, float]] = {}
    all_markets = list(BATTER_MARKETS.values()) + list(PITCHER_MARKETS.values())
    market_str = ",".join(all_markets)

    try:
        url = _odds_url("baseball_mlb", game_id)
        r = requests.get(url, params={
            "apiKey": key,
            "regions": "us",
            "markets": market_str,
            "bookmakers": "draftkings",
            "oddsFormat": "american",
        }, timeout=15)

        if r.status_code != 200:
            print(f"  Odds API error: {r.status_code} {r.text[:120]}")
            return {}

        data = r.json()
        for bm in data.get("bookmakers", []):
            if bm.get("key") != "draftkings":
                continue
            for market in bm.get("markets", []):
                market_key = market.get("key", "")
                # Map market key to stat name
                stat_name = None
                for sn, mk in BATTER_MARKETS.items():
                    if mk == market_key:
                        stat_name = sn
                        break
                if not stat_name:
                    for sn, mk in PITCHER_MARKETS.items():
                        if mk == market_key:
                            stat_name = sn
                            break
                if not stat_name:
                    continue

                for outcome in market.get("outcomes", []):
                    player_desc = outcome.get("description", "")
                    line = outcome.get("point")
                    if player_desc and line is not None:
                        if player_desc not in player_lines:
                            player_lines[player_desc] = {}
                        player_lines[player_desc][stat_name] = line

    except Exception as e:
        print(f"  Error fetching player lines: {e}")

    return player_lines

def fetch_mlb_game_lines() -> List[Dict]:
    """Fetch MLB game odds with ML/spread/total from The Odds API."""
    key = load_api_key()
    if not key:
        return []

    try:
        url = _odds_url("baseball_mlb")
        r = requests.get(url,
            params={
                "apiKey": key,
                "regions": "us",
                "markets": "h2h,spreads,totals",
                "bookmakers": "draftkings",
                "oddsFormat": "american",
            },
            timeout=15,
        )
        if r.status_code != 200:
            return []

        games = r.json()
        parsed = []
        for g in games:
            home_team = g.get("home_team", "")
            away_team = g.get("away_team", "")
            game_id = g.get("id", "")
            commence = g.get("commence_time", "")

            home_abbr = ODDS_TO_ESPN_TEAM.get(home_team, "")
            away_abbr = ODDS_TO_ESPN_TEAM.get(away_team, "")

            dk_data = {"total": None, "spread": None, "ml_home": None, "ml_away": None}
            for bm in g.get("bookmakers", []):
                if bm.get("key") != "draftkings":
                    continue
                for market in bm.get("markets", []):
                    mk = market.get("key", "")
                    outcomes = market.get("outcomes", [])
                    if mk == "totals" and outcomes:
                        dk_data["total"] = outcomes[0].get("point")
                    elif mk == "spreads" and outcomes:
                        dk_data["spread"] = outcomes[0].get("point")
                    elif mk == "h2h" and outcomes:
                        for o in outcomes:
                            if o.get("name") == home_team:
                                dk_data["ml_home"] = o.get("price")
                            elif o.get("name") == away_team:
                                dk_data["ml_away"] = o.get("price")

            parsed.append({
                "game_id": game_id,
                "home_team": home_team,
                "away_team": away_team,
                "home_abbr": home_abbr,
                "away_abbr": away_abbr,
                "commence_time": commence,
                "dk_total": dk_data["total"],
                "dk_spread": dk_data["spread"],
                "dk_ml_home": dk_data["ml_home"],
                "dk_ml_away": dk_data["ml_away"],
            })

        return parsed

    except Exception as e:
        print(f"Error fetching MLB game lines: {e}")
        return []

# ═══════════════════════════════════════════════════════════════════════════════
# PROJECTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def project_mlb_game(home_abbr: str, away_abbr: str, game_id: str = None,
                     dk_total: float = None) -> Dict:
    """Generate full TC projection for an MLB matchup."""
    matchup_key = f"{away_abbr}@{home_abbr}"
    result = {
        "sport": "MLB",
        "matchup": matchup_key,
        "home_team": home_abbr,
        "away_team": away_abbr,
        "dk_total": dk_total,
        "source": "ESPN + The Odds API + SportsDataIO",
    }

    # Fetch rosters with stats
    print(f"  Fetching stats for {away_abbr}...")
    away_players = fetch_espn_mlb_stats(away_abbr)
    print(f"  Fetching stats for {home_abbr}...")
    home_players = fetch_espn_mlb_stats(home_abbr)

    # ── Layer 1: Try Odds API DK player prop lines ──
    player_lines = {}
    dk_api_available = False
    if game_id:
        print(f"  Fetching DK player lines for {away_abbr} @ {home_abbr}...")
        player_lines = fetch_mlb_player_lines(game_id)
        dk_api_available = bool(player_lines)

    # ── Layer 2: SportsDataIO fallback ──
    sdio_lines = {}
    if not dk_api_available:
        try:
            from mlb_sdio_props import fetch_mlb_props
            all_sdio = fetch_mlb_props()
            # Try both key directions — SDIO and ESPN may order home/away differently
            for try_key in [matchup_key, f"{home_abbr}@{away_abbr}"]:
                if try_key in all_sdio:
                    sdio_lines = all_sdio[try_key]
                    break
            if sdio_lines:
                print(f"    ✓ SDIO: {len(sdio_lines)} players with props")
        except Exception as e:
            print(f"    ⚠ SDIO unavailable: {e}")

    # Apply all available lines to players
    for p in away_players + home_players:
        pname_lower = (p.name or "").strip().lower()

        # Odds API DK lines
        dk_lines = player_lines.get(p.name, {})
        for stat_name, line_val in dk_lines.items():
            p.lines[stat_name] = line_val
            tc_val = getattr(p, f"tc_{stat_name}", 0.0)
            if tc_val > 0:
                p.edges[stat_name] = round(tc_val - line_val, 2)

        # SDIO lines
        sdio_player = sdio_lines.get(pname_lower, {})
        for stat_name, line_val in sdio_player.items():
            if stat_name not in p.lines and line_val is not None:
                p.lines[stat_name] = line_val
                tc_val = getattr(p, f"tc_{stat_name}", 0.0)
                if tc_val > 0:
                    p.edges[stat_name] = round(tc_val - line_val, 2)

    # Generate valid props — Odds API, SDIO, or self-edge fallback
    valid_props = []
    dk_available = any(p.lines for p in away_players + home_players)
    line_source = "dk_lines" if dk_api_available else ("sdio_lines" if sdio_lines else "tc-internal-fallback")

    if dk_available:
        # ── Odds API or SDIO lines available ──
        use_thresh = EDGE_THRESH_MLB_SDIO if sdio_lines and not dk_api_available else EDGE_THRESH
        for p in away_players + home_players:
            for stat_name, line_val in p.lines.items():
                tc_val = getattr(p, f"tc_{stat_name}", 0.0)
                edge = p.edges.get(stat_name, 0.0)
                direction = "OVER" if edge > 0 else "UNDER"
                signal = "PASS"
                if abs(edge) >= use_thresh:
                    signal = direction
                src = "dk_lines" if stat_name in player_lines.get(p.name, {}) else "sdio_lines"
                valid_props.append({
                    "player": p.name, "team": p.team, "pos": p.pos,
                    "stat": stat_name, "market_line": line_val,
                    "tc_projection": tc_val, "edge": edge,
                    "direction": direction, "signal": signal,
                    "status": p.status, "source": src,
                })
    else:
        batting_stats = ["hits", "rbi", "runs", "hr", "total_bases", "sb", "singles", "doubles", "walks"]
        pitching_stats = ["strikeouts", "hits_allowed", "walks_allowed", "earned_runs", "outs"]
        for p in away_players + home_players:
            if p.status.upper() in ("OUT", "DNP", "INJURED"):
                continue
            sf = p.sf()
            if sf <= 0:
                continue
            stat_list = pitching_stats if p.pos and "P" in p.pos.upper() else batting_stats
            for stat_name in stat_list:
                tc_val = getattr(p, f"tc_{stat_name}", 0.0)
                if tc_val <= 0:
                    continue
                self_line = math.floor(tc_val * LINE_FACTOR)
                if self_line <= 0:
                    continue
                edge = round(tc_val - self_line, 2)
                direction = "OVER" if edge > 0 else "UNDER"
                signal = "PASS"
                self_edge_thresh = 1.0
                if abs(edge) >= self_edge_thresh:
                    signal = direction
                valid_props.append({
                    "player": p.name, "team": p.team, "pos": p.pos,
                    "stat": stat_name, "market_line": self_line,
                    "tc_projection": tc_val, "edge": edge,
                    "direction": direction, "signal": signal,
                    "status": p.status, "source": "tc-internal-fallback",
                })

    result["away_players"] = [p.dict() for p in away_players]
    result["home_players"] = [p.dict() for p in home_players]
    result["valid_props"] = sorted(valid_props, key=lambda x: abs(x["edge"]), reverse=True)
    result["roster_counts"] = {
        "away_total": len(away_players),
        "home_total": len(home_players),
    }
    result["dk_available"] = dk_available
    result["prop_source"] = line_source
    result["sdio_props_count"] = len(sdio_lines)

    return result

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CLI
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="MLB TC Engine v1.0")
    parser.add_argument("--game", type=str, help="Matchup like 'MIA@PHI'")
    parser.add_argument("--slate", action="store_true", help="Full MLB slate")
    parser.add_argument("--report", action="store_true", help="Generate markdown report")
    parser.add_argument("--backtest", type=str, help="Date for historical backtest (YYYY-MM-DD)")
    parser.add_argument("--output", type=str, default="", help="JSON output path")
    args = parser.parse_args()

    if args.game:
        parts = args.game.split("@")
        if len(parts) == 2:
            away, home = parts[0].strip(), parts[1].strip()
            # Find game ID from live odds
            games = fetch_mlb_game_lines()
            game_id = None
            dk_total = None
            for g in games:
                if g["away_abbr"] == away and g["home_abbr"] == home:
                    game_id = g["game_id"]
                    dk_total = g["dk_total"]
                    break

            print(f"\n{'='*60}")
            print(f"MLB TC PROJECTION: {away} @ {home}")
            if dk_total:
                print(f"DK Total: {dk_total}")
            print(f"{'='*60}")

            proj = project_mlb_game(home, away, game_id, dk_total)
            print(f"\nAway ({away}): {len(proj['away_players'])} players")
            print(f"Home ({home}): {len(proj['home_players'])} players")
            print(f"Valid Props: {len(proj['valid_props'])}")

            # Show top props
            if proj["valid_props"]:
                print(f"\n{'Player':<22} {'Stat':<12} {'TC_Proj':>7} {'DK_Line':>7} {'Edge':>6} {'Signal':<6}")
                print("-" * 65)
                for vp in proj["valid_props"][:20]:
                    sig = vp["signal"]
                    print(f"{vp['player']:<22} {vp['stat']:<12} {vp['tc_projection']:>7.1f} {vp['market_line']:>7.1f} {vp['edge']:>+6.1f} {sig:<6}")

            if args.output:
                with open(args.output, "w") as f:
                    json.dump(proj, f, indent=2)
                print(f"\nSaved to {args.output}")

    elif args.slate:
        games = fetch_mlb_game_lines()
        print(f"\nMLB SLATE: {len(games)} games with DK lines")
        for g in games:
            print(f"  {g['away_abbr']} @ {g['home_abbr']} | Total: {g['dk_total']} | {g['commence_time']}")
        if args.output:
            with open(args.output, "w") as f:
                json.dump(games, f, indent=2)

    elif args.backtest:
        print(f"MLB Backtest for {args.backtest}")
        # Historical backtest logic will be added
        result = {"sport": "MLB", "date": args.backtest, "status": "pending"}
        if args.output:
            with open(args.output, "w") as f:
                json.dump(result, f, indent=2)

    else:
        print("MLB TC Engine v1.0")
        print("  --game 'MIA@PHI' --report    Game projection")
        print("  --slate                       Full slate with DK totals")
        print("  --backtest 2026-06-14         Historical backtest")
        print("  --output path.json            Save output")

if __name__ == "__main__":
    main()
