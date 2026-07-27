#!/usr/bin/env python3
"""
gen_mlb_today.py — MLB Self-Edge Projection Generator
Builds per-player projections using season stats + home/away adjustments.
v2 — Statcast xBA augmentation for AVG/OBP/SLG/OPS (pybaseball).
"""

import json
import os
import time
import hashlib
import sys
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import logging as _mlb_aug_log

sys.path.insert(0, '/home/workspace/Projects')
from tc_math import sport_over_under_signal

try:
    from crash_guard import consume_budget
except ImportError:
    def consume_budget(source, amount=1):
        return True

try:
    from pybaseball import statcast_batter, batting_stats_splits, playerid_lookup
    _PYBASEBALL_AVAILABLE = True
except ImportError:
    _PYBASEBALL_AVAILABLE = False

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

try:
    import statsapi
except ImportError:
    statsapi = None

# ── Configuration ──────────────────────────────────────────────
MIN_GAMES = 5
DEFAULT_LINE_MARGIN = {
    "H": 0.5, "R": 0.3, "RBI": 0.3, "HR": 0.2, "2B": 0.2,
    "3B": 0.1, "BB": 0.4, "SB": 0.2, "AVG": 0.020, "OBP": 0.020,
    "SLG": 0.030, "OPS": 0.030,
}

HOME_BOOST = 1.02
AWAY_PENALTY = 0.98

SELF_EDGE_SPREAD = {
    "H": 0.15, "R": 0.15, "RBI": 0.15,
    "HR": 0.25, "2B": 0.25, "3B": 0.25,
    "BB": 0.18, "SB": 0.25,
    "AVG": 0.25, "OBP": 0.25, "SLG": 0.25, "OPS": 0.25,
    "K": 0.15, "ER": 0.15,
    "ERA": 0.20, "WHIP": 0.20,
}
MIN_SELF_EDGE = 0.05

def _self_edge_line(stat: str, proj_val: float, hash_seed: int) -> tuple:
    """Return (line, edge) with stat-aware spread and absolute minimum gap.
    
    For tiny projections where spread*gap < MIN_SELF_EDGE, line is forced
    MIN_SELF_EDGE away from projection — no cosmetic-only edges.
    """
    spread = SELF_EDGE_SPREAD.get(stat, 0.15)
    low = round(proj_val * (1 - spread), 4)
    high = round(proj_val * (1 + spread), 4)
    if hash_seed % 2 == 0:
        line = low if hash_seed % 4 != 0 else high
    else:
        line = high if hash_seed % 4 != 1 else low
    gap = round(abs(proj_val - line), 4)
    if gap < MIN_SELF_EDGE:
        if hash_seed % 2 == 0:
            line = max(0.0, round(proj_val - MIN_SELF_EDGE, 4))
        else:
            line = round(proj_val + MIN_SELF_EDGE, 4)
        gap = round(abs(proj_val - line), 4)
    return line, gap

PITCHING_STATS = ["K", "BB", "H", "ER"]
PITCHING_RATE_STATS = ["ERA", "WHIP"]
REGRESSION_FACTOR = 0.85

LOG_DIR = Path("/home/workspace/Daily_Log")
CACHE_DIR = Path("/home/workspace/Daily_Log/mlb_cache")

# ── Statcast augmentation cache ─────────────────────────────
_STATCAST_CACHE = {}

def get_today_str() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def ensure_dirs(date_str: str):
    (LOG_DIR / date_str).mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def clean_team_name(name: str) -> str:
    return name.replace(" ", "_").replace("'", "").replace(".", "")


def get_todays_games() -> list:
    return statsapi.schedule(date=get_today_str())


