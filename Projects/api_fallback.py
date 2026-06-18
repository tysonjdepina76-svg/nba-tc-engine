#!/usr/bin/env python3
"""
TC API Fallback Manager — Multi-tier fail-safe for daily_picks.py

Tier architecture:
  Tier 0: Disk cache (per-game, daily) — ZERO API calls
  Tier 1: SGO (MLB only) — zero Odds API cost
  Tier 2: ODDS_API_KEY (primary, $25/mo)
  Tier 3: ODDS_API_KEY_FREE (free tier, 500 req/mo)
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
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

CACHE_DIR = Path("/home/workspace/Daily_Log/cache/odds")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
QUOTA_FILE = Path("/home/workspace/Daily_Log/cache/quota_exhausted.json")

ODDS_BASE = "https://api.the-odds-api.com/v4"

# ── Private: load all Odds API keys from env ─────────────
def _load_keys():
    keys = []
    for env_name in ["ODDS_API_KEY", "ODDS_API_KEY_FREE", "ODDS_API_KEY_BACKUP"]:
        val = os.environ.get(env_name, "").strip()
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
            if k.startswith("ODDS_API_KEY") and v and len(v) > 10:
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
        self._sgo_key = os.environ.get("SPORTSGAMEODDS_API_KEY",
                                        os.environ.get("SGO_API_KEY", ""))

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
    def _call_odds_api(self, endpoint, params, key_label):
        """Return (data, exhausted_bool)."""
        import requests
        full_url = f"{ODDS_BASE}/{endpoint}"
        try:
            r = requests.get(full_url, params=params, timeout=20)
            if r.status_code == 401:
                body = r.text
                if "OUT_OF_USAGE_CREDITS" in body or "QUOTA" in body.upper():
                    _mark_quota_exhausted(key_label)
                    return None, True
                return None, False
            r.raise_for_status()
            return r.json(), False
        except requests.exceptions.RequestException:
            return None, False

    def _try_odds_keys(self, endpoint, params_fn):
        """Try all non-exhausted Odds API keys. Returns (data, key_used)."""
        import requests
        for entry in self.keys:
            label = entry["label"]
            if _is_quota_exhausted(label):
                continue
            key = entry["key"]
            p = params_fn(key)
            data, exhausted = self._call_odds_api(endpoint, p, label)
            if exhausted:
                continue  # try next key
            if data is not None:
                return data, label
        return None, None

    def _find_game_odds(self, sport, away, home):
        """Tier 2+3: Find game via Odds API sports endpoint."""
        sport_key_map = {
            "NBA": "basketball_nba", "WNBA": "basketball_wnba",
            "MLB": "baseball_mlb", "NHL": "icehockey_nhl",
        }
        sk = sport_key_map.get(sport.upper())
        if not sk:
            return None, None

        team_map = {
            "WNBA": {
                "ATL": "atlanta dream", "CHI": "chicago sky", "CON": "connecticut sun",
                "DAL": "dallas wings", "GS": "golden state valkyries", "IND": "indiana fever",
                "LV": "las vegas aces", "LA": "los angeles sparks", "MIN": "minnesota lynx",
                "NY": "new york liberty", "PHX": "phoenix mercury", "POR": "portland fire",
                "SEA": "seattle storm", "TOR": "toronto tempo", "WSH": "washington mystics",
            }
        }
        tmap = team_map.get(sport.upper(), {})

        def norm(n):
            if not n:
                return ""
            nx = n.lower().strip()
            for sfx in [" sky", " liberty", " fever", " dream", " mercury", " wings",
                         " aces", " storm", " tempo", " mystics", " valkyries", " fire",
                         " lynx", " sun", " sparks"]:
                nx = nx.replace(sfx, "")
            return nx.strip()

        def params_fn(key):
            return {
                "apiKey": key, "regions": "us",
                "markets": "h2h,spreads,totals", "oddsFormat": "decimal",
                "commenceTimeFrom": (datetime.now(timezone.utc) - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "commenceTimeTo": (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        data, key_used = self._try_odds_keys(f"sports/{sk}/odds", params_fn)
        if not data:
            return None, None

        a, h = norm(away), norm(home)
        games = data if isinstance(data, list) else []
        for g in games:
            gh, ga = norm(g.get("home_team")), norm(g.get("away_team"))
            if gh == h and ga == a:
                return g, key_used

        away_full = tmap.get(away.upper(), "").lower()
        home_full = tmap.get(home.upper(), "").lower()
        for g in games:
            gf = (g.get("away_team") or "").lower()
            ghf = (g.get("home_team") or "").lower()
            if away_full and away_full in gf and home_full and home_full in ghf:
                return g, key_used
            if a.lower() in gf and h.lower() in ghf:
                return g, key_used
            if away_full and away_full in gf and h.lower() in ghf:
                return g, key_used

        return None, None

    def _fetch_player_props(self, sport, game_id, key_used):
        """Fetch player props for a specific game."""
        sport_key_map = {
            "NBA": "basketball_nba", "WNBA": "basketball_wnba",
        }
        sk = sport_key_map.get(sport.upper())
        if not sk:
            return None

        stat_map_rev = {
            "player_points": "points", "player_rebounds": "rebounds",
            "player_assists": "assists", "player_threes": "threes",
            "player_steals": "steals", "player_blocks": "blocks",
        }

        def params_fn(key):
            return {
                "apiKey": key, "regions": "us",
                "markets": "player_points,player_rebounds,player_assists,player_threes,player_steals,player_blocks",
                "oddsFormat": "decimal",
            }

        data, _ = self._try_odds_keys(
            f"sports/{sk}/events/{game_id}/odds", params_fn
        )
        if not data:
            return None

        lines = {}
        for bk in data.get("bookmakers", []):
            if bk.get("key") != "draftkings":
                continue
            for m in bk.get("markets", []):
                stat = stat_map_rev.get(m.get("key", ""))
                if not stat:
                    continue
                for o in m.get("outcomes", []):
                    name = o.get("description", o.get("name", ""))
                    if o.get("name") == "Over":
                        lines.setdefault(name, {})[stat] = o.get("point")
        return lines

    # ── Tier 1: SGO (MLB only) ─────────────────────────
    def _sgo_mlb_enrich(self, away, home):
        """Fetch MLB lines from SGO — zero Odds API cost."""
        if not self._sgo_key:
            return {"error": "No SGO key", "player_lines": {}, "source": "sgo_error"}
        try:
            import requests
            r = requests.get(
                "https://api.sportsgameodds.com/v2/events",
                params={"leagueID": "MLB"},
                headers={"x-api-key": self._sgo_key},
                timeout=15,
            )
            if r.status_code == 429:
                return {"error": "SGO rate limited", "player_lines": {}, "source": "sgo_rate_limit"}
            r.raise_for_status()
            events = r.json()
            if not isinstance(events, list):
                return {"error": "SGO bad format", "player_lines": {}, "source": "sgo_bad_format"}

            a, h = away.upper(), home.upper()
            ev = None
            for e in events:
                ea = (e.get("awayTeam") or "").upper()
                eh = (e.get("homeTeam") or "").upper()
                if a in ea and h in eh:
                    ev = e
                    break

            if not ev:
                return {"error": f"MLB {away}@{home} not in SGO", "player_lines": {}, "source": "sgo_not_found"}

            eid = ev.get("eventID", ev.get("id", ""))
            if not eid:
                return {"error": "SGO no event ID", "player_lines": {}, "source": "sgo_no_id"}

            r2 = requests.get(
                f"https://api.sportsgameodds.com/v2/events/{eid}/odds",
                headers={"x-api-key": self._sgo_key},
                timeout=15,
            )
            if r2.status_code == 429:
                return {"error": "SGO rate limited", "player_lines": {}, "source": "sgo_rate_limit"}
            r2.raise_for_status()
            odds_data = r2.json()

            total = odds_data.get("total", odds_data.get("totals", {}))
            spread = odds_data.get("spread", odds_data.get("spreads", {}))
            ml = odds_data.get("moneyline", odds_data.get("h2h", {}))

            return {
                "game_odds": {"total": total, "spread": spread, "ml": ml},
                "player_lines": {},
                "player_count": 0,
                "source": "sgo",
                "sgo_event_id": eid,
            }
        except Exception as e:
            return {"error": str(e), "player_lines": {}, "source": "sgo_error"}

    # ── Main entry point ───────────────────────────────
    def enrich(self, sport, away, home):
        """
        Multi-tier enrichment for a single game.
        Returns dict with: game_odds, player_lines, source, tier_used, from_cache
        """
        # Tier 0: Cache
        cached = self._cache_get(sport, away, home)
        if cached:
            cached["tier_used"] = "cache"
            return cached

        result = {"player_lines": {}, "source": "none", "tier_used": "none", "from_cache": False}

        # MLB → Tier 1: SGO
        if sport.upper() == "MLB":
            sgo = self._sgo_mlb_enrich(away, home)
            if sgo and not sgo.get("error"):
                result.update(sgo)
                result["tier_used"] = "sgo"
                self._cache_set(sport, away, home, result)
                return result
            result["sgo_error"] = sgo.get("error", "unknown")

        # Tier 2+3: Odds API (basketball player props)
        if sport.upper() in ("WNBA", "NBA"):
            game, key_used = self._find_game_odds(sport, away, home)
            if game and key_used:
                result["game_odds"] = {
                    "home": game.get("home_team"),
                    "away": game.get("away_team"),
                }
                game_id = game.get("id")
                if game_id:
                    lines = self._fetch_player_props(sport, game_id, key_used)
                    if lines:
                        result["player_lines"] = lines
                        result["player_count"] = len(lines)
                        result["source"] = "odds_api"
                        result["tier_used"] = key_used
                        result["book"] = "draftkings"
                        self._cache_set(sport, away, home, result)
                        return result

                # Game found but props failed → still cache partial
                result["source"] = "odds_api_partial"
                result["tier_used"] = key_used
                self._cache_set(sport, away, home, result)
                return result

        # Tier 4: Self-edge (everything failed)
        result["source"] = "self_edge"
        result["tier_used"] = "self_edge"
        result["fallback"] = True
        return result


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
