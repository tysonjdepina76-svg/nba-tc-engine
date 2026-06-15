"""TC Pipeline — Unified Triple Conservative engine for all sports.

NBA · WNBA · MLB · NHL · FIFA World Cup

Single-file pipeline driven by secrets in /root/.zo/secrets.env:
  ODDS_API_KEY           → The Odds API (game lines, totals, spreads)
  SPORTSGAMEODDS_API_KEY → SportsGameOdds (NBA player props, primary paid feed)

ARCHITECTURE:
  Phase 1 — Game discovery (The Odds API sports → events)
  Phase 2 — TC projection per player-stat (ESPN stats + sport-specific CONS factors)
  Phase 3 — Match projections to DK lines (The Odds API player props for NBA/WNBA only)
  Phase 4 — Edge computation & pick ranking
  Phase 5 — Output: JSON projections + markdown report + CSV for backtest

SPORT-SPECIFIC TC MATH:
  NBA/WNBA:  PTS ×0.85  REB×0.85  AST×0.85  3PM×0.85  STL×0.80  BLK×0.80
  MLB:       HITS×0.82  R×0.78  HR×0.72  RBI×0.78  SB×0.65  K(batter)×0.78  BB×0.72  TB×0.82
  NHL:       G×0.72  A×0.78  SOG×0.82  BLK×0.75  HITS(body)×0.70  PIM×0.60  SV%×0.85
  FIFA WC:   G×0.65  A×0.70  SOG×0.78  SOT×0.75  PAS%×0.85  TKL×0.72  SV×0.80

STATUS FACTOR (all sports): ACTIVE=1.0  Q/GTD/DOUBTFUL=0.55  OUT/DNP/SUSPENDED=0.0

USAGE:
  python3 tc_pipeline.py                     # today's slate, all active sports
  python3 tc_pipeline.py NBA                 # just NBA
  python3 tc_pipeline.py NBA WNBA MLB NHL WC # specific sports
  python3 tc_pipeline.py --report            # generate summary report only
  python3 tc_pipeline.py --purge             # clean obsolete files
"""

import json, os, re, csv, shutil
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"
REPORT_DIR = WORKSPACE / "Daily_Log" / "reports"

ODDS_BASE = "https://api.the-odds-api.com/v4"
LINE_FACTOR = 0.88
Q_MULT = 0.55

# Sport → The Odds API key
ODDS_SPORT_KEY: Dict[str, str] = {
    "NBA": "basketball_nba",
    "WNBA": "basketball_wnba",
    "MLB": "baseball_mlb",
    "NHL": "icehockey_nhl",
    "FIFA WC": "soccer_fifa_world_cup",
    "WC": "soccer_fifa_world_cup",
    "SOCCER": "soccer_fifa_world_cup",
}

