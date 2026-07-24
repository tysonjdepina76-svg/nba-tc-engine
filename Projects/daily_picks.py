#!/usr/bin/env python3
"""TC Sports Pipeline — daily_picks.py
Reads projection files from Daily_Log/YYYY-MM-DD/, generates picks, saves to DB + CSV,
applies enhancer, sends email report, updates last_run.json.
"""

import sys, os, csv, json, argparse, sqlite3, smtplib, glob
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
from src.adapters.espn_odds_fetcher import fetch_espn_odds_cached
from src.adapters.theoddsapi_adapter import get_odds_comparison as fetch_live_odds
from src.adapters.free_api_aggregator import get_live_stats, health_check as free_api_health
from src.enhancer import apply_enhancements
from src.roster_loader import get_loader as get_roster_loader
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("tc_pipeline")
from wnba_team_lookup import correct_team
from mlb_team_lookup import correct_mlb_team

PROJ_DIR = Path(__file__).parent.parent / "Daily_Log"
DATA_DIR = Path(__file__).parent.parent / "data"

SERPAPI_DAILY_MAX = 253
SERPAPI_PER_RUN = 80
SERPAPI_TRACKER = DATA_DIR / "serpapi_usage.json"
PICKS_DIR = DATA_DIR / "picks"
DB_PATH = Path(__file__).parent / "data" / "picks.db"

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")


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

            for stat, vals in proj_dict.items():
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
    if sport.lower() in ("wnba", "mlb"):
        players_out = enrich_lines_via_espn(sport, players_out)
        players_out = enrich_lines_via_serpapi(sport, players_out)
        players_out = enrich_via_free_apis(sport, players_out)
        # enrich_from_github removed — module missing
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

    sport_emoji = {"wnba": "🏀", "mlb": "⚾"}
    sport_colors = {"wnba": "#E94560", "mlb": "#00B4D8"}
    sport_names = {"wnba": "WNBA", "mlb": "MLB"}

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


def generate_combos(picks, sport, date_str):
    """Generate correlated combo picks (2-3 leg parlays) from individual picks."""
    import itertools
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    combo_count = 0
    if len(picks) < 3:
        conn.close()
        return 0

    valid_combos = []
    seen_keys = set()

    for combo_size in [2, 3]:
        if len(picks) < combo_size:
            continue

        for combo in itertools.combinations(picks, combo_size):
            if combo_count >= 25:
                break

            # 1. NO same-player combos — skip duplicates like "Aaron Judge | Aaron Judge"
            player_names = [c["name"] for c in combo]
            if len(set(player_names)) < len(player_names):
                continue

            # 2. Dedup by player+stat key, not just player
            player_key = " | ".join(sorted(player_names))
            stat_key = " | ".join(sorted(f'{c["name"]}:{c["stat"]}' for c in combo))
            dedup_key = f"{player_key}|{stat_key}"
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            # 3. Weighted average edge (projection magnitude as weight)
            edges = [c["edge"] for c in combo]
            proj_weights = [max(abs(c.get("projection", 0)), 0.01) for c in combo]
            total_weight = sum(proj_weights)
            combined_edge = sum(e * w / total_weight for e, w in zip(edges, proj_weights))

            combined_proj = sum(c.get("projection", 0) for c in combo)
            combined_line = sum(c.get("line", 0) for c in combo)

            if combined_edge <= 0.01:
                continue

            proj_str = " + ".join(f'{c["name"]}:{c["projection"]:.1f} {c["stat"].upper()}' for c in combo)

            # 4. Majority-rule direction
            over_votes = sum(1 for c in combo if c.get("direction", "").upper() == "OVER")
            under_votes = combo_size - over_votes
            direction = "OVER" if over_votes >= under_votes else "UNDER"

            # 5. Matchup — single if all legs share it, otherwise MULTI
            matchups = list(set(c.get("matchup", sport) for c in combo))
            matchup_str = matchups[0] if len(matchups) == 1 else "MULTI"

            valid_combos.append((
                date_str, sport, f"{combo_size}-LEG",
                player_key, proj_str,
                round(combined_proj, 2), round(combined_line, 2),
                round(combined_edge, 4), direction, matchup_str
            ))
            combo_count += 1

    if valid_combos:
        c.executemany(
            """INSERT OR REPLACE INTO combos
               (date, league, combo_type, players, projections, combined_projection,
                combined_line, edge, direction, matchup)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            valid_combos
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
    for p in players:
        proj = float(p["projection"])
        line = float(p["line"])
        edge = proj - line
        direction = "OVER" if edge > 0 else "UNDER"

        reason = generate_explanation(p["name"], sport, str(p["stat"]), proj, line, edge)

        picks.append({
            "name": p["name"],
            "team": p.get("team", ""),
            "sport": sport,
            "stat": str(p["stat"]),
            "matchup": p.get("matchup", ""),
            "projection": proj,
            "line": line,
            "edge": edge,
            "direction": direction,
            "reason": reason,
        })

    picks = deduplicate(picks)
    picks = apply_enhancements(picks, sport)

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
    for p in picks:
        if p.get("line", 0) == 0:
            continue
        if abs(p.get("edge", 0)) <= 0.5:
            continue
        c.execute(
            """INSERT OR IGNORE INTO picks (date, league, player, team, stat, tc_projection, market_line, edge,
                                  direction, reason, matchup, period, signal)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                date_str, p["sport"], p["name"], p["team"], p["stat"],
                p["projection"], p["line"], p["edge"], p["direction"],
                p.get("reason", ""), p.get("matchup", ""), "GAME", p.get("signal", "SELF_EDGE"),
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
    parser.add_argument("--sport", choices=["mlb", "wnba", "all"], default="all")
    args = parser.parse_args()

    sports = ["mlb", "wnba"] if args.sport == "all" else [args.sport]

    counts = {"mlb": 0, "wnba": 0}
    all_picks = {"mlb": [], "wnba": []}
    for s in sports:
        try:
            result = generate_picks(s)
            counts[s] = len(result) if result else 0
            all_picks[s] = result or []
        except Exception as exc:
            logger.error(f"Sport {s} failed: {exc}")

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
        "sports": {"mlb": counts["mlb"], "wnba": counts["wnba"]}
    }
    (Path(__file__).parent.parent / "Daily_Log" / "last_run.json").write_text(json.dumps(last_run, indent=2))
    logger.info(f"Pipeline complete. last_run.json updated: {total_picks} picks ({counts['mlb']} MLB, {counts['wnba']} WNBA, {counts.get('wc', 0)} WC)")

    # source_report removed — github_line_sources module missing
    logger.info("[SOURCES] github_line_sources module missing — skipped.")


if __name__ == "__main__":
    main()
