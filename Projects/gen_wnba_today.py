#!/usr/bin/env python3
"""
Generate WNBA projections using per-player season averages.

Loads /home/workspace/data/wnba_player_stats.json (built by build_wnba_stats.py
from all ESPN boxscore backtest data) and produces forward-looking per-player
projections.  Falls back to ESPN live boxscores when season data is missing.
"""

import json, os, sys, logging
import hashlib
from datetime import datetime

sys.path.insert(0, '/home/workspace/Projects')
from tc_math import sport_over_under_signal
import time as _wnba_time

try:
    from crash_guard import consume_budget
except ImportError:
    def consume_budget(source, amount=1):
        return True

try:
    from nba_api.stats.endpoints import leaguegamefinder
    _NBA_API_AVAILABLE = True
except ImportError:
    _NBA_API_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DAILY_LOG = "/home/workspace/Daily_Log"
STATS_PATH = "/home/workspace/data/wnba_player_stats.json"
ROSTERS_PATH = "/home/workspace/data/rosters/wnba_rosters.json"

# ── 2026 WNBA All-Star Game rosters (source: WNBA official, July 2026) ─
ALLSTAR_ROSTERS = {
    "SPO": [  # Weatherspoon / Cheryl Reeve coaching
        "Caitlin Clark", "A'ja Wilson", "Olivia Miles", "Aliyah Boston",
        "Jessica Shepard", "Rhyne Howard", "Allisha Gray", "Jonquel Jones",
        "Courtney Williams", "Kiki Iriafen", "Nneka Ogwumike"
    ],
    "COOP": [  # Cynthia Cooper / Becky Hammon coaching
        "Paige Bueckers", "Breanna Stewart", "Kelsey Mitchell", "Natasha Howard",
        "Gabby Williams", "Angel Reese", "Marina Mabrey", "Dominique Malonga",
        "Kelsey Plum", "Jackie Young", "Sonia Citron"
    ],
}
ALLSTAR_ABBR = set(ALLSTAR_ROSTERS.keys())

# ── load season stats + name map ──────────────────────────────
def _load_stats():
    stats = {}
    name_map = {}  # full_name → initial_name (e.g. "Allisha Gray" → "A. Gray")
    try:
        with open(STATS_PATH) as f:
            stats = json.load(f)
    except Exception as e:
        logger.warning(f"Could not load season stats: {e}")
    if stats:
        try:
            with open(ROSTERS_PATH) as f:
                rosters = json.load(f)
            for team_abbr, team_data in rosters.items():
                for p in team_data.get("players", []):
                    name = p["name"]
                    parts = name.split()
                    if len(parts) >= 2:
                        init_name = f"{parts[0][0]}. {parts[-1]}"
                        if init_name in stats and stats[init_name]["team"] == team_abbr:
                            name_map[name] = init_name
        except Exception:
            pass
    return stats, name_map

STATS, NAME_MAP = _load_stats()
logger.info(f"Loaded stats for {len(STATS)} players, {len(NAME_MAP)} name mappings")

# ═══════════════════════════════════════════════════════════════
#  WNBA Recent-Form Augmentation (nba_api)
#  Pulls last 5 games via LeagueGameFinder, nudges 40% toward
#  recent average for PTS, REB, AST only.
# ═══════════════════════════════════════════════════════════════

_WNBA_AUGMENT_CACHE = {}
WNBA_AUGMENTABLE_STATS = {"PTS", "REB", "AST"}

