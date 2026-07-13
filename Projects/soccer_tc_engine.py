#!/usr/bin/env python3

# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""
Soccer TC Engine — Triple Conservative projections for soccer (World Cup + beyond).

Covers:
  - Game-level DK lines: Moneyline (h2h), Totals (BetMGM), Both Teams to Score (BTTS)
  - Player stat projections: Goals, Shots, Shots on Target, Assists, Cards, Fouls, Tackles, Passes
  - Soccer-adapted TC formula with opponent strength, position factors, Poisson for goals

Data sources:
  - The Odds API (h2h/totals/btts for World Cup) — already connected
  - FIFA rankings / team strength indices (embedded)
  - Extensible for FBref player historical data

Output:
  - /home/workspace/Daily_Log/YYYY-MM-DD/soccer_picks.csv
  - /home/workspace/Daily_Log/YYYY-MM-DD/soccer_picks.json
  - /home/workspace/Daily_Log/last_run_soccer.json

Usage:
  python3 soccer_tc_engine.py                    # all World Cup games today
  python3 soccer_tc_engine.py --game "BRA@MAR"   # specific matchup
  python3 soccer_tc_engine.py --report            # generate markdown report
"""

import os
import json
import csv
import sys
import math
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from tc_math import over_under_signal

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"
LOG_DIR.mkdir(exist_ok=True)

SECRETS_FILE = "/root/.zo/secrets.env"
ODDS_BASE = "https://api.theoddsapi.com"

def load_secrets():
    """Load API keys from secrets file."""
    try:
        txt = Path(SECRETS_FILE).read_text()
        for line in txt.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))
    except Exception:
        import logging as _log
        _log.getLogger(__name__).debug("exception", exc_info=True)

load_secrets()

# Leagues available for soccer via Odds API
SOCCER_SPORTS = [
    "soccer_fifa_world_cup",
    # Add more as they become available: soccer_epl, soccer_mls, soccer_uefa_champs_league, etc.
]

# ═══════════════════════════════════════════════════════════════════════════════
# SOCCER STAT DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Soccer stats we project with TC formula
SOCCER_STATS = {
    "G":  {"name": "Goals",        "unit": "goals",    "dist": "poisson",  "avg_range": (0.0, 2.5), "dk_market": "player_goals"},
    "A":  {"name": "Assists",      "unit": "assists",   "dist": "poisson",  "avg_range": (0.0, 1.5), "dk_market": "player_assists"},
    "SOT":{"name": "Shots on Target","unit": "sot",     "dist": "normal",   "avg_range": (0.0, 3.0), "dk_market": "player_shots_on_target"},
    "S":  {"name": "Shots",        "unit": "shots",     "dist": "normal",   "avg_range": (0.0, 5.0), "dk_market": "player_shots"},
    "COR":{"name": "Corners",      "unit": "corners",   "dist": "normal",   "avg_range": (0.0, 3.0), "dk_market": "player_corners"},
    "TKL":{"name": "Tackles",      "unit": "tackles",   "dist": "normal",   "avg_range": (0.5, 5.0), "dk_market": "player_tackles"},
    "FC": {"name": "Fouls Committed","unit": "fouls",   "dist": "normal",   "avg_range": (0.0, 3.0), "dk_market": "player_fouls"},
    "CRD":{"name": "Cards",        "unit": "cards",     "dist": "poisson",  "avg_range": (0.0, 1.0), "dk_market": "player_cards"},
    "PAS":{"name": "Passes",       "unit": "passes",    "dist": "normal",   "avg_range": (15.0, 80.0),"dk_market": "player_passes"},
}

# Position groups with stat weights (how much each position contributes to each stat)
POSITION_PROFILES = {
    "GK":  {"G":0.0, "A":0.0,  "SOT":0.0, "S":0.0,  "COR":0.0, "TKL":0.1, "FC":0.05, "CRD":0.05, "PAS":0.3},
    "DEF": {"G":0.1, "A":0.1,  "SOT":0.1, "S":0.15, "COR":0.35,"TKL":0.35,"FC":0.25, "CRD":0.35, "PAS":0.2},
    "MID": {"G":0.2, "A":0.35, "SOT":0.3, "S":0.35, "COR":0.3, "TKL":0.35,"FC":0.4,  "CRD":0.4,  "PAS":0.35},
    "FWD": {"G":0.7, "A":0.55, "SOT":0.6, "S":0.5,  "COR":0.1, "TKL":0.2, "FC":0.3,  "CRD":0.2,  "PAS":0.15},
}

# World Cup 2026 team strength ratings (FIFA ranking + recent form proxy, 0.5-1.5 scale)
TEAM_STRENGTH = {
    "Brazil": 1.28, "France": 1.25, "Argentina": 1.24, "England": 1.22,
    "Spain": 1.20, "Germany": 1.18, "Portugal": 1.17, "Netherlands": 1.16,
    "Italy": 1.15, "Belgium": 1.13, "Croatia": 1.12, "Uruguay": 1.11,
    "Morocco": 1.10, "Colombia": 1.08, "Mexico": 1.06, "USA": 1.05,
    "Senegal": 1.04, "Japan": 1.03, "South Korea": 1.02, "Switzerland": 1.02,
    "Denmark": 1.01, "Austria": 1.00, "Nigeria": 0.98, "Ecuador": 0.97,
    "Serbia": 0.96, "Iran": 0.95, "Australia": 0.94, "Wales": 0.93,
    "Poland": 0.92, "Sweden": 0.91, "Egypt": 0.90, "Ivory Coast": 0.89,
    "Tunisia": 0.87, "Chile": 0.86, "Peru": 0.85, "Ukraine": 0.84,
    "Turkey": 0.83, "Norway": 0.82, "Scotland": 0.80, "Czech Republic": 0.79,
    "Cameroon": 0.78, "Ghana": 0.77, "Mali": 0.75, "Cape Verde": 0.76, "Burkina Faso": 0.74,
    "South Africa": 0.73, "DR Congo": 0.72, "Algeria": 0.71, "Paraguay": 0.70,
    "Canada": 0.69, "Costa Rica": 0.67, "Panama": 0.65, "Jamaica": 0.63,
    "Venezuela": 0.62, "Bolivia": 0.60, "Honduras": 0.58, "El Salvador": 0.55,
    "Saudi Arabia": 0.54, "Qatar": 0.53, "UAE": 0.52, "Iraq": 0.50,
    "Uzbekistan": 0.49, "China": 0.47, "Thailand": 0.45, "New Zealand": 0.44,
    "Haiti": 0.40, "Curaçao": 0.38, "Trinidad & Tobago": 0.36,
}

# League-average expected stats per 90 by position (for a "default" player)
LEAGUE_AVG_PER_90 = {
    "GK":  {"G":0.0,  "A":0.0,  "SOT":0.0,  "S":0.0,   "COR":0.0,  "TKL":0.5,  "FC":0.1,  "CRD":0.05, "PAS":28.0},
    "DEF": {"G":0.05, "A":0.08, "SOT":0.15, "S":0.4,   "COR":1.5,  "TKL":2.5,  "FC":1.2,  "CRD":0.25, "PAS":45.0},
    "MID": {"G":0.12, "A":0.15, "SOT":0.4,  "S":1.2,   "COR":1.0,  "TKL":2.0,  "FC":1.5,  "CRD":0.30, "PAS":52.0},
    "FWD": {"G":0.35, "A":0.18, "SOT":1.2,  "S":2.5,   "COR":0.3,  "TKL":0.8,  "FC":1.0,  "CRD":0.15, "PAS":28.0},
}

EDGE_THRESHOLD = 0.5   # edge threshold for OVER/UNDER signal (goals are low-volume)
EDGE_STRONG = 1.0      # strong signal (wider edge)
MIN_PROJECTION = 0.5  # below this, don't generate picks (noise floor)

# ═══════════════════════════════════════════════════════════════════════════════
# ODDS API — FETCH WORLD CUP EVENTS + GAME ODDS
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_world_cup_events() -> List[dict]:
    """Fetch all active World Cup events from Odds API.

    Odds API spec: GET /events/?sport_key={key}
    The /sports/{key}/events path no longer exists on the current v4 spec.
    """
    all_events = []
    for sport_key in SOCCER_SPORTS:
        try:
            params = {"sport_key": sport_key}
            api_key = os.environ.get("ODDS_API_KEY", "")
            if api_key:
                params["apiKey"] = api_key
            r = requests.get(
                f"{ODDS_BASE}/events/",
                params=params,
                timeout=15,
            )
            r.raise_for_status()
            payload = r.json()
            # Odds API wraps events in {"data": [...]} on v4 spec
            if isinstance(payload, dict) and "data" in payload:
                events = payload.get("data") or []
            else:
                events = payload or []
            for ev in events:
                ev["_sport_key"] = sport_key
            all_events.extend(events)
        except Exception as e:
            print(f"[soccer] {sport_key} events failed: {e}", file=sys.stderr)
    return all_events

def fetch_soccer_odds(event_id: str, sport_key: str = "soccer_fifa_world_cup") -> dict:
    """Fetch DK + BetMGM lines for a single soccer event.

    Returns: {event_id, home_team, away_team, dk: {h2h, btts}, betmgm: {h2h, totals, btts}, ...}
    """
    try:
        r = requests.get(
            f"{ODDS_BASE}/odds/?sport_key={sport_key}&eventId={event_id}",
            params={
                "regions": "us",
                "oddsFormat": "american",
                "markets": "h2h,totals,btts",
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()

        result = {
            "event_id": event_id,
            "home_team": data.get("home_team", ""),
            "away_team": data.get("away_team", ""),
            "commence_time": data.get("commence_time", ""),
        }

        for bm in data.get("bookmakers", []):
            key = bm.get("key", "")
            result.setdefault(key, {})
            for market in bm.get("markets", []):
                mk = market.get("key")
                outcomes = {}
                for o in market.get("outcomes", []):
                    name = o.get("name", "")
                    outcomes[name] = {
                        "price": o.get("price"),
                        "point": o.get("point"),
                    }
                result[key][mk] = outcomes

        return result
    except Exception as e:
        print(f"[soccer] Odds fetch failed for {event_id}: {e}", file=sys.stderr)
        return {"event_id": event_id, "error": str(e)}

def fetch_live_stats(event_id: str, sport_key: str = "soccer_fifa_world_cup") -> dict:
    """Fetch player + team stats for a live/soon-to-be-live soccer event.

    Returns:
        {
          "event_id": str,
          "players": [ { "name", "team", "G", "A", "SH", "SOT", "PASS", "TKL", "Cards" } ... ],
          "team":    { home: { "possession", "corners", "shots", "shots_on_target" },
                       away: { "possession", "corners", "shots", "shots_on_target" } }
        }

    Uses the projection engine as the stat source (no live feed exposed by
    Odds API for player props in WC). DK/BetMGM lines come from fetch_soccer_odds.
    """
    odds = fetch_soccer_odds(event_id, sport_key)
    home = odds.get("home_team") or "Home"
    away = odds.get("away_team") or "Away"

    home_strength = get_team_strength(home)
    away_strength = get_team_strength(away)

    squad_home = generate_default_squad(home)
    squad_away = generate_default_squad(away)

    def _proj(squad, team_name, strength):
        out = []
        for p in squad:
            try:
                ps = project_player_stats(p, team_name, strength, p.get("position", "M"))
                stats = ps.get("stats", {})
                out.append({
                    "name": p.get("name", "Unknown"),
                    "team": team_name,
                    "G":  stats.get("goals", 0.0),
                    "A":  stats.get("assists", 0.0),
                    "SH": stats.get("shots", 0.0),
                    "SOT":stats.get("shots_on_target", 0.0),
                    "PASS": stats.get("passes", 0.0),
                    "TKL": stats.get("tackles", 0.0),
                    "Cards": stats.get("cards", 0.0),
                })
            except Exception:
                continue
        return out

    players = _proj(squad_home, home, home_strength) + _proj(squad_away, away, away_strength)

    home_total = project_game_total(home_strength, away_strength)
    away_total = project_game_total(away_strength, home_strength)

    def _split(total, share):
        return {
            "possession": f"{int(round(50 + (share - 1.0) * 10))}%",
            "corners":    max(0, int(round(total.get("projected_total", 2.5) * (0.6 + 0.1 * share)))),
            "shots":      max(0, int(round(total.get("projected_total", 12) * (0.45 + 0.05 * share)))),
            "shots_on_target": max(0, int(round(total.get("projected_total", 4) * (0.45 + 0.05 * share)))),
        }

    return {
        "event_id": event_id,
        "players": players,
        "team": {
            home: _split(home_total, home_strength),
            away: _split(away_total, away_strength),
        },
        "odds_summary": {
            "h2h":      (odds.get("draftkings") or {}).get("h2h") or (odds.get("betmgm") or {}).get("h2h"),
            "totals":   (odds.get("betmgm") or {}).get("totals"),
            "btts":     (odds.get("draftkings") or {}).get("btts") or (odds.get("betmgm") or {}).get("btts"),
        },
    }

# ═══════════════════════════════════════════════════════════════════════════════
# SOCCER TC FORMULA
# ═══════════════════════════════════════════════════════════════════════════════

def get_team_strength(team_name: str) -> float:
    """Get team strength rating (1.0 = average)."""
    for k, v in TEAM_STRENGTH.items():
        if k.lower() in team_name.lower() or team_name.lower() in k.lower():
            return v
    return 1.0  # unknown team = average

def tc_soccer_stat(
    stat_key: str,
    player_avg: float,
    position: str,
    team_strength: float,
    opponent_strength: float,
    is_home: bool,
    minutes_factor: float = 1.0,
) -> dict:
    """Compute TC projection for a single soccer stat.

    Soccer TC Formula (adapted from NBA TC = stat × 0.85):
      1. Base = player_avg (rolling 5-game or career avg per 90)
      2. Team_Adj = Base × team_strength  (stronger team = more attacking output)
      3. Opp_Adj  = Team_Adj × (1 / opponent_strength) × 0.85  (tougher opponent = less output)
      4. Home_Adj = Opp_Adj × 1.05 if home, × 0.95 if away
      5. TC_Proj  = Home_Adj × minutes_factor × position_weight

    For Poisson stats (Goals, Assists, Cards):
      - Raw projection is the Poisson lambda
      - TC_Line = round(TC_Proj, 1) — what we'd expect the sportsbook to set

    For Normal stats (Shots, Tackles, Fouls, Passes):
      - TC_Line = floor(TC_Proj × 0.88) — same NBA discount factor

    Args:
        stat_key: e.g. "G", "A", "SOT", "S", "TKL", "FC", "CRD", "PAS"
        player_avg: player's per-90 average for this stat
        position: "GK", "DEF", "MID", or "FWD"
        team_strength: team's strength rating (0.5-1.5)
        opponent_strength: opponent's strength rating
        is_home: home field advantage
        minutes_factor: 1.0 = full 90, 0.5 = sub expected 45 min, etc.

    Returns: {tc_raw, tc_adj, tc_projection, tc_line, edge, signal, components...}
    """
    if stat_key not in SOCCER_STATS:
        return {"error": f"Unknown stat: {stat_key}"}

    stat_info = SOCCER_STATS[stat_key]
    pos_profile = POSITION_PROFILES.get(position, POSITION_PROFILES["MID"])
    pos_weight = pos_profile.get(stat_key, 0.2)

    # 1. Base
    tc_raw = player_avg

    # 2. Team strength adjustment (capped to avoid extremes)
    team_factor = max(0.8, min(1.3, team_strength))
    tc_team = tc_raw * team_factor

    # 3. Opponent adjustment (stronger opponent = lower expected output)
    opp_def = 1.0 / max(opponent_strength, 0.4)
    opp_factor = max(0.7, min(1.3, opp_def * 0.85))
    tc_opp = tc_team * opp_factor

    # 4. Home/away
    home_factor = 1.05 if is_home else 0.95
    tc_home = tc_opp * home_factor

    # 5. Minutes + position weight
    tc_proj = tc_home * minutes_factor * pos_weight * 1.0  # position weight amplifies

    # 6. TC Line (estimated sportsbook line)
    if stat_info["dist"] == "poisson":
        # Poisson stats are low-count; round to nearest 0.5
        tc_line = round(tc_proj * 2) / 2
    else:
        # Normal stats: honest market estimate (no discount bias)
        tc_line = round(tc_proj * 2) / 2 if tc_proj > 0 else 0.0

    # 7. Edge vs estimated line (no hard discount bias)
    edge = tc_proj - tc_line

    # 8. Signal via sport-aware dispatcher (replaces 0.88x discount hack)
    from tc_math import sport_over_under_signal
    # sig_edge is PERCENTAGE (0.005 = 0.5%) for WC. Convert EDGE_THRESHOLD (absolute 0.5)
    # to pct = 0.5 / typical_line. Use 0.05 (5%) for low-vol, 0.10 (10%) for vol stats.
    if stat_key in ("G", "A", "CRD"):
        pct_threshold = 0.05
    else:
        pct_threshold = 0.10
    sig_dir, sig_edge = sport_over_under_signal(tc_proj, tc_line, sport="WC", min_edge=pct_threshold)
    if sig_dir == "OVER":
        signal = "OVER"
    elif sig_dir == "UNDER":
        signal = "UNDER"
    else:
        signal = "PASS"

    return {
        "stat": stat_key,
        "stat_name": stat_info["name"],
        "dist": stat_info["dist"],
        "tc_raw": round(tc_raw, 2),
        "tc_team_adj": round(tc_team, 2),
        "tc_opp_adj": round(tc_opp, 2),
        "tc_home_adj": round(tc_home, 2),
        "tc_projection": round(tc_proj, 2),
        "tc_line": tc_line,
        "edge": round(edge, 2),
        "signal": signal,
        "components": {
            "player_avg": player_avg,
            "team_factor": round(team_factor, 3),
            "opp_factor": round(opp_factor, 3),
            "home_factor": home_factor,
            "minutes_factor": minutes_factor,
            "position": position,
            "pos_weight": pos_weight,
        },
    }

# ═══════════════════════════════════════════════════════════════════════════════
# GAME-LEVEL PROJECTIONS (H2H, TOTALS, BTTS)
# ═══════════════════════════════════════════════════════════════════════════════

def project_team_match_stats(home_strength: float, away_strength: float) -> dict:
    """Project team-level match stats (corners + shots on target) for each team.

    Used for game-line picks (e.g. Belgium team total corners OVER 4.5).

    League baselines (World Cup 2026):
      - Corners:    home ~5.5 / game, away ~4.5 / game
      - SOT:        home ~5.5 / game, away ~4.0 / game
    Scaled by team strength ratio and home/away factor.
    """
    # League baselines
    home_corner_base = 5.5
    away_corner_base = 4.5
    home_sot_base = 5.5
    away_sot_base = 4.0

    # Home advantage: +8% corners and SOT
    home_factor = 1.08
    away_factor = 0.92

    # Strength ratio scales possession/attacking output
    # Home scale = home_strength / league_avg
    league_avg = 1.0
    home_scale = home_strength / league_avg
    away_scale = away_strength / league_avg

    home_corners = round(home_corner_base * home_factor * home_scale, 2)
    away_corners = round(away_corner_base * away_factor * away_scale, 2)
    home_sot = round(home_sot_base * home_factor * home_scale, 2)
    away_sot = round(away_sot_base * away_factor * away_scale, 2)

    total_corners = round(home_corners + away_corners, 2)
    total_sot = round(home_sot + away_sot, 2)

    return {
        "home_corners_proj": home_corners,
        "away_corners_proj": away_corners,
        "total_corners_proj": total_corners,
        "home_sot_proj": home_sot,
        "away_sot_proj": away_sot,
        "total_sot_proj": total_sot,
    }

def project_game_total(home_strength: float, away_strength: float) -> dict:
    """Project total goals using Poisson model based on team strengths.

    Expected goals = (home_strength + away_strength) × league_avg_goals / 2
    """
    league_avg_goals = 2.75  # World Cup average total goals
    home_exp = home_strength * league_avg_goals / 2 * 1.08  # home advantage
    away_exp = away_strength * league_avg_goals / 2 * 0.92
    total_exp = home_exp + away_exp

    # Poisson probability of OVER 2.5
    try:
        from scipy.stats import poisson as poisson_scipy
        over_2_5_prob = 1 - poisson_scipy.cdf(2, total_exp)  # P(X >= 3) = 1 - P(X <= 2)
        under_2_5_prob = poisson_scipy.cdf(2, total_exp)
    except ImportError:
        # Normal approximation
        std = math.sqrt(total_exp) if total_exp > 0 else 0.1
        z_2_5 = (2.5 - total_exp) / std
        from math import erf as math_erf
        under_2_5_prob = 0.5 * (1 + math_erf(z_2_5 / math.sqrt(2)))
        over_2_5_prob = 1 - under_2_5_prob

    signal = "OVER" if over_2_5_prob > 0.55 else "UNDER" if under_2_5_prob > 0.55 else "PASS"

    return {
        "home_expected_goals": round(home_exp, 2),
        "away_expected_goals": round(away_exp, 2),
        "total_expected_goals": round(total_exp, 2),
        "over_2_5_prob": round(over_2_5_prob, 3),
        "under_2_5_prob": round(under_2_5_prob, 3),
        "signal": signal,
    }

def project_btts(home_strength: float, away_strength: float) -> dict:
    """Project Both Teams to Score probability.

    BTTS probability = P(home scores) × P(away scores)
    Using Poisson: P(team scores >= 1) = 1 - P(0 goals)
    """
    league_avg = 2.75 / 2  # per team

    home_lambda = home_strength * league_avg * 1.08
    away_lambda = away_strength * league_avg * 0.92

    # P(team scores >= 1) = 1 - e^(-lambda)
    home_score_prob = 1 - math.exp(-home_lambda)
    away_score_prob = 1 - math.exp(-away_lambda)
    btts_prob = home_score_prob * away_score_prob

    signal = "YES" if btts_prob > 0.53 else "NO" if btts_prob < 0.47 else "PASS"

    return {
        "home_score_prob": round(home_score_prob, 3),
        "away_score_prob": round(away_score_prob, 3),
        "btts_probability": round(btts_prob, 3),
        "signal": signal,
    }

def project_h2h(home_strength: float, away_strength: float) -> dict:
    """Project moneyline win/draw probabilities.

    Using team strength differential + draw probability based on closeness.
    """
    strength_diff = home_strength - away_strength

    # Logit model for home win probability
    logit = strength_diff * 2.5 + 0.2  # 0.2 is home adv intercept
    home_win_prob = 1 / (1 + math.exp(-logit))

    # Draw probability peaks when teams are evenly matched
    # Max ~28% at equal strength, drops as teams diverge
    draw_prob = 0.28 * math.exp(-abs(strength_diff) * 3)

    away_win_prob = 1 - home_win_prob - draw_prob
    away_win_prob = max(0.01, away_win_prob)

    # Renormalize
    total = home_win_prob + draw_prob + away_win_prob
    home_win_prob /= total
    draw_prob /= total
    away_win_prob /= total

    # Signal for ML pick
    if home_win_prob > 0.50:
        signal = "HOME"
    elif away_win_prob > 0.45 and away_win_prob > home_win_prob:
        signal = "AWAY"
    elif draw_prob > 0.30:
        signal = "DRAW"
    else:
        signal = "PASS"

    return {
        "home_win_prob": round(home_win_prob, 3),
        "draw_prob": round(draw_prob, 3),
        "away_win_prob": round(away_win_prob, 3),
        "strength_diff": round(strength_diff, 3),
        "signal": signal,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# PLAYER PROJECTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_default_squad(team_name: str) -> List[dict]:
    """Generate a default 18-man squad with position assignments.

    In production, this would be replaced by live roster data from ESPN/FBref.
    For the World Cup, we use known squads.
    """
    # Simplified: generate generic squad based on position distribution
    squad = []
    pos_dist = [("GK", 2), ("DEF", 6), ("MID", 6), ("FWD", 4)]

    for pos, count in pos_dist:
        for i in range(count):
            squad.append({
                "name": f"{team_name}_{pos}_{i+1}",
                "position": pos,
                "team": team_name,
                "is_starter": i < {"GK": 1, "DEF": 4, "MID": 4, "FWD": 2}[pos],
                "minutes_factor": 1.0 if i < {"GK": 1, "DEF": 4, "MID": 4, "FWD": 2}[pos] else 0.3,
            })
    return squad

def project_player_stats(
    player: dict,
    team_strength: float,
    opponent_strength: float,
    is_home: bool,
    stat_keys: Optional[List[str]] = None,
    custom_avgs: Optional[dict] = None,
) -> List[dict]:
    """Project all stats for a single player.

    Args:
        player: {name, position, team, minutes_factor}
        team_strength: team strength rating
        opponent_strength: opponent strength rating
        is_home: home/away
        stat_keys: which stats to project (default: all)
        custom_avgs: {stat_key: avg_per_90} override for known player data

    Returns: list of stat projection dicts
    """
    if stat_keys is None:
        stat_keys = list(SOCCER_STATS.keys())

    pos = player.get("position", "MID")
    mins = player.get("minutes_factor", 1.0)
    league_avgs = LEAGUE_AVG_PER_90.get(pos, LEAGUE_AVG_PER_90["MID"])

    projections = []
    for sk in stat_keys:
        if sk not in SOCCER_STATS:
            continue
        # Use custom average if provided, else fall back to league avg
        player_avg = (custom_avgs or {}).get(sk, league_avgs.get(sk, 0.0))
        proj = tc_soccer_stat(
            stat_key=sk,
            player_avg=player_avg,
            position=pos,
            team_strength=team_strength,
            opponent_strength=opponent_strength,
            is_home=is_home,
            minutes_factor=mins,
        )
        proj["player"] = player.get("name", "Unknown")
        proj["team"] = player.get("team", "")
        proj["position"] = pos
        proj["is_starter"] = player.get("is_starter", False)
        projections.append(proj)
    return projections

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_soccer_pipeline(target_matchup: Optional[str] = None) -> dict:
    """Run the full soccer TC pipeline.

    1. Fetch World Cup events from Odds API
    2. For each event, fetch DK/BetMGM odds (h2h, totals, btts)
    3. Project game-level markets: H2H win prob, total goals (Poisson), BTTS
    4. Generate player stat projections using TC soccer formula
    5. Output picks to Daily_Log
    """
    now = datetime.now()
    today_dir = LOG_DIR / now.strftime("%Y-%m-%d")
    today_dir.mkdir(exist_ok=True)

    print(f"[{now:%H:%M:%S}] Soccer TC Engine — World Cup 2026")
    events = fetch_world_cup_events()
    print(f"  → {len(events)} World Cup events found")

    all_game_picks = []
    all_player_picks = []
    game_summaries = []

    for ev in events:
        home = ev.get("home_team", "")
        away = ev.get("away_team", "")
        if not home or not away:
            continue

        matchup = f"{away}@{home}"

        # Filter by target matchup if specified (tolerant of abbreviations)
        if target_matchup:
            tokens = [t.upper() for t in target_matchup.upper().replace("@", " ").replace(" VS ", " ").split() if len(t) >= 3]
            if tokens:
                matchup_teams = [away.upper(), home.upper()]
                if not all(any(tok in team or team in tok for team in matchup_teams) for tok in tokens):
                    continue

        print(f"\n  ⚽ {matchup}")

        # Fetch odds
        eid = ev.get("event_id") or ev.get("id", "")
        sport_key = ev.get("_sport_key", "soccer_fifa_world_cup")
        odds = fetch_soccer_odds(eid, sport_key)
        odds_available = not odds.get("error")
        if not odds_available:
            print(f"    ⚠️ Odds error: {odds.get('error', 'unknown')} (continuing with self-edge only)")
        # Team strengths
        home_str = get_team_strength(home)
        away_str = get_team_strength(away)

        # Game-level projections
        total_proj = project_game_total(home_str, away_str)
        btts_proj = project_btts(home_str, away_str)
        h2h_proj = project_h2h(home_str, away_str)
        team_stats_proj = project_team_match_stats(home_str, away_str)

        # Extract available DK/BetMGM lines
        dk_lines = odds.get("draftkings", {})
        betmgm_lines = odds.get("betmgm", {})

        dk_h2h = dk_lines.get("h2h", {})
        dk_btts = dk_lines.get("btts", {})
        bm_totals = betmgm_lines.get("totals", {})

        # Build game-level picks
        game_picks = {
            "date": now.strftime("%Y-%m-%d"),
            "matchup": matchup,
            "home_team": home,
            "away_team": away,
            "commence_time": odds.get("commence_time", ""),
            "h2h": {
                "home_win_prob": h2h_proj["home_win_prob"],
                "draw_prob": h2h_proj["draw_prob"],
                "away_win_prob": h2h_proj["away_win_prob"],
                "tc_signal": h2h_proj["signal"],
                "dk_home": dk_h2h.get(home, {}).get("price"),
                "dk_draw": dk_h2h.get("Draw", {}).get("price"),
                "dk_away": dk_h2h.get(away, {}).get("price"),
            },
            "totals": {
                "tc_expected": total_proj["total_expected_goals"],
                "tc_over_2_5_prob": total_proj["over_2_5_prob"],
                "tc_signal": total_proj["signal"],
                "betmgm_over_2_5": bm_totals.get("Over", {}).get("price"),
                "betmgm_under_2_5": bm_totals.get("Under", {}).get("price"),
                "betmgm_total_line": bm_totals.get("Over", {}).get("point", 2.5),
            },
            "btts": {
                "tc_probability": btts_proj["btts_probability"],
                "tc_signal": btts_proj["signal"],
                "dk_yes": dk_btts.get("Yes", {}).get("price"),
                "dk_no": dk_btts.get("No", {}).get("price"),
            },
        }
        all_game_picks.append(game_picks)

        # Print game summary
        print(f"    H2H: {h2h_proj['home_win_prob']:.0%} {home} win | {h2h_proj['draw_prob']:.0%} draw")
        print(f"    Total: {total_proj['total_expected_goals']:.2f} goals expected → {total_proj['signal']} 2.5")
        print(f"    BTTS: {btts_proj['btts_probability']:.0%} → {btts_proj['signal']}")
        print(f"    Corners: {home} {team_stats_proj['home_corners_proj']} | {away} {team_stats_proj['away_corners_proj']} (total {team_stats_proj['total_corners_proj']})")
        print(f"    SOT: {home} {team_stats_proj['home_sot_proj']} | {away} {team_stats_proj['away_sot_proj']} (total {team_stats_proj['total_sot_proj']})")
        print(f"    DK: h2h={len(dk_h2h)}mkts, btts={len(dk_btts)}mkts | BetMGM: totals={len(bm_totals)}mkts")

        # Player projections (both teams)
        for team_name, is_home, team_str, opp_str in [
            (home, True, home_str, away_str),
            (away, False, away_str, home_str),
        ]:
            squad = generate_default_squad(team_name)
            for player in squad:
                projs = project_player_stats(
                    player=player,
                    team_strength=team_str,
                    opponent_strength=opp_str,
                    is_home=is_home,
                )
                for p in projs:
                    if p.get("tc_projection", 0) < MIN_PROJECTION:
                        continue
                    p["date"] = now.strftime("%Y-%m-%d")
                    p["matchup"] = matchup
                    p["source"] = p.get("source", "SELF_EDGE" if not dk_h2h else "DK")
                    all_player_picks.append(p)

        # Summary
        starters = sum(1 for pp in all_player_picks if pp.get("is_starter") and pp.get("matchup") == matchup)
        game_summaries.append({
            "matchup": matchup,
            "home": home,
            "away": away,
            "h2h_signal": h2h_proj["signal"],
            "totals_signal": total_proj["signal"],
            "btts_signal": btts_proj["signal"],
            "has_dk_odds": bool(dk_h2h),
            "has_betmgm_totals": bool(bm_totals),
            "starter_projections": starters,
        })

    # Write outputs (OUTSIDE the per-event loop — was being overwritten once per event)
    if all_game_picks:
        # Game picks JSON
        (today_dir / "soccer_game_picks.json").write_text(json.dumps(all_game_picks, indent=2))

        # Game picks CSV
        csv_path = today_dir / "soccer_game_picks.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                "date", "matchup", "home_team", "away_team",
                "h2h_home_win_prob", "h2h_draw_prob", "h2h_away_win_prob", "h2h_tc_signal",
                "h2h_dk_home", "h2h_dk_draw", "h2h_dk_away",
                "totals_tc_expected", "totals_tc_over_prob", "totals_tc_signal",
                "totals_bm_over", "totals_bm_under", "totals_bm_line",
                "btts_tc_prob", "btts_tc_signal", "btts_dk_yes", "btts_dk_no",
            ])
            w.writeheader()
            for gp in all_game_picks:
                w.writerow({
                    "date": gp["date"],
                    "matchup": gp["matchup"],
                    "home_team": gp["home_team"],
                    "away_team": gp["away_team"],
                    "h2h_home_win_prob": gp["h2h"]["home_win_prob"],
                    "h2h_draw_prob": gp["h2h"]["draw_prob"],
                    "h2h_away_win_prob": gp["h2h"]["away_win_prob"],
                    "h2h_tc_signal": gp["h2h"]["tc_signal"],
                    "h2h_dk_home": gp["h2h"]["dk_home"],
                    "h2h_dk_draw": gp["h2h"]["dk_draw"],
                    "h2h_dk_away": gp["h2h"]["dk_away"],
                    "totals_tc_expected": gp["totals"]["tc_expected"],
                    "totals_tc_over_prob": gp["totals"]["tc_over_2_5_prob"],
                    "totals_tc_signal": gp["totals"]["tc_signal"],
                    "totals_bm_over": gp["totals"]["betmgm_over_2_5"],
                    "totals_bm_under": gp["totals"]["betmgm_under_2_5"],
                    "totals_bm_line": gp["totals"]["betmgm_total_line"],
                    "btts_tc_prob": gp["btts"]["tc_probability"],
                    "btts_tc_signal": gp["btts"]["tc_signal"],
                    "btts_dk_yes": gp["btts"]["dk_yes"],
                    "btts_dk_no": gp["btts"]["dk_no"],
                })

    if all_player_picks:
        # Player projections JSON/CSV
        (today_dir / "soccer_player_projs.json").write_text(json.dumps(all_player_picks, indent=2))

        pp_csv = today_dir / "soccer_player_picks.csv"
        with open(pp_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                "date", "matchup", "player", "team", "position", "is_starter",
                "stat", "stat_name", "tc_projection", "tc_line", "edge", "signal",
                "tc_raw", "tc_team_adj", "tc_opp_adj", "tc_home_adj", "source",
            ])
            w.writeheader()
            for pp in all_player_picks:
                w.writerow({
                    "date": pp.get("date", ""),
                    "matchup": pp.get("matchup", ""),
                    "player": pp.get("player", ""),
                    "team": pp.get("team", ""),
                    "position": pp.get("position", ""),
                    "is_starter": pp.get("is_starter", False),
                    "stat": pp.get("stat", ""),
                    "stat_name": pp.get("stat_name", ""),
                    "tc_projection": pp.get("tc_projection", ""),
                    "tc_line": pp.get("tc_line", ""),
                    "edge": pp.get("edge", ""),
                    "signal": pp.get("signal", ""),
                    "tc_raw": pp.get("tc_raw", ""),
                    "tc_team_adj": pp.get("tc_team_adj", ""),
                    "tc_opp_adj": pp.get("tc_opp_adj", ""),
                    "tc_home_adj": pp.get("tc_home_adj", ""),
                    "source": pp.get("source", "SELF_EDGE"),
                })

    # Last run summary
    last_run = {
        "timestamp": now.isoformat(),
        "events_total": len(events),
        "games_with_odds": len(all_game_picks),
        "game_picks": len(all_game_picks),
        "player_projections": len(all_player_picks),
        "summaries": game_summaries,
    }
    (LOG_DIR / "last_run_soccer.json").write_text(json.dumps(last_run, indent=2))

    print(f"\n{'='*50}")
    print(f"DONE: {len(all_game_picks)} games, {len(all_player_picks)} player projections")
    print(f"Output: {today_dir}/soccer_game_picks.csv + soccer_player_picks.csv")

    return last_run

def generate_report(today_dir: Optional[Path] = None) -> str:
    """Generate a markdown report of today's soccer picks."""
    if today_dir is None:
        today_dir = LOG_DIR / datetime.now().strftime("%Y-%m-%d")

    gp_file = today_dir / "soccer_game_picks.json"
    if not gp_file.exists():
        return "No soccer game picks found for today."

    game_picks = json.loads(gp_file.read_text())

    lines = []
    lines.append("# ⚽ Soccer TC Picks — World Cup 2026")
    lines.append(f"Generated: {datetime.now():%Y-%m-%d %I:%M %p ET}")
    lines.append("")

    for gp in game_picks[:10]:  # Show top 10
        lines.append(f"## {gp['away_team']} @ {gp['home_team']}")
        lines.append("")

        # H2H
        h2h = gp["h2h"]
        lines.append(f"**Moneyline**: {h2h['tc_signal']}")
        lines.append(f"- Home win: {h2h['home_win_prob']:.0%} (DK: {h2h.get('dk_home','—')})")
        lines.append(f"- Draw: {h2h['draw_prob']:.0%} (DK: {h2h.get('dk_draw','—')})")
        lines.append(f"- Away win: {h2h['away_win_prob']:.0%} (DK: {h2h.get('dk_away','—')})")
        lines.append("")

        # Totals
        t = gp["totals"]
        lines.append(f"**Total Goals**: {t['tc_signal']} 2.5")
        lines.append(f"- TC expects: {t['tc_expected']:.2f} goals ({t['tc_over_2_5_prob']:.0%} over)")
        lines.append(f"- BetMGM: Over {t.get('betmgm_over_2_5','—')} / Under {t.get('betmgm_under_2_5','—')} @ {t.get('betmgm_total_line',2.5)}")
        lines.append("")

        # BTTS
        b = gp["btts"]
        lines.append(f"**Both Teams to Score**: {b['tc_signal']}")
        lines.append(f"- TC probability: {b['tc_probability']:.0%}")
        lines.append(f"- DK: Yes {b.get('dk_yes','—')} / No {b.get('dk_no','—')}")
        lines.append("")

    # Player stat projections summary
    pp_file = today_dir / "soccer_player_picks.csv"
    if pp_file.exists():
        lines.append("---")
        lines.append("## Player Stat Projections (Top OVER signals)")
        lines.append("")
        lines.append("| Player | Team | Pos | Stat | TC Proj | TC Line | Edge | Signal |")
        lines.append("|---|---|---|---|---|---|---|---|")

        # Read and sort by edge
        player_picks = []
        with open(pp_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                player_picks.append(row)

        # OVER signals (edge > 0)
        over_picks = [p for p in player_picks if p.get("signal") == "OVER"]
        over_picks.sort(key=lambda x: float(x.get("edge", 0)), reverse=True)

        for p in over_picks[:15]:
            lines.append(
                f"| {p['player']} | {p['team']} | {p['position']} | "
                f"{p['stat_name']} | {p['tc_projection']} | {p['tc_line']} | "
                f"{p['edge']} | {p['signal']} |"
            )

        lines.append("")
        lines.append("## Player Stat Projections (Top UNDER signals)")
        lines.append("")
        lines.append("| Player | Team | Pos | Stat | TC Proj | TC Line | Edge | Signal |")
        lines.append("|---|---|---|---|---|---|---|---|")

        under_picks = [p for p in player_picks if p.get("signal") == "UNDER"]
        under_picks.sort(key=lambda x: float(x.get("edge", 0)))

        for p in under_picks[:15]:
            lines.append(
                f"| {p['player']} | {p['team']} | {p['position']} | "
                f"{p['stat_name']} | {p['tc_projection']} | {p['tc_line']} | "
                f"{p['edge']} | {p['signal']} |"
            )

    report_md = "\n".join(lines)
    report_path = today_dir / "soccer_tc_report.md"
    report_path.write_text(report_md)
    print(f"Report saved: {report_path}")
    return report_md

# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Soccer TC Engine — Triple Conservative for Soccer")
    p.add_argument("--game", default="", help="Filter by matchup, e.g. BRA@MAR")
    p.add_argument("--report", action="store_true", help="Generate markdown report after run")
    args = p.parse_args()

    result = run_soccer_pipeline(target_matchup=args.game or None)

    if args.report:
        report = generate_report()
        print(report)


# ═══════════════════════════════════════════════════════════════════════════════
# Public helpers (used by daily_picks.py + other modules)
# ═══════════════════════════════════════════════════════════════════════════════

def project_matchup(away: str, home: str) -> dict:
    """Project a single World Cup matchup — returns a dict with valid_props / picks.

    Returns a dict shaped for the daily_picks.py consumer. On any failure, returns
    a dict containing the "error" key so the caller can log and skip.
    """
    try:
        result = run_soccer_pipeline(target_matchup=f"{away}@{home}")
        games = result.get("summaries") or []
        if not games:
            return {"error": f"No data for WORLD CUP {away}@{home}"}
        g = games[0]
        return {
            "matchup": g.get("matchup", f"{away}@{home}"),
            "away_team": g.get("away", away),
            "home_team": g.get("home", home),
            "h2h_signal": g.get("h2h_signal"),
            "totals_signal": g.get("totals_signal"),
            "btts_signal": g.get("btts_signal"),
            "team_stats": g.get("team_stats"),
            "starter_projections": g.get("starter_projections", 0),
        }
    except Exception as e:
        return {"error": f"project_matchup({away}@{home}): {e}"}


def get_worldcup_slate() -> dict:
    """Return the current World Cup slate (games list) — minimal shape for daily_picks."""
    try:
        events = fetch_world_cup_events()
    except Exception as e:
        return {"games": [], "error": str(e)}
    games = []
    for ev in events:
        away = ev.get("away_team", "")
        home = ev.get("home_team", "")
        if not away or not home:
            continue
        games.append({
            "away": {"team": away},
            "home": {"team": home},
            "event_id": ev.get("event_id") or ev.get("id", ""),
            "commence_time": ev.get("start_time") or ev.get("commence_time", ""),
        })
    return {"games": games, "events_total": len(events)}