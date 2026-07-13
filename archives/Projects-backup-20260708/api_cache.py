"""Unified API cache + batch layer.

Goal: cut total API calls/day from ~4,000 to <500.

Strategy:
  - SGO: fetch ONCE per (sport, day) — full odds dump, cache to JSON
  - OddsAPI: fetch ONCE per game (event_id), cache
  - ESPN: fetch ONCE per event_id (scoreboard/boxscore/summary), cache
  - In-memory + disk cache keyed by URL+params
  - TTL: 6h live / 30d final
"""
import json
import os
import time
import hashlib
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

CACHE_DIR = Path("/home/workspace/Daily_Log/.api_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CALL_LOG_PATH = CACHE_DIR / "calls.jsonl"
_MEM: Dict[str, Tuple[float, Any]] = {}

DEFAULT_TTL_LIVE = 6 * 3600
DEFAULT_TTL_FINAL = 30 * 24 * 3600


def _key(url: str, params: Optional[dict] = None) -> str:
    raw = url + "?" + json.dumps(params or {}, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def _disk_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def cached_get(url: str, params: Optional[dict] = None, ttl_seconds: int = DEFAULT_TTL_LIVE, headers: Optional[dict] = None, timeout: int = 8) -> Optional[Any]:
    """Fetch URL with disk+memory cache. Returns parsed JSON or None on failure."""
    key = _key(url, params)
    now = time.time()

    if key in _MEM:
        ts, data = _MEM[key]
        if now - ts < ttl_seconds:
            return data

    p = _disk_path(key)
    if p.exists():
        try:
            blob = json.loads(p.read_text())
            if now - blob.get("ts", 0) < ttl_seconds:
                data = blob.get("data")
                _MEM[key] = (now, data)
                return data
        except Exception:
            pass

    try:
        qs = urllib.parse.urlencode(params) if params else ""
        full = f"{url}?{qs}" if qs else url
        hdrs = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(full, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
        except Exception:
            data = {"_raw": body}
        _MEM[key] = (now, data)
        p.write_text(json.dumps({"ts": now, "url": url, "params": params, "data": data}))
        return data
    except Exception as e:
        return None


def log_call(provider: str, endpoint: str) -> None:
    """Append a single network call to the daily call log."""
    try:
        with CALL_LOG_PATH.open("a") as f:
            f.write(json.dumps({"ts": time.time(), "provider": provider, "endpoint": endpoint}) + "\n")
    except Exception:
        pass


def cache_stats(today_only: bool = True) -> Dict[str, Any]:
    """Return {provider: count} for today (UTC)."""
    stats = {"ESPN": 0, "SGO": 0, "OddsAPI": 0, "OTHER": 0, "total": 0, "date": time.strftime("%Y-%m-%d", time.gmtime())}
    if not CALL_LOG_PATH.exists():
        return stats
    today = time.strftime("%Y-%m-%d", time.gmtime())
    try:
        for line in CALL_LOG_PATH.read_text().splitlines()[-5000:]:
            try:
                rec = json.loads(line)
                ts = rec.get("ts", 0)
                day = time.strftime("%Y-%m-%d", time.gmtime(ts))
                if today_only and day != today:
                    continue
                prov = rec.get("provider", "OTHER").upper()
                if prov not in ("ESPN", "SGO", "ODDSAPI"):
                    prov = "OTHER"
                stats[prov] = stats.get(prov, 0) + 1
                stats["total"] += 1
            except Exception:
                continue
    except Exception:
        pass
    return stats


def reset_call_log() -> None:
    try:
        CALL_LOG_PATH.unlink()
    except Exception:
        pass