"""MLB book (sportsbook) odds fetcher with caching and fallback."""
from __future__ import annotations
import os, json, time, hashlib
from pathlib import Path
from typing import Dict, List, Optional
import requests

CACHE_DIR = Path("/home/workspace/Daily_Log/odds_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL = int(os.getenv("ODDS_CACHE_TTL", "300"))

BOOKS = ["draftkings", "fanduel", "betmgm", "pointsbet", "caesars"]


def _cache_key(sport: str, market: str) -> str:
    return hashlib.md5(f"{sport}:{market}".encode()).hexdigest()


def _read_cache(key: str) -> Optional[dict]:
    p = CACHE_DIR / f"{key}.json"
    if not p.exists():
        return None
    if time.time() - p.stat().st_mtime > CACHE_TTL:
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _write_cache(key: str, data: dict) -> None:
    (CACHE_DIR / f"{key}.json").write_text(json.dumps(data, indent=2))


def fetch_mlb_moneyline(date_str: str, api_key: Optional[str] = None) -> Dict[str, dict]:
    """Fetch MLB moneylines from multiple books. Falls back to empty dict on quota error."""
    key = _cache_key("mlb_ml", date_str)
    cached = _read_cache(key)
    if cached is not None:
        return cached
    api_key = api_key or os.getenv("ODDS_API_KEY")
    if not api_key:
        return {"games": [], "source": "no_key"}
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    try:
        r = requests.get(url, params={"apiKey": api_key, "regions": "us", "markets": "h2h", "dateFormat": "iso"}, timeout=10)
        if r.status_code == 401:
            return {"games": [], "source": "quota_exhausted"}
        if r.status_code != 200:
            return {"games": [], "source": f"http_{r.status_code}"}
        data = r.json()
        out = {"games": data, "source": "odds_api", "fetched_at": time.time()}
        _write_cache(key, out)
        return out
    except Exception as e:
        return {"games": [], "source": "error", "error": str(e)}


def fetch_mlb_totals(date_str: str, api_key: Optional[str] = None) -> Dict[str, dict]:
    """Fetch MLB over/under totals (game lines)."""
    key = _cache_key("mlb_totals", date_str)
    cached = _read_cache(key)
    if cached is not None:
        return cached
    api_key = api_key or os.getenv("ODDS_API_KEY")
    if not api_key:
        return {"games": [], "source": "no_key"}
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    try:
        r = requests.get(url, params={"apiKey": api_key, "regions": "us", "markets": "totals", "dateFormat": "iso"}, timeout=10)
        if r.status_code == 401:
            return {"games": [], "source": "quota_exhausted"}
        if r.status_code != 200:
            return {"games": [], "source": f"http_{r.status_code}"}
        data = r.json()
        out = {"games": data, "source": "odds_api", "fetched_at": time.time()}
        _write_cache(key, out)
        return out
    except Exception as e:
        return {"games": [], "source": "error", "error": str(e)}


if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else "2026-07-13"
    print(json.dumps(fetch_mlb_moneyline(d), indent=2)[:500])
