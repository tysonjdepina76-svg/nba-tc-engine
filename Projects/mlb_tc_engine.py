"""MLB TC Projection Engine — fetches MLB rosters, season stats, and generates TC projections.

Integrates with the /api/tc API route and daily_picks.py pipeline.
"""
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ET = __import__('datetime').timezone(__import__('datetime').timedelta(hours=-5))

# ── ESPN endpoints ───────────────────────────────────────
ESPN_MLB_TEAMS = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams"
ESPN_MLB_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
ESPN_MLB_TEAM_ROSTER = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/{code}/roster"
ESPN_MLB_SEASON_STATS = "https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/seasons/{year}/types/2/athletes/{id}/statistics"

# ── ESPN World Cup endpoints ────────────────────────────
ESPN_WC_TEAMS = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams"
ESPN_WC_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
ESPN_WC_TEAM_ROSTER = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/{code}/roster"

# ── TC Constants for MLB ─────────────────────────────────
MLB_BAYES_ALPHA: Dict[str, float] = {
    "hits": 15.0, "hr": 10.0, "rbi": 15.0, "runs": 15.0, "sb": 8.0, "avg": 100.0,
    "so": 15.0, "era": 20.0,
}
MLB_PRIOR: Dict[str, float] = {
    "hits": 0.95, "hr": 0.12, "rbi": 0.45, "runs": 0.45, "sb": 0.10, "avg": 0.250,
    "so": 1.0, "era": 4.20,
}
MLB_STAT_CONS: Dict[str, float] = {
    "hits": 0.82, "hr": 0.75, "rbi": 0.82, "runs": 0.82, "sb": 0.70, "avg": 0.88,
    "so": 0.82, "era": 0.78,
}
MLB_LINE_FACTOR = 0.85
MLB_EDGE_THRESHOLDS: Dict[str, float] = {
    "H": 0.5, "HR": 0.2, "RBI": 0.5, "R": 0.5, "SB": 0.2, "AVG": 0.030,
    "K": 1.0, "ERA": 0.75,
}
MLB_Q_MULT = 0.45  # questionable player multiplier

# ── Team code map (ESPN abbreviation → our code) ─────────
MLB_CODE_MAP: Dict[str, str] = {
    "ARI": "ARI", "ATL": "ATL", "BAL": "BAL", "BOS": "BOS",
    "CHC": "CHC", "CHW": "CHW", "CIN": "CIN", "CLE": "CLE",
    "COL": "COL", "DET": "DET", "HOU": "HOU", "KC": "KC",
    "LAA": "LAA", "LAD": "LAD", "MIA": "MIA", "MIL": "MIL",
    "MIN": "MIN", "NYM": "NYM", "NYY": "NYY", "OAK": "OAK",
    "PHI": "PHI", "PIT": "PIT", "SD": "SD", "SF": "SF",
    "SEA": "SEA", "STL": "STL", "TB": "TB", "TEX": "TEX",
    "TOR": "TOR", "WSH": "WSH", "ATH": "ATH",
}

WC_CODE_MAP: Dict[str, str] = {}

HEADERS = {"User-Agent": "Mozilla/5.0 TC", "Accept": "application/json"}


def load_wc_teams() -> Dict[str, str]:
    """Load World Cup team code map from ESPN."""
    global WC_CODE_MAP
    if WC_CODE_MAP:
        return WC_CODE_MAP
    try:
        r = requests.get(ESPN_WC_TEAMS, headers=HEADERS, timeout=15)
        if r.ok:
            data = r.json()
            sports = data.get("sports", [{}])[0]
            leagues = sports.get("leagues", [{}])[0]
            for t in leagues.get("teams", []):
                tm = t.get("team", {})
                code = tm.get("abbreviation", "").upper()
                if code:
                    WC_CODE_MAP[code] = code
    except Exception:
        pass
    return WC_CODE_MAP


def round_n(n, d=1):
    return round(float(n or 0), d)


