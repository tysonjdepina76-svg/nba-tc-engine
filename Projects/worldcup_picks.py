#!/usr/bin/env python3

# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""
World Cup 2026 Daily Pick Scraper — completely standalone, zero impact on basketball pipeline.

Pulls:
  - Match schedule + live scores from ESPN (free)
  - DK player props (goals, assists, shots_on_target, shots) from The Odds API (free tier)

Writes:
  - Daily_Log/worldcup/YYYY-MM-DD/matches.json   — raw match data
  - Daily_Log/worldcup/YYYY-MM-DD/props.json     — player props by match
  - Daily_Log/worldcup/YYYY-MM-DD/picks.csv      — flat prop table
  - Daily_Log/worldcup/last_run.json             — summary

Usage:
  python3 /home/workspace/Projects/worldcup_picks.py
  python3 /home/workspace/Projects/worldcup_picks.py --date 2026-06-14
"""

import os, sys, json, csv, argparse, requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- Secrets ---
WORKSPACE = Path("/home/workspace")
try:
    _sec = Path("/root/.zo/secrets.env")
    if _sec.exists():
        for _line in _sec.read_text().splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except Exception:
    pass

SPORT_KEY = "soccer_fifa_world_cup"
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
ODDS_BASE = "https://api.theoddsapi.com"

LOG_DIR = WORKSPACE / "Daily_Log" / "worldcup"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Odds API Disk Cache ────────────────────────────────
import time as _time
CACHE_DIR = WORKSPACE / "Daily_Log" / "cache" / "odds"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _wc_cache_get(matchup_key, game_id):
    p = CACHE_DIR / f"wc_{matchup_key}.json"
    if p.exists():
        try:
            data = json.loads(p.read_text())
            age = _time.time() - p.stat().st_mtime
            if age < 86400:
                data["_from_cache"] = True
                return data
        except Exception:
            pass
    return None

def _wc_cache_set(matchup_key, game_id, data):
    p = CACHE_DIR / f"wc_{matchup_key}.json"
    clean = {k: v for k, v in data.items() if not k.startswith("_")}
    p.write_text(json.dumps(clean, indent=2, default=str))

# DK player prop markets available for World Cup on the free tier
PROP_MARKETS = [
    "player_goals",
    "player_assists",
    "player_shots_on_target",
    "player_shots",
    "player_tackles",
    "player_fouls",
]
# Books to try in priority order
BOOK_PRIORITY = ["fanduel", "draftkings", "betmgm", "caesars", "fanatics"]

def fetch_espn_matches(date_str=None):
    """Fetch World Cup matches from ESPN — uses unfiltered scoreboard (live + upcoming) to catch in-progress games."""
    """Fetch World Cup matches from ESPN — queries BOTH unfiltered scoreboard (catches in-progress/live games) AND date-filtered schedule."""
    matches = []
    seen = set()
    urls = [ESPN_SCOREBOARD]  # unfiltered: catches live + in-progress + recent
    if date_str:
        urls.append(f"{ESPN_SCOREBOARD}?dates={date_str}")
    for u in urls:
        try:
            r = requests.get(u, timeout=15, headers={"Accept": "application/json",
            "x-api-key": ODDS_API_KEY})
            r.raise_for_status()
            data = r.json()
            for e in data.get("events", []):
                eid = e.get("id", "")
                if eid in seen:
                    continue
                seen.add(eid)
                status = e.get("status", {}).get("type", {})
                comps = e.get("competitions", [])
                teams = []
                for c in comps:
                    for co in c.get("competitors", []):
                        team = co.get("team", {})
                        teams.append({
                            "name": team.get("displayName", ""),
                            "abbrev": team.get("abbreviation", ""),
                            "score": co.get("score", "0"),
                            "homeAway": co.get("homeAway", ""),
                        })
                matches.append({
                    "espn_id": eid,
                    "name": e.get("name", ""),
                    "short_name": e.get("shortName", ""),
                    "date": e.get("date", ""),
                    "status": status.get("description", ""),
                    "status_detail": status.get("shortDetail", ""),
                    "completed": status.get("completed", False),
                    "period": status.get("period", 0),
                    "teams": teams,
                })
        except Exception as exc:
            print(f"ESPN {u} error: {exc}")
    return matches

def norm_team_name(name):
    """Normalize team names for cross-matching ESPN ↔ Odds API."""

    if not name:
        return ""
    n = name.lower().strip()
    repl = {"&": "and", "bosnia & herzegovina": "bosnia and herzegovina"}
    for k, v in repl.items():
        n = n.replace(k, v)
    return n

def fetch_odds_games():
    # Tier 0: disk cache
    cached = _wc_cache_get("all", "slate")
    if cached:
        return cached.get("events", cached)
    """Get all active World Cup games from Odds API with their IDs."""
    if not ODDS_API_KEY:
        return []
    try:
        url = f"{ODDS_BASE}/odds/?sport_key={SPORT_KEY}"
        params = {
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american",
            "commenceTimeFrom": (datetime.now(timezone.utc) - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "commenceTimeTo": (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        r.raise_for_status()
        events = data if isinstance(data, list) else data.get("events", [])
        _wc_cache_set("all", "slate", {"events": events})
        return events
    except Exception as exc:
        print(f"Odds API error: {exc}")
        return []

def fetch_player_props(game_id, away_team="", home_team=""):
    """Fetch player props for a specific game from Odds API. Cached per matchup."""
    # Tier 0: disk cache
    if away_team and home_team:
        mk = f"{away_team}_{home_team}".replace(" ", "_")
        cached = _wc_cache_get(mk, game_id)
        if cached:
            return cached
    # Tier 1: live Odds API
    if not ODDS_API_KEY:
        return {"bookmakers": [], "source": "no-key"}
    try:
        url = f"{ODDS_BASE}/odds/?sport_key={SPORT_KEY}&eventId={game_id}"
        params = {
            "regions": "us",
            "markets": ",".join(PROP_MARKETS),
            "oddsFormat": "american",
        }
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            data = data.get("events", data)
        # cache the result
        if away_team and home_team:
            mk = f"{away_team}_{home_team}".replace(" ", "_")
            _wc_cache_set(mk, game_id, data)
        data["source"] = "odds-api"
        return data
    except Exception as exc:
        print(f"Props fetch error for {game_id}: {exc}")
        return {"bookmakers": [], "source": "error"}

def match_espn_to_odds(espn_match, odds_games):
    """Cross-reference ESPN match to Odds API game by team names."""
    espn_teams = [t["name"] for t in espn_match.get("teams", [])]
    if len(espn_teams) < 2:
        return None
    n_away, n_home = norm_team_name(espn_teams[0]), norm_team_name(espn_teams[1])
    for g in odds_games:
        o_away = norm_team_name(g.get("away_team", ""))
        o_home = norm_team_name(g.get("home_team", ""))
        if n_away == o_away and n_home == o_home:
            return g
        if (n_away in o_away or o_away in n_away) and (n_home in o_home or o_home in n_home):
            return g
    # Try reverse (ESPN might list home first)
    for g in odds_games:
        o_away = norm_team_name(g.get("away_team", ""))
        o_home = norm_team_name(g.get("home_team", ""))
        if n_home == o_away and n_away == o_home:
            return g
    return None

def extract_props(prop_data, preferred_book="draftkings"):
    """Extract player props from Odds API response for a specific book.
    Returns { player_name: { stat: { line, over_price } } }
    """
    props = {}
    stat_map = {
        "player_goals": "goals",
        "player_assists": "assists",
        "player_shots_on_target": "shots_on_target",
        "player_shots": "shots",
        "player_tackles": "tackles",
        "player_fouls": "fouls",
    }
    for bk in prop_data.get("bookmakers", []):
        if bk.get("key") != preferred_book:
            continue
        for m in bk.get("markets", []):
            stat = stat_map.get(m.get("key", ""))
            if not stat:
                continue
            for o in m.get("outcomes", []):
                name = o.get("description", o.get("name", ""))
                if o.get("name") == "Over":
                    props.setdefault(name, {})[stat] = {
                        "line": o.get("point"),
                        "over_price": o.get("price"),
                    }
    return props

def build_csv_rows(matches_with_props):
    """Flatten matches + props into rows for CSV."""
    rows = []
    for m in matches_with_props:
        matchup_short = m.get("short_name", m.get("name", "?"))
        status = m.get("status", "?")
        teams_list = m.get("teams", [])
        home = teams_list[1]["name"] if len(teams_list) > 1 else "?"
        away = teams_list[0]["name"] if len(teams_list) > 0 else "?"
        book = m.get("book", "none")
        props = m.get("player_props", {})
        if not props:
            rows.append({
                "matchup": matchup_short,
                "status": status,
                "home": home,
                "away": away,
                "book": book,
                "player": "",
                "stat": "",
                "line": "",
                "over_price": "",
                "fetched_at": m.get("fetched_at", ""),
            })
        for player_name, stats in props.items():
            for stat, info in stats.items():
                rows.append({
                    "matchup": matchup_short,
                    "status": status,
                    "home": home,
                    "away": away,
                    "book": book,
                    "player": player_name,
                    "stat": stat,
                    "line": info.get("line", ""),
                    "over_price": info.get("over_price", ""),
                    "fetched_at": m.get("fetched_at", ""),
                })
    return rows

def _quota_skip():
    try:
        qpath = Path("/home/workspace/Daily_Log/quota_exhausted.json")
        if not qpath.exists():
            return False
        qdata = json.loads(qpath.read_text())
        for k in qdata.get("keys", []):
            if k.get("key","")[:8] == ODDS_API_KEY[:8]:
                if k.get("exhausted"):
                    return True
    except Exception:
        pass
    return False

def run(date_str=None):
    """Main entry point."""
    now = datetime.now(timezone.utc)
    if not date_str:
        date_str = now.strftime("%Y%m%d")
    day_dir = LOG_DIR / date_str
    day_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== World Cup Picks — {date_str} ===")

    # Step 1: Get matches from ESPN
    espn_matches = fetch_espn_matches(date_str)
    print(f"ESPN matches: {len(espn_matches)}")
    for m in espn_matches:
        print(f"  {m['name']}: {m['status']}")


    # ── Quota Gate: skip Odds API calls when key is exhausted ──
    skip_odds = _quota_skip()
    if skip_odds:
        print("⏭️  QUOTA GATE: Odds API key exhausted — skipping all live API calls, using self-edge only")
        odds_games = []
    else:
    # Step 2: Get game IDs from Odds API
        odds_games = fetch_odds_games()
    print(f"Odds API games: {len(odds_games)}")

    # Step 3: For each upcoming match, fetch player props
    results = []
    for em in espn_matches:
        if em.get("completed"):
            print(f"  Skipping completed: {em['name']}  (Odds API)")
            # Still generate self-edge for completed matches
            self_edge = _generate_self_edge_props(em)
            result = {
                **em,
                "player_props": self_edge,
                "book": "self-edge" if self_edge else "none",
                "fetched_at": now.isoformat(),
            }
            results.append(result)
            continue

        og = match_espn_to_odds(em, odds_games)
        if not og:
            print(f"  No Odds API match for: {em['name']}")
            # Self-edge fallback
            if not em.get("completed"):
                self_edge = _generate_self_edge_props(em)
                if self_edge:
                    book_label = "self-edge"
                    print(f"  SELF-EDGE: {len(self_edge)} players, {sum(len(v) for v in self_edge.values())} props for {em['name']}")
                else:
                    self_edge = {}
                    book_label = "none"
            else:
                self_edge = {}
                book_label = "none"
            result = {
                **em,
                "player_props": self_edge,
                "book": book_label,
                "fetched_at": now.isoformat(),
            }
            results.append(result)
            continue
        # Try books in priority order
        game_id = og["id"]
        props = {}
        book_used = "none"
        teams_ = em.get("teams", [])
        away_ = teams_[0]["name"] if len(teams_) > 0 else ""
        home_ = teams_[1]["name"] if len(teams_) > 1 else ""
        prop_data = fetch_player_props(game_id, away_, home_)

        for bk in BOOK_PRIORITY:
            props = extract_props(prop_data, bk)
            if props:
                book_used = bk
                break

        if not props:
            print(f"  No {', '.join(BOOK_PRIORITY)} props for: {em['name']}")

        # Self-edge fallback: generate props from cached player averages + TC math when Odds API is unavailable
        if not props and not em.get("completed"):
            self_edge = _generate_self_edge_props(em)
            if self_edge:
                props = self_edge
                book_used = "self-edge"
                print(f"  SELF-EDGE: {len(props)} players, {sum(len(v) for v in props.values())} props for {em["name"]}")

        print(f"  {em['name']}: {len(props)} players, {sum(len(v) for v in props.values())} props [{book_used}]")

        result = {
            **em,
            "odds_game_id": game_id,
            "player_props": props,
            "book": book_used,
            "fetched_at": now.isoformat(),
        }
        results.append(result)

    # Step 4: Write outputs
    # matches.json
    with open(day_dir / "matches.json", "w") as f:
        json.dump({"date": date_str, "fetched_at": now.isoformat(), "matches": results}, f, indent=2, default=str)

    # props.json (full detail)
    with open(day_dir / "props.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    # picks.csv
    csv_rows = build_csv_rows(results)
    csv_path = day_dir / "picks.csv"
    with open(csv_path, "w", newline="") as f:
        if csv_rows:
            w = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
            w.writeheader()
            w.writerows(csv_rows)
        else:
            f.write("matchup,status,home,away,book,player,stat,line,over_price,fetched_at\n")

    # last_run.json
    summary = {
        "timestamp": now.isoformat(),
        "date": date_str,
        "matches_total": len(results),
        "matches_upcoming": sum(1 for r in results if not r.get("completed")),
        "matches_with_props": sum(1 for r in results if r.get("player_props")),
        "total_players": sum(len(r.get("player_props", {})) for r in results),
        "total_props": sum(sum(len(v) for v in r.get("player_props", {}).values()) for r in results),
        "books_used": list(set(r.get("book", "none") for r in results)),
    }
    with open(LOG_DIR / "last_run.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nDone. {summary['total_players']} players, {summary['total_props']} props")
    print(f"Output: {day_dir}/")
    print(f"  {day_dir}/matches.json")
    print(f"  {day_dir}/props.json")
    print(f"  {csv_path}")
    print(f"  {LOG_DIR}/last_run.json")

    return results

# ═══════════════════════════════════════════════════════════════════
# SELF-EDGE FALLBACK — when Odds API is exhausted, generate props from cached player averages + TC math
# ═══════════════════════════════════════════════════════════════════

AVG_CACHE = WORKSPACE / "Daily_Log" / "wc_player_avgs.json"
WC_TEAM_STRENGTH = {
    "Brazil": 1.28, "France": 1.25, "Argentina": 1.24, "England": 1.22,
    "Spain": 1.20, "Germany": 1.18, "Portugal": 1.17, "Netherlands": 1.16,
    "Italy": 1.15, "Belgium": 1.13, "Croatia": 1.12, "Uruguay": 1.11,
    "Morocco": 1.10, "Colombia": 1.08, "Mexico": 1.06, "United States": 1.05,
    "USA": 1.05, "Senegal": 1.04, "Japan": 1.03, "South Korea": 1.02, "Switzerland": 1.02,
    "Denmark": 1.01, "Austria": 1.00, "Nigeria": 0.98, "Ecuador": 0.97,
    "Serbia": 0.96, "Iran": 0.95, "Australia": 0.94, "Wales": 0.93,
    "Poland": 0.92, "Sweden": 0.91, "Egypt": 0.90, "Ivory Coast": 0.89,
    "Tunisia": 0.87, "Chile": 0.86, "Peru": 0.85, "Ukraine": 0.84,
    "Türkiye": 0.83, "Turkey": 0.83, "Norway": 0.82, "Scotland": 0.80,
    "Czech Republic": 0.79, "Czechia": 0.79, "Cameroon": 0.78, "Ghana": 0.77, "Mali": 0.75, "Cape Verde": 0.76,
    "Burkina Faso": 0.74, "South Africa": 0.73, "DR Congo": 0.72, "Congo DR": 0.72, "Bosnia-Herzegovina": 0.81, "Algeria": 0.71,
    "Paraguay": 0.70, "Canada": 0.69, "Costa Rica": 0.67, "Panama": 0.65,
    "Jamaica": 0.63, "Venezuela": 0.62, "Bolivia": 0.60, "Honduras": 0.58,
    "El Salvador": 0.55, "Saudi Arabia": 0.54, "Qatar": 0.53, "UAE": 0.52,
    "Iraq": 0.50, "Uzbekistan": 0.49, "China": 0.47, "Thailand": 0.45,
    "New Zealand": 0.44, "Haiti": 0.40, "Curaçao": 0.38, "Trinidad & Tobago": 0.36,
}

STAT_KEYS = ["goals", "assists", "shots_on_target", "shots", "fouls", "tackles", "cards", "passes"]
STAT_MAP = {"G": "goals", "A": "assists", "SOT": "shots_on_target", "S": "shots", "FC": "fouls"}

def _load_player_avgs():
    if not AVG_CACHE.exists():
        return {}
    return json.loads(AVG_CACHE.read_text())

def _team_strength(team_name):
    for k, v in WC_TEAM_STRENGTH.items():
        if k.lower() in team_name.lower() or team_name.lower() in k.lower():
            return v
    return 1.0


def _team_name_match(roster_name, match_name):
    """Fuzzy match roster team name to match team name."""
    r = roster_name.lower().strip()
    m = match_name.lower().strip()
    if r == m:
        return True
    if r in m or m in r:
        return True
    # Handle aliases
    aliases = {"united states": "usa", "korea republic": "south korea", "korea dpr": "north korea",
               "côte d'ivoire": "ivory coast", "cote d'ivoire": "ivory coast",
               "trinidad and tobago": "trinidad & tobago", "curaçao": "curacao", "dr congo": "congo dr", "congo dr": "dr congo", "dr congo": "congo dr", "congo dr": "dr congo"}
    for a, b in aliases.items():
        if (a in r and b in m) or (b in r and a in m):
            return True
    return False

def _player_in_roster(player_name, roster_set):
    """Check if player name appears in roster set, using fuzzy matching."""
    if not player_name or not roster_set:
        return False
    # Direct match
    if player_name in roster_set:
        return True
    # Normalize: last name only
    parts = player_name.strip().split()
    last = parts[-1] if parts else player_name
    for r in roster_set:
        r_parts = r.strip().split()
        r_last = r_parts[-1] if r_parts else r
        if last.lower() == r_last.lower():
            return True
        if player_name.lower() == r.lower():
            return True
    return False


def _get_team_player_names(team_name: str):
    """Get all player names on a team from the roster cache."""
    ROSTER_CACHE = WORKSPACE / "Daily_Log" / "wc_team_rosters.json"
    names = set()
    if ROSTER_CACHE.exists():
        rosters = json.loads(ROSTER_CACHE.read_text())
        for roster_team, players in rosters.items():
            if _team_name_match(roster_team, team_name):
                for p in players:
                    if isinstance(p, dict):
                        names.add(p.get("name", ""))
                    else:
                        names.add(str(p))
                break
    return names

def _generate_self_edge_props(match):
    teams = match.get("teams", [])
    if len(teams) < 2:
        return {}
    away_name = teams[0].get("name", "")
    home_name = teams[1].get("name", "")
    away_str = _team_strength(away_name)
    home_str = _team_strength(home_name)
    
    # Load team rosters to filter players by team
    ROSTER_CACHE = WORKSPACE / "Daily_Log" / "wc_team_rosters.json"
    allowed_players = set()
    if ROSTER_CACHE.exists():
        rosters = json.loads(ROSTER_CACHE.read_text())
        for team_roster_name in rosters:
            if _team_name_match(team_roster_name, away_name):
                for p in rosters[team_roster_name]:
                    if isinstance(p, dict):
                        allowed_players.add(p.get("name", ""))
                    else:
                        allowed_players.add(str(p))
            if _team_name_match(team_roster_name, home_name):
                for p in rosters[team_roster_name]:
                    if isinstance(p, dict):
                        allowed_players.add(p.get("name", ""))
                    else:
                        allowed_players.add(str(p))
    
    avgs = _load_player_avgs()
    props = {}
    covered_players = set()

    if avgs:
        for player_name, pdata in avgs.items():
            if not isinstance(pdata, dict):
                continue
            if allowed_players and not _player_in_roster(player_name, allowed_players):
                continue
            is_home_player = player_name.lower() in {n.lower() for n in _get_team_player_names(home_name)}
            opp_strength = home_str if is_home_player else away_str
            own_strength = away_str if is_home_player else home_str
            home_adj_val = 1.1 if is_home_player else 0.95
            stat_props = {}
            for skey in STAT_KEYS:
                raw_key = None
                for rk, mk in STAT_MAP.items():
                    if mk == skey:
                        raw_key = rk
                        break
                if not raw_key:
                    continue
                raw_val = pdata.get(raw_key, 0)
                if raw_val <= 0:
                    continue
                tc_proj = raw_val * max(0.8, min(1.3, own_strength)) * max(0.7, min(1.3, (1.0 / max(opp_strength, 0.4)) * 0.85)) * home_adj_val
                tc_line = round(tc_proj * 2) / 2 if skey in ("goals", "assists", "cards") else max(0.0, round(tc_proj * 0.88 * 10) / 10)
                stat_props[skey] = {"line": tc_line, "over_price": -110, "edge_pct": round((tc_proj - tc_line) / max(tc_line, 0.01) * 100, 1), "source": "self-edge"}
            if stat_props:
                props[player_name] = stat_props
                covered_players.add(player_name.lower())

    # FALLBACK: default stats for players without historical data
    if allowed_players:
        DEFAULT_AVGS = {"G": 0.15, "A": 0.10, "SOT": 0.5, "S": 1.0, "FC": 0.8, "TKL": 1.2, "CRD": 0.2, "PAS": 25.0}
        for player_name in sorted(allowed_players):
            if player_name.lower() in covered_players:
                continue
            home_names = _get_team_player_names(home_name)
            is_home = player_name.lower() in {n.lower() for n in home_names}
            opp_str = away_str if is_home else home_str
            own_str_val = home_str if is_home else away_str
            h_adj = 1.1 if is_home else 0.95
            stat_props = {}
            for raw_key, default_val in DEFAULT_AVGS.items():
                skey = STAT_MAP.get(raw_key)
                if not skey:
                    continue
                scaled = default_val * max(0.8, min(1.3, own_str_val)) * max(0.7, min(1.3, (1.0 / max(opp_str, 0.4)) * 0.85)) * h_adj
                tc_line = round(scaled * 2) / 2 if skey in ("goals", "assists", "cards") else max(0.0, round(scaled * 0.88 * 10) / 10)
                if tc_line > 0:
                    stat_props[skey] = {"line": tc_line, "over_price": -110, "edge_pct": round((scaled - tc_line) / max(tc_line, 0.01) * 100, 1), "source": "self-edge-default"}
            if stat_props:
                props[player_name] = stat_props

    return props
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="World Cup 2026 Daily Pick Scraper")
    parser.add_argument("--date", default=None, help="Date in YYYYMMDD format (default: today UTC)")
    args = parser.parse_args()
    run(args.date)
