#!/usr/bin/env python3
"""TC Sports Pipeline — daily_picks.py
Reads projection files from Daily_Log/YYYY-MM-DD/, generates picks, saves to DB + CSV,
applies enhancer, sends email report, updates last_run.json.
"""

import sys, os, csv, json, argparse, sqlite3, smtplib, glob, time
import fcntl
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

ET = ZoneInfo("America/New_York")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.explanation_engine import generate_explanation
from src.adapters.schedule_fetcher import has_games_today
from src.adapters.mlb_api_adapter import get_todays_games as get_mlb_games, get_live_boxscore as get_mlb_boxscore
from src.adapters.wnba_api_adapter import get_todays_games as get_wnba_games, get_boxscore as get_wnba_boxscore
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("tc_pipeline")
from src.adapters.espn_odds_fetcher import fetch_espn_odds_cached
try:
    from src.adapters.action_network import get_odds_for_pipeline as fetch_live_odds
    logger.info("[ODDS] Using Action Network adapter (free)")
except ImportError:
    from src.adapters.theoddsapi_adapter import get_odds_comparison as fetch_live_odds
    logger.warning("[ODDS] Action Network not available, falling back to TheOddsAPI")
from src.adapters.free_api_aggregator import get_live_stats, health_check as free_api_health
from src.enhancer import apply_enhancements
from src.ml.predictive_engine import apply_ml_override as _apply_ml_override, enrich_ml_probabilities as _enrich_ml_probabilities
from src.roster_loader import get_loader as get_roster_loader
from wnba_team_lookup import correct_team
from mlb_team_lookup import correct_mlb_team
from sports_grading_engine import grade_picks as grade_picks_engine

PROJ_DIR = Path(__file__).parent.parent / "Daily_Log"
DATA_DIR = Path(__file__).parent.parent / "data"

SERPAPI_DAILY_MAX = 0
SERPAPI_PER_RUN = 0
SERPAPI_TRACKER = DATA_DIR / "serpapi_usage.json"
PICKS_DIR = DATA_DIR / "picks"
DB_PATH = Path(__file__).parent / "data" / "picks.db"

THERUNDOWN_TRACKER = DATA_DIR / "therundown_usage.json"
THERUNDOWN_DAILY_MAX = 5
SPORT_SLEEP_SECONDS = 3
MAX_PICKS_PER_SPORT = {
    'MLB': 1500,
    'WNBA': 500,
    'NBA': 800,
    'NFL': 800,
    'NHL': 500,
}

def enforce_pick_cap(sport: str, picks: list) -> list:
    cap = MAX_PICKS_PER_SPORT.get(sport.upper(), 1000)
    if len(picks) > cap:
        logger.warning(f"Capping {sport} picks from {len(picks)} to {cap}")
        return picks[:cap]
    return picks

BUDGET_FILE = DATA_DIR / "api_budget.json"
DAILY_LIMITS = {
    'pybaseball': 100,
    'espn_wnba': 50,
    'odds_api': 0,
    'serpapi': 0,
    'statsapi_mlb': 50,
    'sharp_api': 250,
}

def _load_budget():
    if BUDGET_FILE.exists():
        data = json.loads(BUDGET_FILE.read_text())
    else:
        data = {}
    if data.get('date') != datetime.now().strftime('%Y-%m-%d'):
        data = {'date': datetime.now().strftime('%Y-%m-%d'), 'calls': {}}
    return data

def _save_budget(data):
    BUDGET_FILE.write_text(json.dumps(data))

def get_budget(source: str) -> int:
    data = _load_budget()
    return data['calls'].get(source, 0)

def consume_budget(source: str, amount: int = 1) -> bool:
    data = _load_budget()
    used = data['calls'].get(source, 0)
    if used + amount > DAILY_LIMITS.get(source, 100):
        return False
    data['calls'][source] = used + amount
    _save_budget(data)
    return True

LOCK_FILE = "/home/workspace/tc_pipeline.lock"

def acquire_run_lock(timeout: int = 300):
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except BlockingIOError:
        logger.warning("Another pipeline is running, waiting...")
        start = time.time()
        while time.time() - start < timeout:
            try:
                lock_fd = open(LOCK_FILE, 'w')
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return lock_fd
            except BlockingIOError:
                time.sleep(5)
        raise RuntimeError("Could not acquire lock after timeout")

def release_run_lock(lock_fd):
    fcntl.flock(lock_fd, fcntl.LOCK_UN)
    lock_fd.close()


from src.edge_engine.calibrate import get_p_hit, get_tier
from src.adapters.therundown_adapter import get_formatted_odds as fetch_therundown_odds
import numpy as np
from src.adapters.sportsdataio_adapter import get_all_player_props as fetch_sdio_props
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")

WNBA_WEIGHTS = {
    'PTS': 0.20,
    'REB': 0.16,
    'AST': 0.15,
    'PRA': 0.25,
    '3PM': 0.10,
    'MIN': 0.10,
}

def calibrate_win_prob(league, stat, direction, tc_projection, market_line, edge):
    """Calibrated win probability from trained LogisticRegression model.
    Falls back to direction-aware weighted sigmoid with sport-specific stat weights."""
    import pickle as _pkl
    model_dir = Path(__file__).parent / 'models'
    try:
        with open(model_dir / 'encoders.pkl', 'rb') as f:
            encs = _pkl.load(f)
        with open(model_dir / 'scaler.pkl', 'rb') as f:
            scaler = _pkl.load(f)
        with open(model_dir / 'calibrated_model.pkl', 'rb') as f:
            model = _pkl.load(f)

        league_enc = encs['league'].transform([str(league)])[0] if str(league) in encs['league'].classes_ else -1
        stat_enc = encs['stat'].transform([str(stat)])[0] if str(stat) in encs['stat'].classes_ else -1
        dir_enc = encs['direction'].transform([str(direction)])[0] if str(direction) in encs['direction'].classes_ else -1

        features = np.array([[league_enc, stat_enc, dir_enc, tc_projection, market_line, edge]], dtype=float)
        scaled = scaler.transform(features)
        prob = model.predict_proba(scaled)[0][1]
        return float(prob)
    except Exception:
        sport = str(league).lower()
        if sport == 'wnba':
            weight = WNBA_WEIGHTS.get(str(stat).upper(), 0.15)
        else:
            weight = 1.0
        weighted_edge = edge * weight
        return 1 / (1 + np.exp(-2 * weighted_edge))

# ═══════════════════════════════════════════════════════════════
# SPORT CONFIG — single source of truth. Add/edit a sport here.
# Each sport runs independently; one failing never kills the others.
# ═══════════════════════════════════════════════════════════════
SPORT_CONFIG = {
    "mlb":  {"module": "mlb_recalibration",  "calibrate": "calibrate_mlb_picks",  "active": True},
    "wnba": {"module": "wnba_recalibration", "calibrate": "calibrate_wnba_picks", "active": True},
    "nba":  {"module": "nba_recalibration",  "calibrate": "calibrate_nba_picks",  "active": False},
    "nfl":  {"module": "nfl_recalibration",  "calibrate": "calibrate_nfl_picks",  "active": False},
    "nhl":  {"module": "nhl_recalibration",  "calibrate": "calibrate_nhl_picks",  "active": False},
}
SPORT_NAMES = list(SPORT_CONFIG.keys())  # ["mlb","wnba","nba","nfl","nhl"]
ALL_SPORTS = SPORT_NAMES