def _augment_wnba_stat(player_name: str, proj_val: float, stat_type: str) -> float:
    if not _NBA_API_AVAILABLE or not consume_budget("nba_api"):
        return proj_val

    cache_key = f"{player_name}_{stat_type}"
    if cache_key in _WNBA_AUGMENT_CACHE:
        return _WNBA_AUGMENT_CACHE[cache_key]

    try:
        WNBA_LEAGUE_ID = "10"
        game_finder = leaguegamefinder.LeagueGameFinder(league_id_nullable=WNBA_LEAGUE_ID)
        games = game_finder.get_data_frames()[0]

        player_games = games[games["PLAYER_NAME"].str.contains(player_name, case=False, na=False)]
        if player_games.empty:
            return proj_val

        player_games = player_games.sort_values("GAME_DATE", ascending=False).head(5)

        stat_map = {"PTS": "PTS", "REB": "REB", "AST": "AST"}
        nba_stat_col = stat_map.get(stat_type, "PTS")

        recent_avg = float(player_games[nba_stat_col].mean())

        adjusted = proj_val + (recent_avg - proj_val) * 0.4

        if stat_type == "PTS":
            adjusted = max(5.0, min(30.0, adjusted))
        elif stat_type == "REB":
            adjusted = max(2.0, min(18.0, adjusted))
        elif stat_type == "AST":
            adjusted = max(1.0, min(12.0, adjusted))

        _WNBA_AUGMENT_CACHE[cache_key] = round(adjusted, 1)
        _wnba_time.sleep(0.3)
        return _WNBA_AUGMENT_CACHE[cache_key]

    except Exception:
        return proj_val


def apply_wnba_augmentation(game_proj: dict) -> dict:
    for side in ("away", "home"):
        side_data = game_proj.get(side, {}).get("all", {})
        for player in side_data.get("players", []):
            player_name = player.get("player", "") or player.get("name", "")
            for proj_entry in player.get("projections", []):
                stat = proj_entry.get("stat", "")
                if stat in WNBA_AUGMENTABLE_STATS:
                    old_proj = proj_entry["projection"]
                    new_proj = _augment_wnba_stat(player_name, old_proj, stat)
                    if new_proj != old_proj:
                        proj_entry["projection"] = new_proj
                        line = proj_entry.get("line", 0)
                        direction, edge = sport_over_under_signal(
                            projection=new_proj, market_line=line, sport="WNBA", min_edge=0.0
                        )
                        if direction in ("INVALID", "FLAT"):
                            direction = "OVER" if new_proj > line else "UNDER"
                            edge = round(abs(new_proj - line), 2)
                        proj_entry["edge"] = round(edge, 2)
                        proj_entry["direction"] = direction
    return game_proj

# ── per-player projection ─────────────────────────────────────
def project_player(name: str) -> dict:
    """Return {PTS, REB, AST, STL, BLK, 3PM, TO, PRA, PR, PA} or None."""
    init = NAME_MAP.get(name)
    if not init or init not in STATS:
        return None
    s = STATS[init]
    r5 = s.get("recent5", s["season"])
    season = s["season"]
    return {
        "PTS": round(0.4 * season["PTS"] + 0.6 * r5["PTS"], 1),
        "REB": round(0.4 * season["REB"] + 0.6 * r5["REB"], 1),
        "AST": round(0.4 * season["AST"] + 0.6 * r5["AST"], 1),
        "STL": round(0.4 * season.get("STL", 0) + 0.6 * r5.get("STL", 0), 1),
        "BLK": round(0.4 * season.get("BLK", 0) + 0.6 * r5.get("BLK", 0), 1),
        "3PM": round(0.4 * season.get("3PM", 0) + 0.6 * r5.get("3PM", 0), 1),
        "TO": round(0.4 * season.get("TO", 0) + 0.6 * r5.get("TO", 0), 1),
        "PRA": round(0.4 * season.get("PRA", 0) + 0.6 * r5.get("PRA", 0), 1),
        "PR": round(0.4 * season.get("P+R", 0) + 0.6 * r5.get("P+R", 0), 1),
        "PA": round(0.4 * season.get("P+A", 0) + 0.6 * r5.get("P+A", 0), 1),
    }

WNBA_SELF_EDGE_SPREAD = {
    "PTS": 0.15, "REB": 0.18, "AST": 0.15,
    "3PM": 0.25, "STL": 0.25, "BLK": 0.25, "TO": 0.15,
    "OREB": 0.18, "DREB": 0.18, "PF": 0.20,
}
WNBA_MIN_SELF_EDGE = 0.05