# Per-sport stat definitions
SPORT_STATS: Dict[str, Dict[str, Dict]] = {
    "NBA": {
        "PTS": {"cons": 0.85, "label": "Points", "symbol": "★", "espn_key": "avgPoints"},
        "REB": {"cons": 0.85, "label": "Rebounds", "symbol": "◆", "espn_key": "avgRebounds"},
        "AST": {"cons": 0.85, "label": "Assists", "symbol": "●", "espn_key": "avgAssists"},
        "3PM": {"cons": 0.85, "label": "Threes", "symbol": "▲", "espn_key": "avgThreePointFieldGoalsMade"},
        "STL": {"cons": 0.80, "label": "Steals", "symbol": "◇", "espn_key": "avgSteals"},
        "BLK": {"cons": 0.80, "label": "Blocks", "symbol": "■", "espn_key": "avgBlocks"},
    },
    "WNBA": {
        "PTS": {"cons": 0.85, "label": "Points", "symbol": "★", "espn_key": "avgPoints"},
        "REB": {"cons": 0.85, "label": "Rebounds", "symbol": "◆", "espn_key": "avgRebounds"},
        "AST": {"cons": 0.85, "label": "Assists", "symbol": "●", "espn_key": "avgAssists"},
        "3PM": {"cons": 0.85, "label": "Threes", "symbol": "▲", "espn_key": "avgThreePointFieldGoalsMade"},
        "STL": {"cons": 0.80, "label": "Steals", "symbol": "◇", "espn_key": "avgSteals"},
        "BLK": {"cons": 0.80, "label": "Blocks", "symbol": "■", "espn_key": "avgBlocks"},
    },
    "MLB": {
        "HITS": {"cons": 0.82, "label": "Hits", "symbol": "⚡", "espn_key": "avgHits"},
        "R": {"cons": 0.78, "label": "Runs", "symbol": "🏃", "espn_key": "avgRuns"},
        "HR": {"cons": 0.72, "label": "HR", "symbol": "💣", "espn_key": "avgHomeRuns"},
        "RBI": {"cons": 0.78, "label": "RBI", "symbol": "💰", "espn_key": "avgRBI"},
        "SB": {"cons": 0.65, "label": "SB", "symbol": "⚡", "espn_key": "avgStolenBases"},
        "TB": {"cons": 0.82, "label": "Total Bases", "symbol": "⬡", "espn_key": "avgTotalBases"},
    },
    "NHL": {
        "G": {"cons": 0.72, "label": "Goals", "symbol": "🥅", "espn_key": "avgGoals"},
        "A": {"cons": 0.78, "label": "Assists", "symbol": "🍎", "espn_key": "avgAssists"},
        "SOG": {"cons": 0.82, "label": "Shots on Goal", "symbol": "🏒", "espn_key": "avgShotsOnGoal"},
        "BLK": {"cons": 0.75, "label": "Blocks", "symbol": "🛡️", "espn_key": "avgBlocks"},
        "HITS": {"cons": 0.70, "label": "Hits", "symbol": "💥", "espn_key": "avgHits"},
    },
    "FIFA WC": {
        "G": {"cons": 0.65, "label": "Goals", "symbol": "⚽", "espn_key": "avgGoals"},
        "A": {"cons": 0.70, "label": "Assists", "symbol": "🎯", "espn_key": "avgAssists"},
        "SOG": {"cons": 0.78, "label": "Shots on Goal", "symbol": "🎯", "espn_key": "avgShotsOnGoal"},
        "SOT": {"cons": 0.75, "label": "Shots on Target", "symbol": "🎯", "espn_key": "avgShotsOnTarget"},
        "TKL": {"cons": 0.72, "label": "Tackles", "symbol": "🛡️", "espn_key": "avgTackles"},
        "SV": {"cons": 0.80, "label": "Saves", "symbol": "🧤", "espn_key": "avgSaves"},
    },
}

# ESPN league path per sport
ESPN_LEAGUE: Dict[str, str] = {
    "NBA": "basketball/nba",
    "WNBA": "basketball/wnba",
    "MLB": "baseball/mlb",
    "NHL": "hockey/nhl",
    "FIFA WC": "soccer/fifa.world",
    "WC": "soccer/fifa.world",
}

# Total edge gap by sport (TC combined to DK total calibration)
TOTAL_GAP: Dict[str, float] = {
    "NBA": 9.3, "WNBA": 14.0, "NCAAB": 12.0,
    "MLB": 4.5, "NHL": 3.0, "FIFA WC": 2.5, "WC": 2.5,
}

# ═══════════════════════════════════════════════════════════
# SECRETS
# ═══════════════════════════════════════════════════════════

def load_secrets() -> Tuple[str, str]:
    """Load API keys from environment and secrets file."""
    odds_key = os.environ.get("ODDS_API_KEY") or os.environ.get("Theoddsapi") or ""
    sgo_key = os.environ.get("SPORTSGAMEODDS_API_KEY") or os.environ.get("SportsDataIo") or ""

    secrets_file = Path("/root/.zo/secrets.env")
    if secrets_file.exists():
        try:
            raw = secrets_file.read_text()
            for line in raw.splitlines():
                line = line.strip()
                for k, var in [("ODDS_API_KEY", "odds_key"), ("Theoddsapi", "odds_key"),
                               ("SPORTSGAMEODDS_API_KEY", "sgo_key"), ("SportsDataIo", "sgo_key")]:
                    if line.startswith(k + "="):
                        v = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if var == "odds_key" and not odds_key:
                            odds_key = v
                        elif var == "sgo_key" and not sgo_key:
                            sgo_key = v
        except Exception:
            pass

    return (odds_key, sgo_key)

ODDS_KEY, SGO_KEY = load_secrets()

# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def rnd(n: Any, d: int = 1) -> float:
    return round(float(n or 0), d)

def sf(status: str) -> float:
    s = str(status or "ACTIVE").upper()
    if "OUT" in s or "DNP" in s or "SUSPENDED" in s:
        return 0.0
    if "QUESTION" in s or s == "Q" or "DOUBTFUL" in s or "GTD" in s or "PROBABLE" in s:
        return Q_MULT
    return 1.0