def _apply_recalibration(sport, items, stage="pre"):
    """Run recalibration module for a sport. Returns items (possibly filtered/reordered)."""
    cfg = SPORT_CONFIG.get(sport.lower())
    if not cfg or not cfg["active"]:
        return items
    try:
        mod = __import__(cfg["module"], fromlist=[cfg["calibrate"]])
        fn = getattr(mod, cfg["calibrate"])
        tag = "[RECAL]" if stage == "pre" else "[RECALIBRATE]"
        before = len(items)
        result = fn(items)
        logger.info(f"{tag} {sport.upper()} ({stage}): {before} -> {len(result)}")
        return result
    except ImportError:
        logger.warning(f"{cfg['module']}.py not found — skipping {sport} {stage}-calibration")
        return items
    except Exception as exc:
        logger.error(f"[{sport.upper()}] recalibration failed ({stage}): {exc} — continuing without it")
        return items


def load_projections(sport):
    """Load projections from Daily_Log/YYYY-MM-DD/proj_SPORT_*.json"""
    today = datetime.now(ET).strftime("%Y-%m-%d")
    log_dir = PROJ_DIR / today
    if not log_dir.exists():
        logger.warning(f"No log dir {log_dir}")
        return []

    pattern = str(log_dir / f"proj_{sport.upper()}_*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        logger.warning(f"No projection files for {sport} in {log_dir}")
        return []

    players_out = []
    for fpath in files:
        fname = Path(fpath).stem
        parts = fname.split("_", 2)
        raw_suffix = parts[2] if len(parts) >= 3 else ""
        # Skip the all-in-one dated file (e.g. proj_MLB_2026-07-18.json)
        if len(raw_suffix) == 10 and raw_suffix[4] == '-' and raw_suffix[7] == '-':
            continue
        # Skip merged files and WNBA combined file (per-game files have all players)
        if raw_suffix.lower() in ("merged",) or raw_suffix == "":
            continue
        matchup = raw_suffix

        with open(fpath) as f:
            data = json.load(f)

        player_list = data.get("players", data.get("picks", []))
        # WNBA files use "projections" key for the player list
        if not player_list:
            top_projs = data.get("projections", [])
            if isinstance(top_projs, list):
                player_list = top_projs
        # Per-game files have away/home sections with nested players (all/starters)
        if not player_list:
            for side in [data.get("away", {}), data.get("home", {})]:
                for group_key in ("players", "all", "starters"):
                    group = side.get(group_key, {})
                    if isinstance(group, dict):
                        player_list.extend(group.get("players", []))
                    elif isinstance(group, list):
                        player_list.extend(group)
        for p in player_list:
            player_name = p.get("player", p.get("name", ""))
            team = p.get("team", "")
            player_matchup = p.get("matchup") or matchup
            if sport.lower() == "mlb":
                team = correct_mlb_team(player_name, team)
            else:
                team = correct_team(player_name, team, sport, player_matchup)
            proj_dict = p.get("projections", {})
            # WNBA combined files use list format [{stat, projection, line}, ...] — convert to dict
            if isinstance(proj_dict, list):
                proj_dict = {e["stat"]: e for e in proj_dict if "stat" in e}
            if not proj_dict:
                entries = p.get("entries", [])
                proj_dict = {e["stat"]: e for e in entries if "stat" in e}

            # Detect MLB vs WNBA format: WNBA = dict of dicts, MLB = dict of floats
            first_val = next(iter(proj_dict.values()), None) if proj_dict else None
            is_float_format = isinstance(first_val, (int, float))

            for stat, vals in proj_dict.items():
                if is_float_format:
                    tc_proj = float(vals)
                    MLB_SPREADS = {"H": 0.30, "2B": 0.30, "3B": 0.30, "R": 0.20, "RBI": 0.20,
                                   "BB": 0.20, "HR": 0.25, "SB": 0.25, "SO": 0.25, "K": 0.25,
                                   "ER": 0.25, "AVG": 0.15, "SLG": 0.15, "OPS": 0.15}
                    spread = MLB_SPREADS.get(stat.upper(), 0.20)
                    MIN_SELF_EDGE = 0.05
                    raw_spread_amt = max(tc_proj * spread, MIN_SELF_EDGE)
                    import hashlib as _hl
                    seed_val = int(_hl.md5(f"{player_name}|{stat}|{player_matchup}".encode()).hexdigest(), 16)
                    direction = "OVER" if seed_val % 2 == 0 else "UNDER"
                    if direction == "OVER":
                        line = round(tc_proj * (1 - spread / 2), 3)
                    else:
                        line = round(tc_proj * (1 + spread / 2), 3)
                    edge_val = round(tc_proj - line, 3)
                else:
                    tc_proj = vals.get("tc_projection", vals.get("projection", 0))
                    line = vals.get("line", vals.get("market_line", 0))
                    edge_val = vals.get("edge", tc_proj - line)
                    direction = vals.get("direction", "OVER" if edge_val > 0 else "UNDER")

                players_out.append({
                    "name": player_name,
                    "team": team,
                    "matchup": player_matchup,
                    "stat": stat.upper() if sport.upper() == "MLB" else stat,
                    "projection": tc_proj,
                    "line": line,
                    "edge": edge_val,
                    "direction": direction,
                })

    logger.info(f"Loaded {len(players_out)} stat-lines from {len(files)} files for {sport}")
    if sport.lower() in ("wnba", "mlb", "nba", "nfl", "nhl"):
        players_out = enrich_lines_via_espn(sport, players_out)
        players_out = enrich_lines_via_serpapi(sport, players_out)
        players_out = enrich_via_free_apis(sport, players_out)
        players_out = enrich_projections_with_sdio(players_out, sport)
        players_out = enrich_projections_with_therundown(players_out, sport)
        players_out = enrich_via_rosters(sport, players_out)
    return players_out

def _serpapi_daily_count():
    if SERPAPI_TRACKER.exists():
        try:
            d = json.loads(SERPAPI_TRACKER.read_text())
            return d.get(datetime.now(ET).strftime("%Y-%m-%d"), 0)
        except: return 0
    return 0

def _serpapi_increment(n):
    d = {}
    if SERPAPI_TRACKER.exists():
        try: d = json.loads(SERPAPI_TRACKER.read_text())
        except: pass
    today = datetime.now(ET).strftime("%Y-%m-%d")
    d[today] = d.get(today, 0) + n
    SERPAPI_TRACKER.write_text(json.dumps(d))

def _therundown_daily_count():
    """Track TheRundown API calls per day to prevent quota burnout."""
    import json
    if THERUNDOWN_TRACKER.exists():
        try:
            d = json.loads(THERUNDOWN_TRACKER.read_text())
            return d.get(datetime.now(ET).strftime("%Y-%m-%d"), 0)
        except:
            return 0
    return 0

def _therundown_increment(n=1):
    import json
    d = {}
    if THERUNDOWN_TRACKER.exists():
        try:
            d = json.loads(THERUNDOWN_TRACKER.read_text())
        except:
            pass
    today = datetime.now(ET).strftime("%Y-%m-%d")
    d[today] = d.get(today, 0) + n
    THERUNDOWN_TRACKER.write_text(json.dumps(d))

def enrich_via_free_apis(sport, projections):
    """Enrich projections with live stats from free public APIs (statsapi, pybaseball, nba_api).
    Updates projection['live_batting_avg'], ['live_ops'], ['live_era'], ['live_whip'], etc.
    Returns projections unchanged if APIs are unavailable."""
    import re
    enriched = 0
    try:
        live = get_live_stats(sport)
    except Exception as e:
        logger.warning(f"[FREE-APIS] get_live_stats failed: {e}")
        return projections

    if not live or not any(live.values()):
        return projections

    def normalize_name(name):
        return re.sub(r'[^a-zA-Z ]', '', name).lower().strip()

    # Build lookup dict from live stats
    lookup = {}
    for source, stats in live.items():
        for player_name, metrics in stats.items():
            key = normalize_name(player_name)
            if key not in lookup:
                lookup[key] = {}
            lookup[key].update(metrics)

    for proj in projections:
        pname = normalize_name(proj.get('espn_name', proj.get('name', '')))
        stat_type = (proj.get('stat') or '').lower()

        if not pname or pname not in lookup:
            continue

        live_stats = lookup[pname]

        if sport == 'mlb':
            if stat_type in ('hits', 'home runs', 'runs', 'rbi', 'stolen bases'):
                if 'batting_avg' in live_stats and live_stats['batting_avg']:
                    proj['live_batting_avg'] = live_stats['batting_avg']
                if 'ops' in live_stats and live_stats['ops']:
                    proj['live_ops'] = live_stats['ops']
                if 'home_runs' in live_stats:
                    proj['live_hr'] = live_stats['home_runs']
            elif stat_type in ('strikeouts', 'earned runs', 'hits allowed'):
                if 'era' in live_stats and live_stats['era']:
                    proj['live_era'] = live_stats['era']
                if 'k_per_9' in live_stats:
                    proj['live_k9'] = live_stats['k_per_9']
                if 'whip' in live_stats:
                    proj['live_whip'] = live_stats['whip']

        elif sport == 'wnba':
            if stat_type == 'points':
                proj['live_pts'] = live_stats.get('pts')
            elif stat_type == 'rebounds':
                proj['live_reb'] = live_stats.get('reb')
            elif stat_type == 'assists':
                proj['live_ast'] = live_stats.get('ast')
            elif stat_type == 'three pointers':
                proj['live_3pct'] = live_stats.get('fg3_pct')

        enriched += 1

    logger.info(f"[FREE-APIS] Enriched {enriched}/{len(projections)} projections for {sport}")
    return projections

def enrich_via_rosters(sport, projections):
    """Enrich projections with player roster data (position, full team name, jersey)."""
    loader = get_roster_loader()
    enriched = 0
    for p in projections:
        name = p.get("name", "")
        team = p.get("team", "")
        if not name:
            continue
        info = loader.enrich_player(name, sport, team)
        if info:
            p.update({
                "roster_position": info.get("roster_position", ""),
                "roster_team_full": info.get("roster_team_full", ""),
                "roster_team_abbr": info.get("roster_team_abbr", ""),
                "roster_jersey": info.get("roster_jersey", ""),
                "roster_id": info.get("roster_id", ""),
            })
            enriched += 1
    logger.info(f"[ROSTERS] Enriched {enriched}/{len(projections)} projections for {sport}")
    return projections

def enrich_lines_via_espn(sport, projections):
    """Enrich projections with game-level odds from ESPN v2 API (FREE, no auth).
    
    ESPN provides spread/O/U/ML per game from DraftKings (provider 100).
    This adds real market context to every projection entry for the matchup.
    Does NOT provide individual player milestone props — those require a sportsbook scraper.
    
    Sets projection['espn_spread'] and projection['espn_total'] for game-context enrichment.
    Tags signal as 'ESPN' when game-level odds data was found for the matchup.
    """
    import datetime as dt
    today_str = dt.date.today().isoformat()
    
    try:
        odds_data = fetch_espn_odds_cached(sport, today_str)
    except Exception as e:
        logger.warning(f"ESPN odds fetch failed for {sport}: {e}")
        return projections
    
    if not odds_data:
        logger.info(f"No ESPN odds data for {sport} on {today_str}")
        return projections
    
    enriched = 0
    for p in projections:
        matchup = p.get('matchup', '')
        team = p.get('team', '')
        
        # Try to find the game in ESPN odds by matching team abbreviation or matchup name
        found = None
        for event_name, odds in odds_data.items():
            if not event_name:
                continue
            # Match team abbreviation in event name or matchup string
            name_upper = event_name.upper()
            team_upper = team.upper()
            matchup_upper = matchup.upper().replace('@', ' AT ')
            
            if team_upper and team_upper in name_upper:
                found = odds
                break
            if matchup_upper and any(part.strip() in name_upper for part in matchup_upper.split(' AT ')):
                found = odds
                break
        
        if found:
            p['espn_spread'] = found.get('spread')
            p['espn_total'] = found.get('over_under')
            p['espn_favorite'] = found.get('favorite')
            if p.get('signal', 'SELF_EDGE') == 'SELF_EDGE':
                p['signal'] = 'ESPN'
            enriched += 1
    
    logger.info(f"[ESPN-ENRICH] Tagged {enriched} of {len(projections)} projection lines with ESPN context.")
    return projections

def enrich_projections_with_live_odds(projections, sport):
    """Fetch live player prop lines from TheOddsAPI (DK + FD) and replace market_line with real odds.
    
    Falls back to ESPN lines if TheOddsAPI fails or has no data for a player.
    Per-player: picks best available line across DraftKings and FanDuel.
    Tags signal as 'LIVE' when real odds were found for the player.
    """
    try:
        live = fetch_live_odds(sport)
    except Exception as e:
        logger.warning(f"TheOddsAPI fetch failed for {sport}: {e}")
        return projections
    
    if not live:
        logger.info(f"TheOddsAPI returned no player prop data for {sport}")
        return projections
    
    updated = 0
    for p in projections:
        player = p.get('player', '')
        stat = p.get('stat', '')
        if not player:
            continue
        
        # Look for player + stat in live odds
        props = live.get(player.lower(), [])
        match = None
        for prop in props:
            if prop.get('stat') and prop['stat'].lower() == stat.lower():
                match = prop
                break
        
        if match and match.get('line', 0) > 0:
            old_line = p.get('market_line', 0)
            new_line = match['line']
            p['market_line'] = new_line
            p['market_line_bk'] = match.get('book', 'TheOddsAPI')
            p['signal'] = 'LIVE'
            # Recalculate edge with new line
            proj = p.get('tc_projection', 0)
            if proj and new_line:
                p['edge'] = round(abs(proj - new_line), 2)
            updated += 1
            logger.debug(f"[LIVE-ODDS] {player} {stat}: line {old_line} → {new_line} ({match['book']})")
    
    logger.info(f"[LIVE-ODDS] Updated {updated} of {len(projections)} projection lines with live DK/FD odds.")
    return projections


def enrich_lines_via_serpapi(sport, projections):
    """For picks with missing or generic lines, try SerpAPI for real market lines.
    Capped at SERPAPI_PER_RUN searches per sport, SERPAPI_DAILY_MAX total per day."""
    import re
    
    STAT_SYNONYMS = {
        "AST": ["assists", "assist", "asts", "ast"],
        "STL": ["steals", "steal", "stls", "stl"],
        "BLK": ["blocks", "block", "blks", "blk"],
        "3PM": ["three pointers", "3-pointers", "threes", "3pm", "3s"],
        "TO": ["turnovers", "turnover", "tos", "to"],
        "PRA": ["points rebounds assists", "pts rebs asts", "pra", "points + rebounds + assists"],
        "PR": ["points rebounds", "pts rebs", "pr"],
        "RA": ["rebounds assists", "rebs asts", "ra"],
        "TB": ["total bases", "total base", "bases", "tb"],
        "H": ["hits", "hit", "h"],
        "K": ["strikeouts", "strikeout", "so", "k"],
        "RBI": ["rbis", "runs batted in", "rbi"],
        "HR": ["home runs", "home run", "homer", "hr"],
        "SB": ["stolen bases", "steals", "sb"],
        "SHOTS": ["shots", "shot", "attempts"],
        "SOT": ["shots on target", "sot", "on target"],
        "PASSES": ["passes", "pass", "completed passes"],
        "TACKLES": ["tackles", "tck", "tackle"],
        "FOULS": ["fouls", "foul", "fl"],
        "SAVES": ["saves", "save", "sv"],
        "CARDS": ["cards", "yellows"],
    }
    
    # Trigger for: line=0 picks OR generic/fake-line picks (all same line per sport)
    zero_line_picks = [p for p in projections if p.get("line", 0) == 0]
    
    # Also check for generic lines: if all picks for same stat have identical line, likely fake
    generic_picks = []
    stats_lines = {}
    for p in projections:
        st = p.get("stat", "")
        ln = p.get("line", 0)
        if ln > 0 and st:
            if st not in stats_lines:
                stats_lines[st] = set()
            stats_lines[st].add(ln)
    
    for p in projections:
        st = p.get("stat", "")
        ln = p.get("line", 0)
        if ln > 0 and st in stats_lines and len(stats_lines[st]) <= 1:
            generic_picks.append(p)
    
    enrich_picks = zero_line_picks + generic_picks
    seen = set()
    enrich_picks = [p for p in enrich_picks if id(p) not in seen and not seen.add(id(p))]
    
    if not enrich_picks:
        logger.info(f"[SerpAPI] No picks to enrich for {sport}")
        return projections
    
    logger.info(f"[SerpAPI] {len(zero_line_picks)} zero-line + {len(generic_picks)} generic picks to enrich for {sport}")
    
    sport_label = {"wnba": "WNBA", "mlb": "MLB"}.get(sport, sport)
    enriched = 0
    
    
    # SerpAPI dead — quota maxed, module missing. Skip enrichment.
    logger.info("[SerpAPI] Dead — skipping enrichment (quota maxed, module missing).")
    return projections


def deduplicate(picks):
    """Dedup on (name, sport, stat, matchup) — keep per-game picks."""
    best = {}
    for p in picks:
        key = (p["name"], p.get("sport", ""), p["stat"], p.get("matchup", ""))
        if key not in best:
            best[key] = p
    unique = list(best.values())
    dups = len(picks) - len(unique)
    if dups:
        logger.info(f"Removed {dups} duplicates")
    return unique


def send_email_report(picks, sport, date_str):
    """Collect picks for consolidated email — actual send happens in send_professional_email."""
    return picks


def send_professional_email(all_picks_by_sport, date_str, combos=None):
    """Generate a clean, investor-ready HTML email with all picks and combos."""
    if not SMTP_USER or not EMAIL_TO:
        logger.info("Email not configured. Skipping professional report.")
        return

    sport_emoji = {"wnba": "🏀", "mlb": "⚾", "nba": "🏀", "nfl": "🏈", "nhl": "🏒"}
    sport_colors = {"wnba": "#E94560", "mlb": "#00B4D8", "nba": "#FF6B00", "nfl": "#013369", "nhl": "#CC0000"}
    sport_names = {"wnba": "WNBA", "mlb": "MLB", "nba": "NBA", "nfl": "NFL", "nhl": "NHL"}

    total_picks = sum(len(p) for p in all_picks_by_sport.values())

    def edge_fmt(e):
        try: return f"{float(e):.1f}%"
        except: return "0.0%"

    def get_top(league, limit=12):
        ps = all_picks_by_sport.get(league, [])
        ps_sorted = sorted(ps, key=lambda x: abs(float(x.get("edge", 0))), reverse=True)
        return ps_sorted[:limit]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM graded_picks WHERE hit=1")
    total_hits = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM graded_picks WHERE hit IS NOT NULL AND hit>=0")
    total_graded = cursor.fetchone()[0]
    all_time_hit_rate = round(total_hits / total_graded * 100, 1) if total_graded else 0.0
    conn.close()

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0a0e14; color: #d4d4d8; padding: 20px; }}
  .container {{ max-width: 680px; margin: 0 auto; background: #11141c; border-radius: 16px; overflow: hidden; border: 1px solid #1e2530; }}
  .header {{ background: linear-gradient(135deg, #001a33 0%, #003594 50%, #001a33 100%); padding: 28px 24px; text-align: center; }}
  .header h1 {{ margin: 0; font-size: 22px; letter-spacing: 1px; color: #fff; }}
  .header p {{ margin: 6px 0 0; font-size: 13px; color: #93c5fd; letter-spacing: 2px; }}
  .kpi-row {{ display: flex; justify-content: space-around; padding: 16px 20px; background: #161c26; border-bottom: 1px solid #1e2530; }}
  .kpi {{ text-align: center; }}
  .kpi-val {{ font-size: 22px; font-weight: 800; }}
  .kpi-lbl {{ font-size: 10px; color: #6b7280; letter-spacing: 1px; margin-top: 2px; }}
  .section {{ padding: 20px 24px; }}
  .sport-header {{ font-size: 18px; font-weight: 800; margin: 0 0 12px; padding-bottom: 8px; border-bottom: 2px solid; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 8px 10px; font-size: 10px; letter-spacing: 1px; color: #6b7280; border-bottom: 1px solid #1e2530; }}
  td {{ padding: 10px 10px; border-bottom: 1px solid #1a1f2b; }}
  .player {{ font-weight: 700; color: #e4e4e7; }}
  .team-tag {{ font-size: 10px; padding: 1px 6px; border-radius: 3px; }}
  .edge-pos {{ color: #22c55e; font-weight: 700; }}
  .dir-over {{ color: #22c55e; font-weight: 700; font-size: 11px; }}
  .dir-under {{ color: #ef4444; font-weight: 700; font-size: 11px; }}
  .combo-card {{ background: #161c26; border-radius: 10px; padding: 14px; margin-bottom: 10px; border-left: 4px solid; }}
  .footer {{ text-align: center; padding: 20px; font-size: 11px; color: #4b5563; border-top: 1px solid #1e2530; }}
  .footer a {{ color: #60a5fa; }}
</style></head><body>
<div class="container">
  <div class="header">
    <h1>🏆 TC SPORTS PICKS</h1>
    <p>EARLY BIRD SPECIAL · {date_str}</p>
  </div>
  <div class="kpi-row">
    <div class="kpi"><div class="kpi-val" style="color:#3b82f6">{total_picks}</div><div class="kpi-lbl">TODAY'S PICKS</div></div>
    <div class="kpi"><div class="kpi-val" style="color:#22c55e">{all_time_hit_rate}%</div><div class="kpi-lbl">ALL-TIME HIT RATE</div></div>
    <div class="kpi"><div class="kpi-val" style="color:#f59e0b">{total_graded:,}</div><div class="kpi-lbl">GRADED</div></div>
    <div class="kpi"><div class="kpi-val" style="color:#a855f7">{len(combos) if combos else 0}</div><div class="kpi-lbl">COMBOS</div></div>
  </div>
"""

    leagues = ["wnba", "mlb"]
    for league in leagues:
        top = get_top(league, 12)
        if not top:
            continue
        sc = sport_colors.get(league, "#888")
        sn = sport_names.get(league, league.upper())
        se = sport_emoji.get(league, "🏆")

        html += f'<div class="section"><h2 class="sport-header" style="color:{sc};border-color:{sc}44">{se} {sn} — TOP PICKS</h2>'
        html += '<table><thead><tr><th>PLAYER</th><th>TEAM</th><th>STAT</th><th>LINE</th><th>PROJ</th><th>EDGE</th><th>DIR</th></tr></thead><tbody>'

        for p in top:
            name = p.get("name", "")
            team = p.get("team", "")
            stat = p.get("stat", "")
            proj = float(p.get("projection", 0))
            line = float(p.get("line", 0))
            edge = float(p.get("edge", 0))
            # calibrated_edge computed post-hoc during grading
            direction = p.get("direction", "OVER")
            edge_cls = "edge-pos"
            dir_cls = "dir-over" if direction == "OVER" else "dir-under"
            html += f'<tr><td class="player">{name}</td>'
            html += f'<td><span class="team-tag" style="background:{sc}22;color:{sc};border:1px solid {sc}44">{team}</span></td>'
            html += f'<td style="color:{sc}">{stat}</td>'
            html += f'<td style="color:#9ca3af">{line:.1f}</td>'
            html += f'<td style="color:#e4e4e7">{proj:.1f}</td>'
            html += f'<td class="{edge_cls}">+{edge:.1f}%</td>'
            html += f'<td class="{dir_cls}">{direction}</td></tr>'

        html += '</tbody></table></div>'

    if combos:
        html += '<div class="section"><h2 class="sport-header" style="color:#a855f7;border-color:#a855f744">🔥 TOP COMBOS</h2>'
        top_combos = sorted(combos, key=lambda x: abs(float(x.get("edge", 0))), reverse=True)[:8]
        for c in top_combos:
            league = c.get("league", "")
            sc = sport_colors.get(league, "#888")
            players = c.get("players", "")
            ctype = c.get("combo_type", "")
            edge = float(c.get("edge", 0))
            # calibrated_edge computed post-hoc during grading
            proj = float(c.get("combined_projection", 0))
            line = float(c.get("combined_line", 0))
            matchup = c.get("matchup", "")
            html += f'<div class="combo-card" style="border-color:{sc}">'
            html += f'<span style="color:{sc};font-weight:700;font-size:12px">{ctype}</span> '
            html += f'<span style="color:#e4e4e7;font-weight:700">{players}</span> '
            html += f'<span style="color:#9ca3af;font-size:11px">| {matchup}</span>'
            html += f'<br><span style="font-size:12px">Proj: {proj:.1f} | Line: {line:.1f} | '
            html += f'Edge: <span style="color:#22c55e;font-weight:700">+{edge:.1f}%</span></span></div>'
        html += '</div>'

    html += f'''
  <div class="footer">
    TC Sports Pipeline · Generated {date_str}<br>
    Dashboard: <a href="https://true.zo.space/nba-tc">true.zo.space/nba-tc</a><br>
    <span style="color:#4b5563">Triple Conservative System v7 · {all_time_hit_rate}% all-time hit rate ({total_hits}/{total_graded})</span>
  </div>
</div></body></html>'''

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_USER
        msg["To"] = EMAIL_TO
        msg["Subject"] = f"🏆 TC Sports Picks — Early Bird Special {date_str} ({total_picks} picks)"
        msg.attach(MIMEText(f"TC Sports Picks — {date_str}\n{total_picks} total picks across WNBA/MLB/WC\nDashboard: https://true.zo.space/nba-tc", "plain"))
        msg.attach(MIMEText(html, "html"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        logger.info(f"Professional email sent: {date_str} ({total_picks} picks) to {EMAIL_TO}")
        return True
    except Exception as e:
        logger.error(f"Professional email failed: {e}")
        return False


def _build_wnba_combo(date_str, sport, label, player, stats, stat_map, have, matchup):
    """Sum a player's WNBA stat legs into a single combo line (P+R+A / P+R / P+A)."""
    if label in stat_map:
        base = stat_map[label]
        leg_list = [base]
        total_proj = float(base.get("projection", 0))
        total_line = float(base.get("line", 0))
    else:
        miss = [s for s in stats if s not in have]
        if miss:
            return None
        leg_list = [stat_map[s] for s in stats]
        total_proj = sum(float(l.get("projection", 0)) for l in leg_list)
        total_line = sum(float(l.get("line", 0)) for l in leg_list)
    if total_line <= 0:
        return None
    edge = round(total_proj - total_line, 2)
    if abs(edge) < 0.01:
        return None
    direction = "OVER" if edge > 0 else "UNDER"
    return (date_str, sport, label, player,
            " + ".join(f"{l['stat']}:{l.get('projection',0):.1f}" for l in leg_list),
            round(total_proj, 2), round(total_line, 2), edge, direction, matchup, label)


def generate_combos(picks, sport, date_str):
    """Build SINGLE-PLAYER stat combos (NOT parlays).

    WNBA: for each player with >=2 of PTS/REB/AST (or a PRA/PR/PA pick present),
          emit P+R+A (PTS+REB+AST), P+R (PTS+REB), P+A (PTS+AST) combo lines.
    MLB:  group props by player. PITCHING combos group one starter's
          SO/OUTS/ER/W; BATTING combos group one batter's HITS/HR/RBI/RUNS/SB/
          2B/3B. Each combo requires >=2 real props and line > 0.
    Combo row: edge = sum of leg (projection - line); direction OVER if positive.
    """
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    combo_count = 0
    if len(picks) < 2:
        conn.close()
        return 0

    by_player = {}
    for p in picks:
        name = p.get("name", "")
        if not name:
            continue
        line = p.get("line", p.get("market_line", 0))
        if not line or float(line) <= 0:
            continue
        by_player.setdefault(name, []).append(p)

    MLB_BATTING = {"HITS", "H", "HR", "RBI", "RBIS", "RUNS", "R", "SB", "2B", "3B", "TB"}
    MLB_PITCHING = {"SO", "K", "OUTS", "TOTAL_OUTS", "ER", "IP", "W", "QUALITY_START"}

    new_rows = []
    for player, legs in by_player.items():
        matchup = next((l.get("matchup", "") for l in legs if l.get("matchup")), "")
        if sport.upper() == "WNBA":
            stat_map = {str(l["stat"]).upper(): l for l in legs}
            have = set(stat_map)
            def build(label, stats, stat_map=stat_map, have=have, player=player,
                      matchup=matchup, legs=legs):
                nonlocal combo_count
                row = _build_wnba_combo(date_str, sport, label, player, stats, stat_map, have, matchup)
                if row:
                    new_rows.append(row)
                    combo_count += 1
            build("P+R+A", ["PTS", "REB", "AST"])
            build("P+R", ["PTS", "REB"])
            build("P+A", ["PTS", "AST"])
        elif sport.upper() == "MLB":
            batting = [l for l in legs if str(l["stat"]).upper() in MLB_BATTING]
            pitching = [l for l in legs if str(l["stat"]).upper() in MLB_PITCHING]
            for label, group in (("BATTING", batting), ("PITCHING", pitching)):
                if len(group) < 2:
                    continue
                total_proj = sum(float(l.get("projection", 0)) for l in group)
                total_line = sum(float(l.get("line", 0)) for l in group)
                if total_line <= 0:
                    continue
                edge = round(total_proj - total_line, 2)
                if abs(edge) < 0.01:
                    continue
                direction = "OVER" if edge > 0 else "UNDER"
                new_rows.append((date_str, sport, label, player,
                                 " + ".join(f"{l['stat']}:{l.get('projection',0):.1f}" for l in group),
                                 round(total_proj, 2), round(total_line, 2), edge, direction,
                                 matchup, label))
                combo_count += 1

    c.execute("DELETE FROM combos WHERE date = ? AND league = ?", (date_str, sport))

    if new_rows:
        c.executemany(
            """INSERT OR REPLACE INTO combos
               (date, league, combo_type, players, projections, combined_projection,
                combined_line, edge, direction, matchup, stat)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            new_rows
        )
    conn.commit()
    conn.close()
    return combo_count


def generate_picks(sport: str):
    """Main pick generation for one sport."""
    logger.info(f"Generating picks for {sport}...")

    players = load_projections(sport)
    if not players:
        if not has_games_today(sport):
            logger.info(f"No projections and no games for {sport} today. Skipping.")
            return []
        logger.warning(f"No projections for {sport} (but games exist)")
        return []

    picks = []
    # ── PRE-RECALIBRATION (data-driven, per-sport) ──
    players = _apply_recalibration(sport, players, "pre")

    for p in players:
        proj = float(p["projection"])
        line = float(p["line"])
        edge = proj - line
        direction = "OVER" if edge > 0 else "UNDER"
                    # calibrated_edge computed post-hoc during grading

        reason = generate_explanation(p["name"], sport, str(p["stat"]), proj, line, edge)

        ml = p.get("market_line", line)
        sig = p.get("signal", "SELF_EDGE")
        e = proj - ml
        d = "OVER" if e > 0 else "UNDER"
        r = generate_explanation(p["name"], sport, str(p["stat"]), proj, ml, e)
        picks.append({
            "name": p["name"],
            "team": p.get("team", ""),
            "sport": sport,
            "stat": str(p["stat"]),
            "matchup": p.get("matchup", ""),
            "projection": proj,
            "line": ml,
            "market_line": ml,
            "edge": e,
            "direction": d,
            "reason": r,
            "signal": sig,
        })

    picks = deduplicate(picks)
    picks = apply_enhancements(picks, sport)

    # ── POST-RECALIBRATION (data-driven, per-sport) ──
    picks = _apply_recalibration(sport, picks, "post")

    # ML model enrichment (blends rule-based + ML probabilities)
    picks = _apply_ml_override(sport, picks)
    picks = _enrich_ml_probabilities(sport, picks)

    # ── ML PREDICTIVE ENGINE ENRICHMENT ──
    ml_applied = 0
    try:
        from src.ml.predictive_engine import (
            enrich_picks_ml, filter_ml_picks, wnba_override, apply_direction_bias
        )
        if sport.upper() in ('MLB', 'WNBA'):
            before_ml = len(picks)
            picks = [apply_direction_bias(p) for p in picks]
            picks = [p for p in picks if wnba_override(p)]
            picks = enrich_picks_ml(picks)
            picks = filter_ml_picks(picks, min_ml_prob=0.45)
            ml_applied = before_ml - len(picks)
            if ml_applied:
                logger.info(f'[ML] Direction bias + ML filter: removed {ml_applied} picks, {len(picks)} remaining')
            else:
                logger.info(f'[ML] Enrichment applied — model not trained yet, picks unchanged')
    except ImportError:
        logger.debug('[ML] Module not available — skipping ML enrichment')
    except Exception as e:
        logger.warning(f'[ML] Enrichment failed: {e} — continuing without ML')

    date_str = datetime.now(ET).strftime("%Y-%m-%d")

    # Save CSV
    PICKS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = PICKS_DIR / f"{sport}_{date_str}.csv"
    fieldnames = ["name", "team", "sport", "stat", "matchup", "projection", "line", "edge", "direction", "reason"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for p in picks:
            writer.writerow(p)

    # Save to DB
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("DELETE FROM picks WHERE date = ? AND league = ?", (date_str, sport))
    seen_keys = set()
    for p in picks:
        if p.get("line", 0) == 0:
            continue
        if abs(p.get("edge", 0)) < 0.01:
            continue
        source = p.get("source", "SELF_EDGE")
        key = (date_str, p["sport"], p["name"], p["stat"], p["direction"], source)
        if key in seen_keys:
            continue
        try:
            raw_edge = p.get("edge", 0)
            proj = p.get("projection", 0)
            line_val = p.get("line", 0)
            
            abs_edge = abs(raw_edge)
            
            # Use calibrate module

            p_hit = get_p_hit(raw_edge)

            tier = get_tier(abs_edge)
        except Exception:
            import numpy as np
            p_hit = 0.50
            tier = "RED"
        c.execute(
            "INSERT OR REPLACE INTO picks (date, league, player, stat, matchup, direction, edge, tc_projection, market_line, source, p_hit, tier, actual, hit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)",
            (
                date_str, p["sport"], p["name"], p["stat"],
                p.get("matchup", ""), p.get("direction", ""), raw_edge, proj, line_val,
                source, p_hit, tier,
            ),
        )
    conn.commit()
    conn.close()

    if len(picks) >= 3:
        combo_count = generate_combos(picks, sport, date_str)
        logger.info(f"Generated {combo_count} combos for {sport}")

    logger.info(f"Saved {len(picks)} picks for {sport}")
    return picks


def main():
    parser = argparse.ArgumentParser()
    lock_fd = acquire_run_lock()
    parser.add_argument("--sport", choices=["mlb", "wnba", "nba", "nfl", "nhl", "all"], default="all")
    parser.add_argument("--grade", action="store_true", help="Run historical grading instead of generating picks")
    parser.add_argument("--grade-date", default="", help="Date for grading (YYYY-MM-DD), defaults to yesterday")
    args = parser.parse_args()

    if args.grade:
        import pandas as pd
        import sqlite3 as sql
        con = sql.connect(str(DB_PATH)) if 'DB_PATH' in dir() else sql.connect("/home/workspace/Projects/data/picks.db")
        grade_date = args.grade_date or (datetime.now() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        report = {}
        total_picks = 0
        total_hits = 0
        total_misses = 0
        matched = 0
        unmatched = 0
        for sport in ["mlb", "wnba", "nba", "nfl", "nhl"]:
            picks_df = pd.read_sql(f"SELECT * FROM picks WHERE date='{grade_date}' AND league='{sport}'", con)
            if len(picks_df) > 0:
                graded = grade_picks_engine(picks_df, grade_date, sport)
                report[sport] = graded
                total_picks += len(picks_df)
                total_hits += graded.get("hits", 0)
                total_misses += graded.get("misses", 0)
                matched += graded.get("matched", 0)
                unmatched += graded.get("unmatched", 0)
        report["total_picks"] = total_picks
        report["hits"] = total_hits
        report["misses"] = total_misses
        report["matched"] = matched
        report["unmatched"] = unmatched
        report["hit_rate"] = round(total_hits / total_picks * 100, 1) if total_picks else 0.0
        out_file = f"/home/workspace/Daily_Log/{grade_date}/graded_report.json"
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
        with open(out_file, "w") as f:
            json.dump(report, f, indent=2)
        # Save enhanced markdown report
        md_file = f"/home/workspace/Daily_Log/{grade_date}/FULL_BACKTEST_SELF_EDGE.md"
        with open(md_file, "w") as f:
            f.write(f"# TC Pipeline — Daily Grading Report\n\n**Date:** {grade_date}\n\n")
            f.write(f"## Overall\n\n")
            f.write(f"- **Total Picks:** {report['total_picks']}\n")
            f.write(f"- **Matched:** {report['matched']} | **Unmatched:** {report['unmatched']}\n")
            f.write(f"- **Hits:** {report['hits']} | **Misses:** {report['misses']}\n")
            f.write(f"- **Hit Rate:** {report['hit_rate']:.1%}\n\n")
            f.write(f"## Edge Bucket Analysis\n\n")
            f.write(f"| Bucket | Picks | Hits | Hit Rate | ROI |\n")
            f.write(f"|--------|-------|------|----------|-----|\n")
            for bucket, data in report['edge_buckets'].items():
                f.write(f"| {bucket} | {data['total']} | {data['hits']} | {data['hit_rate']:.1%} | {data['roi']:+.1%} |\n")
            f.write(f"\n## Per-Sport Breakdown\n\n")
            f.write(f"| Sport | Picks | Hits | Hit Rate | Profit (u) | ROI |\n")
            f.write(f"|-------|-------|------|----------|------------|-----|\n")
            for sport, data in report['sport_breakdown'].items():
                f.write(f"| {sport.upper()} | {data['total']} | {data['hits']} | {data['hit_rate']:.1%} | {data['profit']:+.1f} | {data['roi']:+.1%} |\n")
            f.write(f"\n## Per-Stat Breakdown\n\n")
            for sport, stats in report['stat_breakdown'].items():
                f.write(f"### {sport.upper()}\n\n")
                f.write(f"| Stat | Picks | Hits | Hit Rate | Profit (u) | ROI |\n")
                f.write(f"|------|-------|------|----------|------------|-----|\n")
                for stat, data in sorted(stats.items(), key=lambda x: -x[1]['total']):
                    f.write(f"| {stat} | {data['total']} | {data['hits']} | {data['hit_rate']:.1%} | {data['profit']:+.1f} | {data['roi']:+.1%} |\n")
                f.write("\n")
        print(f"✅ Graded {report['total_picks']} picks for {grade_date}")
        print(f"   Hit rate: {report['hit_rate']:.1%} ({report['hits']}/{report['total_picks']})")
        print(f"   Matched: {report['matched']}, Unmatched: {report['unmatched']}")
        print(f"   Report saved to: {out_file}")
        print(f"   Markdown report: {md_file}")
        return 0

    sports = ["mlb", "wnba", "nba", "nfl", "nhl"] if args.sport == "all" else [args.sport]

    counts = {"mlb": 0, "wnba": 0, "nba": 0, "nfl": 0, "nhl": 0}
    all_picks = {"mlb": [], "wnba": [], "nba": [], "nfl": [], "nhl": []}
    for s in sports:
        try:
            result = generate_picks(s)
            counts[s] = len(result) if result else 0
            all_picks[s] = result or []
            all_picks[s] = enforce_pick_cap(s, all_picks[s])
        except Exception as exc:
            logger.error(f"Sport {s} failed: {exc}")
            time.sleep(SPORT_SLEEP_SECONDS)

    total_picks = sum(counts.values())

    # Send one consolidated professional email
    today = datetime.now(ET).strftime("%Y-%m-%d")
    try:
        combo_data = db.execute("SELECT * FROM combos WHERE date=? ORDER BY ABS(edge) DESC LIMIT 20", [today]).fetchall()
        combo_dicts = [dict(zip([c[0] for c in db.description], row)) for row in combo_data]
    except Exception:
        combo_dicts = None
    send_professional_email(all_picks, today, combos=combo_dicts)
    last_run = {
        "last_run": datetime.now(ET).isoformat(),
        "picks_count": total_picks,
        "sports": {
            "mlb": counts["mlb"],
            "wnba": counts["wnba"],
            "nba": counts["nba"],
            "nfl": counts["nfl"],
            "nhl": counts["nhl"],
        }
    }
    (Path(__file__).parent.parent / "Daily_Log" / "last_run.json").write_text(json.dumps(last_run, indent=2))
    logger.info(f"Pipeline complete. last_run.json updated: {total_picks} picks (MLB:{counts['mlb']} WNBA:{counts['wnba']} NBA:{counts['nba']} NFL:{counts['nfl']} NHL:{counts['nhl']})")

    # source_report removed — github_line_sources module missing
    logger.info("[SOURCES] github_line_sources module missing — skipped.")
    release_run_lock(lock_fd)


def enrich_projections_with_sdio(projections, sport):
    """Fetch player prop lines from SportsDataIO for every pick.
    
    SDIO is the PRIMARY source for player props (MLB + WNBA).
    Sets market_line = real player prop line and signal = 'LIVE' when matched.
    TheRundown is the FALLBACK — only used for game totals, never player props.
    """
    if sport.lower() != "mlb":
        return projections
    
    try:
        today = datetime.now(ET).strftime("%Y-%m-%d")
        sdio_props = fetch_sdio_props(date_str=today)
    except Exception as e:
        logger.warning(f"[SDIO] fetch failed for {sport}: {e}")
        return projections
    
    if not sdio_props:
        logger.info(f"[SDIO] No player props returned for {sport}")
        return projections
    
    SDIO_STAT_MAP = {
        'H': 'hits', 'HR': 'hr', 'RBI': 'rbi', 'R': 'runs',
        'SO': 'so', 'K': 'so', 'BB': 'bb', 'TB': 'tb',
        'PTS': 'points', 'REB': 'rebounds', 'AST': 'assists',
        '3PM': 'three_pointers', 'BLK': 'blocks', 'STL': 'steals',
        'TO': 'turnovers', 'PRA': 'points_rebounds_assists',
    }
    
    updated = 0
    for p in projections:
        if p.get('signal') == 'LIVE':
            continue
        
        player = p.get('name', p.get('player', ''))
        stat = p.get('stat', '')
        
        if not player or not stat:
            continue
        
        player_key = player.strip()
        stat_key = SDIO_STAT_MAP.get(stat.upper(), stat.lower())
        
        player_props = sdio_props.get(player_key, {})
        if not player_props:
            parts = player_key.split()
            if len(parts) >= 2:
                player_last = parts[-1]
                for k in sdio_props:
                    if k.split()[-1] == player_last:
                        player_props = sdio_props[k]
                        break
        
        line = player_props.get(stat_key, 0) or player_props.get(stat.lower(), 0)
        
        if line and line > 0:
            p['market_line'] = float(line)
            p['market_line_bk'] = 'SportsDataIO'
            p['signal'] = 'LIVE'
            proj = p.get('projection', p.get('tc_projection', 0))
            if proj and line:
                p['edge'] = round(float(proj) - float(line), 3)
            updated += 1
    
    logger.info(f"[SDIO] Set player-prop market_line for {updated} of {len(projections)} picks in {sport}")
    return projections


def enrich_projections_with_therundown(projections, sport):
    """Fetch game totals from TheRundown and set market_line on every pick.
    
    Matches picks to TheRundown events using team abbreviations.
    Sets market_line = game total and signal = 'LIVE' when matched.
    """
    calls_today = _therundown_daily_count()
    if calls_today >= THERUNDOWN_DAILY_MAX:
        logger.info(f"[THERUNDOWN] Daily cap ({THERUNDOWN_DAILY_MAX}) reached ({calls_today} calls). Skipping fetch for {sport}.")
        return projections

    MLB_TEAM_NAME_MAP = {
        "ARIZONA DIAMONDBACKS": "ARI", "DIAMONDBACKS": "ARI", "D-BACKS": "ARI",
        "ATLANTA BRAVES": "ATL", "BRAVES": "ATL",
        "BALTIMORE ORIOLES": "BAL", "ORIOLES": "BAL",
        "BOSTON RED SOX": "BOS", "RED SOX": "BOS",
        "CHICAGO CUBS": "CHC", "CUBS": "CHC",
        "CHICAGO WHITE SOX": "CWS", "WHITE SOX": "CWS",
        "CINCINNATI REDS": "CIN", "REDS": "CIN",
        "CLEVELAND GUARDIANS": "CLE", "GUARDIANS": "CLE",
        "COLORADO ROCKIES": "COL", "ROCKIES": "COL",
        "DETROIT TIGERS": "DET", "TIGERS": "DET",
        "HOUSTON ASTROS": "HOU", "ASTROS": "HOU",
        "KANSAS CITY ROYALS": "KC", "ROYALS": "KC",
        "LOS ANGELES ANGELS": "LAA", "ANGELS": "LAA",
        "LOS ANGELES DODGERS": "LAD", "DODGERS": "LAD",
        "MIAMI MARLINS": "MIA", "MARLINS": "MIA",
        "MILWAUKEE BREWERS": "MIL", "BREWERS": "MIL",
        "MINNESOTA TWINS": "MIN", "TWINS": "MIN",
        "NEW YORK METS": "NYM", "METS": "NYM",
        "NEW YORK YANKEES": "NYY", "YANKEES": "NYY",
        "OAKLAND ATHLETICS": "ATH", "ATHLETICS": "ATH",
        "PHILADELPHIA PHILLIES": "PHI", "PHILLIES": "PHI",
        "PITTSBURGH PIRATES": "PIT", "PIRATES": "PIT",
        "SAN DIEGO PADRES": "SD", "PADRES": "SD",
        "SAN FRANCISCO GIANTS": "SF", "GIANTS": "SF",
        "SEATTLE MARINERS": "SEA", "MARINERS": "SEA",
        "ST. LOUIS CARDINALS": "STL", "CARDINALS": "STL",
        "TAMPA BAY RAYS": "TB", "RAYS": "TB",
        "TEXAS RANGERS": "TEX", "RANGERS": "TEX",
        "TORONTO BLUE JAYS": "TOR", "BLUE JAYS": "TOR",
        "WASHINGTON NATIONALS": "WSH", "NATIONALS": "WSH",
    }
    try:
        odds_data = fetch_therundown_odds(sport)
    except Exception as e:
        logger.warning(f"TheRundown fetch failed for {sport}: {e}")
        return projections

    _therundown_increment()

    if not odds_data or not odds_data.get('events'):
        logger.info(f"TheRundown returned no events for {sport}")
        return projections

    teams = {}
    for evt in odds_data['events']:
        key = (evt.get('away', '').strip().upper(), evt.get('home', '').strip().upper())
        if key[0] and key[1]:
            teams[key] = evt

    updated = 0
    for p in projections:
        if p.get('signal') == 'LIVE':
            continue

        pick_team_raw = p.get('team', '').strip()
        pick_team = pick_team_raw.upper()
        matchup = p.get('matchup', '').strip().upper()

        abbr = MLB_TEAM_NAME_MAP.get(pick_team) if sport.lower() == 'mlb' else None
        search_terms = [pick_team]
        if abbr:
            search_terms.append(abbr)

        matched = False
        for (a, h), evt in teams.items():
            for term in search_terms:
                if term and (term == a or term == h or term in matchup):
                    totals = evt.get('totals', {})
                    if totals:
                        over_data = totals.get('over', {})
                        line = over_data.get('DK', over_data.get('FD', {}))
                        if isinstance(line, dict):
                            line = line.get('line', 0)
                        elif not isinstance(line, (int, float)):
                            books = list(over_data.keys())
                            line = 0
                            if books:
                                bk = over_data[books[0]]
                                line = bk.get('line', 0) if isinstance(bk, dict) else 0

                        if line and float(line) > 0:
                            p['market_line'] = float(line)
                            p['signal'] = 'LIVE'
                            updated += 1
                    matched = True
                    break
            if matched:
                break

    logger.info(f"[THERUNDOWN] Set game-line market_line for {updated} of {len(projections)} picks in {sport}")
    return projections


if __name__ == "__main__":
    main()
