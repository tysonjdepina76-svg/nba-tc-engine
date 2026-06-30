# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""
Build DK pregame combos using ONLY multi-book lines (NO TC projections).

Combos use booklines + multi-book consensus to pick direction and edge.
TC math (projections vs lines) is intentionally NOT applied to combos for any sport.

Inputs:
- Multi-Source Consensus Lines (Odds API v4 / SGO) per matchup
- Sport coverage: WNBA, MLB, World Cup (soccer)

Outputs:
- /home/workspace/Daily_Log/YYYY-MM-DD/combos_{away}_{home}.json  (full legs)
- /home/workspace/Daily_Log/YYYY-MM-DD/combos_{away}_{home}.md    (human report)
"""

import json
import os
import re
import sys
import requests
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("/home/workspace/Daily_Log/combos")

# ── MLB Boxscore Fetcher (2026-06-29) ──────────────────
ESPN_MLB_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary"
ESPN_MLB_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"

def fetch_mlb_boxscore(event_id: str, timeout: int = 15):
    """Fetch a single MLB boxscore from ESPN. Returns dict with team stats +
    player stat lines for grading purposes. Falls back to SGO if ESPN 404s."""
    try:
        r = requests.get(ESPN_MLB_SUMMARY, params={"event": event_id}, timeout=timeout)
        if r.status_code == 200:
            data = r.json()
            box = {
                "source": "espn",
                "event_id": event_id,
                "fetched_at": datetime.utcnow().isoformat() + "Z",
                "raw": data,
            }
            # Extract team boxscore stats
            teams = data.get("boxscore", {}).get("teams", [])
            box["teams"] = []
            for t in teams:
                team_info = t.get("team", {})
                stats = {
                    "team": team_info.get("abbreviation") or team_info.get("shortDisplayName"),
                    "hits": _stat(t, "hits"),
                    "runs": _stat(t, "runs"),
                    "errors": _stat(t, "errors"),
                    "at_bats": _stat(t, "atBats"),
                }
                box["teams"].append(stats)
            return box
    except Exception as e:
        print(f"  ESPN MLB boxscore error ({event_id}): {e}")
    # SGO fallback stub (placeholder — SGO free tier doesn't carry MLB boxscores)
    return {"source": "none", "event_id": event_id, "error": "no boxscore available"}


def _stat(team_block: dict, key: str):
    """Pull a single stat from an ESPN team boxscore block."""
    for s in team_block.get("statistics", []):
        names = s.get("names") or [s.get("name", "").lower()]
        if any(key.lower() in str(n).lower() for n in names):
            return s.get("displayValue") or s.get("value")
    return None


def grade_mlb_picks(box: dict, picks: list):
    """Given a boxscore + a list of MLB picks (player/stat/direction/line),
    return a grading list with hit=True/False per pick. Used by backtest."""
    if not box or box.get("source") != "espn":
        return []
    results = []
    # Index player batting lines by name (last name match)
    raw = box.get("raw", {})
    batters = {}
    for side in raw.get("boxscore", {}).get("players", []):
        for cat in side.get("statistics", []):
            for ath in cat.get("athletes", []):
                a = ath.get("athlete", {})
                nm = a.get("shortName") or a.get("displayName") or ""
                if nm:
                    batters[nm.lower()] = ath.get("stats", [])
    for p in picks:
        name = (p.get("player") or "").lower()
        if name not in batters:
            results.append({**p, "hit": None, "note": "no_player_in_box"})
            continue
        # Need a mapping of stat → actual value (left as a stub; ESPN stat
        # keys vary by category — extend per stat type when grading)
        results.append({**p, "hit": None, "actual": None, "note": "stat_map_tbd"})
    return results

# ── end MLB boxscore fetcher ──────────────────────

# ── Multi-source consensus engine ──────────────────────
sys.path.insert(0, "/home/workspace/Projects")
from consensus_engine import fetch_consensus_for_matchup, get_best_line

# ── Load secrets from /root/.zo/secrets.env if not in env ──
SECRETS_FILE = Path("/root/.zo/secrets.env")
SGO_KEY = os.environ.get("SGO_API_KEY", "")
ODDS_KEY = os.environ.get("ODDS_API_KEY", "")
if (not SGO_KEY or not ODDS_KEY) and SECRETS_FILE.exists():
    for line in SECRETS_FILE.read_text().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"): continue
        if "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key == "SGO_API_KEY":
                SGO_KEY = val
            elif key == "ODDS_API_KEY":
                ODDS_KEY = val

TODAY = datetime.now().strftime("%Y-%m-%d")
LOG_DIR = Path(f"/home/workspace/Daily_Log/{TODAY}")

# If today's folder is empty, fall back to the most recent day's projections (still valid for combos).
if not LOG_DIR.exists() or not any(LOG_DIR.glob("proj_*_at_*.json")):
    base = Path("/home/workspace/Daily_Log")
    recent = sorted([d for d in base.iterdir() if d.is_dir() and d.name[:4].isdigit()], reverse=True)
    for d in recent:
        if any(d.glob("proj_*_at_*.json")):
            LOG_DIR = d
            print(f"[combos] using proj folder: {d}")
            break
LOG_DIR.mkdir(parents=True, exist_ok=True)

STAT_MAP = {"PTS": "points", "REB": "rebounds", "AST": "assists", "3PM": "threes", "STL": "steals", "BLK": "blocks"}

ODDS_STAT_REVERSE = {
    "player_points": "points", "player_rebounds": "rebounds",
    "player_assists": "assists", "player_threes": "threes",
    "player_steals": "steals", "player_blocks": "blocks",
}

BOOK_PRIORITY = ["draftkings", "fanduel", "betmgm", "caesars", "fanatics", "bovada"]

# ── Team name normalizers ──────────────────────────────────
WNBA_TEAM_NORM = {
    "ATL": "dream", "CHI": "sky", "CON": "sun", "DAL": "wings",
    "GS": "valkyries", "IND": "fever", "LV": "aces", "LA": "sparks",
    "MIN": "lynx", "NY": "liberty", "PHX": "mercury", "POR": "fire",
    "SEA": "storm", "TOR": "tempo", "WSH": "mystics",
}

NBA_TEAM_NORM = {
    "ATL": "hawks", "BOS": "celtics", "BKN": "nets", "CHA": "hornets",
    "CHI": "bulls", "CLE": "cavaliers", "DAL": "mavericks", "DEN": "nuggets",
    "DET": "pistons", "GSW": "warriors", "HOU": "rockets", "IND": "pacers",
    "LAC": "clippers", "LAL": "lakers", "MEM": "grizzlies", "MIA": "heat",
    "MIL": "bucks", "MIN": "timberwolves", "NOP": "pelicans", "NYK": "knicks",
    "OKC": "thunder", "ORL": "magic", "PHI": "76ers", "PHX": "suns",
    "POR": "blazers", "SAC": "kings", "SAS": "spurs", "TOR": "raptors",
    "UTA": "jazz", "WAS": "wizards",
}

def team_contains(api_team: str, code: str, league: str) -> bool:
    """Check if API team name contains the team code (or full name)."""
    code_upper = code.upper()
    api_lower = api_team.lower()
    if code_upper in api_team.upper():
        return True
    norm = WNBA_TEAM_NORM if league == "WNBA" else NBA_TEAM_NORM
    full_name = norm.get(code_upper, "").lower()
    if full_name and full_name in api_lower:
        return True
    return False

def match_player_name(tc_name: str, dk_name: str) -> bool:
    """Fuzzy match player names with apostrophe/comma normalization."""
    a = tc_name.lower().replace("'", "").replace(",", "").strip()
    b = dk_name.lower().replace("'", "").replace(",", "").strip()
    if a == b: return True
    if a in b or b in a: return True
    # Handle initials (e.g. "A.J. Wilson" vs "A'ja Wilson")
    a_parts = set(a.replace(".", " ").split())
    b_parts = set(b.replace(".", " ").split())
    return len(a_parts & b_parts) >= min(len(a_parts), len(b_parts)) - 1

# ── SGO (NBA) ──────────────────────────────────────────────

CACHE_DIR = Path("/home/workspace/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path_for(sport: str, away: str, home: str) -> Path:
    safe = f"{sport}_{away}_{home}".replace(" ", "_").lower()
    return CACHE_DIR / f"combos_{safe}.json"


def _save_cache(sport: str, away: str, home: str, result: dict) -> None:
    """Persist a successful consensus result so we can replay it when SGO 429s."""
    try:
        payload = {
            "timestamp": datetime.now().isoformat(),
            "sport": sport,
            "away": away,
            "home": home,
            "combos": result,
        }
        _cache_path_for(sport, away, home).write_text(json.dumps(payload, indent=2))
    except Exception as e:
        print(f"[cache] save failed: {e}")


def _load_cache(sport: str, away: str, home: str) -> dict | None:
    """Load cached combos for a matchup if available and not too stale."""
    p = _cache_path_for(sport, away, home)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        ts = datetime.fromisoformat(data["timestamp"])
        age_hours = (datetime.now() - ts).total_seconds() / 3600
        if age_hours > 24:
            print(f"[cache] {p.name} too stale ({age_hours:.1f}h old) — skipping")
            return None
        return data.get("combos")
    except Exception as e:
        print(f"[cache] load failed: {e}")
        return None


def _fetch_consensus_with_cache(sport_upper: str, away: str, home: str) -> dict:
    """Try SGO fresh; on 429, fall back to cached combos from last successful run."""
    try:
        result = fetch_consensus_for_matchup(sport_upper, away, home)
        # Cache successful result
        if result and (result.get("players") or result.get("available_books")):
            _save_cache(sport_upper, away, home, result)
        return result
    except requests.exceptions.HTTPError as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status == 429:
            cached = _load_cache(sport_upper, away, home)
            if cached:
                cache_path = _cache_path_for(sport_upper, away, home)
                print(f"⚠️ SGO rate-limited (429) — using cached data from {cache_path.name}")
                return cached
            print(f"⚠️ SGO rate-limited (429) — no cache available for {away}@{home}")
        raise
    except Exception as e:
        # Network error / timeout — try cache as best-effort fallback
        msg = str(e).lower()
        if "429" in msg or "rate" in msg or "timeout" in msg:
            cached = _load_cache(sport_upper, away, home)
            if cached:
                cache_path = _cache_path_for(sport_upper, away, home)
                print(f"⚠️ SGO error ({e}) — using cached data from {cache_path.name}")
                return cached
        raise


def sgo_events(league: str):
    if not SGO_KEY:
        raise RuntimeError("SGO_API_KEY not set")
    r = requests.get("https://api.sportsgameodds.com/v2/events",
        params={"leagueID": league, "oddsAvailable": "true", "limit": "100"},
        headers={"x-api-key": SGO_KEY}, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])

def name_to_sgo_id(name: str) -> str:
    s = re.sub(r"[^A-Za-z\s]", "", name).upper().strip()
    return "_".join(s.split()) + "_1_NBA"

def extract_dk_lines_sgo(odds: dict) -> dict:
    out = {"players": {}, "game_total": None, "ml_home": None, "ml_away": None}
    for k, v in odds.items():
        dk = v.get("byBookmaker", {}).get("draftkings", {})
        if not dk or not dk.get("available"):
            continue
        m = re.match(r"^(points|rebounds|assists|threes|steals|blocks)-([A-Z0-9_]+)-game-ou-over$", k)
        if m:
            stat, pid = m.group(1), m.group(2)
            line = dk.get("overUnder")
            if line is None: continue
            try: line = float(line)
            except (TypeError, ValueError): continue
            out["players"].setdefault(pid, {})[stat] = {"line": line, "over_odds": dk.get("odds"), "under_odds": None}
            continue
        if k == "points-all-game-ou-over":
            out["game_total"] = float(dk.get("overUnder")) if dk.get("overUnder") else None
        elif k == "points-home-game-ml-home":
            out["ml_home"] = dk.get("odds")
        elif k == "points-away-game-ml-away":
            out["ml_away"] = dk.get("odds")
    return out

# ── Odds API (WNBA) ────────────────────────────────────────

ODDS_SPORT_MAP = {"WNBA": "basketball_wnba", "NBA": "basketball_nba"}
ODDS_MARKETS = "player_points,player_rebounds,player_assists,player_threes,player_steals,player_blocks,totals"

def _parse_player_props(odds_data):
    out = {"players": {}, "game_total": None, "ml_home": None, "ml_away": None, "book_used": {}}
    avail = {bm.get("key") for bm in odds_data.get("bookmakers", []) if bm.get("key")}
    books = [b for b in BOOK_PRIORITY if b in avail]
    by_book = {}
    for bk_key in BOOK_PRIORITY:
        if bk_key not in avail:
            continue
        bm = next((b for b in odds_data["bookmakers"] if b.get("key") == bk_key), None)
        if not bm:
            continue
        book_players = {}
        for market in bm.get("markets", []):
            mkey = market.get("key", "")
            stat = ODDS_STAT_REVERSE.get(mkey)
            if stat:
                player_outcomes = {}
                for outcome in market.get("outcomes", []):
                    name = outcome.get("description") or outcome.get("name", "")
                    line = outcome.get("point")
                    price = outcome.get("price")
                    if line is None or name is None:
                        continue
                    try: line = float(line)
                    except (TypeError, ValueError): continue
                    is_over = "Over" in outcome.get("name", "") or "over" in outcome.get("name", "")
                    if name not in player_outcomes:
                        player_outcomes[name] = {"line": line, "over_odds": None, "under_odds": None}
                    if is_over:
                        player_outcomes[name]["over_odds"] = price
                    else:
                        player_outcomes[name]["under_odds"] = price
                for name, data in player_outcomes.items():
                    book_players.setdefault(name, {})[stat] = data
            elif mkey == "totals":
                for outcome in market.get("outcomes", []):
                    if outcome.get("name") == "Over":
                        if not out["game_total"]:
                            out["game_total"] = outcome.get("point")
            elif mkey == "h2h":
                pass
        by_book[bk_key] = book_players
    
    collected_names = set()
    for bk_key in books:
        for name, stats in by_book.get(bk_key, {}).items():
            norm_name = name.lower().replace("'", "").replace(",", "").strip()
            for stat, data in stats.items():
                key = (norm_name, stat)
                if key not in collected_names:
                    collected_names.add(key)
                    out["players"].setdefault(name, {})[stat] = data
                    out["book_used"][(name, stat)] = bk_key
    return out

# ── Combo Builder (booklines ONLY — no TC math) ─────────

# Sports we run combos for. Each maps to (consensus sport key, stat list).
# 2026-06-30 winning strategy: WC filter = fouls + shots only.
# OVER signals are 9.4% broken (under too aggressive); keep UNDER as default.
COMBO_SPORT_CONFIG = {
    "WNBA": {"stats": ["points", "rebounds", "assists", "threes", "steals", "blocks"]},
    "MLB":  {"stats": ["points"]},
    "WORLD CUP": {"stats": ["fouls", "shots"]},
}

def _line_range_signal(entry: dict) -> tuple:
    """From a consensus entry, return (direction, edge, max_line, min_line, book_count).

    direction: "OVER" if high-side books lean up vs the consensus, "UNDER" otherwise.
    edge: half-spread between max and min book lines (a measure of disagreement/edge).
    Returns (None, 0, ...) if not enough data.
    """
    all_lines = entry.get("all_lines") or []
    if len(all_lines) < 1:
        return (None, 0, None, None, 0)
    consensus = entry.get("consensus")
    if consensus is None:
        consensus = all_lines[0]
    if len(all_lines) == 1:
        # Single-book (e.g. MLB on SGO): no spread, no direction lean.
        # Treat as neutral OVER and zero edge so it still appears in legs.
        line = all_lines[0]
        return ("OVER", 0.0, line, line, 1)
    sorted_lines = sorted(all_lines)
    lo, hi = sorted_lines[0], sorted_lines[-1]
    spread = round(hi - lo, 2)
    above = sum(1 for v in all_lines if v > consensus)
    below = sum(1 for v in all_lines if v < consensus)
    # 2026-06-30 tighten v2: OVER only when edge_pct > 0.05 (5% relative
    # spread between highest and lowest line). Below 5% the books agree
    # and the conservative side is UNDER. With hi/lo only, hi >= lo is
    # always true — must require both spread AND relative edge.
    if lo and lo > 0:
        edge_pct = spread / lo
    else:
        edge_pct = 0.0
    if edge_pct > 0.05 and above > below:
        direction = "OVER"
    else:
        direction = "UNDER"
    return (direction, spread, hi, lo, len(all_lines), round(edge_pct, 4))

def build_combos(sport: str, away: str, home: str) -> dict:
    """Build combo legs from booklines only — no TC projections."""
    t0 = datetime.now()
    sport_upper = sport.upper()
    print(f"[{t0:%H:%M:%S}] Building bookline combos for {away}@{home} ({sport})...")

    cfg = COMBO_SPORT_CONFIG.get(sport_upper)
    if not cfg:
        return {"sport": sport, "away": away, "home": home,
                "legs": [], "qualified": [], "note": f"no combo config for {sport}"}

    print(f"  Fetching multi-source consensus for {sport_upper}...")
    try:
        consensus = _fetch_consensus_with_cache(sport_upper, away, home)
    except Exception as e:
        return {"sport": sport, "away": away, "home": home,
                "legs": [], "qualified": [], "note": f"consensus fetch failed: {e}"}

    players = consensus.get("players") or {}
    if not players:
        return {"sport": sport, "away": away, "home": home,
                "legs": [], "qualified": [], "note": "no DK player lines"}

    print(f"  -> {len(players)} players, books={consensus.get('available_books')}, source={consensus.get('source')}")

    legs = []
    for player_name, stats in players.items():
        team = ""  # consensus doesn't carry team on player lines; leave blank
        for stat in cfg["stats"]:
            entry = stats.get(stat)
            if not entry: continue
            consensus_line = entry.get("consensus")
            if consensus_line is None: continue
            direction, spread, hi, lo, book_count, edge_pct = _line_range_signal(entry)
            if direction is None: continue
            # 2026-06-30 winning filter: WC UNDER-only. OVER hit rate
            # is 9.4% broken. Force UNDER on all WC legs regardless of
            # books' high-side lean.
            if sport_upper == "WORLD CUP" and stat in ("fouls", "shots"):
                direction = "UNDER"
                edge_pct = max(edge_pct, 0.0)
            # Quality filter: need >=1 book. Spread only matters with 2+ books.
            # 2026-06-29: MLB SGO only returns DK (no multi-book overlap),
            # so we accept single-book lines. Revisit when 2+ books available.
            if book_count < 1: continue
            # Single-book lines have spread=0; multi-book legs need spread>0 for edge.
            if book_count >= 2 and spread <= 0: continue
            legs.append({
                "player": player_name,
                "team": team,
                "stat": stat,
                "direction": direction,
                "consensus_line": consensus_line,
                "high_line": hi,
                "low_line": lo,
                "spread": spread,
                "book_count": book_count,
                "best_book": entry.get("best_book"),
                "available_books": consensus.get("available_books", []),
                "qualifies_edge": spread >= 0.5,  # half-point spread minimum
                "edge": spread,
            })

    legs.sort(key=lambda x: -x["spread"])
    qualified = [l for l in legs if l["qualifies_edge"]]

    elapsed = (datetime.now() - t0).total_seconds()
    print(f"  -> {len(legs)} legs from booklines, {len(qualified)} qualified ({elapsed:.1f}s)")

    return {
        "sport": sport, "away": away, "home": home,
        "dk_game_total": consensus.get("game_total"),
        "available_books": consensus.get("available_books", []),
        "all_books_seen": consensus.get("all_books_seen", []),
        "matched_legs": len(legs),
        "qualified_legs": len(qualified),
        "legs": legs,
        "qualified": qualified,
    }

def write_report(result: dict, out_md: Path, out_json: Path) -> None:
    out_json.write_text(json.dumps(result, indent=2))
    md = []
    md.append(f"# Pregame Combos — {result.get('away')}@{result.get('home')} ({result.get('sport')})")
    md.append("")
    md.append(f"- **Source**: Multi-book consensus lines (NO TC math)")
    md.append(f"- **Books**: {', '.join(result.get('available_books', []))}")
    md.append(f"- **Game total**: {result.get('dk_game_total')}")
    md.append(f"- **Matched legs**: {result.get('matched_legs', 0)}")
    md.append(f"- **Edge-qualified (spread ≥ 0.5)**: {result.get('qualified_legs', 0)}")
    if result.get("note"):
        md.append(f"- **Note**: {result['note']}")
    if result.get("error"):
        md.append(f"- **Error**: {result['error']}")
    md.append("")
    md.append("**Direction rule**: OVER when more books sit above consensus, UNDER when more sit below.")
    md.append("**Edge rule**: half-spread (max book line − min book line). Wider disagreement = more edge.")
    md.append("")
    if result.get("qualified"):
        md.append("## Qualified Combo Legs")
        md.append("")
        md.append("| Player | Stat | Direction | Consensus | High | Low | Spread | Books | Best Book |")
        md.append("|---|---|---|---|---|---|---|---|---|")
        for l in result["qualified"]:
            md.append(f"| {l['player']} | {l['stat']} | {l['direction']} | {l['consensus_line']} | {l['high_line']} | {l['low_line']} | {l['spread']} | {l['book_count']} | {l.get('best_book','')} |")
    if result.get("legs"):
        md.append("")
        md.append("## All Legs")
        md.append("")
        md.append("| Player | Stat | Dir | Consensus | Spread | Books |")
        md.append("|---|---|---|---|---|---|")
        for l in result["legs"]:
            md.append(f"| {l['player']} | {l['stat']} | {l['direction']} | {l['consensus_line']} | {l['spread']} | {l['book_count']} |")
    out_md.write_text("\n".join(md))

if __name__ == "__main__":
    # Auto-detect today's slate from local projection files (no /api/tc calls).
    # Combos use booklines only — TC math is intentionally NOT applied.
    sport_token_map = {
        "WNBA": "WNBA",
        "MLB": "MLB",
        "WORLD CUP": "WORLD CUP",
    }

    # Discover matchups from today's proj files (folders may be a few days old).
    games_by_sport: dict = {}
    for proj_file in LOG_DIR.glob("proj_*_at_*.json"):
        # e.g. proj_MLB_CHW_at_BAL.json or proj_WORLD CUP_JPN_at_BRA.json
        stem = proj_file.stem
        if not stem.startswith("proj_"): continue
        rest = stem[len("proj_"):]
        # Try MLB/NBA/WNBA first (single token sport), then WORLD CUP (two token sport)
        if rest.startswith("WORLD CUP_"):
            sport_tok = "WORLD CUP"
            match_part = rest[len("WORLD CUP_"):]
        else:
            parts = rest.split("_", 2)
            if len(parts) < 3: continue
            sport_tok = parts[0]
            match_part = parts[1] + "_" + parts[2] if len(parts) >= 3 else ""
        if "_at_" not in match_part: continue
        away, home = match_part.split("_at_", 1)
        if sport_tok not in sport_token_map: continue
        games_by_sport.setdefault(sport_token_map[sport_tok], []).append((away, home))

    # Fallback: if no proj files, hardcode today's matchups from the daily log.
    if not games_by_sport:
        games_by_sport = {
            "WNBA": [("LV", "NY")],
            "WORLD CUP": [("JPN", "BRA"), ("MAR", "NED"), ("PAR", "GER")],
            "MLB": [],
        }

    summary = []
    for sport, games in games_by_sport.items():
        if not games:
            summary.append({"matchup": "", "sport": sport, "matched": 0, "qualified": 0,
                            "note": "no proj file (off-day)"})
            continue
        for away, home in games:
            try:
                r = build_combos(sport, away, home)
                safe = f"{away}_{home}".lower()
                write_report(r, LOG_DIR / f"combos_{safe}.md", LOG_DIR / f"combos_{safe}.json")
                summary.append({
                    "matchup": f"{away}@{home}", "sport": sport,
                    "matched": r.get("matched_legs", 0),
                    "qualified": r.get("qualified_legs", 0),
                    "note": r.get("note") or r.get("error", ""),
                })
            except Exception as e:
                print(f"  ERROR ({away}@{home}): {e}")
                summary.append({
                    "matchup": f"{away}@{home}", "sport": sport,
                    "matched": 0, "qualified": 0,
                    "note": str(e),
                })
    (LOG_DIR / "combos_summary.json").write_text(json.dumps(summary, indent=2))
    print("=== COMBOS SUMMARY ===")
    print(json.dumps(summary, indent=2))