def get_team_roster(team_name: str) -> list:
    cache_file = CACHE_DIR / f"roster_{clean_team_name(team_name)}.json"
    if cache_file.exists():
        with open(cache_file) as f:
            data = json.load(f)
            if data.get("_fetch_date") == get_today_str():
                return data["players"]

    try:
        teams = statsapi.lookup_team(team_name)
        if not teams:
            return []
        team_id = teams[0]["id"]
        roster = statsapi.roster(team_id)
    except Exception as e:
        print(f"  [WARN] Roster failed for {team_name}: {e}")
        return []

    players = []
    for entry in roster.split("\n"):
        parts = entry.strip().split(maxsplit=1)
        if len(parts) >= 2:
            num = parts[0]
            name = parts[1].strip()
            players.append({"name": name, "roster_num": num})

    if players:
        with open(cache_file, "w") as f:
            json.dump({"_fetch_date": get_today_str(), "players": players}, f)

    return players


def find_player_id(name: str) -> int:
    cache_file = CACHE_DIR / f"lookup_{name.replace(' ', '_')}.json"
    if cache_file.exists():
        with open(cache_file) as f:
            data = json.load(f)
            if data.get("_fetch_date") == get_today_str():
                return data.get("player_id", 0)

    try:
        results = statsapi.lookup_player(name)
        if results:
            pid = results[0]["id"]
            with open(cache_file, "w") as f:
                json.dump({"_fetch_date": get_today_str(), "player_id": pid}, f)
            return pid
    except Exception:
        pass
    return 0


def get_player_stats(player_name: str, player_id: int) -> dict:
    cache_file = CACHE_DIR / f"pid_{player_name.replace(' ', '_')}.json"
    if cache_file.exists():
        with open(cache_file) as f:
            cached = json.load(f)
            if cached.get("_fetch_date") == get_today_str():
                return cached.get("stats", {})

    try:
        stats = statsapi.player_stat_data(player_id, group="hitting", type="season")
    except Exception:
        return {}

    if not stats or "stats" not in stats or not stats["stats"]:
        return {}

    s = stats["stats"][0]["stats"]
    g = s.get("gamesPlayed", 1) or 1

    result = {
        "G": g,
        "AVG": float(s.get("avg", ".000") or ".000"),
        "OBP": float(s.get("obp", ".000") or ".000"),
        "SLG": float(s.get("slg", ".000") or ".000"),
        "OPS": float(s.get("ops", ".000") or ".000"),
        "H": float(s.get("hits", 0) or 0),
        "R": float(s.get("runs", 0) or 0),
        "RBI": float(s.get("rbi", 0) or 0),
        "HR": float(s.get("homeRuns", 0) or 0),
        "2B": float(s.get("doubles", 0) or 0),
        "3B": float(s.get("triples", 0) or 0),
        "BB": float(s.get("baseOnBalls", 0) or 0),
        "SB": float(s.get("stolenBases", 0) or 0),
    }

    with open(cache_file, "w") as f:
        json.dump({"_fetch_date": get_today_str(), "stats": result}, f)

    return result


def get_pitcher_stats(player_name: str, player_id: int) -> dict:
    cache_file = CACHE_DIR / f"pid_pitch_{player_name.replace(' ', '_')}.json"
    if cache_file.exists():
        with open(cache_file) as f:
            cached = json.load(f)
            if cached.get("_fetch_date") == get_today_str():
                return cached.get("stats", {})

    try:
        stats = statsapi.player_stat_data(player_id, group="pitching", type="season")
    except Exception:
        return {}

    if not stats or "stats" not in stats or not stats["stats"]:
        return {}

    s = stats["stats"][0]["stats"]
    g = s.get("gamesPlayed", 1) or 1
    gs = s.get("gamesStarted", 1) or 1
    ip_str = s.get("inningsPitched", "0.0") or "0.0"
    try:
        ip = float(ip_str)
    except (ValueError, TypeError):
        ip = 0.0

    result = {
        "G": int(g), "GS": int(gs), "IP": round(ip, 2),
        "K": float(s.get("strikeOuts", 0) or 0),
        "BB": float(s.get("baseOnBalls", 0) or 0),
        "H": float(s.get("hits", 0) or 0),
        "ER": float(s.get("earnedRuns", 0) or 0),
        "ERA": float(s.get("era", "0.00") or "0.00"),
        "WHIP": float(s.get("whip", "0.00") or "0.00"),
    }

    with open(cache_file, "w") as f:
        json.dump({"_fetch_date": get_today_str(), "stats": result}, f)

    return result


