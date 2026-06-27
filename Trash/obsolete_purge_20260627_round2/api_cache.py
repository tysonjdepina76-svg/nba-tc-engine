#!/usr/bin/env python3
"""Unified API cache — primary read path for all daily_picks endpoints.

Usage:
    from api_cache import cached_get
    data = cached_get("espn_wnba_scoreboard", "https://...", ttl=7200)

Cache layout: /home/workspace/Daily_Log/cache/api/{name}.json
Each entry stores {fetched_at, latency_ms, status_code, data, ttl_seconds}.
On every hit, the registry is updated with last_used timestamp.
Re-runs cost zero API calls when cache is warm.
"""
import json
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

CACHE_DIR = Path("/home/workspace/Daily_Log/cache/api")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
REGISTRY = Path("/home/workspace/Daily_Log/api_registry.json")

def _now():
    return datetime.now(timezone.utc).isoformat()

def cached_get(name, url, params=None, headers=None, ttl=7200, timeout=15, force=False):
    """Fetch with disk cache. Returns (data, from_cache_bool)."""
    cache_path = CACHE_DIR / f"{name}.json"
    # Tier 0: cache hit
    if not force and cache_path.exists():
        try:
            entry = json.loads(cache_path.read_text())
            age = time.time() - entry["fetched_at_epoch"]
            if age < ttl:
                _bump_registry(name, "cache_hit")
                return entry["data"], True
        except Exception:
            pass
    # Tier 1: live fetch
    t0 = time.time()
    try:
        r = requests.get(url, params=params or {}, headers=headers or {}, timeout=timeout)
        latency = round((time.time() - t0) * 1000, 1)
        ok = 200 <= r.status_code < 300
        try:
            data = r.json()
        except Exception:
            data = {"_raw": r.text[:1000], "status_code": r.status_code}
        # Persist
        cache_path.write_text(json.dumps({
            "name": name,
            "url": url,
            "fetched_at": _now(),
            "fetched_at_epoch": time.time(),
            "ttl_seconds": ttl,
            "status_code": r.status_code,
            "latency_ms": latency,
            "data": data}, indent=2, default=str))
        _bump_registry(name, "live_fetch", status=r.status_code, latency=latency)
        return data, False
    except Exception as e:
        # Network error → if we have stale cache, serve it
        if cache_path.exists():
            try:
                entry = json.loads(cache_path.read_text())
                _bump_registry(name, "stale_cache_on_error")
                return entry["data"], True
            except Exception:
                pass
        _bump_registry(name, "error", error=str(e)[:200])
        return {"error": str(e), "cached": False}, False

def _bump_registry(name, event, **kw):
    """Update api_registry.json with last-used timestamp per endpoint name."""
    if not REGISTRY.exists():
        return
    try:
        reg = json.loads(REGISTRY.read_text())
    except Exception:
        return
    for ep in reg.get("endpoints", []):
        if ep["name"] == name:
            ep["last_used_at"] = _now()
            ep["last_event"] = event
            for k, v in kw.items():
                ep[f"last_{k}"] = v
            break
    reg["last_updated_at"] = _now()
    REGISTRY.write_text(json.dumps(reg, indent=2, default=str))

def cache_age_minutes(name):
    p = CACHE_DIR / f"{name}.json"
    if not p.exists():
        return None
    try:
        e = json.loads(p.read_text())
        return round((time.time() - e["fetched_at_epoch"]) / 60, 1)
    except Exception:
        return None

def warm_cache_from_registry(force=False):
    """Walk api_registry.json and warm cache for all OK endpoints. Used after scans."""
    if not REGISTRY.exists():
        return {"warmed": 0, "skipped": 0}
    reg = json.loads(REGISTRY.read_text())
    warmed = 0
    skipped = 0
    for ep in reg.get("endpoints", []):
        if not ep.get("ok"):
            skipped += 1
            continue
        url = ep["url"]
        params={}
        if ep.get("key_label"):
            # Re-derive apiKey from env
            import os
            key = os.environ.get(ep["key_label"], "")
            if not key:
                sf = Path("/root/.zo/secrets.env")
                if sf.exists():
                    for line in sf.read_text().splitlines():
                        if line.startswith(ep["key_label"] + "="):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            if key:
                        cached_get(ep["name"], url, params=params, headers={"x-api-key": key}, force=force)
        warmed += 1
    return {"warmed": warmed, "skipped": skipped}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "warm":
        r = warm_cache_from_registry(force="--force" in sys.argv)
        print(json.dumps(r, indent=2))
    else:
        print(f"Cache dir: {CACHE_DIR}")
        print(f"Cached entries: {len(list(CACHE_DIR.glob('*.json')))}")
        print(f"Registry: {REGISTRY}")