def tc_proj(stat: str, raw_val: float, cons: float, status: str) -> float:
    """TC projection = raw_avg × CONS × status_factor"""
    return rnd(float(raw_val or 0) * cons * sf(status), 1)

def line_from_tc(tc_val: float) -> int:
    return int(max(0, tc_val) * LINE_FACTOR)

def edge_calc(tc_val: float, market: Optional[float]) -> float:
    if market is None:
        return 0.0
    return rnd(tc_val - market, 1)

def now_dt() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")

# ═══════════════════════════════════════════════════════════
# PHASE 1: GAME DISCOVERY
# ═══════════════════════════════════════════════════════════

def fetch_sport_events(sport: str) -> List[Dict]:
    """Fetch upcoming events for a sport from The Odds API."""
    sk = ODDS_SPORT_KEY.get(sport.upper(), "")
    if not sk or not ODDS_KEY:
        return []
    try:
        r = requests.get(
            f"{ODDS_BASE}/sports/{sk}/events",
            params={"apiKey": ODDS_KEY},
            timeout=12,
        )
        if r.ok:
            return r.json()
        print(f"  ⚠️  Events {sport}: {r.status_code}")
    except Exception as e:
        print(f"  ⚠️  Events {sport}: {e}")
    return []

def fetch_game_odds(sport: str, event_id: str) -> Dict:
    """Fetch DK game lines (total, spread, ML) for an event."""
    sk = ODDS_SPORT_KEY.get(sport.upper(), "")
    if not sk or not ODDS_KEY:
        return {}
    try:
        r = requests.get(
            f"{ODDS_BASE}/sports/{sk}/events/{event_id}/odds",
            params={
                "apiKey": ODDS_KEY,
                "regions": "us",
                "markets": "h2h,spreads,totals",
                "bookmakers": "draftkings",
            },
            timeout=12,
        )
        if r.ok:
            data = r.json()
            for bm in (data.get("bookmakers") or []):
                if bm.get("key") == "draftkings":
                    mkts = {m["key"]: m["outcomes"] for m in bm.get("markets", [])}
                    total = mkts.get("totals", [{}])[0].get("point") if "totals" in mkts else None
                    h2h = mkts.get("h2h", [])
                    away_ml = home_ml = None
                    for o in h2h:
                        if o.get("name") == data.get("away_team"):
                            away_ml = o.get("price")
                        else:
                            home_ml = o.get("price")
                    spreads = mkts.get("spreads", [])
                    away_sp = home_sp = None
                    for o in spreads:
                        if o.get("name") == data.get("away_team"):
                            away_sp = o.get("point")
                        else:
                            home_sp = o.get("point")
                    return {
                        "dk_total": total,
                        "away_ml": away_ml,
                        "home_ml": home_ml,
                        "away_spread": away_sp,
                        "home_spread": home_sp,
                        "source": "the-odds-api:draftkings",
                    }
    except Exception as e:
        print(f"    ⚠️  Odds fetch: {e}")
    return {}

# ═══════════════════════════════════════════════════════════
# PHASE 2: PLAYER STAT PROJECTIONS
# ═══════════════════════════════════════════════════════════

def fetch_espn_roster(sport: str, team_abbr: str) -> List[Dict]:
    """Fetch team roster + stats from ESPN API."""
    league = ESPN_LEAGUE.get(sport.upper(), "")
    if not league:
        return []

    players = []

    # ESPN uses full team names, not abbreviations, for most endpoints
    # We use the scoreboard endpoint to discover teams and their IDs
    try:
        scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/{league}/scoreboard"
        r = requests.get(scoreboard_url, headers={"Accept": "application/json"}, timeout=15)
        if not r.ok:
            return []

        sb = r.json()
        team_ids = set()

        # Find team IDs matching our abbreviation
        for event in (sb.get("events") or []):
            for comp in (event.get("competitions") or []):
                for team in (comp.get("competitors") or []):
                    abbr = (team.get("team", {}).get("abbreviation") or "").upper()
                    tid = team.get("team", {}).get("id", "")
                    if abbr == team_abbr.upper() and tid:
                        team_ids.add(tid)

        if not team_ids:
            return []

        # Get detailed roster for each matching team
        for tid in list(team_ids)[:1]:  # Take first match
            roster_url = f"https://site.api.espn.com/apis/site/v2/sports/{league}/teams/{tid}/roster"
            try:
                rr = requests.get(roster_url, headers={"Accept": "application/json"}, timeout=15)
                if rr.ok:
                    roster_data = rr.json()
                    for item in (roster_data.get("athletes") or []):
                        ath = item.get("athlete") or item
                        players.append({
                            "id": str(ath.get("id", "")),
                            "name": str(ath.get("displayName") or ath.get("fullName") or "Unknown"),
                            "pos": str(ath.get("position", {}).get("abbreviation") or ""),
                            "jersey": str(ath.get("jersey") or ""),
                            "team": team_abbr,
                        })
            except Exception:
                pass

    except Exception as e:
        print(f"    ⚠️  ESPN roster {team_abbr}: {e}")

    return players