def _wnba_self_edge_line(stat: str, proj_val: float, hash_seed: int):
    spread = WNBA_SELF_EDGE_SPREAD.get(stat, 0.15)
    low = round(proj_val * (1 - spread), 4)
    high = round(proj_val * (1 + spread), 4)
    if hash_seed % 2 == 0:
        line = low if hash_seed % 4 != 0 else high
    else:
        line = high if hash_seed % 4 != 1 else low
    gap = round(abs(proj_val - line), 4)
    if gap < WNBA_MIN_SELF_EDGE:
        if hash_seed % 2 == 0:
            line = max(0.0, round(proj_val - WNBA_MIN_SELF_EDGE, 4))
        else:
            line = round(proj_val + WNBA_MIN_SELF_EDGE, 4)
        gap = round(abs(proj_val - line), 4)
    return line, gap

def build_projection(p, stat: str, val: float) -> dict:
    key = f"{p.get('player', p.get('name', 'UNKNOWN'))}_{stat}_{p.get('team', '')}"
    hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
    line, edge = _wnba_self_edge_line(stat, val, hash_val)
    direction = "OVER" if val > line else "UNDER"
    return {"stat": stat, "projection": val, "line": line, "edge": round(edge, 2), "direction": direction, "period": "GAME"}

# ── ESPN fallback (kept from original) ────────────────────────
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary"
WNBA_STATS = ["PTS", "REB", "AST", "STL", "BLK", "3PM", "TO", "OREB", "DREB", "PF"]
ESPN_TO_TC_STAT = {"3PT": "3PM"}

def _fetch_scoreboard(date_str):
    import requests
    if "-" in date_str:
        dparam = date_str.replace("-", "")
    else:
        dparam, date_str = date_str, f"{dparam[:4]}-{dparam[4:6]}-{dparam[6:]}"
    r = requests.get(f"{ESPN_SCOREBOARD}?dates={dparam}", timeout=30)
    r.raise_for_status()
    return date_str, r.json()

def _fetch_boxscore(game_id):
    import requests
    r = requests.get(f"{ESPN_SUMMARY}?event={game_id}", timeout=30)
    r.raise_for_status()
    return r.json()

def _extract_players_fallback(boxscore, team_side):
    """Extract from live ESPN boxscore — fallback only."""
    players = []
    competitors = (boxscore.get("header", {}).get("competitions", [{}])[0].get("competitors", []))
    target = next((c.get("team", {}).get("displayName", "") for c in competitors if c.get("homeAway") == team_side), "Unknown")
    if target == "Unknown":
        return [], target
    for team_entry in boxscore.get("boxscore", {}).get("players", []):
        if team_entry.get("team", {}).get("displayName", "") != target:
            continue
        for cat in team_entry.get("statistics", []):
            stat_names = cat.get("names", [])
            for athlete in cat.get("athletes", []):
                athlete_data = athlete.get("athlete", {})
                stats_raw = athlete.get("stats", [])
                projs = [
                    {"stat": ESPN_TO_TC_STAT.get(stat_names[i], stat_names[i]),
                     "projection": float(val) if val not in (None, "", "-") else 0.0,
                     "line": (float(val) - 0.5 if val not in (None, "", "-") else -0.5),
                     "edge": 0.5, "period": "GAME"}
                    for i, val in enumerate(stats_raw)
                    if i < len(stat_names) and ESPN_TO_TC_STAT.get(stat_names[i], stat_names[i]) in WNBA_STATS
                ]
                if projs:
                    players.append({
                        "player": athlete_data.get("displayName", "Unknown"),
                        "team": target, "starter": athlete.get("starter", False),
                        "did_not_play": athlete.get("didNotPlay", False),
                        "status": "Active" if not athlete.get("didNotPlay") else "DNP",
                        "projections": projs
                    })
        break
    return players, target