def status_factor(status: str) -> float:
    s = str(status or "ACTIVE").upper()
    if "OUT" in s or "DNP" in s or "INJURED" in s:
        return 0
    if "QUESTION" in s or "DOUBTFUL" in s or "Q" == s or "GTD" in s or "DAY" in s:
        return MLB_Q_MULT
    return 1.0


def bayes_shrink(stat: str, raw: float, n: int = 5) -> float:
    alpha = MLB_BAYES_ALPHA.get(stat, 10.0)
    prior = MLB_PRIOR.get(stat, 0.5)
    return ((raw or 0) * n + prior * alpha) / (n + alpha)


def tc_for(stat: str, raw: float, status: str = "ACTIVE") -> float:
    shrunk = bayes_shrink(stat, raw)
    cons = MLB_STAT_CONS.get(stat, 0.80)
    return round_n(shrunk * cons * status_factor(status), 3 if stat == "avg" else 1)


def line_from_tc(tc_val: float, stat: str = "hits") -> float:
    if stat == "avg":
        return round_n(tc_val * MLB_LINE_FACTOR, 3)
    return max(0.5, round_n(tc_val * MLB_LINE_FACTOR, 1))


def edge_from(tc_val: float, line_val: float) -> float:
    return round_n(tc_val - (line_val or 0), 1)


def fetch_mlb_roster(team_code: str) -> List[dict]:
    """Fetch full MLB roster from ESPN for a team."""
    code = team_code.lower()
    players = []
    try:
        r = requests.get(ESPN_MLB_TEAM_ROSTER.format(code=code), headers=HEADERS, timeout=15)
        if not r.ok:
            return players
        data = r.json()
        for group in data.get("athletes", []):
            pos_group = group.get("position", "")
            for item in group.get("items", []):
                ath = item
                players.append({
                    "id": str(ath.get("id", "")),
                    "name": f"{ath.get('firstName', '')} {ath.get('lastName', '')}".strip(),
                    "pos": ath.get("position", {}).get("abbreviation", pos_group),
                    "pos_group": pos_group,
                    "jersey": ath.get("jersey", ""),
                    "ht": ath.get("displayHeight", ""),
                    "wt": ath.get("displayWeight", ""),
                    "bats": ath.get("bats", ""),
                    "throws": ath.get("throws", ""),
                    "status": "ACTIVE",
                })
    except Exception as e:
        print(f"[MLB roster {team_code}] error: {e}")
    return players


def fetch_mlb_season_stats(athlete_id: str, year: int = 2026) -> dict:
    """Fetch current-season MLB stats for an athlete."""
    try:
        url = ESPN_MLB_SEASON_STATS.format(year=year, id=athlete_id)
        r = requests.get(url, headers=HEADERS, timeout=10)
        if not r.ok:
            return {}
        data = r.json()
        splits = data.get("splits", {})
        batting = {}
        pitching = {}
        for cat in splits.get("categories", []):
            cname = cat.get("name", "")
            stats = {s["name"]: s.get("value", 0) for s in cat.get("stats", [])}
            if cname == "batting":
                batting = stats
            elif cname == "pitching":
                pitching = stats
        # Compute per-game averages
        gp = float(batting.get("gamesPlayed", pitching.get("gamesPlayed", 1))) or 1
        gs = float(batting.get("gamesStarted", pitching.get("gamesStarted", gp))) or gp
        is_pitcher = bool(pitching and pitching.get("inningsPitched", 0))
        result = {
            "games_played": int(gp),
            "games_started": int(gs),
            "is_pitcher": is_pitcher,
        }
        if is_pitcher:
            ip = float(pitching.get("inningsPitched", 0)) or 1
            result.update({
                "era": round_n(float(pitching.get("ERA", pitching.get("earnedRunAverage", 4.5))), 2),
                "strikeouts": float(pitching.get("strikeOuts", pitching.get("strikeouts", 0))),
                "wins": float(pitching.get("wins", 0)),
                "whip": round_n(float(pitching.get("WHIP", pitching.get("walksAndHitsPerInning", 1.35))), 2),
                "k_per_game": round_n(float(pitching.get("strikeOuts", 0)) / gp, 1) if gp else 0,
                "ip_per_game": round_n(ip / gp, 1) if gp else 0,
            })
        else:
            result.update({
                "avg": round_n(float(batting.get("avg", 0.250)), 3),
                "hits": float(batting.get("hits", 0)),
                "home_runs": float(batting.get("homeRuns", 0)),
                "rbi": float(batting.get("RBIs", 0)),
                "runs": float(batting.get("runs", 0)),
                "stolen_bases": float(batting.get("stolenBases", 0)),
                "ops": round_n(float(batting.get("OPS", batting.get("onBasePlusSlugging", 0.700))), 3),
                "h_per_game": round_n(float(batting.get("hits", 0)) / gp, 2) if gp else 0,
                "hr_per_game": round_n(float(batting.get("homeRuns", 0)) / gp, 2) if gp else 0,
                "rbi_per_game": round_n(float(batting.get("RBIs", 0)) / gp, 2) if gp else 0,
                "r_per_game": round_n(float(batting.get("runs", 0)) / gp, 2) if gp else 0,
                "sb_per_game": round_n(float(batting.get("stolenBases", 0)) / gp, 2) if gp else 0,
            })
        return result
    except Exception as e:
        return {"error": str(e)}