def fetch_player_stats(sport: str, player_id: str) -> Dict:
    """Fetch season-average stats for a player."""
    league = ESPN_LEAGUE.get(sport.upper(), "")
    if not league or not player_id:
        return {}

    try:
        # Determine the correct stat endpoint based on sport
        parts = league.split("/")
        sport_type, league_code = parts[0], parts[1]

        if sport_type == "basketball":
            url = f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league_code}/athletes/{player_id}/statistics?lang=en&region=us"
        elif sport_type == "baseball":
            url = f"https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league_code}/athletes/{player_id}/statistics?lang=en&region=us"
        elif sport_type == "hockey":
            url = f"https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league_code}/athletes/{player_id}/statistics?lang=en&region=us"
        else:
            url = f"https://sports.core.api.espn.com/v2/sports/{league}/athletes/{player_id}/statistics?lang=en&region=us"

        r = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
        if r.ok:
            data = r.json()
            stats = {}
            for cat in (data.get("splits", {}).get("categories") or []):
                for s in (cat.get("stats") or []):
                    name = s.get("name", "")
                    val = s.get("value")
                    if val:
                        try:
                            stats[name] = float(val)
                        except (ValueError, TypeError):
                            stats[name] = 0.0
            return stats
    except Exception:
        pass

    return {}

def project_player(sport: str, player: Dict, status: str = "ACTIVE") -> Dict:
    """Generate TC projections for a single player across all sport stats."""
    stat_map = SPORT_STATS.get(sport.upper(), {})
    if not stat_map:
        return player

    # Fetch detailed stats
    pid = player.get("id", "")
    stats_data = fetch_player_stats(sport, pid) if pid else {}

    projections = {}
    for stat_key, cfg in stat_map.items():
        espn_key = cfg["espn_key"]
        raw = stats_data.get(espn_key, 0.0)
        tc_val = tc_proj(stat_key, raw, cfg["cons"], status)
        line_val = line_from_tc(tc_val)
        projections[f"tc_{stat_key.lower()}"] = tc_val
        projections[f"line_{stat_key.lower()}"] = line_val
        projections[f"raw_{stat_key.lower()}"] = raw

    return {**player, **projections, "status": status, "source": "espn_live_stats"}

async def project_team(sport: str, team_abbr: str) -> List[Dict]:
    """Fetch roster + project all players for a team."""
    roster = fetch_espn_roster(sport, team_abbr)
    if not roster:
        # Fallback: return empty
        return []

    projected = []
    for p in roster[:20]:  # Cap at 20 players per team
        pp = project_player(sport, p)
        projected.append(pp)

    # Sort by top stat (PTS/G/HITS depending on sport)
    sort_key = list(SPORT_STATS.get(sport.upper(), {}).keys())[0] if SPORT_STATS.get(sport.upper(), {}) else "PTS"
    projected.sort(key=lambda x: -float(x.get(f"tc_{sort_key.lower()}", 0)))
    return projected

# ═══════════════════════════════════════════════════════════
# PHASE 3 + 4: EDGE COMPUTATION + RANKING
# ═══════════════════════════════════════════════════════════