# ── main ──────────────────────────────────────────────────────
def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    date_str, scoreboard = _fetch_scoreboard(date_str)
    events = scoreboard.get("events", [])
    if not events:
        logger.info(f"No WNBA games on {date_str}")
        return

    date_dir = os.path.join(DAILY_LOG, date_str)
    os.makedirs(date_dir, exist_ok=True)
    all_players, per_game_files = [], []

    for event in events:
        game_id = event["id"]
        comps = event.get("competitions", [{}])[0].get("competitors", [])
        away_abbr = home_abbr = ""
        for c in comps:
            abbr = c.get("team", {}).get("abbreviation", "")
            if c.get("homeAway") == "away": away_abbr = abbr
            else: home_abbr = abbr
        matchup = f"{away_abbr}_at_{home_abbr}"

        # Is this an All-Star game?
        is_allstar = away_abbr in ALLSTAR_ABBR and home_abbr in ALLSTAR_ABBR
        
        # Try to load rosters for this matchup
        away_roster, home_roster = [], []
        if is_allstar:
            away_roster = [{"name": n} for n in ALLSTAR_ROSTERS.get(away_abbr, [])]
            home_roster = [{"name": n} for n in ALLSTAR_ROSTERS.get(home_abbr, [])]
            logger.info(f"  All-Star detected: {len(away_roster)} {away_abbr} + {len(home_roster)} {home_abbr}")
        else:
            try:
                with open(ROSTERS_PATH) as f:
                    rosters = json.load(f)
                for team_abbr, team_data in rosters.items():
                    if team_abbr == away_abbr:
                        away_roster = team_data.get("players", [])
                    elif team_abbr == home_abbr:
                        home_roster = team_data.get("players", [])
            except Exception:
                pass

        def make_projs_from_season(roster):
            out = []
            for p in roster:
                proj = project_player(p["name"])
                if not proj:
                    continue
                projs = [build_projection(p, k, v) for k, v in proj.items() if v > 0]
                out.append({
                    "player": p["name"], "team": away_abbr if roster is away_roster else home_abbr,
                    "projections": projs, "status": "Active", "source": "season_avg"
                })
            return out

        away_players = make_projs_from_season(away_roster)
        home_players = make_projs_from_season(home_roster)

        # Fallback: try live ESPN if season misses too many players
        if len(away_players) < 3 or len(home_players) < 3:
            logger.info(f"  {matchup}: season coverage low (A:{len(away_players)} H:{len(home_players)}), falling back to ESPN")
            try:
                box = _fetch_boxscore(game_id)
                away_players, away_team = _extract_players_fallback(box, "away")
                home_players, home_team = _extract_players_fallback(box, "home")
            except Exception as e:
                logger.warning(f"  ESPN fallback failed: {e}")

        if not away_players and not home_players:
            logger.warning(f"  {matchup}: no players, skipping")
            continue

        logger.info(f"  {matchup}: {len(away_players)} away + {len(home_players)} home")

        game_proj = {
            "away": {"all": {"players": away_players}},
            "home": {"all": {"players": home_players}}
        }
        game_proj = apply_wnba_augmentation(game_proj)
        out_path = os.path.join(date_dir, f"proj_WNBA_{matchup}.json")
        with open(out_path, "w") as f:
            json.dump(game_proj, f, indent=2)
        per_game_files.append(out_path)

        for p in away_players:
            p["matchup"] = matchup
            all_players.append(p)
        for p in home_players:
            p["matchup"] = matchup
            all_players.append(p)

    combined_path = os.path.join(date_dir, "proj_WNBA_.json")
    with open(combined_path, "w") as f:
        json.dump({"date": date_str, "sport": "WNBA", "per_game_files": per_game_files, "players": all_players}, f, indent=2)
    logger.info(f"✅ {combined_path} — {len(all_players)} players")

if __name__ == "__main__":
    main()