def annotate_mlb_player(player: dict) -> dict:
    """Add TC projections to an MLB player dict."""
    p = dict(player)
    stats = p.get("season_stats", {})
    is_p = stats.get("is_pitcher", False)

    if is_p:
        raw_k = stats.get("k_per_game", 0)
        p["raw_k"] = round_n(raw_k, 1)
        p["tc_k"] = tc_for("so", raw_k, p.get("status", "ACTIVE"))
        p["line_k"] = line_from_tc(p["tc_k"], "so")
        p["edge_k"] = edge_from(p["tc_k"], p["line_k"])
        p["raw_era"] = stats.get("era", 4.50)
        p["tc_era"] = tc_for("era", p["raw_era"], p.get("status", "ACTIVE"))
    else:
        p["raw_h"] = round_n(stats.get("h_per_game", 0), 2)
        p["raw_hr"] = round_n(stats.get("hr_per_game", 0), 2)
        p["raw_rbi"] = round_n(stats.get("rbi_per_game", 0), 2)
        p["raw_r"] = round_n(stats.get("r_per_game", 0), 2)
        p["raw_sb"] = round_n(stats.get("sb_per_game", 0), 2)
        p["raw_avg"] = stats.get("avg", 0.250)
        p["tc_h"] = tc_for("hits", p["raw_h"], p.get("status", "ACTIVE"))
        p["line_h"] = line_from_tc(p["tc_h"], "hits")
        p["edge_h"] = edge_from(p["tc_h"], p["line_h"])
        p["tc_hr"] = tc_for("hr", p["raw_hr"], p.get("status", "ACTIVE"))
        p["line_hr"] = line_from_tc(p["tc_hr"], "hr")
        p["edge_hr"] = edge_from(p["tc_hr"], p["line_hr"])
        p["tc_rbi"] = tc_for("rbi", p["raw_rbi"], p.get("status", "ACTIVE"))
        p["line_rbi"] = line_from_tc(p["tc_rbi"], "rbi")
        p["edge_rbi"] = edge_from(p["tc_rbi"], p["line_rbi"])
        p["tc_r"] = tc_for("runs", p["raw_r"], p.get("status", "ACTIVE"))
        p["line_r"] = line_from_tc(p["tc_r"], "runs")
        p["edge_r"] = edge_from(p["tc_r"], p["line_r"])
        p["tc_sb"] = tc_for("sb", p["raw_sb"], p.get("status", "ACTIVE"))
        p["line_sb"] = line_from_tc(p["tc_sb"], "sb")
        p["edge_sb"] = edge_from(p["tc_sb"], p["line_sb"])
        p["tc_avg"] = tc_for("avg", p["raw_avg"], p.get("status", "ACTIVE"))
    return p


