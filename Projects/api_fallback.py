#!/usr/bin/env python3
"""
TC API Fallback Manager — Multi-tier fail-safe for daily_picks.py

Tier architecture:
  Tier 0: Disk cache (per-game, daily) — ZERO API calls
  Tier 1: SGO (MLB only) — zero Odds API cost
  Tier 4: Self-edge (internal TC projections, no market verification)

Quota detection: when Odds API returns OUT_OF_USAGE_CREDITS, the key is
marked exhausted for the day and skipped on retry.

Usage:
  from api_fallback import FallbackManager
  fm = FallbackManager()
  result = fm.enrich(sport, away, home)
"""

import json
import os
import sys
import time
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add SGO cache module path
sys.path.insert(0, str(Path("/home/workspace")))
from Cache.sgo.cache import sgo_get

CACHE_DIR = Path("/home/workspace/Daily_Log/cache/odds")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
QUOTA_FILE = Path("/home/workspace/Daily_Log/cache/quota_exhausted.json")

# ── Private: load all Odds API keys from env ─────────────
def _load_keys():
    keys = []
    # Scan ODDS_API_KEY and any env var with ODDS in the name
    for env_name, val in os.environ.items():
        if 'ODDS' in env_name.upper():
            val = val.strip()
            if val and len(val) > 10:
                keys.append({"key": val, "label": env_name, "exhausted": False})
    # Also scan secrets file
    sf = Path("/root/.zo/secrets.env")
    if sf.exists():
        for line in sf.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if 'ODDS' in k.upper() and v and len(v) > 10:
                already = any(x["key"] == v for x in keys)
                if not already:
                    keys.append({"key": v, "label": k, "exhausted": False})
    return keys

def _load_quota():
    if QUOTA_FILE.exists():
        try:
            return json.loads(QUOTA_FILE.read_text())
        except Exception:
            pass
    return {}

def _save_quota(q):
    QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUOTA_FILE.write_text(json.dumps(q, indent=2))

def _is_quota_exhausted(key_label):
    q = _load_quota()
    entry = q.get(key_label, {})
    if not entry:
        return False
    marked = entry.get("marked_at", "")
    try:
        mt = datetime.fromisoformat(marked)
        now = datetime.now(timezone.utc)
        if (now - mt).total_seconds() < 86400:  # 24h exhaustion window
            return True
    except Exception:
        pass
    return False

def _mark_quota_exhausted(key_label):
    q = _load_quota()
    q[key_label] = {"exhausted": True, "marked_at": datetime.now(timezone.utc).isoformat()}
    _save_quota(q)

def _clear_quota(key_label):
    q = _load_quota()
    q.pop(key_label, None)
    _save_quota(q)

