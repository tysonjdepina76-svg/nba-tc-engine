# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""TC Daily Pick Log — captures every pick with full roster context for backtesting.

Runs on a schedule (5 min before tip) and writes:
- /home/workspace/Daily_Log/YYYY-MM-DD/slate_NBA.json  (raw responses)
- /home/workspace/Daily_Log/YYYY-MM-DD/slate_WNBA.json
- /home/workspace/Daily_Log/YYYY-MM-DD/slate_MLB.json
- /home/workspace/Daily_Log/YYYY-MM-DD/slate_WORLD_CUP.json
- /home/workspace/Daily_Log/YYYY-MM-DD/picks.csv         (flat backtest table)
- /home/workspace/Daily_Log/YYYY-MM-DD/picks.json        (structured picks)
- /home/workspace/Daily_Log/last_run.json                (latest summary)

Designed to be the single source of truth for daily picks and historical results.
"""

import os
import json
import csv
import sys
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── All active sports in the pipeline ─────────────────────
ALL_SPORTS = ("NBA", "WNBA", "MLB", "NHL", "WORLD_CUP", "NFL")
BASKETBALL = {"NBA", "WNBA"}  # sports with full player props + rosters
BOOKLINE_SPORTS = {"MLB", "NHL", "WORLD_CUP", "SOCCER"}

def generate_ou_picks(projection, sport, matchup, date_str):
    """Generate OVER/UNDER picks for bookline sports from raw projection + DK line.
    Bypasses TC math — direction is set purely from (tc_projection vs market_line).
    """
    picks = []
    for p in projection.get("valid_props", []):
        if p.get("status") and p.get("status") not in ("ACTIVE", None):
            continue
        line = p.get("market_line")
        proj = p.get("tc_projection")
        if line is None or proj is None:
            continue
        try:
            line = float(line); proj = float(proj)
        except (TypeError, ValueError):
            continue
        if line <= 0:
            continue
        edge = proj - line  # positive = OVER, negative = UNDER
        # Threshold: only fire when projection diverges from line by >= 0.5
        if abs(edge) < 0.5:
            continue
        picks.append({
            "date": date_str,
            "league": sport,
            "matchup": matchup,
            "team": p.get("team"),
            "player": p.get("player"),
            "role": p.get("pos"),
            "status": "ACTIVE",
            "stat": p.get("stat"),
            "direction": "OVER" if edge > 0 else "UNDER",
            "signal": "OVER" if edge > 0 else "UNDER",
            "market_line": line,
            "tc_projection": proj,
            "tc_target": None,
            "edge": round(edge, 3),
            "threshold": 0.5,
            "raw_average": p.get("tc_raw"),
            "source": "OVER_UNDER",  # critical: NOT TC math
            "actual": None,
            "result": "PENDING",
        })
    return picks

from mock_lines import get_mock_market_line
MLB_SPORTS = {"MLB"}  # sports with

ET = timezone(timedelta(hours=-5))
def now_et():
    return datetime.now(ET)
def today_et():
    # Honor TC_RUN_DATE env var (set by --date arg) so backtests can run for prior dates
    _forced = os.environ.get("TC_RUN_DATE")
    if _forced:
        return _forced
    return now_et().strftime("%Y-%m-%d")

try:
    _sec = Path("/root/.zo/secrets.env")
    if _sec.exists():
        for _line in _sec.read_text().splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ[_k.strip()] = _v.strip()  # FORCE write, not setdefault
    # ── Standardize known aliases so all consumers find what they expect ──
    _aliases = {
        "THEODDSAPI": "ODDS_API_KEY",
        "ODDS_API_KEY": "THEODDSAPI",
        "SPORTSDATAIO_API_KEY": "SPORTS_DATA_API_KEY",
        "SPORTS_DATA_API_KEY": "SPORTSDATAIO_API_KEY",
    }
    for _from, _to in _aliases.items():
        if os.environ.get(_from) and not os.environ.get(_to):
            os.environ[_to] = os.environ[_from]
except Exception as _e:
    print(f"\u26a0\ufe0f secrets load failed: {_e}")

# Add workspace root for imports
WORKSPACE = Path("/home/workspace")
sys.path.insert(0, str(WORKSPACE))
sys.path.insert(0, str(WORKSPACE / "Projects"))

from consensus_engine import fetch_consensus_for_matchup, CONSENSUS_SPORT_MAP, get_best_line
from api_fallback import FallbackManager, quota_status

API_BASE = "https://true.zo.space"
LOG_DIR = WORKSPACE / "Daily_Log"
LOG_DIR.mkdir(exist_ok=True)

ED_THRESHOLD = 2.0  # TC edge threshold to call OVER/UNDER signal

# ── API Call Budget Gate ──
try:
    import sys as _sys
    _tcsports = "/home/workspace/tc-sports-app/src"
    if _tcsports not in _sys.path:
        _sys.path.insert(0, _tcsports)
    from monitoring.api_call_budget import budget_ok, budget_status, track_api_call, BUDGET_FILE
    _budget = budget_status()
    _daily_ok = budget_ok()
    print(f'   Budget: {_budget["calls_today"]}/{_budget["daily_limit"]} calls today, {_budget["calls_month"]}/{_budget["monthly_limit"]} calls this month')
    if not _daily_ok:
        print('🛑 BUDGET GATE: Daily API call limit reached — using cache only')
        _budget_exceeded = True
    else:
        _budget_exceeded = False
except Exception as e:
    print(f'   Budget tracker not available: {e}')
    _budget_exceeded = False
    def track_api_call(provider, endpoint, status): pass

# ── SGO + Quota Gate: skip API calls when rate-limited or exhausted ──
def _sgo_rate_limited():
    """Check api_registry.json — return True if all SGO endpoints are 429."""
    reg_path = LOG_DIR / "api_registry.json"
    if not reg_path.exists():
        return False
    try:
        reg = json.loads(reg_path.read_text())
        sgo_eps = [e for e in reg.get("endpoints", []) if e.get("name", "").startswith("SGO ")]
        if not sgo_eps:
            return False
        return all(e.get("status_code") == 429 for e in sgo_eps)
    except Exception:
        return False

def _all_odds_keys_exhausted():
    """Return True if every known Odds API key is marked exhausted for today."""
    try:
        qs = quota_status()
        keys = qs.get("keys", [])
        if not keys:
            return False
        return all(k.get("exhausted") for k in keys)
    except Exception:
        return False

def _quota_cache_only():
    """Return True when we should skip live API calls entirely — all keys exhausted and cache is warm."""
    if not _all_odds_keys_exhausted():
        return False
    cache_dir = LOG_DIR / "cache" / "api"
    if not cache_dir.exists():
        return False
    cache_files = list(cache_dir.glob("*.json"))
    if not cache_files:
        return False
    now_epoch = __import__("time").time()
    for cf in cache_files:
        try:
            entry = json.loads(cf.read_text())
            age = now_epoch - entry.get("fetched_at_epoch", 0)
            if age < 7200:
                return True  # at least one cache entry is fresh (<2h)
        except Exception:
            continue
    return False

def fetch_live_slate(sport):
    """Fetch live slate for a sport. Returns games (future + recent)."""
    try:
        r = requests.get(
            f"{API_BASE}/api/tc",
            params={"sport": sport, "mode": "live-stats"},
            timeout=30,
            headers={"Accept": "application/json"},
        )
        if r.ok:
            return r.json()
        return {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def filter_future_games(games, sport):
    """Return only games that haven't been completed yet.

    ESPN sometimes surfaces recent games for ~12h after they end. For a daily
    betting log we only want UPCOMING games with active DK lines.
    """
    out = []
    for g in games or []:
        if g.get("completed"):
            continue
        # If a status field is set to "Final", drop it too
        st = (g.get("status") or "").lower()
        if "final" in st:
            continue
        out.append(g)
    return out

def _fetch_lines_via_registry(sport):
    """Look up the line_fetcher in sports_registry for this sport and call it.
    Returns a dict with at minimum {"games": [...], "source": "..."} or {} on failure.
    Never raises — returns {} if the sport has no line_fetcher or it errors.
    """
    try:
        from sports_registry import REGISTRY
        cfg = REGISTRY.get(sport)
        if not cfg or not cfg.line_fetcher:
            return {}
        result = cfg.line_fetcher(sport) or {}
        return result if isinstance(result, dict) else {}
    except Exception as e:
        print(f"  [line_fetcher] {sport} fetch failed: {e}")
        return {}


def _merge_lines_into_games(slate_entries, lines_games):
    """Merge spread/moneyline/total from lines_games into slate_entries by matchup key.
    Matchup key is f"{away}@{home}" (normalized to handle dict vs string away/home).
    Mutates slate_entries in place. Missing fields stay as None.
    """
    lines_by_matchup = {}
    for g in lines_games:
        if not g.get("away") or not g.get("home"):
            continue
        away_raw = g.get("away", {})
        home_raw = g.get("home", {})
        away = away_raw.get("team", "") if isinstance(away_raw, dict) else (away_raw if isinstance(away_raw, str) else "")
        home = home_raw.get("team", "") if isinstance(home_raw, dict) else (home_raw if isinstance(home_raw, str) else "")
        matchup = f"{away}@{home}"
        lines_by_matchup[matchup] = g
    for g in slate_entries:
        if not g.get("away") or not g.get("home"):
            continue
        away_raw = g.get("away", {})
        home_raw = g.get("home", {})
        away = away_raw.get("team", "") if isinstance(away_raw, dict) else (away_raw if isinstance(away_raw, str) else "")
        home = home_raw.get("team", "") if isinstance(home_raw, dict) else (home_raw if isinstance(home_raw, str) else "")
        matchup = f"{away}@{home}"
        src = lines_by_matchup.get(matchup)
        if not src:
            continue
        g["spread"] = src.get("spread")
        g["moneyline"] = src.get("moneyline")
        g["total"] = src.get("total")
        g["lines_source"] = src.get("source")


def fetch_game_projection(sport, away, home):
    """Look up the configured engine/fetcher for this sport and return a projection.
    Returns dict with keys:
    """
    try:
        r = requests.get(
            f"{API_BASE}/api/tc",
            params={"sport": sport, "away": away, "home": home, "mode": "project"},
            timeout=60,
            headers={"Accept": "application/json"},
        )
        if r.ok:
            return r.json()
        return {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def normalize_source(s):
    """Collapse pipeline-specific source labels to canonical DK/SGO/MOCK/SELF_EDGE."""
    s = (s or "").lower()
    if "draftkings" in s or s == "dk" or "sdio" in s:
        return "DK"
    if "sgo" in s or "oddsapi" in s:
        return "SGO"
    if "mock" in s:
        return "MOCK"
    if "self" in s or "edge" in s:
        return "SELF_EDGE"
    return s.upper() or "UNKNOWN"


def extract_picks(projection, sport, matchup):
    """Extract all valid prop picks from a projection response."""
    picks = []
    valid_props = projection.get("valid_props", [])
    for p in valid_props:
        # MLB/WC/NHL props don't have "valid" key — they're pre-filtered by the engine
        if "valid" in p and not p.get("valid"):
            continue
        picks.append({
            "date": now_et().strftime("%Y-%m-%d"),
            "league": sport,
            "matchup": matchup,
            "team": p.get("team"),
            "player": p.get("player"),
            "role": p.get("role"),
            "status": p.get("status"),
            "stat": p.get("stat"),
            "direction": p.get("direction"),
            "market_line": p.get("market_line"),
            "tc_projection": p.get("tc_projection"),
            "tc_target": p.get("tc_target"),
            "edge": p.get("edge"),
            "threshold": p.get("threshold"),
            "raw_average": p.get("raw_average"),
            "source": p.get("source"),
            "actual": p.get("actual"),
            "result": p.get("result", "PENDING"),
        })
    # For NBA/WNBA: if no valid props but odds are available, add a TOTAL pick placeholder
    if not picks and sport in BASKETBALL:
        odds = projection.get("odds", {})
        if odds.get("total") is not None:
            picks.append({
                "date": now_et().strftime("%Y-%m-%d"),
                "league": sport,
                "matchup": matchup,
                "team": "",
                "player": "TOTAL",
                "role": "GAME",
                "status": "ACTIVE",
                "stat": "TOTAL",
                "direction": "N/A",
                "market_line": odds.get("total"),
                "tc_projection": projection.get("tc_combined"),
                "tc_target": projection.get("tc_line"),
                "edge": projection.get("edge"),
                "threshold": None,
                "raw_average": None,
                "source": odds.get("ml_source", projection.get("source", "")),
                "actual": None,
                "result": "PENDING",
            })
    # For non-basketball: also add game-level pick if no player props yet
    elif not picks and sport not in BASKETBALL:
        odds = projection.get("odds", {})
        if odds.get("total") is not None:
            picks.append({
                "date": now_et().strftime("%Y-%m-%d"),
                "league": sport,
                "matchup": matchup,
                "team": "",
                "player": "TOTAL",
                "role": "GAME",
                "status": "ACTIVE",
                "stat": "TOTAL",
                "direction": "N/A",
                "market_line": odds.get("total"),
                "tc_projection": projection.get("tc_combined"),
                "tc_target": projection.get("tc_line"),
                "edge": projection.get("edge"),
                "threshold": None,
                "raw_average": None,
                "source": odds.get("ml_source", projection.get("source", "")),
                "actual": None,
                "result": "PENDING",
            })
    return picks

def extract_game_summary(projection, sport, matchup):
    """Extract top-line game summary — handles both basketball and multi-sport."""
    if sport in BASKETBALL:
        a = projection.get("assessment", {})
        return {
            "date": now_et().strftime("%Y-%m-%d"),
            "sport": sport,
            "matchup": matchup,
            "away_team": projection.get("away_team"),
            "home_team": projection.get("home_team"),
            "tc_combined": projection.get("tc_combined"),
            "tc_line": projection.get("tc_line"),
            "market_total": projection.get("market_total"),
            "dk_total": projection.get("dk_total"),
            "edge": projection.get("edge"),
            "signal": projection.get("signal"),
            "source": projection.get("source"),
            "valid_prop_count": len(projection.get("valid_props", [])),
            "roster_size": sum(projection.get("roster_counts", {}).values()) if projection.get("roster_counts") else None,
            "pending_props_no_dk": len(projection.get("prop_backtest", {}).get("rows", [])) - len([r for r in projection.get("prop_backtest", {}).get("rows", []) if r.get("market_line")]),
            "picks_with_dk": len([r for r in projection.get("prop_backtest", {}).get("rows", []) if r.get("market_line")]),
        }
    else:
        odds = projection.get("odds", {})
        roster_counts = projection.get("roster_counts", {})
        vp = projection.get("valid_props", [])
        return {
            "date": now_et().strftime("%Y-%m-%d"),
            "sport": sport,
            "matchup": matchup,
            "away_team": projection.get("away_team"),
            "home_team": projection.get("home_team"),
            "tc_combined": projection.get("tc_combined"),
            "tc_line": projection.get("tc_line"),
            "market_total": odds.get("total"),
            "dk_total": odds.get("total"),
            "edge": projection.get("edge"),
            "signal": projection.get("signal", "NO DK LINES"),
            "source": odds.get("ml_source", projection.get("source", "")),
            "valid_prop_count": len(vp),
            "roster_size": sum(roster_counts.values()) if roster_counts else 0,
            "pending_props_no_dk": 0,
            "picks_with_dk": len(vp),
        }

def run_daily_log(sports=ALL_SPORTS):
    """Run the full daily log capture. Filters out completed games."""
    now = now_et()
    today_dir = LOG_DIR / now.strftime("%Y-%m-%d")
    today_dir.mkdir(exist_ok=True)

    all_picks = []
    all_summaries = []
    errors = []
    skipped_completed = 0

    # ── Initialize fallback manager + dump quota status ──
    fm = FallbackManager()
    quota = quota_status()
    exhausted_keys = [k["key"] for k in quota.get("keys", []) if k["exhausted"]]
    if exhausted_keys:
        print(f"⚠️  Exhausted API keys: {', '.join(exhausted_keys)}")
    print(f"   Cache hits today: {quota.get('cache_hits_today', 0)}")

    # ── Quota gate: if all keys exhausted + cache warm, skip live API calls ──
    skip_live = _quota_cache_only()
    if skip_live:
        print("🛑 QUOTA GATE: All Odds API keys exhausted + warm cache — skipping live API calls")
    sgo_blocked = _sgo_rate_limited()
    if sgo_blocked:
        print("⚠️  SGO GATE: All SGO endpoints 429 rate-limited — skipping SGO calls")

    for sport in sports:
        print(f"[{now.strftime('%H:%M:%S')}] Fetching {sport} slate...")
        
        # ── WNBA: use dedicated TC engine ──
        if sport == "WNBA":
            from wnba_tc_engine import project_game, get_today_slate
            
            raw_games = get_today_slate()  # returns list of {away, home, status, completed, event_id}
            if not raw_games:
                print(f"  No games on slate for {sport} — skipping")
                (today_dir / f"slate_{sport}.json").write_text(json.dumps([], indent=2))
                continue

            games = [g for g in raw_games if not g.get("completed") and "final" not in (g.get("status","") or "").lower()]
            skipped_completed += len(raw_games) - len(games)

            # Conditional merge of market lines from the line_fetcher.
            # Only merge if we actually got non-empty data; otherwise log and continue.
            _lines = _fetch_lines_via_registry(sport)
            if _lines.get("games"):
                _merge_lines_into_games(raw_games, _lines["games"])
                print(f"  Merged lines for {len(_lines['games'])} game(s) from {_lines.get('source','?')}")
            elif _lines:
                print(f"  {sport} lines unavailable (source={_lines.get('source','none')}) — proceeding without market data")

            (today_dir / f"slate_{sport}.json").write_text(json.dumps({"games": raw_games}, indent=2))
            print(f"  Slate has {len(raw_games)} game(s); {len(games)} upcoming after filtering completed")

            for g in games:
                away = g.get("away", "")
                home = g.get("home", "")
                if not away or not home:
                    continue
                matchup = f"{away}@{home}"
                print(f"  Projecting {matchup}...")
                proj = project_game(away, home)
                if proj.get("mode") == "error":
                    errors.append(f"{sport} {matchup}: {proj.get('error', 'unknown')}")
                    continue

                # Enrich with DK lines via FallbackManager if available
                try:
                    enriched = fm.enrich(sport, away, home)
                    if enriched.get("player_lines"):
                        player_lines = enriched["player_lines"]
                        stat_map = {"PTS": "points", "REB": "rebounds", "AST": "assists",
                                    "3PM": "threes", "STL": "steals", "BLK": "blocks"}
                        matched = 0
                        for vp in proj.get("valid_props", []):
                            pl_name = vp.get("player", "")
                            stat_key = vp.get("stat", "")
                            dk_stat = stat_map.get(stat_key)
                            if not dk_stat or vp.get("market_line"):
                                continue
                            for dk_name in player_lines:
                                if pl_name == dk_name or pl_name in dk_name or dk_name in pl_name:
                                    if dk_stat in player_lines[dk_name]:
                                        vp["market_line"] = player_lines[dk_name][dk_stat]
                                        matched += 1
                                    break
                        if matched:
                            print(f"    → Merged: {matched} props received DK lines")
                        proj["enrichment"] = enriched
                except Exception as oe:
                    print(f"    ⚠️ Enrichment error: {oe}")

                # Save raw projection
                safe = matchup.replace("@", "_at_")
                (today_dir / f"proj_{sport}_{safe}.json").write_text(json.dumps(proj, indent=2, default=str))

                # Extract picks + summary
                picks = extract_picks(proj, sport, matchup)
                summary = extract_game_summary(proj, sport, matchup)
                pending = sum(1 for p in picks if p.get("market_line") in (None, ""))
                summary["pending_props_no_dk"] = pending
                summary["picks_with_dk"] = len(picks) - pending
                all_picks.extend(picks)
                all_summaries.append(summary)
                print(f"    -> {len(picks)} valid picks, signal={summary['signal']} (DK: {len(picks) - pending}, pending: {pending})")
            continue  # skip generic fetch for WNBA

        # ── WORLD CUP: load from local worldcup_picks.py output (no /api/tc live-stats) ──
        if sport in ("WORLD CUP", "WORLD_CUP", "SOCCER"):
            from soccer_tc_engine import project_matchup, get_worldcup_slate
            wc_slate = get_worldcup_slate()
            if not wc_slate:
                print(f"  No games on slate for {sport} — skipping")
                (today_dir / f"slate_{sport}.json").write_text(json.dumps([], indent=2))
                continue

            games = wc_slate.get("games", [])
            # For sports with no games today, skip gracefully
            if not games:
                print(f"  No games on slate for {sport} — skipping")
                # Still save empty slate
                (today_dir / f"slate_{sport}.json").write_text(json.dumps(wc_slate, indent=2))
                continue

            for g in games:
                # Normalize away/home — can be dict {team: "NY"} or plain string "NY"
                away_raw = g.get("away", {})
                home_raw = g.get("home", {})
                away = away_raw.get("team", "") if isinstance(away_raw, dict) else (away_raw if isinstance(away_raw, str) else "")
                home = home_raw.get("team", "") if isinstance(home_raw, dict) else (home_raw if isinstance(home_raw, str) else "")
                if not away or not home:
                    continue
                matchup = f"{away}@{home}"
                print(f"  Projecting {matchup}...")
                proj = project_matchup(away, home)
                if "error" in proj:
                    errors.append(f"{sport} {matchup}: {proj['error']}")
                    continue

                # ── Multi-tier enrichment via FallbackManager ──
                if sport in BASKETBALL:
                    enriched = None
                    try:
                        enriched = fm.enrich(sport, away, home)
                        tier = enriched.get("tier_used", "?")
                        src = enriched.get("source", "?")
                        pl_count = enriched.get("player_count", 0)
                        from_cache = enriched.get("_from_cache", enriched.get("from_cache", False))
                        cache_tag = " [cache]" if from_cache else ""
                        print(f"    → Enrichment: tier={tier}, source={src}, {pl_count} players{cache_tag}")

                        if enriched.get("player_lines"):
                            player_lines = enriched["player_lines"]
                            stat_map = {"PTS": "points", "REB": "rebounds", "AST": "assists",
                                        "3PM": "threes", "STL": "steals", "BLK": "blocks"}
                            matched = 0
                            for vp in proj.get("valid_props", []):
                                pl_name = vp.get("player", "")
                                stat_key = vp.get("stat", "")
                                dk_stat = stat_map.get(stat_key)
                                if not dk_stat:
                                    continue
                                for dk_name in player_lines:
                                    if pl_name == dk_name or pl_name in dk_name or dk_name in pl_name:
                                        if dk_stat in player_lines[dk_name]:
                                            vp["market_line"] = player_lines[dk_name][dk_stat]
                                            matched += 1
                                        break
                            print(f"    → Merged: {matched} props received DK lines")
                            proj["enrichment"] = enriched

                        # Fallback to consensus engine if Odds API gave partial/no lines
                        if not enriched.get("player_lines") or enriched.get("source") == "self_edge":
                            try:
                                cons = fetch_consensus_for_matchup(sport, away, home)
                                if cons and not cons.get("error") and cons.get("players"):
                                    cons_count = cons.get("player_count", 0)
                                    cons_books = cons.get("available_books", [])
                                    proj["consensus"] = cons
                                    print(f"    → Consensus fallback: {cons_count} players, {len(cons_books)} books")
                                    matched = 0
                                    for vp in proj.get("valid_props", []):
                                        if vp.get("market_line"):
                                            continue
                                        line = get_best_line(cons, vp.get("player", ""), vp.get("stat", ""))
                                        if line is not None:
                                            vp["market_line"] = line
                                            vp["consensus_source"] = cons.get("source", "unknown")
                                            matched += 1
                                    if matched:
                                        print(f"    → Consensus merged: {matched} props enriched")
                            except Exception as ce:
                                print(f"    ⚠️ Consensus fallback skipped: {ce}")

                    except Exception as oe:
                        print(f"    ⚠️ Enrichment error: {oe}")
                else:
                    # Non-basketball: log DK lines
                    odds = proj.get("odds", {})
                    if odds.get("total"):
                        print(f"    → DK lines: total={odds.get('total')}, spread={odds.get('home_spread')}, source={odds.get('ml_source', '?')}")
                    else:
                        print(f"    → No DK lines available ({odds.get('ml_source', odds.get('source', '?'))})")

                # Save raw projection
                safe = matchup.replace("@", "_at_")
                (today_dir / f"proj_{sport}_{safe}.json").write_text(json.dumps(proj, indent=2))

        else:
            slate = fetch_live_slate(sport)
            if "error" in slate:
                errors.append(f"{sport} slate: {slate['error']}")
                continue

            raw_games = slate.get("games", [])
            # For sports with no games today, skip gracefully
            if not raw_games:
                print(f"  No games on slate for {sport} — skipping")
                # Still save empty slate
                (today_dir / f"slate_{sport}.json").write_text(json.dumps(slate, indent=2))
                continue

            games = filter_future_games(raw_games, sport)
            skipped_completed += len(raw_games) - len(games)

            # Conditional merge of market lines from the line_fetcher.
            # Only merge if we actually got non-empty data; otherwise log and continue.
            _lines = _fetch_lines_via_registry(sport)
            if _lines.get("games"):
                _merge_lines_into_games(raw_games, _lines["games"])
                print(f"  Merged lines for {len(_lines['games'])} game(s) from {_lines.get('source','?')}")
            elif _lines:
                print(f"  {sport} lines unavailable (source={_lines.get('source','none')}) — proceeding without market data")

            # Save raw slate (full, including completed games, for backtest)
            (today_dir / f"slate_{sport}.json").write_text(json.dumps(slate, indent=2))
            print(f"  Slate has {len(raw_games)} game(s); {len(games)} upcoming after filtering completed")

            for g in games:
                # Normalize away/home — can be dict {team: "NY"} or plain string "NY"
                away_raw = g.get("away", {})
                home_raw = g.get("home", {})
                away = away_raw.get("team", "") if isinstance(away_raw, dict) else (away_raw if isinstance(away_raw, str) else "")
                home = home_raw.get("team", "") if isinstance(home_raw, dict) else (home_raw if isinstance(home_raw, str) else "")
                if not away or not home:
                    continue
                matchup = f"{away}@{home}"
                print(f"  Projecting {matchup}...")
                proj = fetch_game_projection(sport, away, home)
                if "error" in proj:
                    errors.append(f"{sport} {matchup}: {proj['error']}")
                    continue

                # ── Multi-tier enrichment via FallbackManager ──
                if sport in BASKETBALL:
                    enriched = None
                    try:
                        enriched = fm.enrich(sport, away, home)
                        tier = enriched.get("tier_used", "?")
                        src = enriched.get("source", "?")
                        pl_count = enriched.get("player_count", 0)
                        from_cache = enriched.get("_from_cache", enriched.get("from_cache", False))
                        cache_tag = " [cache]" if from_cache else ""
                        print(f"    → Enrichment: tier={tier}, source={src}, {pl_count} players{cache_tag}")

                        if enriched.get("player_lines"):
                            player_lines = enriched["player_lines"]
                            stat_map = {"PTS": "points", "REB": "rebounds", "AST": "assists",
                                        "3PM": "threes", "STL": "steals", "BLK": "blocks"}
                            matched = 0
                            for vp in proj.get("valid_props", []):
                                pl_name = vp.get("player", "")
                                stat_key = vp.get("stat", "")
                                dk_stat = stat_map.get(stat_key)
                                if not dk_stat:
                                    continue
                                for dk_name in player_lines:
                                    if pl_name == dk_name or pl_name in dk_name or dk_name in pl_name:
                                        if dk_stat in player_lines[dk_name]:
                                            vp["market_line"] = player_lines[dk_name][dk_stat]
                                            matched += 1
                                        break
                            print(f"    → Merged: {matched} props received DK lines")
                            proj["enrichment"] = enriched

                        # Fallback to consensus engine if Odds API gave partial/no lines
                        if not enriched.get("player_lines") or enriched.get("source") == "self_edge":
                            try:
                                cons = fetch_consensus_for_matchup(sport, away, home)
                                if cons and not cons.get("error") and cons.get("players"):
                                    cons_count = cons.get("player_count", 0)
                                    cons_books = cons.get("available_books", [])
                                    proj["consensus"] = cons
                                    print(f"    → Consensus fallback: {cons_count} players, {len(cons_books)} books")
                                    matched = 0
                                    for vp in proj.get("valid_props", []):
                                        if vp.get("market_line"):
                                            continue
                                        line = get_best_line(cons, vp.get("player", ""), vp.get("stat", ""))
                                        if line is not None:
                                            vp["market_line"] = line
                                            vp["consensus_source"] = cons.get("source", "unknown")
                                            matched += 1
                                    if matched:
                                        print(f"    → Consensus merged: {matched} props enriched")
                            except Exception as ce:
                                print(f"    ⚠️ Consensus fallback skipped: {ce}")

                    except Exception as oe:
                        print(f"    ⚠️ Enrichment error: {oe}")
                else:
                    # Non-basketball: log DK lines
                    odds = proj.get("odds", {})
                    if odds.get("total"):
                        print(f"    → DK lines: total={odds.get('total')}, spread={odds.get('home_spread')}, source={odds.get('ml_source', '?')}")
                    else:
                        print(f"    → No DK lines available ({odds.get('ml_source', odds.get('source', '?'))})")

                # Save raw projection
                safe = matchup.replace("@", "_at_")
                (today_dir / f"proj_{sport}_{safe}.json").write_text(json.dumps(proj, indent=2))

                # Extract picks + summary
                picks = extract_picks(proj, sport, matchup)
                summary = extract_game_summary(proj, sport, matchup)
                if sport in BASKETBALL:
                    pending = sum(1 for p in picks if p.get("market_line") in (None, ""))
                    summary["pending_props_no_dk"] = pending
                    summary["picks_with_dk"] = len(picks) - pending
                all_picks.extend(picks)
                all_summaries.append(summary)
                if sport in BASKETBALL:
                    print(f"    -> {len(picks)} valid picks, signal={summary['signal']} (DK: {len(picks) - pending}, pending: {pending})")
                else:
                    print(f"    -> {len(picks)} game-level entries, signal={summary['signal']}")

                # BOOKLINE sports (MLB/NHL/WC): bypass TC math, re-derive O/U from line vs proj
                if sport in BOOKLINE_SPORTS:
                    picks = generate_ou_picks(proj, sport, matchup, today_dir.name)
                else:
                    picks = extract_picks(proj, sport, matchup)
                summary = extract_game_summary(proj, sport, matchup)
                if sport in BASKETBALL:
                    pending = sum(1 for p in picks if p.get("market_line") in (None, ""))
                    summary["pending_props_no_dk"] = pending
                    summary["picks_with_dk"] = len(picks) - pending
                all_picks.extend(picks)
                all_summaries.append(summary)
                if sport in BASKETBALL:
                    print(f"    -> {len(picks)} valid picks, signal={summary['signal']} (DK: {len(picks) - pending}, pending: {pending})")
                else:
                    print(f"    -> {len(picks)} game-level entries, signal={summary['signal']}")

    # Dedup protection (in case of re-runs for same day)
    dedup_key = ["date", "player", "stat", "direction", "market_line", "matchup"]
    seen = set()
    deduped_picks = []
    for p in all_picks:
        k = tuple(str(p.get(c, "")) for c in dedup_key)
        if k in seen:
            continue
        seen.add(k)
        deduped_picks.append(p)
    all_picks = deduped_picks

    # Write flat CSV — deduplicated, keeping DK-enriched versions
    csv_path = today_dir / "picks.csv"
    csv_fields = [
        "date", "league", "matchup", "team", "player", "role", "status",
        "stat", "direction", "market_line", "tc_projection", "tc_target",
        "edge", "threshold", "raw_average", "source", "actual", "result",
    ]
    write_header = not csv_path.exists()
    with open(csv_path, "a" if csv_path.exists() else "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        if write_header:
            w.writeheader()
        for p in all_picks:
            row = {k: p.get(k, "") for k in csv_fields}
            row["source"] = normalize_source(row.get("source", ""))
            w.writerow(row)

    # Write structured picks
    (today_dir / "picks.json").write_text(json.dumps(all_picks, indent=2))
    (today_dir / "summaries.json").write_text(json.dumps(all_summaries, indent=2))

    # Write last_run summary
    last_run = {
        "timestamp": now.isoformat(),
        "sports": list(sports),
        "games_logged": len(all_summaries),
        "picks_logged": len(all_picks),
        "completed_games_skipped": skipped_completed,
        "errors": errors,
        "summaries": all_summaries,
    }
    (LOG_DIR / "last_run.json").write_text(json.dumps(last_run, indent=2))

    print(f"\nDone: {len(all_summaries)} games, {len(all_picks)} picks (skipped {skipped_completed} completed games)")
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors:
            print(f"  - {e}")

    # ── Build TC-enhanced DK combos (ALL active sports) ──
    try:
        from Projects.build_pregame_combos import build_combos, write_report
        from Projects.soccer_combo_engine import build_combo_legs_from_worldcup, build_combos as sc_build, _read_worldcup_picks, render_summary as sc_render

        combo_summary = []

        # Basketball games: WNBA, NBA (use DK combo engine)
        bk_sports = ["WNBA", "NBA"]
        bk_games = [(s["sport"], s["away_team"], s["home_team"]) for s in all_summaries if s["sport"] in bk_sports]
        if bk_games:
            print(f"\nBuilding TC combos for {len(bk_games)} basketball games...")
            for sport, away, home in bk_games:
                try:
                    r = build_combos(sport, away, home)
                except Exception as e:
                    r = {"sport": sport, "away": away, "home": home,
                         "legs": [], "qualified": [], "error": str(e)}
                safe = f"{away}_{home}".lower()
                write_report(r, today_dir / f"combos_{safe}.md", today_dir / f"combos_{safe}.json")
                combo_summary.append({
                    "matchup": f"{away}@{home}", "sport": sport,
                    "matched": r.get("matched_legs", 0),
                    "qualified": r.get("qualified_legs", 0),
                    "engine": "dk_combos",
                })
            print(f"Basketball combos: {sum(c['qualified'] for c in combo_summary if c.get('engine')=='dk_combos')} qualified legs across {len(bk_games)} games")

        # Soccer / World Cup games (use soccer_combo_engine)
        wc_games = [(s["sport"], s["away_team"], s["home_team"]) for s in all_summaries if s.get("sport") in ("WORLD_CUP", "WORLD CUP", "SOCCER")]
        print(f"  >> DEBUG: wc_games count = {len(wc_games)}, sports = {set(s.get("sport") for s in all_summaries)}")
        if wc_games:
            print(f"\nBuilding TC combos for {len(wc_games)} soccer/World Cup games...")
            picks_rows, wc_date = _read_worldcup_picks()
            all_legs = build_combo_legs_from_worldcup(picks_rows)
            wc_total = 0
            wc_qualified = []
            wc_total = 0
            wc_player_picks_path = today_dir / "soccer_player_picks.csv"
            if not wc_player_picks_path.exists():
                print("  [soccer] No soccer_player_picks.csv; skipping WC combos")
            else:
                import csv as _csv
                with open(wc_player_picks_path) as _f:
                    wc_rows = list(_csv.DictReader(_f))
                # Group by matchup
                from collections import defaultdict
                by_match = defaultdict(list)
                for r in wc_rows:
                    sig = (r.get("signal") or "PASS").upper()
                    if sig == "PASS":
                        continue
                    if float(r.get("tc_projection") or 0) <= 0:
                        continue
                    by_match[r["matchup"]].append(r)

                for matchup, rows in by_match.items():
                    # Parse "Away@Home"
                    try:
                        away, home = matchup.split("@")
                    except ValueError:
                        continue
                    qualified = []
                    for r in rows:
                        proj = float(r.get("tc_projection") or 0)
                        role = r.get("position") or ""
                        stat = r.get("stat") or ""
                        # Map CSV stat key to combo engine stat
                        stat_map = {
                            "G": "goals", "A": "assists", "S": "shots",
                            "SOT": "shots_on_target", "CORNERS": "corners",
                            "TKL": "tackles", "FL": "fouls", "CARD": "cards",
                            "PASS": "passes",
                        }
                        stat_combo = stat_map.get(stat, stat.lower())
                        mock_line = get_mock_market_line(proj, sport="WC", player_role=role)
                        sig_dir, sig_edge = self_edge_signal(proj, mock_line, sport="WC")
                        if sig_dir == "FLAT":
                            continue
                        # Convert edge to model_prob and implied prob for fake odds
                        model_prob = min(0.90, max(0.10, 0.5 + sig_edge))
                        # Fake odds: -110 baseline, shift by model prob
                        if model_prob >= 0.5:
                            odds = int(-100 * model_prob / (1 - model_prob))
                        else:
                            odds = int(100 * (1 - model_prob) / model_prob)
                        imp = abs(odds) / (abs(odds) + 100.0) if odds < 0 else 100.0 / (100.0 + odds)
                        edge = round(model_prob - imp, 4)
                        if edge < 0.02:
                            continue
                        qualified.append({
                            "player": r.get("player", ""),
                            "team": r.get("team", ""),
                            "role": role,
                            "stat": stat_combo,
                            "direction": sig_dir.lower() if sig_dir != "FLAT" else "over",
                            "dk_line": mock_line,
                            "dk_odds": str(odds),
                            "tc_projection": proj,
                            "raw_average": proj,
                            "edge": edge,
                            "threshold": SELF_EDGE_THRESHOLDS.get("WC", 0.035),
                            "qualifies_edge": True,
                            "source": "SELF_EDGE",
                            "matchup": matchup,
                            "match": matchup.replace("@", " @ "),
                            "commence": "",
                            "book": "self_edge",
                            "line": mock_line,
                            "odds": odds,
                            "model_prob": model_prob,
                        })
                    if qualified:
                        combo_summary.append({
                            "matchup": matchup,
                            "away_team": away,
                            "home_team": home,
                            "engine": "self_edge",
                            "legs": len(qualified),
                            "qualified": len(qualified),
                            "qualified_legs": qualified,
                        })
                        wc_total += len(qualified)
                        wc_qualified.extend(qualified)
            print(f"Soccer combos: {wc_total} self-edge legs across {len(by_match)} games")

        if combo_summary:
            (today_dir / "combos_summary.json").write_text(json.dumps(combo_summary, indent=2))

        # Self-edge WC picks → write to picks.csv directly (no DK lines)
        if "WORLD_CUP" in sports or "SOCCER" in sports:
            if today_dir.joinpath("soccer_player_picks.csv").exists():
                self_edge_rows = []
                import csv as _csv
                with open(today_dir / "soccer_player_picks.csv") as _f:
                    _r = _csv.DictReader(_f)
                    for row in _r:
                        sig = (row.get("signal") or "").upper()
                        if sig in ("OVER", "UNDER"):
                            self_edge_rows.append({
                                "date": row.get("date", ""),
                                "league": "WORLD_CUP",
                                "matchup": row.get("matchup", ""),
                                "team": row.get("team", ""),
                                "player": row.get("player", ""),
                                "role": row.get("position", ""),
                                "status": "starter" if row.get("is_starter", "").lower() == "true" else "bench",
                                "stat": row.get("stat", ""),
                                "direction": sig,
                                "market_line": row.get("tc_line", ""),
                                "tc_projection": row.get("tc_projection", ""),
                                "tc_target": row.get("tc_line", ""),
                                "edge": row.get("edge", ""),
                                "threshold": str(0.5),
                                "raw_average": row.get("tc_projection", ""),
                                "source": "SELF_EDGE",
                                "actual": "",
                                "result": "PENDING",
                            })
                if self_edge_rows:
                    csv_path = today_dir / "picks.csv"
                    csv_fields = [
                        "date", "league", "matchup", "team", "player", "role", "status",
                        "stat", "direction", "market_line", "tc_projection", "tc_target",
                        "edge", "threshold", "raw_average", "source", "actual", "result",
                    ]
                    write_header = not csv_path.exists()
                    with open(csv_path, "a" if csv_path.exists() else "w", newline="") as f:
                        w = _csv.DictWriter(f, fieldnames=csv_fields)
                        if write_header:
                            w.writeheader()
                        seen = set()
                        for r in self_edge_rows:
                            k = (r["date"], r["matchup"], r["player"], r["stat"], r["direction"])
                            if k in seen:
                                continue
                            seen.add(k)
                            w.writerow(r)
                    print(f"WC self-edge picks written: {len(self_edge_rows)} rows")

                print(f"Combos: {sum(c['qualified'] for c in combo_summary)} total qualified across {len(combo_summary)} games")
    except Exception as e:
        print(f"Combo builder: {e}")

    # ── Fantasy image cards (PNG output for dashboard) ──
    try:
        import subprocess
        from fantasy_images import make_cards, make_roundup
        sport_for_images = "WNBA" if "WNBA" in sports else (sports[0] if sports else None)
        cards, msg = make_cards(sport=sport_for_images, player_filter=None, max_n=10)
        if cards:
            print(f"🖼️  Fantasy cards: {len(cards)} generated — {msg}")
        roundup, rmsg = make_roundup(sport=sport_for_images)
        if roundup:
            print(f"🖼️  Roundup: {rmsg}")
    except Exception as img_err:
        print(f"⚠️ Fantasy images skipped: {img_err}")

    # ── Enhance: Position sizing + ML scoring + historical tracking ──
    try:
        import sys as _esp
        # Remove any conflicting src packages (e.g. tc-sports-app) before importing enhance_picks
        _workspace = str(WORKSPACE)
        for _p in [_p for _p in _esp.path if _p and __import__('os').path.isdir(__import__('os').path.join(_p, 'src', 'domain')) and not __import__('os').path.isfile(__import__('os').path.join(_p, 'src', 'domain', 'enhance_picks.py'))]:
            _esp.path.remove(_p)
        if _workspace not in _esp.path:
            _esp.path.insert(0, _workspace)
        if str(WORKSPACE / "Projects") not in _esp.path:
            _esp.path.insert(0, str(WORKSPACE / "Projects"))
        from src.domain.enhance_picks import enhance
        tracker_db = LOG_DIR / "tc_history.sqlite"
        enhanced_count = 0
        for sport_dir in today_dir.glob("proj_*.json"):
            try:
                data = json.loads(sport_dir.read_text())
                picks_in = data.get("picks") if isinstance(data, dict) else data
                if not picks_in:
                    continue
                result = enhance(picks_in, bankroll=10000.0, db_path=str(tracker_db))
                out_path = sport_dir.parent / f"wiring_{sport_dir.stem.replace('proj_', '')}.json"
                out_path.write_text(json.dumps(result, indent=2, default=str))
                enhanced_count += len(result.get("positions", []))
            except Exception as inner_err:
                print(f"  ⚠️ enhance {sport_dir.name}: {inner_err}")
        if enhanced_count:
            print(f"📐 Enhanced {enhanced_count} picks → wiring_*.json (size+ML+history)")
    except Exception as enhance_err:
        import traceback
        import sys as _diag_sys
        print(f"⚠️ enhance_picks: {enhance_err}")
        print(f"   sys.path[0:5]: {_diag_sys.path[:5]}")
        print(f"   cwd: {__import__('os').getcwd()}")
        traceback.print_exc()

    return last_run

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TC Sports Daily Picks")
    parser.add_argument("--sport", required=True, choices=["NBA", "WNBA", "NFL", "MLB", "SOCCER", "NHL", "WORLD_CUP"],
                        help="Sport to generate picks for")
    parser.add_argument("--date", default=now_et().strftime("%Y-%m-%d"),
                        help="Date in YYYY-MM-DD format (default: today ET)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print projections without saving")
    args = parser.parse_args()
    sports = (args.sport,)
    # override today with --date for downstream capture
    os.environ["TC_RUN_DATE"] = args.date
    if args.dry_run:
        os.environ["TC_DRY_RUN"] = "1"
    run_daily_log(sports)
