#!/usr/bin/env python3
"""
backtest_pipeline.py — Odds API Historical Backtest with TC Math Settlement.

Fetches historical DraftKings player combo props (PRA/PR/PA) from The Odds API,
cross-references with ESPN box scores for actual player stats, and computes
TC projection hit rates.

CREDIT OPTIMIZATION:
  - The Odds API charges 10x credits on /v4/historical/ endpoints.
  - This pipeline makes ONE call per sport per date (NOT per event).
  - No API calls inside loops over events/players.
  - ESPN box-score fetches are FREE (no credit cost).

PIPELINE:
  1. Fetch historical DK combo props → save raw JSON
  2. Fetch game scores (Odds API) → save raw JSON
  3. Fetch ESPN box scores for player settlement → save actuals JSON
  4. Offline: run TC Math, compare projections vs DK lines + actuals
  5. Generate markdown report

Usage:
  python3 backtest_pipeline.py --league WNBA --date 2026-06-10
  python3 backtest_pipeline.py --league NBA --days 3
  python3 backtest_pipeline.py --league BOTH --date 2026-06-11 --no-bayes
  python3 backtest_pipeline.py --dry-run  # show what WOULD be fetched, no API calls

Flags:
  --league     NBA, WNBA, or BOTH (default: WNBA)
  --date       Single date YYYY-MM-DD (default: yesterday)
  --days       Number of past days to fetch (default: 1, max: 7)
  --output     Output directory (default: Daily_Log/backtests/YYYY-MM-DD/)
  --dry-run    Print what would be fetched, no API calls
  --no-bayes   Disable Bayesian shrinkage
  --no-pace    Disable team-pace adjustment
  --no-b2b     Disable back-to-back adjustment
  --verbose    Extra debug logging

Author: Zo Computer / true.zo.computer
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

SECRETS_FILE = Path("/root/.zo/secrets.env")
ODDS_API_KEY = ""
if SECRETS_FILE.exists():
    for line in SECRETS_FILE.read_text().split("\n"):
        line = line.strip()
        if 'ODDS' in line.upper() and '=' in line and 'KEY' in line.upper():
            ODDS_API_KEY = line.split('=', 1)[1].strip().strip('"').strip("'")
            break

ODDS_BASE = "https://api.theoddsapi.com"

SPORT_MAP = {
    "WNBA": "basketball_wnba",
    "NBA": "basketball_nba",
}

# ── Market definitions ─────────────────────────────────
# NOTE: The Odds API /v4/historical/ endpoint only supports game-level markets
# (h2h, spreads, totals). Player props and combo props are NOT available via
# the historical endpoint. We fetch game-level context here and use ESPN for
# player actuals + TC math for projection evaluation.
HISTORICAL_MARKETS = "h2h,spreads,totals"
COMBO_MARKETS = "player_points_rebounds_assists,player_points_rebounds,player_points_assists"
STAT_MARKETS = "player_points,player_rebounds,player_assists,player_threes,player_steals,player_blocks"
COMBO_MARKET_MAP = {
    "player_points_rebounds_assists": "PRA",
    "player_points_rebounds": "PR",
    "player_points_assists": "PA",
}
ODDS_STAT_MAP = {
    "player_points": "points", "player_rebounds": "rebounds",
    "player_assists": "assists", "player_threes": "threes",
    "player_steals": "steals", "player_blocks": "blocks",
}

# ESPN boxscore stat mapping (keys as they appear in ESPN v2)
ESPN_STAT_KEYS = ["points", "rebounds", "assists", "steals", "blocks",
                  "threePointFieldGoalsMade-threePointFieldGoalsAttempted"]

# TC Math constants — per-stat CONS multipliers, Bayesian priors, cutoffs
STAT_CONS = {
    "PTS": 0.85, "REB": 0.85, "AST": 0.85,
    "STL": 0.80, "BLK": 0.80, "3PM": 0.85,
}
STAT_BAYES_ALPHA = {
    "PTS": 7.0, "REB": 7.0, "AST": 7.0,
    "STL": 5.0, "BLK": 7.0, "3PM": 7.0,
}
STAT_PRIOR = {
    "PTS": 6.0, "REB": 3.0, "AST": 2.0,
    "STL": 0.8, "BLK": 0.5, "3PM": 0.5,
}
MIN_AVG = {
    "PTS": 0.5, "REB": 0.5, "AST": 0.5,
    "STL": 0.05, "BLK": 0.05, "3PM": 0.05,
}
FAST_TEAMS_WNBA = {"LV", "CHI", "IND", "ATL"}
SLOW_TEAMS_WNBA = {"MIN", "NY", "SEA"}
FAST_TEAMS_NBA = {"IND", "SAC", "OKC", "GSW"}
SLOW_TEAMS_NBA = {"NYK", "MIA", "ORL"}

# ═══════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════

VERBOSE = False

def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def vlog(msg: str) -> None:
    if VERBOSE:
        log(f"  DEBUG  {msg}")

# ═══════════════════════════════════════════════════════════════
# PARSING HELPERS
# ═══════════════════════════════════════════════════════════════

def num(s):
    """Robust number parser: handles ESPN '2-5' ranges and None."""
    if s in (None, "", "--"):
        return 0.0
    s = str(s).strip()
    if s.startswith("-") and s[1:].isdigit():
        return int(s)
    if "-" in s:
        s = s.split("-")[0]
    try:
        return int(s)
    except Exception:
        try:
            return float(s)
        except Exception:
            return 0.0

def normalize_name(name: str) -> str:
    """Strip apostrophes, periods, commas for fuzzy matching."""
    n = name.lower()
    n = re.sub(r"['.',\-]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n

def match_player(espn_name: str, dk_name: str) -> bool:
    """Fuzzy match ESPN shortName to DK description."""
    a = normalize_name(espn_name)
    b = normalize_name(dk_name)
    if a == b:
        return True
    parts_a = set(a.split())
    parts_b = set(b.split())
    common = parts_a & parts_b
    return len(common) >= min(len(parts_a), len(parts_b)) - 1 and len(common) >= 1

# ═══════════════════════════════════════════════════════════════
# PHASE 1 — FETCH HISTORICAL DK COMBO PROPS
# ═══════════════════════════════════════════════════════════════

def fetch_historical_combo_props(sport_key: str, date_str: str) -> list:
    """
    Fetch historical game-level odds (h2h, spreads, totals) for a date.
    ONE API call — returns ALL events on that date.
    
    Cost: 10 credits (historical endpoint).
    NOTE: Player prop/combo markets are NOT supported on the historical endpoint.
    Use ESPN box scores + TC math for player-level backtesting.
    """
    url = f"{ODDS_BASE}/historical/sports/{sport_key}/odds"
    params = {
        "date": f"{date_str}T12:00:00Z",
        "regions": "us",
        "markets": HISTORICAL_MARKETS,
        "oddsFormat": "american",
        "bookmakers": "draftkings",
        "dateFormat": "iso",
    }
    log(f"  GET {url}")
    log(f"  params: date={date_str}, markets={HISTORICAL_MARKETS}, regions=us")
    r = requests.get(url, params=params, timeout=45)
    r.raise_for_status()
    data = r.json()
    events = data.get("data", [])
    credits_used = r.headers.get("x-requests-used", "?")
    credits_remaining = r.headers.get("x-requests-remaining", "?")
    log(f"  Response: {len(events)} events | credits used={credits_used} remaining={credits_remaining}")
    return events

def fetch_historical_scores(sport_key: str, days_from: int = 3) -> list:
    """
    Fetch completed game scores for last N days.
    Max daysFrom = 3 per Odds API limit.
    """
    url = f"{ODDS_BASE}/sports/{sport_key}/scores/"
    params = {
        "daysFrom": days_from,
        "dateFormat": "iso",
    }
    log(f"  GET {url}")
    log(f"  params: daysFrom={days_from}")
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    credits_used = r.headers.get("x-requests-used", "?")
    log(f"  Response: {len(data)} scores | credits used={credits_used}")
    return data

# ═══════════════════════════════════════════════════════════════
# PHASE 2 — EXTRACT DK COMBO LINES TO STRUCTURED DATA
# ═══════════════════════════════════════════════════════════════

def extract_dk_combos(historical_events: list) -> List[dict]:
    """
    Parse historical Odds API response → list of combo line dicts.
    Each dict: {player, team, stat, combo_type, dk_line, dk_odds, commence_time, event_id}
    """
    combos: List[dict] = []
    for ev in historical_events:
        event_id = ev.get("id", "")
        commence = ev.get("commence_time", "")
        home = ev.get("home_team", "?")
        away = ev.get("away_team", "?")
        for bm in ev.get("bookmakers", []):
            if bm.get("key") != "draftkings":
                continue
            for market in bm.get("markets", []):
                mkey = market.get("key", "")
                combo_type = COMBO_MARKET_MAP.get(mkey)
                if not combo_type:
                    continue
                for out in market.get("outcomes", []):
                    if out.get("name") != "Over":
                        continue
                    player_dk = out.get("description") or out.get("name", "Unknown")
                    point = out.get("point")
                    price = out.get("price")
                    if point is None:
                        continue
                    try:
                        line = float(point)
                    except (TypeError, ValueError):
                        continue
                    combos.append({
                        "player_dk": player_dk,
                        "team": "",
                        "combo_type": combo_type,
                        "dk_line": line,
                        "dk_odds": price,
                        "commence_time": commence,
                        "event_id": event_id,
                        "home": home,
                        "away": away,
                    })
    vlog(f"  Extracted {len(combos)} DK combo legs from {len(historical_events)} events")
    return combos

def extract_dk_player_stats(historical_events: list) -> Dict[str, List[dict]]:
    """
    Parse individual player stat lines from historical Odds API response.
    Returns: {player_dk_name: [{stat: "PTS", dk_line: 22.5, dk_odds: -110}, ...]}
    """
    player_lines: Dict[str, List[dict]] = defaultdict(list)
    for ev in historical_events:
        for bm in ev.get("bookmakers", []):
            if bm.get("key") != "draftkings":
                continue
            for market in bm.get("markets", []):
                mkey = market.get("key", "")
                stat = ODDS_STAT_MAP.get(mkey)
                if not stat:
                    continue
                for out in market.get("outcomes", []):
                    if out.get("name") != "Over":
                        continue
                    player_dk = out.get("description") or out.get("name", "Unknown")
                    point = out.get("point")
                    price = out.get("price")
                    if point is None:
                        continue
                    try:
                        line = float(point)
                    except (TypeError, ValueError):
                        continue
                    player_lines[player_dk].append({
                        "stat": stat,
                        "dk_line": line,
                        "dk_odds": price,
                    })
    return dict(player_lines)

# ═══════════════════════════════════════════════════════════════
# PHASE 3 — ESPN BOXSCORE FETCH (FREE — no Odds API credits)
# ═══════════════════════════════════════════════════════════════

def fetch_espn_scoreboard(date_ymd: str, league: str) -> list:
    """Fetch ESPN scoreboard for a date. Returns events list."""
    sport_path = "wnba" if league.upper() == "WNBA" else "nba"
    url = (
        f"https://site.api.espn.com/apis/site/v2/sports/basketball/"
        f"{sport_path}/scoreboard?dates={date_ymd.replace('-', '')}"
    )
    vlog(f"  ESPN scoreboard: {url}")
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("events", [])
    except Exception as e:
        vlog(f"  ESPN scoreboard error: {e}")
        return []

def fetch_espn_boxscore(event_id: str, league: str) -> dict:
    """Fetch ESPN boxscore for a completed event."""
    sport_path = "wnba" if league.upper() == "WNBA" else "nba"
    url = (
        f"https://site.api.espn.com/apis/site/v2/sports/basketball/"
        f"{sport_path}/summary?event={event_id}"
    )
    vlog(f"  ESPN boxscore: event={event_id}")
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        vlog(f"  ESPN boxscore error: {e}")
        return {}

def extract_espn_actuals(espn_events: list, league: str) -> List[dict]:
    """
    Fetch boxscores for all completed ESPN events and extract player stats.
    Returns list of {date, matchup, team, name, pts, reb, ast, stl, blk, tpm, min}.
    """
    actuals: List[dict] = []
    for ev in espn_events:
        comp = ev.get("competitions", [{}])[0]
        comps = comp.get("competitors", [])
        if len(comps) < 2:
            continue
        status = (ev.get("status", {}).get("type", {}).get("description") or "").lower()
        if "final" not in status:
            continue
        event_id = ev.get("id", "")
        date_str = ev.get("date", "")[:10]
        home_c = next((c for c in comps if c.get("homeAway") == "home"), comps[1])
        away_c = next((c for c in comps if c.get("homeAway") == "away"), comps[0])
        home_abbr = (home_c.get("team", {}).get("abbreviation") or "?").upper()
        away_abbr = (away_c.get("team", {}).get("abbreviation") or "?").upper()
        matchup = f"{away_abbr}@{home_abbr}"

        box = fetch_espn_boxscore(event_id, league)
        for p_block in box.get("boxscore", {}).get("players", []):
            team = p_block.get("team", {}).get("abbreviation", "?").upper()
            for stat_group in p_block.get("statistics", []):
                keys = stat_group.get("keys", [])
                for a in stat_group.get("athletes", []):
                    ath = a.get("athlete", {})
                    name = ath.get("shortName") or ath.get("displayName", "?")
                    raw = a.get("stats", [])
                    rec = dict(zip(keys, raw))
                    minutes_str = rec.get("minutes", "0")
                    if isinstance(minutes_str, str) and ":" in minutes_str:
                        minutes = num(minutes_str.split(":")[0])
                    else:
                        minutes = num(minutes_str)
                    actuals.append({
                        "date": date_str,
                        "matchup": matchup,
                        "team": team,
                        "name": name,
                        "PTS": num(rec.get("points")),
                        "REB": num(rec.get("rebounds")),
                        "AST": num(rec.get("assists")),
                        "STL": num(rec.get("steals")),
                        "BLK": num(rec.get("blocks")),
                        "3PM": num(rec.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted")),
                        "MIN": minutes,
                    })
    return actuals

# ═══════════════════════════════════════════════════════════════
# PHASE 4 — TC MATH ENGINE (offline — no API calls)
# ═══════════════════════════════════════════════════════════════

def bayes_shrink(sample_mean: float, n: int, stat: str) -> float:
    """
    Bayesian shrinkage: pull sample mean toward league prior.
    weight_prior = alpha / (n + alpha)
    """
    alpha = STAT_BAYES_ALPHA.get(stat, 7.0)
    prior = STAT_PRIOR.get(stat, 1.0)
    return (sample_mean * n + prior * alpha) / (n + alpha)

def apply_pace(projection: float, team: str, league: str) -> float:
    """Adjust projection for fast/slow teams (±3%)."""
    fast = FAST_TEAMS_WNBA if league.upper() == "WNBA" else FAST_TEAMS_NBA
    slow = SLOW_TEAMS_WNBA if league.upper() == "WNBA" else SLOW_TEAMS_NBA
    if team.upper() in fast:
        return round(projection * 1.03, 1)
    elif team.upper() in slow:
        return round(projection * 0.97, 1)
    return projection

def grade_daily_pipeline_projections(espn_actuals: List[dict], league: str) -> List[dict]:
    """
    Fallback: Load the daily pipeline's TC projections from Daily_Log/YYYY-MM-DD/
    and grade them against ESPN box-score actuals.
    
    Matches players by normalizing names (ESPN uses "R. Howard" format, 
    pipeline uses "Rhyne Howard" full names).
    """
    # Build lookup from ESPN actuals: key = (team, stat, normalized_name)
    espn_lookup: Dict[Tuple[str, str, str], dict] = {}
    for a in espn_actuals:
        norm_name = _normalize_espn_name(a["name"])
        team = a["team"]
        for stat in ("PTS", "REB", "AST", "STL", "BLK", "3PM"):
            key = (team, stat, norm_name)
            espn_lookup[key] = a

    # Find and load daily projection files
    date_str = espn_actuals[0]["date"] if espn_actuals else ""
    proj_pattern = f"proj_{league}_*.json"
    log_dir = LOG_DIR / date_str if date_str else LOG_DIR
    
    graded = []
    proj_count = 0
    
    if not log_dir.exists():
        return graded
    
    proj_files = sorted(log_dir.glob(proj_pattern))
    for pf in proj_files:
        try:
            data = json.loads(pf.read_text())
        except Exception:
            continue
        
        props = data.get("valid_props", [])
        proj_count += len(props)
        
        for prop in props:
            player = prop.get("player", "")
            team = prop.get("team", "")
            stat = prop.get("stat", "")
            tc_proj = prop.get("tc_projection", 0)
            
            # Normalize player name for matching
            norm_name = _normalize_pipeline_name(player)
            
            key = (team, stat, norm_name)
            if key not in espn_lookup:
                continue
            
            actual_row = espn_lookup[key]
            actual_val = actual_row.get(stat, 0)
            
            diff = round(actual_val - tc_proj, 2)
            if abs(diff) < 0.1:
                result = "PUSH"
            elif actual_val > tc_proj:
                result = "HIT"
            else:
                result = "MISS"
            
            graded.append({
                "date": actual_row["date"],
                "matchup": actual_row["matchup"],
                "team": team,
                "name": player,
                "stat": stat,
                "raw_avg": prop.get("raw_average", 0),
                "tc_proj": tc_proj,
                "actual": actual_val,
                "diff": diff,
                "result": result,
                "minutes": actual_row.get("MIN", 0),
                "source": "daily_pipeline_fallback",
            })
    
    if proj_count:
        log(f"  Loaded {proj_count} props from {len(proj_files)} files, matched {len(graded)}")
    
    return graded


def _normalize_espn_name(name: str) -> str:
    """Normalize ESPN name format 'R. Howard' → 'rhoward' for fuzzy matching."""
    parts = name.split()
    if len(parts) >= 2 and len(parts[0]) == 2 and parts[0].endswith('.'):
        return (parts[0][0] + parts[-1]).lower()
    return name.lower().replace(" ", "").replace(".", "").replace("-", "").replace("'", "")


def _normalize_pipeline_name(name: str) -> str:
    """Normalize pipeline name format 'Rhyne Howard' → matching key."""
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1]).lower()
    return name.lower().replace(" ", "").replace(".", "").replace("-", "").replace("'", "")

def compute_tc_projections(espn_actuals: List[dict],
                           use_bayes: bool = True,
                           use_pace: bool = True,
                           use_b2b: bool = True) -> List[dict]:
    """
    Compute TC projections from ESPN box scores using leave-one-out methodology.
    For each player on each game date, compute:
      - Rolling average of prior games (excluding current)
      - Apply CONS multiplier
      - Apply Bayesian shrinkage
      - Apply team-pace and B2B adjustments
    
    Returns list of {date, matchup, team, name, stat, raw_avg, tc_proj, actual, result}
    """
    # Group by (team, player_name)
    by_player: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for r in espn_actuals:
        by_player[(r["team"], r["name"])].append(r)
    for recs in by_player.values():
        recs.sort(key=lambda x: x["date"])

    # Track team last-game dates for B2B detection
    team_last_date: Dict[str, str] = {}

    projections: List[dict] = []
    starter_dropped = 0

    for (team, name), recs in by_player.items():
        if len(recs) < 2:
            continue
        # Starter gate: drop players with last-game minutes < 12
        if recs[-1]["MIN"] < 12:
            starter_dropped += 1
            continue

        for idx, current in enumerate(recs):
            others = [r for j, r in enumerate(recs) if j != idx]
            if not others:
                continue
            n = len(others)

            for stat in ("PTS", "REB", "AST", "STL", "BLK", "3PM"):
                vals = [o[stat] for o in others]
                sample_mean = sum(vals) / n
                if sample_mean < MIN_AVG.get(stat, 0.05):
                    continue

                # Bayesian shrinkage toward league prior
                if use_bayes:
                    mean = bayes_shrink(sample_mean, n, stat)
                else:
                    mean = sample_mean

                # Team-pace adjustment
                if use_pace:
                    mean = apply_pace(mean, team, "WNBA" if "WNBA" in current.get("date", "") else "NBA")

                # B2B adjustment: -5% if played yesterday
                if use_b2b and team in team_last_date:
                    try:
                        cur_d = datetime.strptime(current["date"], "%Y-%m-%d")
                        last_d = datetime.strptime(team_last_date[team], "%Y-%m-%d")
                        if (cur_d - last_d).days == 1:
                            mean *= 0.95
                    except Exception:
                        pass

                tc = round(mean * STAT_CONS[stat], 1)
                actual = current[stat]
                diff = round(actual - tc, 2)
                if abs(diff) < 0.1:
                    result = "PUSH"
                elif actual > tc:
                    result = "HIT"
                else:
                    result = "MISS"

                projections.append({
                    "date": current["date"],
                    "matchup": current["matchup"],
                    "team": team,
                    "name": name,
                    "stat": stat,
                    "raw_avg": round(sample_mean, 2),
                    "tc_proj": tc,
                    "actual": actual,
                    "diff": diff,
                    "result": result,
                    "minutes": current["MIN"],
                })

        team_last_date[team] = recs[-1]["date"]

    log(f"  TC projections computed: {len(projections)} picks "
        f"(dropped {starter_dropped} low-minute players)")
    return projections

# ═══════════════════════════════════════════════════════════════
# PHASE 5 — CROSS-REFERENCE: TC vs DK LINES
# ═══════════════════════════════════════════════════════════════

def cross_tc_vs_dk(tc_projections: List[dict],
                   dk_player_lines: Dict[str, List[dict]]) -> List[dict]:
    """
    For each TC projection, find the matching DK line and compute edge.
    Edge = TC_proj - DK_line (positive = TC says OVER relative to DK line)
    """
    edges: List[dict] = []
    matched = 0
    unmatched = 0
    for p in tc_projections:
        stat = p["stat"]
        player_name = p["name"]
        best_match = None
        best_score = 0
        for dk_name, dk_stats in dk_player_lines.items():
            if not match_player(player_name, dk_name):
                continue
            for ds in dk_stats:
                if ds["stat"] != stat:
                    continue
                score = len(normalize_name(player_name).split() & normalize_name(dk_name).split())
                if score > best_score:
                    best_score = score
                    best_match = ds
        if best_match:
            dk_line = best_match["dk_line"]
            edge = round(p["tc_proj"] - dk_line, 2)
            direction = "OVER" if edge > 0 else "UNDER" if edge < 0 else "PUSH"
            edges.append({**p, "dk_line": dk_line, "dk_odds": best_match.get("dk_odds"),
                          "edge": edge, "edge_direction": direction})
            matched += 1
        else:
            unmatched += 1
    log(f"  Cross-ref TC vs DK: {matched} matched, {unmatched} unmatched")
    return edges

# ═══════════════════════════════════════════════════════════════
# PHASE 6 — REPORTING
# ═══════════════════════════════════════════════════════════════

def generate_report(projections: List[dict],
                    dk_combos: List[dict],
                    edges: List[dict],
                    league: str,
                    date_range: str,
                    features: dict,
                    out_dir: Path) -> str:
    """Generate markdown report + CSV + JSON summary."""

    # Aggregate stats
    by_stat = defaultdict(lambda: [0, 0, 0])  # HIT, MISS, PUSH
    by_team = defaultdict(lambda: [0, 0, 0])
    by_matchup = defaultdict(lambda: [0, 0, 0])
    edge_qualified = []

    for p in projections:
        idx = 0 if p["result"] == "HIT" else 1 if p["result"] == "MISS" else 2
        by_stat[p["stat"]][idx] += 1
        by_team[p["team"]][idx] += 1
        by_matchup[p["matchup"]][idx] += 1

    overall = [sum(b[i] for b in by_stat.values()) for i in range(3)]

    # Edge-filtered picks
    if edges:
        for e in edges:
            if abs(e.get("edge", 0)) >= 0.5:
                edge_qualified.append(e)

    def hit_pct(b):
        total = b[0] + b[1]
        return f"{b[0]/total*100:.1f}%" if total > 0 else "—"

    def hit_frac(b):
        total = b[0] + b[1]
        return f"{b[0]}/{total}" if total > 0 else "0/0"

    md = []
    md.append(f"# TC Backtest Report — {league}")
    md.append("")
    md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    md.append(f"**Date range:** {date_range}")
    md.append(f"**Total picks graded:** {len(projections)}")
    md.append(f"**DK combo lines fetched:** {len(dk_combos)}")
    md.append(f"**TC vs DK cross-ref matches:** {len(edges)}")
    md.append("")

    # Methodology
    md.append("## Methodology")
    md.append("")
    md.append("| Parameter | Value |")
    md.append("|---|---|")
    md.append(f"| CONS (PTS/REB/AST/3PM) | {STAT_CONS['PTS']}x |")
    md.append(f"| CONS (STL/BLK) | {STAT_CONS['STL']}x |")
    md.append(f"| Bayesian shrinkage | {'ON' if features.get('bayes') else 'OFF'} |")
    md.append(f"| Team-pace adjustment | {'ON' if features.get('pace') else 'OFF'} |")
    md.append(f"| B2B adjustment | {'ON' if features.get('b2b') else 'OFF'} |")
    md.append(f"| Starter gate (min 12 min) | ON |")
    md.append(f"| Grade window | ±0.1 PUSH |")
    md.append("")

    # Overall
    md.append("## Overall Hit Rate")
    md.append("")
    md.append(f"**{hit_pct(overall)}** ({hit_frac(overall)} graded)  |  Pushes: {overall[2]}")
    md.append("")

    # By Stat
    md.append("## Hit Rate by Stat")
    md.append("")
    md.append("| Stat | Picks | Hit | Miss | Push | Hit% |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for s in ("PTS", "REB", "AST", "STL", "BLK", "3PM"):
        if s in by_stat:
            b = by_stat[s]
            md.append(f"| {s} | {sum(b)} | {b[0]} | {b[1]} | {b[2]} | {hit_pct(b)} |")
    md.append("")

    # By Team
    md.append("## Hit Rate by Team")
    md.append("")
    md.append("| Team | Picks | Hit | Miss | Push | Hit% |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for t, b in sorted(by_team.items(), key=lambda x: -(x[1][0] / max(1, x[1][0] + x[1][1])) if x[1][0] + x[1][1] > 0 else 0):
        md.append(f"| {t} | {sum(b)} | {b[0]} | {b[1]} | {b[2]} | {hit_pct(b)} |")
    md.append("")

    # By Matchup
    md.append("## Hit Rate by Matchup")
    md.append("")
    md.append("| Matchup | Picks | Hit | Miss | Push | Hit% |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for m, b in sorted(by_matchup.items(), key=lambda x: -(x[1][0] / max(1, x[1][0] + x[1][1])) if x[1][0] + x[1][1] > 0 else 0):
        md.append(f"| {m} | {sum(b)} | {b[0]} | {b[1]} | {b[2]} | {hit_pct(b)} |")
    md.append("")

    # Edge-qualified picks (TC vs DK line gap)
    if edge_qualified:
        md.append("## Edge-Qualified Picks (|TC − DK| ≥ 0.5)")
        md.append("")
        md.append("| Date | Player | Stat | TC Proj | DK Line | Edge | Direction | Actual | Result |")
        md.append("|---|---|---|---:|---:|---:|---:|---:|---|")
        for e in sorted(edge_qualified, key=lambda x: -abs(x["edge"]))[:30]:
            emoji = "🟢" if e["result"] == "HIT" else "🔴" if e["result"] == "MISS" else "⚪"
            md.append(f"| {e['date']} | {e['name']} ({e['team']}) | {e['stat']} "
                     f"| {e['tc_proj']} | {e['dk_line']} | {e['edge']:+} | {e['edge_direction']} "
                     f"| {e['actual']} | {emoji} {e['result']} |")
        md.append("")

    # Recent picks
    md.append("## Recent Projections (last 40)")
    md.append("")
    md.append("| Date | Matchup | Player | Stat | TC | Actual | Diff | Result |")
    md.append("|---|---|---|---|---:|---:|---:|---|")
    for p in sorted(projections, key=lambda x: (x["date"], x["matchup"]))[-40:]:
        emoji = "🟢" if p["result"] == "HIT" else "🔴" if p["result"] == "MISS" else "⚪"
        md.append(f"| {p['date']} | {p['matchup']} | {p['name']} ({p['team']}) | {p['stat']} "
                 f"| {p['tc_proj']} | {p['actual']} | {p['diff']:+} | {emoji} {p['result']} |")
    md.append("")

    # Top/Bottom performers
    by_player_hit = defaultdict(lambda: [0, 0])
    for p in projections:
        k = f"{p['name']} ({p['team']})"
        if p["result"] == "HIT":
            by_player_hit[k][0] += 1
        elif p["result"] == "MISS":
            by_player_hit[k][1] += 1

    top_players = sorted([(n, b) for n, b in by_player_hit.items() if b[0] + b[1] >= 3],
                         key=lambda x: -x[1][0] / max(1, x[1][0] + x[1][1]))[:10]
    bot_players = sorted([(n, b) for n, b in by_player_hit.items() if b[0] + b[1] >= 3],
                         key=lambda x: x[1][0] / max(1, x[1][0] + x[1][1]))[:10]

    if top_players:
        md.append("## Best TC Performers (min 3 picks)")
        md.append("")
        md.append("| Player | Record | Hit% |")
        md.append("|---|---|---|")
        for n, b in top_players:
            md.append(f"| {n} | {b[0]}/{b[0]+b[1]} | {b[0]/max(1,b[0]+b[1])*100:.1f}% |")
        md.append("")

    if bot_players:
        md.append("## Worst TC Performers (min 3 picks)")
        md.append("")
        md.append("| Player | Record | Hit% |")
        md.append("|---|---|---|")
        for n, b in bot_players:
            md.append(f"| {n} | {b[0]}/{b[0]+b[1]} | {b[0]/max(1,b[0]+b[1])*100:.1f}% |")
        md.append("")

    # File listing
    md.append("## Output Files")
    md.append("")
    md.append(f"| File | Description |")
    md.append("|---|---|")
    md.append(f"| `{out_dir.name}/report.md` | This report |")
    md.append(f"| `{out_dir.name}/historical_raw.json` | Raw Odds API historical response |")
    md.append(f"| `{out_dir.name}/scores_raw.json` | Raw Odds API scores response |")
    md.append(f"| `{out_dir.name}/espn_actuals.json` | Parsed ESPN box score actuals |")
    md.append(f"| `{out_dir.name}/projections.csv` | Full TC projections CSV |")
    md.append(f"| `{out_dir.name}/projections.json` | Full TC projections JSON |")
    md.append(f"| `{out_dir.name}/edges.json` | TC-vs-DK edge cross-reference |")
    md.append(f"| `{out_dir.name}/summary.json` | Summary statistics |")

    report_text = "\n".join(md) + "\n"
    (out_dir / "report.md").write_text(report_text)

    # Save CSVs/JSONs
    if projections:
        with open(out_dir / "projections.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(projections[0].keys()))
            w.writeheader()
            w.writerows(projections)

    (out_dir / "projections.json").write_text(json.dumps(projections, indent=2))
    if edges:
        (out_dir / "edges.json").write_text(json.dumps(edges, indent=2))

    # Summary
    summary = {
        "generated_at": datetime.now().isoformat(),
        "league": league,
        "date_range": date_range,
        "total_picks": len(projections),
        "overall_hit_rate": overall[0] / max(1, overall[0] + overall[1]) if overall[0] + overall[1] > 0 else 0,
        "overall_hit_fraction": f"{overall[0]}/{overall[0]+overall[1]}",
        "pushes": overall[2],
        "dk_combos_fetched": len(dk_combos),
        "tc_vs_dk_matches": len(edges),
        "by_stat": {k: {"hit": v[0], "miss": v[1], "push": v[2],
                        "rate": v[0] / max(1, v[0] + v[1])}
                    for k, v in by_stat.items()},
        "features": features,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    vlog(f"  Summary: {json.dumps(summary, indent=2)}")

    return report_text

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    global VERBOSE

    parser = argparse.ArgumentParser(
        description="TC Backtest Pipeline — Odds API historical combo props + ESPN settlement"
    )
    parser.add_argument("--league", default="WNBA", choices=["NBA", "WNBA", "BOTH"],
                        help="League to backtest (default: WNBA)")
    parser.add_argument("--date", default="",
                        help="Single date YYYY-MM-DD (default: yesterday)")
    parser.add_argument("--days", type=int, default=1,
                        help="Number of past days to fetch (default: 1, max: 7)")
    parser.add_argument("--output", default="",
                        help="Output directory (default: Daily_Log/backtests/YYYY-MM-DD/)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan, skip all API calls")
    parser.add_argument("--no-bayes", action="store_true",
                        help="Disable Bayesian shrinkage")
    parser.add_argument("--no-pace", action="store_true",
                        help="Disable team-pace adjustment")
    parser.add_argument("--no-b2b", action="store_true",
                        help="Disable back-to-back adjustment")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose debug logging")
    args = parser.parse_args()

    VERBOSE = args.verbose
    days = min(args.days, 7)

    # Determine date range
    if args.date:
        start_date = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        start_date = datetime.now() - timedelta(days=1)
    end_date = start_date + timedelta(days=days - 1)
    today = datetime.now()
    if end_date > today:
        end_date = today
        start_date = end_date - timedelta(days=days - 1)

    # Output directory
    if args.output:
        out_dir = Path(args.output)
    else:
        out_dir = LOG_DIR / f"backtests/{start_date.strftime('%Y-%m-%d')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    leagues = [args.league] if args.league != "BOTH" else ["WNBA", "NBA"]

    log("=" * 60)
    log("TC BACKTEST PIPELINE")
    log("=" * 60)
    log(f"  League(s): {leagues}")
    log(f"  Date range: {start_date.date()} to {end_date.date()} ({days} day(s))")
    log(f"  Features: bayes={not args.no_bayes}, pace={not args.no_pace}, b2b={not args.no_b2b}")
    log(f"  Output: {out_dir}")
    log(f"  Dry run: {args.dry_run}")
    log("")


    # ── Estimate credit cost ──
    est_calls = len(leagues) * days + len(leagues)  # historical (10x) + scores (1x)
    est_credits = len(leagues) * days * 10 + len(leagues)
    log(f"ESTIMATED CREDITS: ~{est_credits} ({est_calls} API calls)")
    log("")

    if args.dry_run:
        log("DRY RUN COMPLETE — no API calls made.")
        log(f"Would write output to: {out_dir}")
        return

    all_projections: List[dict] = []
    all_dk_combos: List[dict] = []
    all_edges: List[dict] = []

    for league in leagues:
        log(f"--- {league} ---")
        sport_key = SPORT_MAP.get(league.upper())
        if not sport_key:
            log(f"  Unknown league: {league}")
            continue

        # ── Phase 1: Fetch historical DK combo props ──
        log(f"PHASE 1: Fetching historical DK combo props ({league})...")
        historical_events = []
        cur = start_date
        while cur <= end_date:
            date_str = cur.strftime("%Y-%m-%d")
            try:
                events = fetch_historical_combo_props(sport_key, date_str)
                historical_events.extend(events)
                log(f"  {date_str}: {len(events)} events")
            except Exception as e:
                log(f"  {date_str}: ERROR — {e}")
            cur += timedelta(days=1)

        raw_file = out_dir / f"historical_{league.lower()}_raw.json"
        raw_file.write_text(json.dumps(historical_events, indent=2))
        log(f"  Saved: {raw_file}")

        # ── Phase 2: DK combo lines + player stat lines ──
        log(f"PHASE 2: Extracting DK combo lines...")
        dk_combos = extract_dk_combos(historical_events)
        dk_player_lines = extract_dk_player_stats(historical_events)
        log(f"  Combos: {len(dk_combos)} legs across {len(dk_player_lines)} players")
        all_dk_combos.extend(dk_combos)

        # ── Phase 3: Fetch scores (game-level cross-ref) ──
        log(f"PHASE 3: Fetching scores ({league})...")
        try:
            scores = fetch_historical_scores(sport_key, days_from=days)
            scores_file = out_dir / f"scores_{league.lower()}_raw.json"
            scores_file.write_text(json.dumps(scores, indent=2))
            log(f"  Saved: {scores_file} ({len(scores)} games)")
        except Exception as e:
            log(f"  Scores fetch error: {e}")

        # ── Phase 4: ESPN box scores (player-level settlement) ──
        log(f"PHASE 4: Fetching ESPN box scores ({league})...")
        all_espn_actuals = []
        cur = start_date
        while cur <= end_date:
            date_str = cur.strftime("%Y-%m-%d")
            date_ymd = cur.strftime("%Y%m%d")
            espn_events = fetch_espn_scoreboard(date_ymd, league)
            if espn_events:
                actuals = extract_espn_actuals(espn_events, league)
                all_espn_actuals.extend(actuals)
                completed = sum(1 for ev in espn_events
                                if "final" in (ev.get("status", {}).get("type", {}).get("description", "") or "").lower())
                log(f"  {date_str}: {len(espn_events)} games, {completed} completed, {len(actuals)} player-games")
            else:
                log(f"  {date_str}: no games")
            cur += timedelta(days=1)

        actuals_file = out_dir / f"espn_actuals_{league.lower()}.json"
        actuals_file.write_text(json.dumps(all_espn_actuals, indent=2))
        log(f"  Saved: {actuals_file} ({len(all_espn_actuals)} player-games)")

        # ── Phase 5: TC Math ──
        log(f"PHASE 5: Running TC Math ({league})...")
        features = {
            "bayes": not args.no_bayes,
            "pace": not args.no_pace,
            "b2b": not args.no_b2b,
        }
        projections = compute_tc_projections(
            all_espn_actuals,
            use_bayes=features["bayes"],
            use_pace=features["pace"],
            use_b2b=features["b2b"],
        )
        all_projections.extend(projections)

        # ── Phase 5b: Fallback to daily pipeline projections ──
        if len(projections) == 0 and len(all_espn_actuals) > 0:
            log(f"PHASE 5b: No TC math projections — loading daily pipeline projections as fallback...")
            daily_projs = grade_daily_pipeline_projections(all_espn_actuals, league)
            log(f"  Daily pipeline fallback: {len(daily_projs)} picks graded")
            all_projections.extend(daily_projs)

        # ── Phase 6: Cross-ref TC vs DK lines ──
        log(f"PHASE 6: Cross-referencing TC vs DK lines ({league})...")
        edges = cross_tc_vs_dk(projections, dk_player_lines)
        all_edges.extend(edges)

    # ── Final: Generate report ──
    log("")
    log("REPORT GENERATION")
    date_range_str = f"{start_date.date()}" if days == 1 else f"{start_date.date()} to {end_date.date()}"
    report = generate_report(
        all_projections, all_dk_combos, all_edges,
        league=args.league,
        date_range=date_range_str,
        features=features,
        out_dir=out_dir,
    )

    log("")
    log("=" * 60)
    log("BACKTEST COMPLETE")
    log(f"  Picks: {len(all_projections)}")
    log(f"  DK combos: {len(all_dk_combos)}")
    log(f"  TC vs DK edges: {len(all_edges)}")
    log(f"  Report: {out_dir}/report.md")
    log(f"  Files: {out_dir}/")
    log("=" * 60)

    # Print report to stdout for visibility
    print("\n" + report)

if __name__ == "__main__":
    main()