class FallbackManager:
    """Manages multi-tier API fallback with caching and quota awareness."""

    def __init__(self):
        self.keys = _load_keys()
        self._today = datetime.now().strftime("%Y-%m-%d")
        self.sgo_key = os.environ.get("SGO_API_KEY", "")

    # ── Cache ─────────────────────────────────────────
    def _cache_path(self, sport, away, home):
        safe = f"{away}_{home}".replace(" ", "_").replace("@", "_at_")
        d = CACHE_DIR / self._today
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{sport.lower()}_{safe}.json"

    def _cache_get(self, sport, away, home):
        p = self._cache_path(sport, away, home)
        if p.exists():
            try:
                data = json.loads(p.read_text())
                age = time.time() - p.stat().st_mtime
                if age < 7200:  # 2-hour freshness window
                    data["_from_cache"] = True
                    return data
            except Exception:
                pass
        return None

    def _cache_set(self, sport, away, home, data):
        p = self._cache_path(sport, away, home)
        clean = {k: v for k, v in data.items() if not k.startswith("_")}
        p.write_text(json.dumps(clean, indent=2, default=str))

    # ── Tier 2+3: Odds API ────────────────────────────

    def enrich(self, sport: str, away: str, home: str):
        """Multi-tier: cache → Odds API → self-edge fallback."""
        # Tier 0: try cache
        data = self._cache_get(sport, away, home)
        if data is not None:
            return data

        # Map sport to Odds API sport key
        ODDS_SPORT = {
            "WNBA": "basketball_wnba",
            "NBA": "basketball_nba",
            "MLB": "baseball_mlb",
            "NHL": "icehockey_nhl",
        }
        sport_key = ODDS_SPORT.get(sport, "")
        if not sport_key:
            return {"sport": sport, "away": away, "home": home, "source": "unsupported-sport"}

        # Try each available key
        ODDS_BASE = "https://api.the-odds-api.com/v4/sports"
        for entry in self.keys:
            if entry["exhausted"]:
                continue
            key = entry["key"]
            try:
                # Step 1: Find the event ID for this matchup
                r = requests.get(
                    f"{ODDS_BASE}/{sport_key}/odds",
                    params={
                        "apiKey": key,
                        "regions": "us",
                        "dateFormat": "iso",
                    },
                    timeout=15,
                )
                if r.status_code == 401:
                    entry["exhausted"] = True
                    _mark_quota_exhausted(entry["label"])
                    continue
                if r.status_code not in (200, 422):
                    continue

                games = r.json() if isinstance(r.json, type) else r.json()
                if isinstance(games, dict) and "data" in games:
                    games = games["data"]
                if not isinstance(games, list):
                    continue

                event_id = None
                for g in games:
                    ga = (g.get("away_team") or "").upper()
                    gh = (g.get("home_team") or "").upper()
                    if away.upper() in ga and home.upper() in gh:
                        event_id = g.get("id")
                        break

                if not event_id:
                    continue

                # Step 2: Fetch player props for this event
                markets = "player_points,player_rebounds,player_assists,player_threes,player_steals,player_blocks"
                r2 = requests.get(
                    f"{ODDS_BASE}/{sport_key}/events/{event_id}/odds",
                    params={
                        "apiKey": key,
                        "regions": "us",
                        "markets": markets,
                        "bookmakers": "draftkings",
                        "oddsFormat": "american",
                    },
                    timeout=15,
                )
                if r2.status_code != 200:
                    continue

                odds_data = r2.json()
                player_lines = {}
                stat_map = {
                    "player_points": "points", "player_rebounds": "rebounds",
                    "player_assists": "assists", "player_threes": "threes",
                    "player_steals": "steals", "player_blocks": "blocks",
                }

                for bm in odds_data.get("bookmakers", []):
                    if bm.get("key") != "draftkings":
                        continue
                    for market in bm.get("markets", []):
                        mkey = market.get("key", "")
                        stat = stat_map.get(mkey)
                        if not stat:
                            continue
                        for outcome in market.get("outcomes", []):
                            name = outcome.get("description") or outcome.get("name", "")
                            line = outcome.get("point")
                            if name and line is not None:
                                try:
                                    line = float(line)
                                except (TypeError, ValueError):
                                    continue
                                if name not in player_lines:
                                    player_lines[name] = {}
                                player_lines[name][stat] = line

                result = {
                    "sport": sport,
                    "away": away,
                    "home": home,
                    "event_id": event_id,
                    "source": f"odds-api ({entry['label']})",
                    "player_lines": player_lines,
                    "player_count": len(player_lines),
                    "tier_used": entry["label"],
                    "available_books": ["draftkings"],
                }
                self._cache_set(sport, away, home, result)
                return result

            except Exception:
                continue

        # Tier 4: self-edge fallback
        return {"sport": sport, "away": away, "home": home, "source": "self-edge"}

# ── Quota status CLI ───────────────────────────────────
def quota_status():
    """Return dict of all keys and their exhaustion status."""
    keys = _load_keys()
    q = _load_quota()
    out = []
    for entry in keys:
        label = entry["label"]
        exhausted = _is_quota_exhausted(label)
        marked = q.get(label, {}).get("marked_at", "")
        out.append({"key": label, "exhausted": exhausted, "marked_at": marked,
                     "key_prefix": entry["key"][:12] + "..."})
    return {"keys": out, "cache_hits_today": _count_cache_files()}

def _count_cache_files():
    today = datetime.now().strftime("%Y-%m-%d")
    d = CACHE_DIR / today
    if d.exists():
        return len(list(d.glob("*.json")))
    return 0

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 4:
        sport, away, home = sys.argv[1], sys.argv[2], sys.argv[3]
        fm = FallbackManager()
        result = fm.enrich(sport, away, home)
        print(json.dumps(result, indent=2, default=str))
    else:
        print(json.dumps(quota_status(), indent=2))
