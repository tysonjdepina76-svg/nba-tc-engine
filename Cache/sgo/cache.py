#!/usr/bin/env python3
"""
SGO 6-Hour Cache
Caches all SportsGameOdds API responses on disk. When fresh (< 6hr),
returns cached data in ~1-2ms. When stale, makes live call and updates cache.

Usage:
    from Cache.sgo.cache import sgo_get, sgo_cache_stats

    resp = sgo_get("/v2/events", params={"leagueID": "MLB"})
    data = resp["data"]  # parsed JSON

    resp = sgo_get(f"/v2/events/{eid}/odds")
    stats = sgo_cache_stats()
"""

import hashlib
import json
import os
import time
from pathlib import Path

import requests

CACHE_DIR = Path("/home/workspace/Cache/sgo")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

TTL = 6 * 3600     # 6 hours in seconds
SGO_BASE = "https://api.sportsgameodds.com"

def _load_sgo_key():
    """Load SGO key from secrets, stripping any leading garbage."""
    val = os.environ.get("SPORTSGAMEODDS_API_KEY", "")
    if not val:
        sf = Path("/root/.zo/secrets.env")
        if sf.exists():
            for line in sf.read_text().splitlines():
                line = line.strip()
                if line.startswith("SPORTSGAMEODDS_API_KEY"):
                    _, _, v = line.partition("=")
                    val = v.strip().strip('"').strip("'")
                    break
    return val.strip() if val else ""


def _cache_key(url_path, params):
    """Deterministic cache filename from URL path + sorted query params."""
    key_str = url_path
    if params:
        sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        key_str += f"?{sorted_params}"
    h = hashlib.md5(key_str.encode()).hexdigest()
    return h[:16]


def sgo_get(url_path, params=None, ttl_seconds=TTL):
    """
    Cached SGO GET — 6-hour TTL by default.

    Returns dict:
        {"data": <parsed JSON>, "from_cache": True/False, "age_seconds": N,
         "status_code": int, "url": str}
    On failure:
        {"error": "...", "from_cache": False}
    """
    key = _cache_key(url_path, params)
    cache_file = CACHE_DIR / f"{key}.json"
    now = time.time()

    # Check cache
    if cache_file.exists():
        try:
            entry = json.loads(cache_file.read_text())
            age = now - entry.get("fetched_at_epoch", 0)
            if age < ttl_seconds:
                return {
                    "data": entry.get("data"),
                    "from_cache": True,
                    "age_seconds": round(age, 1),
                    "fetched_at_epoch": entry.get("fetched_at_epoch"),
                    "status_code": entry.get("status_code", 200),
                    "url": entry.get("url", ""),
                }
        except (json.JSONDecodeError, KeyError):
            cache_file.unlink(missing_ok=True)

    # Live call
    sgo_key = _load_sgo_key()
    if not sgo_key:
        return {"error": "No SGO key configured", "from_cache": False}

    full_url = f"{SGO_BASE}{url_path}"
    try:
        r = requests.get(
            full_url,
            params=params or {},
            headers={"x-api-key": sgo_key},
            timeout=15,
        )
        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text[:2000]}

        if r.status_code == 200:
            entry = {
                "fetched_at_epoch": now,
                "status_code": r.status_code,
                "url": full_url,
                "params": params,
                "data": data,
            }
            cache_file.write_text(json.dumps(entry, indent=2))

        return {
            "data": data,
            "from_cache": False,
            "age_seconds": 0,
            "status_code": r.status_code,
            "url": full_url,
        }
    except Exception as e:
        # If live call fails but we have stale cache, return it
        if cache_file.exists():
            try:
                entry = json.loads(cache_file.read_text())
                age = now - entry.get("fetched_at_epoch", 0)
                return {
                    "data": entry.get("data"),
                    "from_cache": True,
                    "age_seconds": round(age, 1),
                    "stale": True,
                    "status_code": entry.get("status_code", 200),
                    "url": entry.get("url", ""),
                }
            except Exception:
                pass
        return {"error": str(e), "from_cache": False}


def sgo_cache_stats():
    """Return cache stats: file count, total size, age range."""
    files = list(CACHE_DIR.glob("*.json"))
    if not files:
        return {"files": 0, "size_bytes": 0, "oldest_hours": 0, "newest_hours": 0}

    now = time.time()
    total_size = 0
    ages = []
    for f in files:
        total_size += f.stat().st_size
        try:
            entry = json.loads(f.read_text())
            age = now - entry.get("fetched_at_epoch", now)
            ages.append(age / 3600)
        except Exception:
            pass

    return {
        "files": len(files),
        "size_kb": round(total_size / 1024, 1),
        "oldest_hours": round(max(ages), 1) if ages else 0,
        "newest_hours": round(min(ages), 1) if ages else 0,
        "avg_hours": round(sum(ages) / len(ages), 1) if ages else 0,
    }


def sgo_clear_cache():
    """Wipe all cached SGO files."""
    for f in CACHE_DIR.glob("*.json"):
        f.unlink()
    return True
