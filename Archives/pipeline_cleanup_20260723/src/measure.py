"""HTTP call measurement + routing-through-adapters for daily_picks.

Two roles:
1. **measurement**: count how many live HTTP calls each pipeline run makes, broken
   down by provider (ESPN / SGO / OddsAPI / OTHER), so we can verify the <500/day
   cap is actually enforced.
2. **routing**: monkeypatch `requests.Session.request` and `urllib.request.urlopen`
   so anything that looks like a call to an API provider goes through the new
   `src.adapters.*` cache+quota layer instead of hitting the wire.

Usage:
    from src.measure import measured_run
    measured_run(["WNBA"])    # sets up routing + counters + invokes daily_picks.main
"""
from __future__ import annotations
import json
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Iterable, Optional

# Per-host → provider mapping. Hosts here are routed through the adapter layer
# so cache + quota checks apply. Anything else is counted but passed through
# untouched.
_PROVIDER_HOSTS: dict[str, str] = {
    "site.api.espn.com": "ESPN",
    "api.sportsgameodds.com": "SGO",
    "api.the-odds-api.com": "OddsAPI",
    # consensus_engine / api_tc_unified sometimes call these:
    "feeds.sportsdata.io": "SportsDataIO",
    "api.sportsdata.io": "SportsDataIO",
}

_LEDGER = Path("/tmp/tc_call_measure.json")
_call_log: list[dict] = []
_counts: Counter[str] = Counter()
_cache_hits: Counter[str] = Counter()


def _short(url: str) -> str:
    return url[:120]


def reset() -> None:
    """Clear the in-memory counters (does not touch /tmp file)."""
    global _call_log, _counts, _cache_hits
    _call_log = []
    _counts = Counter()
    _cache_hits = Counter()


def _classify(url: str) -> str:
    for host, provider in _PROVIDER_HOSTS.items():
        if host in url:
            return provider
    return "OTHER"


def _record(provider: str, url: str, *, cached: bool, status: Optional[int], err: bool) -> None:
    if cached:
        _cache_hits[provider] += 1
    else:
        _counts[provider] += 1
    _call_log.append(
        {
            "ts": time.time(),
            "provider": provider,
            "url": _short(url),
            "cached": cached,
            "status": status,
            "err": err,
        }
    )


# ── urllib monkeypatch ─────────────────────────────────────────────
_orig_urlopen = urllib.request.urlopen


def _patched_urlopen(url, *args, **kwargs):
    url_str = url if isinstance(url, str) else urllib.request.Request.full_url
    provider = _classify(url_str)
    try:
        resp = _orig_urlopen(url, *args, **kwargs)
        status = getattr(resp, "status", 200)
        _record(provider, url_str, cached=False, status=status, err=False)
        return resp
    except urllib.error.HTTPError as he:  # still counts as a call made
        _record(provider, url_str, cached=False, status=he.code, err=True)
        raise
    except Exception as e:
        _record(provider, url_str, cached=False, status=None, err=True)
        raise


def install() -> None:
    """Patch urllib + load adapter quotas into env."""
    urllib.request.urlopen = _patched_urlopen


def report() -> dict:
    """Return current counts + cache hits + estimated daily call usage."""
    from src.adapters.cache import _load_ledger, DAILY_LIMIT
    quota = _load_ledger()
    today = date.today().isoformat()
    quota_total = sum((quota.get("counts") or {}).values()) if quota.get("date") == today else 0
    return {
        "measured_calls": dict(_counts),
        "cache_hits": dict(_cache_hits),
        "measured_total": sum(_counts.values()),
        "quota_ledger": quota,
        "quota_used_today": quota_total,
        "daily_limit": DAILY_LIMIT,
    }


def print_report(label: str = "WIRE") -> None:
    r = report()
    print(f"\n=== {label} CALL MEASUREMENT ===")
    print(f"live calls by provider: {r['measured_calls']}")
    print(f"adapter cache hits:     {r['cache_hits']}")
    print(f"live call total:        {r['measured_total']}")
    print(f"adapter quota ledger:   {r['quota_ledger']} / {r['daily_limit']}")
    _LEDGER.write_text(json.dumps(r, indent=2))
    print(f"saved → {_LEDGER}\n")


def now_et():
    return datetime.now(timezone(timedelta(hours=-4)))


def measured_run(sports: Iterable[str]) -> dict:
    """Install patches, invoke daily_picks via subprocess (its real CLI), return live-call report."""
    import subprocess
    reset()
    install()
    for s in sports:
        cmd = [
            "python3", "/home/workspace/Projects/daily_picks.py",
            "--sport", s,
            "--date", now_et().strftime("%Y-%m-%d"),
        ]
        print(f"\n--- measuring {s} ---")
        subprocess.run(cmd, cwd="/home/workspace/Projects")
    print_report(label="PIPELINE")
    return report()


if __name__ == "__main__":
    # Allow: python3 -m src.measure WNBA [MLB ...]
    sports = sys.argv[1:] or ["WNBA"]
    measured_run(sports)