def build_mlb_projection(sport: str, away_code: str, home_code: str) -> dict:
    """Build a full MLB TC projection for a matchup."""
    away = away_code.upper()
    home = home_code.upper()
    now = datetime.now(ET).isoformat()

    # Fetch rosters
    away_roster = fetch_mlb_roster(away)
    home_roster = fetch_mlb_roster(home)

    # Fetch season stats for all players
    for p in away_roster + home_roster:
        pid = p.get("id")
        if pid:
            stats = fetch_mlb_season_stats(pid)
            p["season_stats"] = stats
            if stats.get("is_pitcher"):
                p["role"] = "PITCHER"
            else:
                p["role"] = "BATTER"

    # Annotate with TC projections
    away_annotated = [annotate_mlb_player(p) for p in away_roster]
    home_annotated = [annotate_mlb_player(p) for p in home_roster]

    # Sort by playing time / production
    def score(p):
        if p.get("season_stats", {}).get("is_pitcher"):
            return p.get("season_stats", {}).get("games_started", 0)
        return p.get("season_stats", {}).get("games_started", 0) * 2 + p.get("season_stats", {}).get("hits", 0)

    away_sorted = sorted(away_annotated, key=score, reverse=True)
    home_sorted = sorted(home_annotated, key=score, reverse=True)

    # Determine projected starters (top 8 position players + starting pitcher for each team)
    away_players_all = away_sorted
    home_players_all = home_sorted

    # Identify starting pitchers (most games started)
    away_sp = [p for p in away_sorted if p.get("season_stats", {}).get("is_pitcher")]
    home_sp = [p for p in home_sorted if p.get("season_stats", {}).get("is_pitcher")]

    # For projection display, highlight top batters and starting pitchers
    def leader_symbols(players, stat_keys):
        active = [p for p in players if status_factor(p.get("status", "ACTIVE")) > 0]
        for p in players:
            p["symbols"] = []
        symbols = [("H", "★H"), ("HR", "◆HR"), ("RBI", "▲RBI"), ("R", "●R"), ("SB", "◇SB")]
        for rk, sym in symbols:
            key = f"raw_{rk.lower().replace('★','').replace('◆','').replace('▲','').replace('●','').replace('◇','')}"
            raw_key = {"H": "raw_h", "HR": "raw_hr", "RBI": "raw_rbi", "R": "raw_r", "SB": "raw_sb"}[rk]
            vals = [float(p.get(raw_key, 0) or 0) for p in active]
            if not vals:
                continue
            mv = max(vals)
            if mv <= 0:
                continue
            for p in active:
                if float(p.get(raw_key, 0) or 0) == mv:
                    p["symbols"].append(sym)
        return players

    away_players_all = leader_symbols(away_players_all, ["H", "HR", "RBI", "R", "SB"])
    home_players_all = leader_symbols(home_players_all, ["H", "HR", "RBI", "R", "SB"])

    # Summarize
    def summarize_team(players, team_code):
        batters = [p for p in players if not p.get("season_stats", {}).get("is_pitcher")]
        pitchers = [p for p in players if p.get("season_stats", {}).get("is_pitcher")]
        active_b = [p for p in batters if status_factor(p.get("status", "ACTIVE")) > 0]
        tc_h = round_n(sum(p.get("tc_h", 0) for p in active_b), 1)
        tc_hr = round_n(sum(p.get("tc_hr", 0) for p in active_b), 1)
        tc_rbi = round_n(sum(p.get("tc_rbi", 0) for p in active_b), 1)
        tc_r = round_n(sum(p.get("tc_r", 0) for p in active_b), 1)
        return {
            "team": team_code,
            "all": {"players": players},
            "starters": {"players": players[:9]},  # top 9 by playing time
            "bench": {"players": players[9:]},
            "totals": {
                "tc_hits": tc_h, "tc_hr": tc_hr, "tc_rbi": tc_rbi, "tc_runs": tc_r,
                "active_batters": len(active_b),
                "active_pitchers": len([p for p in pitchers if status_factor(p.get("status", "ACTIVE")) > 0]),
            },
            "injuries": [],
            "injury_summary": {"total": 0, "out": 0, "questionable": 0, "source": "ESPN MLB roster"},
        }

    away_summary = summarize_team(away_sorted, away)
    home_summary = summarize_team(home_sorted, home)

    # Generate prop rows
    prop_rows = []
    for team_side, players in [(away, away_sorted), (home, home_sorted)]:
        for p in players:
            if p.get("season_stats", {}).get("is_pitcher"):
                for stat, raw_key, tc_key, line_key, edge_key, label in [
                    ("K", "raw_k", "tc_k", "line_k", "edge_k", "Strikeouts"),
                ]:
                    edge = p.get(edge_key, 0)
                    th = MLB_EDGE_THRESHOLDS.get(stat, 1.0)
                    direction = "OVER" if edge >= th else ("UNDER" if edge <= -th else "NO BET")
                    prop_rows.append({
                        "date": datetime.now(ET).strftime("%Y-%m-%d"),
                        "league": "MLB",
                        "game": f"{away}@{home}",
                        "team": team_side,
                        "player": p["name"],
                        "role": "SP" if p.get("season_stats", {}).get("games_started", 0) >= 3 else "PITCHER",
                        "stat": stat,
                        "direction": direction,
                        "market_line": None,
                        "tc_projection": p.get(tc_key),
                        "tc_target": p.get(line_key),
                        "edge": edge,
                        "actual": None,
                        "result": "PENDING",
                        "source": "mlb_tc_engine",
                        "raw_average": p.get(raw_key),
                        "status": p.get("status", "ACTIVE"),
                        "valid": edge > 0,
                        "threshold": th,
                    })
            else:
                for stat, raw_key, tc_key, line_key, edge_key, label in [
                    ("H", "raw_h", "tc_h", "line_h", "edge_h", "Hits"),
                    ("HR", "raw_hr", "tc_hr", "line_hr", "edge_hr", "Home Runs"),
                    ("RBI", "raw_rbi", "tc_rbi", "line_rbi", "edge_rbi", "RBI"),
                    ("R", "raw_r", "tc_r", "line_r", "edge_r", "Runs"),
                    ("SB", "raw_sb", "tc_sb", "line_sb", "edge_sb", "Stolen Bases"),
                ]:
                    edge = p.get(edge_key, 0)
                    th = MLB_EDGE_THRESHOLDS.get(stat, 0.5)
                    direction = "OVER" if edge >= th else ("UNDER" if edge <= -th else "NO BET")
                    prop_rows.append({
                        "date": datetime.now(ET).strftime("%Y-%m-%d"),
                        "league": "MLB",
                        "game": f"{away}@{home}",
                        "team": team_side,
                        "player": p["name"],
                        "role": "START" if p.get("season_stats", {}).get("games_started", 0) >= (p.get("season_stats", {}).get("games_played", 1) * 0.7) else "BENCH",
                        "stat": stat,
                        "direction": direction,
                        "market_line": None,
                        "tc_projection": p.get(tc_key),
                        "tc_target": p.get(line_key),
                        "edge": edge,
                        "actual": None,
                        "result": "PENDING",
                        "source": "mlb_tc_engine",
                        "raw_average": p.get(raw_key),
                        "status": p.get("status", "ACTIVE"),
                        "valid": edge > 0,
                        "threshold": th,
                    })

    valid_props = [r for r in prop_rows if r.get("valid")]

    return {
        "mode": "live",
        "sport": sport,
        "matchup": f"{away}@{home}",
        "away_team": away,
        "home_team": home,
        "source": f"ESPN MLB roster + {datetime.now().year} season stats",
        "timestamp": now,
        "tc_combined": None,
        "tc_line": None,
        "market_total": None,
        "edge": None,
        "signal": "MLB PROJECTION",
        "odds": {},
        "assessment": {
            "summary": f"MLB {away}@{home} — {len(away_roster)}+{len(home_roster)} players projected.",
            "roster_rule": "MLB uses ESPN roster + 2026 season stats for per-game projections",
        },
        "roster_counts": {
            "away": len(away_roster),
            "home": len(home_roster),
            "away_active": len([p for p in away_sorted if status_factor(p.get("status", "ACTIVE")) > 0]),
            "home_active": len([p for p in home_sorted if status_factor(p.get("status", "ACTIVE")) > 0]),
        },
        "away": away_summary,
        "home": home_summary,
        "valid_props": valid_props,
        "prop_rows": prop_rows,
        "pick_filters": MLB_EDGE_THRESHOLDS,
        "stat_categories": list(MLB_EDGE_THRESHOLDS.keys()),
        "note": "MLB TC projections. DK player props not available via The Odds API — lines are TC-derived targets.",
    }