def compute_picks(sport: str, away_players: List[Dict], home_players: List[Dict],
                  away_team: str, home_team: str, odds: Dict) -> Dict:
    """Build the full TC projection output with edge-ranked picks."""
    stat_map = SPORT_STATS.get(sport.upper(), {})
    stat_keys = list(stat_map.keys())

    # Compute team totals
    away_total = sum(p.get(f"tc_{k.lower()}", 0) for p in away_players for k in stat_keys[:3])
    home_total = sum(p.get(f"tc_{k.lower()}", 0) for p in home_players for k in stat_keys[:3])
    tc_combined = rnd(away_total + home_total, 1)

    # Compute TC line vs DK total
    gap = TOTAL_GAP.get(sport.upper(), 9.3)
    tc_line = int(tc_combined + gap)
    dk_total = odds.get("dk_total")
    edge = edge_calc(tc_line, dk_total) if dk_total else 0.0
    signal = "PASS"
    if dk_total and abs(edge) > 5:
        signal = "OVER" if edge > 0 else "UNDER"

    # Build player pick rows
    picks = []
    for team_label, players in [(away_team, away_players), (home_team, home_players)]:
        for p in players:
            ps = sf(p.get("status", "ACTIVE"))
            for k in stat_keys:
                cfg = stat_map[k]
                tc_v = p.get(f"tc_{k.lower()}", 0)
                line_v = p.get(f"line_{k.lower()}", 0)
                raw_v = p.get(f"raw_{k.lower()}", 0)
                # Edge = TC projection - TC line (not market line)
                e = rnd(tc_v - line_v, 1)
                direction = "OVER" if e > 0 else "UNDER" if e < 0 else "PASS"
                picks.append({
                    "date": today(),
                    "league": sport,
                    "game": f"{away_team}@{home_team}",
                    "team": team_label,
                    "player": p.get("name", "?"),
                    "pos": p.get("pos", ""),
                    "role": "ACTIVE" if ps > 0 else "OUT",
                    "stat": k,
                    "direction": direction,
                    "market_line": None,  # No player prop odds available for non-basketball
                    "tc_projection": tc_v,
                    "tc_target": line_v,
                    "edge": e,
                    "raw_average": raw_v,
                    "source": p.get("source", "espn"),
                    "actual": None,
                    "result": "PENDING",
                })

    # Filter valid picks (players with real projections)
    valid = [p for p in picks if p["tc_projection"] > 0 and p["role"] == "ACTIVE"]

    # Sort by edge magnitude
    valid.sort(key=lambda x: -abs(x["edge"]))

    return {
        "sport": sport,
        "matchup": f"{away_team}@{home_team}",
        "away_team": away_team,
        "home_team": home_team,
        "timestamp": now_dt(),
        "tc_combined": tc_combined,
        "tc_line": tc_line,
        "dk_total": dk_total,
        "edge": edge,
        "signal": signal,
        "odds_source": odds.get("source", "none"),
        "away_ml": odds.get("away_ml"),
        "home_ml": odds.get("home_ml"),
        "away_spread": odds.get("away_spread"),
        "home_spread": odds.get("home_spread"),
        "roster_counts": {
            "away": len(away_players),
            "home": len(home_players),
            "away_active": sum(1 for p in away_players if sf(p.get("status", "ACTIVE")) > 0),
            "home_active": sum(1 for p in home_players if sf(p.get("status", "ACTIVE")) > 0),
        },
        "away_players": away_players,
        "home_players": home_players,
        "picks": picks,
        "valid_picks": valid,
        "pick_count": len(valid),
        "stat_config": stat_map,
        "tc_formula": {
            "LINE_FACTOR": LINE_FACTOR,
            "Q_MULT": Q_MULT,
            "sport_gap": gap,
            "per_stat_cons": {k: v["cons"] for k, v in stat_map.items()},
        },
    }

# ═══════════════════════════════════════════════════════════
# PHASE 5: OUTPUTS
# ═══════════════════════════════════════════════════════════

def write_projection(proj: Dict, date_dir: Path) -> Path:
    """Write projection JSON to file."""
    sport = proj.get("sport", "UNK")
    matchup = proj.get("matchup", "unknown").replace("@", "_at_")
    fname = f"proj_{sport}_{matchup}.json"
    path = date_dir / fname
    path.write_text(json.dumps(proj, indent=2, default=str))
    return path

def write_picks_csv(all_picks: List[Dict], date_dir: Path) -> Path:
    """Write all picks to CSV for backtesting."""
    path = date_dir / "picks.csv"
    fields = [
        "date", "league", "game", "team", "player", "pos", "role",
        "stat", "direction", "market_line", "tc_projection", "tc_target",
        "edge", "raw_average", "source", "actual", "result",
    ]
    write_header = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            w.writeheader()
        for p in all_picks:
            row = {k: p.get(k, "") for k in fields}
            w.writerow(row)
    return path