# ═══════════════════════════════════════════════════════════════
#  MLB Statcast Augmentation (pybaseball)
#  Applies to rate stats only: AVG, OBP, SLG, OPS
#  Uses xBA + platoon splits to nudge projection 30% toward truth
# ═══════════════════════════════════════════════════════════════

_MLB_AUGMENT_CACHE = {}

AUGMENTABLE_RATE_STATS = {"AVG", "OBP", "SLG", "OPS"}

def _clean_player_name(name: str) -> str:
    """Remove position prefix (1B, 2B, 3B, SS, OF, C, DH, etc.)"""
    pos_tags = {'1B', '2B', '3B', 'SS', 'OF', 'C', 'DH'}
    parts = name.strip().split()
    if len(parts) > 1 and parts[0] in pos_tags:
        return " ".join(parts[1:])
    return name.strip()

def _augment_mlb_rate_stat(player_name: str, proj_val: float, pitcher_hand: str = "R") -> float:
    if not _PYBASEBALL_AVAILABLE or not consume_budget("pybaseball"):
        return proj_val

    cache_key = f"{player_name}_{pitcher_hand}"
    if cache_key in _MLB_AUGMENT_CACHE:
        return _MLB_AUGMENT_CACHE[cache_key]

    try:
        cleaned = _clean_player_name(player_name)
        parts = cleaned.split()
        if len(parts) < 2:
            return proj_val
        last, first = parts[-1], parts[0]
        lookup = playerid_lookup(last, first)
        if lookup.empty:
            return proj_val
        player_id = lookup.iloc[0]["key_mlbam"]

        end_date = datetime.now()
        start_date = end_date - timedelta(days=14)
        statcast = statcast_batter(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), player_id)

        if statcast.empty:
            return proj_val

        avg_xba = statcast["estimated_ba_using_speedangle"].mean()

        splits = batting_stats_splits(player_id, year=datetime.now().year)
        platoon_avg = proj_val
        if not splits.empty:
            col = "vs RHP" if pitcher_hand == "R" else "vs LHP"
            vs_split = splits[splits["split"] == col]
            if not vs_split.empty:
                platoon_avg = vs_split.iloc[0]["avg"]

        blended = (avg_xba * 0.6) + (platoon_avg * 0.4)
        adjusted = proj_val + (blended - proj_val) * 0.3
        adjusted = max(0.100, min(0.450, adjusted))

        _MLB_AUGMENT_CACHE[cache_key] = round(adjusted, 3)
        return _MLB_AUGMENT_CACHE[cache_key]

    except Exception:
        return proj_val


def apply_mlb_augmentation(proj: dict) -> dict:
    for player in proj.get("players", []):
        name = player.get("name", "")
        projs = player.get("projections", {})
        for stat in list(projs.keys()):
            if stat in AUGMENTABLE_RATE_STATS:
                old_proj = projs[stat]["projection"]
                new_proj = _augment_mlb_rate_stat(name, old_proj)
                if new_proj != old_proj:
                    projs[stat]["projection"] = new_proj
                    line = projs[stat].get("line", 0)
                    direction, edge = sport_over_under_signal(
                        projection=new_proj, market_line=line, sport="MLB", min_edge=0.0
                    )
                    if direction in ("INVALID", "FLAT"):
                        direction = "OVER" if new_proj > line else "UNDER"
                        edge = round(abs(new_proj - line), 4)
                    projs[stat]["edge"] = round(edge, 4)
                    projs[stat]["direction"] = direction
    return proj


# ═══════════════════════════════════════════════════════════════
# PROJECTION BUILDING
# ═══════════════════════════════════════════════════════════════

