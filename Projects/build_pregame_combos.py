"""
Build DK pregame combos using TC projections + Multi-Source Consensus Lines.

Inputs:
- TC projections from /api/tc (sport, away, home, mode=project)
- NBA: SportsGameOdds v2 (DK player props + game ML/total)
- WNBA: The Odds API v4 ($30/mo plan — player props per event)

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

SGO_KEY = os.environ.get("SGO_API_KEY", os.environ.get("SPORTSGAMEODDS_API_KEY", ""))
ODDS_KEY = os.environ.get("ODDS_API_KEY", os.environ.get("THEODDSAPI", ""))
API_BASE = os.environ.get("API_BASE", "https://true.zo.space")

# ── Multi-source consensus engine ──────────────────────
sys.path.insert(0, "/home/workspace/Projects")
from consensus_engine import fetch_consensus_for_matchup, get_best_line

# ── Load secrets from /root/.zo/secrets.env if not in env ──
SECRETS_FILE = Path("/root/.zo/secrets.env")
if (not SGO_KEY or not ODDS_KEY) and SECRETS_FILE.exists():
    for line in SECRETS_FILE.read_text().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"): continue
        if "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key == "SPORTSGAMEODDS_API_KEY" and not SGO_KEY:
                SGO_KEY = val
            elif key == "ODDS_API_KEY" and not ODDS_KEY:
                ODDS_KEY = val

TODAY = datetime.now().strftime("%Y-%m-%d")
LOG_DIR = Path(f"/home/workspace/Daily_Log/{TODAY}")
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

def sgo_events(league: str):
    if not SGO_KEY:
        raise RuntimeError("SGO_API_KEY not set")
    r = requests.get("https://api.sportsgameodds.com/v2/events",
        params={"leagueID": league, "oddsAvailable": "true"},
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

def odds_api_events(sport: str):
    if not ODDS_KEY:
        raise RuntimeError("ODDS_API_KEY not set")
    sport_path = ODDS_SPORT_MAP.get(sport.upper(), "basketball_wnba")
    r = requests.get(f"https://api.the-odds-api.com/v4/sports/{sport_path}/events",
        params={"apiKey": ODDS_KEY, "dateFormat": "iso"}, timeout=15)
    r.raise_for_status()
    return r.json()

def odds_api_player_lines(event_id: str, sport: str):
    if not ODDS_KEY:
        raise RuntimeError("ODDS_API_KEY not set")
    sport_path = ODDS_SPORT_MAP.get(sport.upper(), "basketball_wnba")
    r = requests.get(
        f"https://api.the-odds-api.com/v4/sports/{sport_path}/events/{event_id}/odds",
        params={"apiKey": ODDS_KEY, "regions": "us", "markets": ODDS_MARKETS,
                "oddsFormat": "american"},
        timeout=20)
    r.raise_for_status()
    return r.json()

def extract_dk_lines_oddsapi_multi(odds_data: dict) -> dict:
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

# ── TC Projection + Combo Builder ──────────────────────────

def fetch_tc_projection(sport: str, away: str, home: str) -> dict:
    r = requests.get(f"{API_BASE}/api/tc",
        params={"sport": sport, "away": away, "home": home, "mode": "project"},
        headers={"Accept": "application/json"}, timeout=120)
    r.raise_for_status()
    return r.json()


def build_combos(sport: str, away: str, home: str) -> dict:
    t0 = datetime.now()
    print(f"[{t0:%H:%M:%S}] Fetching TC projection {away}@{home} ({sport})...")
    proj = fetch_tc_projection(sport, away, home)
    valid = [p for p in proj.get("valid_props", []) if p.get("valid")]
    print(f"  -> {len(valid)} TC valid props")

    league = sport.upper()
    lines = {"players": {}, "game_total": None, "ml_home": None, "ml_away": None, "book_used": {}}
    use_odds_api = False

    if league == "NBA":
        print(f"  Fetching SGO events for NBA...")
        events = sgo_events("NBA")
        print(f"  -> {len(events)} SGO events")
        ev = None
        for e in events:
            if (e["teams"]["away"]["names"]["short"] == away and
                e["teams"]["home"]["names"]["short"] == home):
                ev = e; break
        if not ev:
            print(f"  No SGO event matched {away}@{home} — trying Odds API fallback")
            use_odds_api = True
        else:
            lines = extract_dk_lines_sgo(ev.get("odds", {}))
            print(f"  -> {len(lines['players'])} players, total={lines['game_total']}")

    elif league == "WNBA":
        print(f"  Fetching Odds API events for WNBA...")
        use_odds_api = True

    if use_odds_api:
        try:
            print(f"  Fetching multi-source consensus for {league}...")
            consensus = fetch_consensus_for_matchup(league, away, home)
            lines = consensus
            total_str = lines.get('game_total', 'N/A') if lines else 'N/A'
            player_count = len(lines.get('players', {})) if lines else 0
            print(f"  -> {player_count} players, total={total_str}")
        except Exception as e:
            print(f"  Odds API failed: {e}")
            return {"sport": sport, "away": away, "home": home,
                    "legs": [], "qualified": [], "note": f"odds_api_error: {e}"}

    if not lines or not lines.get("players"):
        return {"sport": sport, "away": away, "home": home,
                "legs": [], "qualified": [], "note": "no DK player lines"}

    # Match TC picks to DK lines
    legs = []
    for p in valid:
        player_name = p.get("player", "")
        stat = STAT_MAP.get(p.get("stat", ""))
        if not stat: continue

        dk_player = None
        for dk_name, dk_stats in lines["players"].items():
            if match_player_name(player_name, dk_name):
                dk_player = dk_stats
                break
        if not dk_player or stat not in dk_player:
            continue

        line = dk_player[stat].get("consensus")
        consensus_src = dk_player[stat].get("consensus")
        if line is None:
            # Fallback to raw DK line if consensus not available
            line = dk_player[stat].get("line")
        if line is None:
            continue
        consensus_sources = dk_player[stat].get("consensus_sources")
        tc_proj = p.get("tc_projection") or p.get("tc_target")
        if tc_proj is None: continue

        direction = p.get("direction", "OVER")
        # For WNBA: TC runs below DK lines, so flip to UNDER when TC < DK
        if direction == "OVER" and tc_proj < line:
            direction = "UNDER"
        edge = round(tc_proj - line, 2) if direction == "OVER" else round(line - tc_proj, 2)
        # WNBA: lower edge threshold (DK lines are tighter)
        min_edge = 0.5 if league == "WNBA" else 2.0
        legs.append({
            "player": player_name,
            "team": p.get("team", ""),
            "role": p.get("role"),
            "stat": p["stat"],
            "direction": direction,
            "dk_line": line,
            "dk_odds": None,
            "tc_projection": tc_proj,
            "tc_target": p.get("tc_target"),
            "raw_average": p.get("raw_average"),
            "edge": edge,
            "threshold": p.get("threshold"),
            "qualifies_edge": edge >= min_edge,
            "consensus_source": consensus_src,
            "consensus_sources": consensus_sources,
        })

    legs.sort(key=lambda x: -abs(x["edge"]))
    qualified = [l for l in legs if l["qualifies_edge"]]

    elapsed = (datetime.now() - t0).total_seconds()
    print(f"  -> {len(legs)} matched, {len(qualified)} edge-qualified ({elapsed:.1f}s)")

    return {
        "sport": sport, "away": away, "home": home,
        "tc_total_picks": len(valid),
        "dk_game_total": lines.get("game_total") if lines else None,
        "dk_ml_home": lines.get("ml_home") if lines else None,
        "dk_ml_away": lines.get("ml_away") if lines else None,
        "matched_legs": len(legs),
        "qualified_legs": len(qualified),
        "legs": legs,
        "qualified": qualified,
    }

def write_report(result: dict, out_md: Path, out_json: Path) -> None:
    out_json.write_text(json.dumps(result, indent=2))
    md = []
    md.append(f"# TC Pregame Combos — {result.get('away')}@{result.get('home')} ({result.get('sport')})")
    md.append("")
    md.append(f"- **TC valid picks**: {result.get('tc_total_picks', 'n/a')}")
    md.append(f"- **DK game total**: {result.get('dk_game_total')}")
    md.append(f"- **DK ML (home/away)**: {result.get('dk_ml_home')} / {result.get('dk_ml_away')}")
    md.append(f"- **Matched legs (TC + DK)**: {result.get('matched_legs', 0)}")
    md.append(f"- **Edge-qualified (≥{0.5 if result.get('sport','').upper() == 'WNBA' else 2.0:.1f})**: {result.get('qualified_legs', 0)}")
    if result.get("note"):
        md.append(f"- **Note**: {result['note']}")
    if result.get("error"):
        md.append(f"- **Error**: {result['error']}")
    md.append("")
    if result.get("qualified"):
        md.append("## Qualified Combo Legs")
        md.append("")
        md.append("| Player | Team | Role | Stat | Dir | DK Line | TC Proj | Edge | Odds |")
        md.append("|---|---|---|---|---|---|---|---|---|")
        for l in result["qualified"]:
            md.append(f"| {l['player']} | {l['team']} | {l.get('role','')} | {l['stat']} | {l['direction']} | {l['dk_line']} | {l['tc_projection']} | {l['edge']} | {l.get('dk_odds','')} |")
    if result.get("legs"):
        md.append("")
        md.append("## All Matched Legs")
        md.append("")
        md.append("| Player | Stat | Dir | DK | TC | Edge |")
        md.append("|---|---|---|---|---|---|")
        for l in result["legs"]:
            md.append(f"| {l['player']} | {l['stat']} | {l['direction']} | {l['dk_line']} | {l['tc_projection']} | {l['edge']} |")
    out_md.write_text("\n".join(md))


if __name__ == "__main__":
    # Auto-detect today's slate from the TC API for all sports
    sports_order = ["WNBA"]
    summary = []
    for sport in sports_order:
        try:
            # Fetch today's slate for the sport
            r = requests.get(f"{API_BASE}/api/tc",
                params={"sport": sport, "mode": "slate"},
                headers={"Accept": "application/json"}, timeout=120)
            r.raise_for_status()
            slate = r.json()
            for away, home in slate.get("games", []):
                r = build_combos(sport, away, home)
                safe = f"{away}_{home}".lower()
                write_report(r, LOG_DIR / f"combos_{safe}.md", LOG_DIR / f"combos_{safe}.json")
                summary.append({
                    "matchup": f"{away}@{home}", "sport": sport,
                    "matched": r.get("matched_legs", 0),
                    "qualified": r.get("qualified_legs", 0),
                    "dk_total": r.get("dk_game_total"),
                    "note": r.get("note") or r.get("error", ""),
                })
        except Exception as e:
            print(f"  ERROR: {e}")
            summary.append({
                "matchup": "", "sport": sport,
                "matched": 0, "qualified": 0,
                "dk_total": None,
                "note": str(e),
            })
    (LOG_DIR / "combos_summary.json").write_text(json.dumps(summary, indent=2))
    print("=== COMBOS SUMMARY ===")
    print(json.dumps(summary, indent=2))