def generate_report(results: List[Dict]) -> str:
    """Generate a human-readable markdown report."""
    lines = []
    lines.append(f"# TC Pipeline Report — {today()}")
    lines.append("")
    lines.append(f"Generated: {now_dt()}")
    lines.append(f"Sports covered: {', '.join(sorted(set(r.get('sport','?') for r in results)))}")
    lines.append(f"Games projected: {len(results)}")
    lines.append("")

    # Summary table
    lines.append("## Game Summary")
    lines.append("")
    lines.append("| Sport | Matchup | TC Combined | TC Line | DK Total | Edge | Signal | Picks |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in results:
        sport = r.get("sport", "?")
        matchup = r.get("matchup", "?")
        tc_comb = r.get("tc_combined", 0)
        tc_line = r.get("tc_line", 0)
        dk_total = r.get("dk_total", "—")
        edge = r.get("edge", 0)
        signal = r.get("signal", "—")
        picks = r.get("pick_count", 0)
        edge_str = f"+{edge}" if edge > 0 else str(edge)
        lines.append(f"| {sport} | {matchup} | {tc_comb} | {tc_line} | {dk_total} | {edge_str} | {signal} | {picks} |")

    lines.append("")

    # Per-sport TC formulas
    lines.append("## TC Formulas by Sport")
    lines.append("")
    for sport_name in sorted(SPORT_STATS.keys()):
        sm = SPORT_STATS[sport_name]
        lines.append(f"### {sport_name}")
        lines.append("")
        lines.append("| Stat | CONS | Label |")
        lines.append("|---|---|---|")
        for k, v in sm.items():
            lines.append(f"| {k} | ×{v['cons']:.2f} | {v['label']} {v['symbol']} |")
        lines.append(f"| **Status** | ×1.0 (ACTIVE) ×0.55 (Q/GTD) ×0.0 (OUT) | |")
        lines.append(f"| **Line Factor** | TC × {LINE_FACTOR} | |")
        lines.append(f"| **Total Gap** | +{TOTAL_GAP.get(sport_name, 9.3)} | |")
        lines.append("")

    # Top 20 picks across all games
    lines.append("## Top 20 Picks by Edge (All Sports)")
    lines.append("")
    all_picks = []
    for r in results:
        for p in r.get("valid_picks", []):
            all_picks.append(p)
    all_picks.sort(key=lambda x: -abs(x.get("edge", 0)))
    top20 = all_picks[:20]

    lines.append("| # | Sport | Game | Player | Stat | Direction | TC Proj | Edge |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, p in enumerate(top20, 1):
        edge_str = f"+{p['edge']}" if p.get("edge", 0) > 0 else str(p.get("edge", 0))
        lines.append(f"| {i} | {p['league']} | {p['game']} | {p['player']} | {p['stat']} | {p['direction']} | {p['tc_projection']} | {edge_str} |")

    lines.append("")
    lines.append("## API Status")
    lines.append("")
    lines.append(f"- **The Odds API**: {'✅ Connected' if ODDS_KEY else '❌ Missing — set ODDS_API_KEY in secrets'}")
    lines.append(f"- **SGO API (NBA props)**: {'✅ Connected' if SGO_KEY else '⚠️ Missing — set SPORTSGAMEODDS_API_KEY'}")
    lines.append(f"- **Player props available for**: NBA, WNBA (via Odds API / SGO)")
    lines.append(f"- **Game lines available for**: NBA, WNBA, MLB, NHL, FIFA World Cup (via Odds API)")
    lines.append(f"- **Stats scraped from**: ESPN live APIs for all sports")
    lines.append("")
    lines.append("⚠️ *MLB, NHL, and FIFA World Cup currently have game-level odds only (totals, spreads, ML) — no player prop lines from our API tier. TC projections are generated but can't be compared to DK player prop lines yet.*")

    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════
# PURGE OBSOLETE FILES
# ═══════════════════════════════════════════════════════════

OBSOLETE_FILES = [
    "Projects/wnba_pipeline_v2.py",       # replaced by tc_pipeline.py
    "Projects/build_pregame_combos.py",   # integrated into tc_pipeline.py
    "Projects/dk_combos_engine.py",       # integrated
    "Projects/historical_odds_backtest.py", # stale standalone backtest
    "Projects/recompute_bayes.py",        # one-off script, logic in tc_math.py
    "Projects/boxscore_live_scraper.py",  # replaced by live stats panel
    "Projects/halftime_final_boxscores.py", # replaced
]

def purge_obsolete() -> List[str]:
    """Move obsolete files to archive and report."""
    archive_dir = WORKSPACE / "Projects" / "_archive"
    archive_dir.mkdir(exist_ok=True)
    purged = []
    for fname in OBSOLETE_FILES:
        fpath = WORKSPACE / fname
        if fpath.exists():
            dest = archive_dir / fpath.name
            shutil.move(str(fpath), str(dest))
            purged.append(str(fpath))
            print(f"  Archived: {fpath} → {dest}")
    return purged

# ═══════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════

def run_pipeline(sports: Optional[List[str]] = None) -> Dict:
    """Run the full TC pipeline for specified sports (or all active)."""
    if sports is None:
        sports = ["NBA", "WNBA"]

    date_dir = LOG_DIR / today()
    date_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"TC PIPELINE — {today()} — {now_dt()}")
    print(f"{'='*60}")

    all_results = []
    all_picks = []
    errors = []

    for sport in sports:
        sport_upper = sport.upper()
        print(f"\n🔍 {sport_upper} — Discovering games...")

        events = fetch_sport_events(sport_upper)
        if not events:
            print(f"  No events found for {sport_upper}")
            continue

        # Filter to today's games + upcoming
        print(f"  Found {len(events)} events")
        for ev in events[:8]:  # Cap at 8 games per sport
            away = ev.get("away_team", "")
            home = ev.get("home_team", "")
            eid = ev.get("id", "")
            commence = ev.get("commence_time", "")

            print(f"  📊 {away} @ {home}")

            # Get game odds
            odds = fetch_game_odds(sport_upper, eid) if eid else {}
            if odds.get("dk_total"):
                print(f"    DK Total: {odds['dk_total']} | Spread: {odds.get('away_spread')}")

            # Get player projections (async not needed for sync pipeline)
            print(f"    Projecting players...")
            away_players = []
            home_players = []

            # For NBA/WNBA, use existing ESPN APIs via API
            # For other sports, try ESPN rosters
            if sport_upper in ("NBA", "WNBA"):
                # Use the zo.space API for basketball (already works)
                try:
                    r = requests.get(
                        "https://true.zo.space/api/tc",
                        params={"sport": sport_upper, "away": away, "home": home},
                        headers={"Accept": "application/json"},
                        timeout=60,
                    )
                    if r.ok:
                        data = r.json()
                        away_roster = data.get("away", {}).get("all", {}).get("players", [])
                        home_roster = data.get("home", {}).get("all", {}).get("players", [])
                        # Convert to pipeline format
                        away_players = [
                            {
                                "id": p.get("id", ""),
                                "name": p.get("name", "?"),
                                "pos": p.get("pos", ""),
                                "team": away,
                                "status": p.get("status", "ACTIVE"),
                                "tc_pts": p.get("tc_pts", 0),
                                "tc_reb": p.get("tc_reb", 0),
                                "tc_ast": p.get("tc_ast", 0),
                                "tc_3pm": p.get("tc_3pm", 0),
                                "tc_stl": p.get("tc_stl", 0),
                                "tc_blk": p.get("tc_blk", 0),
                                "line_pts": p.get("line_pts", 0),
                                "line_reb": p.get("line_reb", 0),
                                "line_ast": p.get("line_ast", 0),
                                "line_3pm": p.get("line_3pm", 0),
                                "line_stl": p.get("line_stl", 0),
                                "line_blk": p.get("line_blk", 0),
                                "raw_pts": p.get("raw_pts", 0) or p.get("pts", 0),
                                "raw_reb": p.get("raw_reb", 0) or p.get("reb", 0),
                                "raw_ast": p.get("raw_ast", 0) or p.get("ast", 0),
                                "raw_3pm": p.get("raw_tpm", 0) or p.get("tpm", 0),
                                "raw_stl": p.get("raw_stl", 0) or p.get("stl", 0),
                                "raw_blk": p.get("raw_blk", 0) or p.get("blk", 0),
                                "source": "zo.space/api/tc",
                            }
                            for p in away_roster
                        ]
                        home_players = [
                            {
                                "id": p.get("id", ""),
                                "name": p.get("name", "?"),
                                "pos": p.get("pos", ""),
                                "team": home,
                                "status": p.get("status", "ACTIVE"),
                                "tc_pts": p.get("tc_pts", 0),
                                "tc_reb": p.get("tc_reb", 0),
                                "tc_ast": p.get("tc_ast", 0),
                                "tc_3pm": p.get("tc_3pm", 0),
                                "tc_stl": p.get("tc_stl", 0),
                                "tc_blk": p.get("tc_blk", 0),
                                "line_pts": p.get("line_pts", 0),
                                "line_reb": p.get("line_reb", 0),
                                "line_ast": p.get("line_ast", 0),
                                "line_3pm": p.get("line_3pm", 0),
                                "line_stl": p.get("line_stl", 0),
                                "line_blk": p.get("line_blk", 0),
                                "raw_pts": p.get("raw_pts", 0) or p.get("pts", 0),
                                "raw_reb": p.get("raw_reb", 0) or p.get("reb", 0),
                                "raw_ast": p.get("raw_ast", 0) or p.get("ast", 0),
                                "raw_3pm": p.get("raw_tpm", 0) or p.get("tpm", 0),
                                "raw_stl": p.get("raw_stl", 0) or p.get("stl", 0),
                                "raw_blk": p.get("raw_blk", 0) or p.get("blk", 0),
                                "source": "zo.space/api/tc",
                            }
                            for p in home_roster
                        ]
                    else:
                        print(f"    ⚠️  API returned {r.status_code}")
                except Exception as e:
                    print(f"    ⚠️  API error: {e}")
                    errors.append(f"{sport_upper} {away}@{home}: {e}")
            else:
                # Non-basketball: try ESPN roster + project
                away_players = project_team(sport_upper, away.split()[-1][:3] if away else "?")
                home_players = project_team(sport_upper, home.split()[-1][:3] if home else "?")
                if not away_players:
                    print(f"    ⚠️  Could not load roster for {away}")
                if not home_players:
                    print(f"    ⚠️  Could not load roster for {home}")

            if not away_players and not home_players and sport_upper not in ("NBA", "WNBA"):
                print(f"    ⚠️  No player data — skipping {away}@{home}")
                continue

            # Compute picks
            result = compute_picks(sport_upper, away_players, home_players, away, home, odds)
            all_results.append(result)
            all_picks.extend(result.get("valid_picks", []))

            # Write projection
            out_path = write_projection(result, date_dir)
            print(f"    ✅ {result['pick_count']} picks → {out_path.name}")

    # Write CSV
    if all_picks:
        csv_path = write_picks_csv(all_picks, date_dir)
        print(f"\n📄 Picks CSV: {csv_path}")

    # Generate report
    if all_results:
        report_md = generate_report(all_results)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / f"tc_report_{today()}.md"
        report_path.write_text(report_md)
        print(f"\n📋 Report: {report_path}")

    # Summary
    summary = {
        "date": today(),
        "timestamp": now_dt(),
        "sports": list(set(r["sport"] for r in all_results)),
        "games": len(all_results),
        "picks": len(all_picks),
        "errors": errors,
        "api_status": {
            "ODDS_API_KEY": bool(ODDS_KEY),
            "SGO_API_KEY": bool(SGO_KEY),
        },
    }
    (date_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n{'='*60}")
    print(f"DONE: {len(all_results)} games, {len(all_picks)} picks")
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors:
            print(f"  - {e}")
    print(f"{'='*60}")

    return summary

# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    args = sys.argv[1:]

    if "--purge" in args:
        print("🧹 Purging obsolete files...")
        purged = purge_obsolete()
        print(f"Archived {len(purged)} files.")
        if args == ["--purge"]:
            sys.exit(0)

    if "--report" in args and len(args) == 1:
        # Generate report from existing daily log
        date_dir = LOG_DIR / today()
        results = []
        for f in sorted(date_dir.glob("proj_*.json")):
            try:
                results.append(json.loads(f.read_text()))
            except Exception:
                pass
        if results:
            report_md = generate_report(results)
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            report_path = REPORT_DIR / f"tc_report_{today()}.md"
            report_path.write_text(report_md)
            print(f"📋 Report: {report_path}")
        else:
            print("No projections found for today.")
        sys.exit(0)

    # Filter sport args
    sports = [a for a in args if not a.startswith("--")] if args else ["NBA", "WNBA"]
    if not sports:
        sports = ["NBA", "WNBA", "MLB", "NHL", "WC"]

    run_pipeline(sports)