def build_projections_for_game(game: dict) -> dict:
    away = game["away_name"]
    home = game["home_name"]
    game_id = game["game_id"]

    result = {
        "game_id": game_id,
        "away": away,
        "home": home,
        "start_time": game.get("game_datetime", ""),
        "generated_at": datetime.now(ET).isoformat(),
        "players": [],
    }

    for team_name, venue_bonus in [(away, AWAY_PENALTY), (home, HOME_BOOST)]:
        print(f"  Loading roster: {team_name}")
        players = get_team_roster(team_name)
        print(f"    {len(players)} players on roster")

        for p in players[:40]:
            name = p["name"]
            pid = find_player_id(name)
            if not pid:
                continue

            stats = get_player_stats(name, pid)
            games = stats.get("G", 0)
            if games < MIN_GAMES:
                continue

            projs = {}

            for stat in ["H", "R", "RBI", "HR", "2B", "3B", "BB", "SB"]:
                raw = (stats[stat] / games) * REGRESSION_FACTOR * venue_bonus
                proj_val = round(raw, 2)
                key = f"{name}_{stat}_{game_id}"
                hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
                line, _ = _self_edge_line(stat, proj_val, hash_val)
                direction, edge = sport_over_under_signal(projection=proj_val, market_line=line, sport="MLB", min_edge=0.0)
                if direction in ("INVALID", "FLAT"):
                    direction = "OVER" if proj_val > line else "UNDER"
                    edge = round(abs(proj_val - line), 3)
                projs[stat] = {"projection": proj_val, "line": line, "edge": round(edge, 3), "direction": direction}

            for stat in ["AVG", "OBP", "SLG", "OPS"]:
                raw = stats[stat] * REGRESSION_FACTOR * venue_bonus
                proj_val = round(raw, 3)
                key = f"{name}_{stat}_{game_id}"
                hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
                line, _ = _self_edge_line(stat, proj_val, hash_val)
                direction, edge = sport_over_under_signal(projection=proj_val, market_line=line, sport="MLB", min_edge=0.0)
                if direction in ("INVALID", "FLAT"):
                    direction = "OVER" if proj_val > line else "UNDER"
                    edge = round(abs(proj_val - line), 4)
                projs[stat] = {"projection": proj_val, "line": line, "edge": round(edge, 4), "direction": direction}

            result["players"].append({
                "name": name,
                "player_id": pid,
                "team": team_name,
                "venue": "home" if venue_bonus == HOME_BOOST else "away",
                "games_played": games,
                "season_stats": stats,
                "projections": projs,
            })
            time.sleep(0.3)

    # ── PITCHER PROJECTIONS ──
    for team_name, _ in [(away, None), (home, None)]:
        game_meta = game
        pitcher_key = "home_probable_pitcher" if team_name == home else "away_probable_pitcher"
        pitcher_name = game_meta.get(pitcher_key, "")
        if not pitcher_name:
            continue
        pid = find_player_id(pitcher_name)
        if not pid:
            print(f"    [PITCH] No ID for {pitcher_name}")
            continue

        pstats = get_pitcher_stats(pitcher_name, pid)
        gs = pstats.get("GS", 0)
        if gs < 1:
            continue

        ip = pstats.get("IP", 0)
        if ip < 10:
            continue

        projs = {}
        ip_pg = ip / gs
        for stat in PITCHING_STATS:
            per_game = pstats[stat] / gs if gs > 0 else 0
            raw = per_game * REGRESSION_FACTOR
            proj_val = round(raw, 2)
            key = f"PITCHER_{pitcher_name}_{stat}_{game_id}"
            hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
            line, _ = _self_edge_line(stat, proj_val, hash_val)
            direction, edge = sport_over_under_signal(projection=proj_val, market_line=line, sport="MLB", min_edge=0.0)
            if direction in ("INVALID", "FLAT"):
                direction = "OVER" if proj_val > line else "UNDER"
                edge = round(abs(proj_val - line), 3)
            projs[stat] = {"projection": proj_val, "line": line, "edge": round(edge, 3), "direction": direction}

        for stat in PITCHING_RATE_STATS:
            raw = pstats[stat] * REGRESSION_FACTOR
            proj_val = round(raw, 3)
            key = f"PITCHER_{pitcher_name}_{stat}_{game_id}"
            hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
            line, _ = _self_edge_line(stat, proj_val, hash_val)
            direction, edge = sport_over_under_signal(projection=proj_val, market_line=line, sport="MLB", min_edge=0.0)
            if direction in ("INVALID", "FLAT"):
                direction = "OVER" if proj_val > line else "UNDER"
                edge = round(abs(proj_val - line), 4)
            projs[stat] = {"projection": proj_val, "line": line, "edge": round(edge, 4), "direction": direction}

        result["players"].append({
            "name": pitcher_name,
            "player_id": pid,
            "team": team_name,
            "role": "PITCHER",
            "venue": "home" if team_name == home else "away",
            "games_played": gs,
            "games_started": gs,
            "innings_pitched": ip,
            "ip_per_start": round(ip_pg, 2),
            "season_stats": pstats,
            "projections": projs,
        })
        time.sleep(0.3)

    return result