# ── World Cup / Soccer ──────────────────────────────────
def fetch_wc_roster(team_code: str) -> List[dict]:
    """Fetch World Cup team roster from ESPN."""
    code = team_code.lower()
    players = []
    try:
        r = requests.get(ESPN_WC_TEAM_ROSTER.format(code=code), headers=HEADERS, timeout=15)
        if not r.ok:
            return players
        data = r.json()
        for group in data.get("athletes", []):
            pos_group = group.get("position", "")
            for item in group.get("items", []):
                ath = item
                players.append({
                    "id": str(ath.get("id", "")),
                    "name": ath.get("displayName", f"{ath.get('firstName', '')} {ath.get('lastName', '')}").strip(),
                    "pos": ath.get("position", {}).get("abbreviation", pos_group),
                    "pos_group": pos_group,
                    "jersey": ath.get("jersey", ""),
                    "ht": ath.get("displayHeight", ""),
                    "wt": ath.get("displayWeight", ""),
                    "nationality": ath.get("nationality", ""),
                    "status": "ACTIVE",
                })
    except Exception as e:
        print(f"[WC roster {team_code}] error: {e}")
    return players


def build_wc_projection(sport: str, away_code: str, home_code: str) -> dict:
    """Build World Cup projection with rosters."""
    away = away_code.upper()
    home = home_code.upper()
    now = datetime.now(ET).isoformat()

    away_roster = fetch_wc_roster(away)
    home_roster = fetch_wc_roster(home)

    def annotate(p):
        p["symbols"] = []
        return p

    away_players = [annotate(p) for p in away_roster]
    home_players = [annotate(p) for p in home_roster]

    return {
        "mode": "live",
        "sport": sport,
        "matchup": f"{away}@{home}",
        "away_team": away,
        "home_team": home,
        "source": "ESPN World Cup roster",
        "timestamp": now,
        "tc_combined": None,
        "tc_line": None,
        "market_total": None,
        "edge": None,
        "signal": "SOCCER ROSTERS",
        "odds": {},
        "assessment": {
            "summary": f"World Cup {away}@{home} — {len(away_roster)}+{len(home_roster)} players.",
            "roster_rule": "World Cup uses ESPN team rosters. DK player props not available for soccer.",
        },
        "roster_counts": {
            "away": len(away_roster),
            "home": len(home_roster),
            "away_active": len(away_players),
            "home_active": len(home_players),
        },
        "away": {"all": {"players": away_players}, "starters": {"players": away_players[:11]}, "bench": {"players": away_players[11:]}, "totals": {}, "injuries": []},
        "home": {"all": {"players": home_players}, "starters": {"players": home_players[:11]}, "bench": {"players": home_players[11:]}, "totals": {}, "injuries": []},
        "valid_props": [],
        "note": "World Cup soccer projection. DK player props and game lines not available. Rosters only.",
    }


# ── CLI test ────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sport = sys.argv[1] if len(sys.argv) > 1 else "MLB"
    away = sys.argv[2] if len(sys.argv) > 2 else "MIA"
    home = sys.argv[3] if len(sys.argv) > 3 else "PHI"

    if sport.upper() == "MLB":
        result = build_mlb_projection("MLB", away, home)
    else:
        result = build_wc_projection("WORLD_CUP", away, home)

    # Only output the JSON — no extra prints (API route parses this)
    print(json.dumps(result, indent=2, default=str))