# ═══════════════════════════════════════════════════════════════
# MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════

def generate() -> dict:
    if not statsapi:
        return {"error": "statsapi not installed"}

    date_str = get_today_str()
    ensure_dirs(date_str)

    print(f"[gen_mlb_today] Date: {date_str} ET")
    games = get_todays_games()
    print(f"[gen_mlb_today] {len(games)} games scheduled")

    output = {"date": date_str, "sport": "MLB", "games": []}

    for game in games:
        away = game["away_name"]
        home = game["home_name"]
        status = game["status"]
        print(f"\n{'='*60}")
        print(f"  {away} @ {home} [{status}]")
        print(f"{'='*60}")

        if status in ("Final", "Game Over"):
            print("  Skipping completed game")
            continue

        proj = build_projections_for_game(game)

        proj = apply_mlb_augmentation(proj)

        output["games"].append(proj)

        fname = f"proj_MLB_{clean_team_name(away)}_at_{clean_team_name(home)}.json"
        fpath = LOG_DIR / date_str / fname
        with open(fpath, "w") as f:
            json.dump(proj, f, indent=2)
        print(f"  Saved: {fpath}")

    # ── Enrich game lines from TheRundown ──
    try:
        sys.path.insert(0, str(Path(__file__).parent / 'src' / 'adapters'))
        from therundown_adapter import get_formatted_odds
        rundown = get_formatted_odds('MLB')
        if rundown and rundown.get('events'):
            for game_entry in output['games']:
                away = game_entry.get('away', '') or game_entry.get('away_name', '')
                home = game_entry.get('home', '') or game_entry.get('home_name', '')
                for ev in rundown['events']:
                    if ev.get('away_full') == away and ev.get('home_full') == home:
                        game_entry['game_lines'] = {
                            'spread': ev.get('spread', {}),
                            'moneyline': ev.get('moneyline', {}),
                            'totals': ev.get('totals', {}),
                            'event_id': ev.get('event_id', ''),
                            'event_date': ev.get('event_date', ''),
                        }
                        break
            enriched = sum(1 for g in output['games'] if 'game_lines' in g)
            print(f"[gen_mlb_today] TheRundown lines enriched: {enriched}/{len(output['games'])} games")
    except Exception as e:
        print(f"[gen_mlb_today] TheRundown enrichment skipped: {e}")

    summary_path = LOG_DIR / date_str / "proj_MLB_summary.json"
    with open(summary_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSummary saved: {summary_path}")
    print(f"Total player projections: {sum(len(g['players']) for g in output['games'])}")

    return output


if __name__ == "__main__":
    generate()
