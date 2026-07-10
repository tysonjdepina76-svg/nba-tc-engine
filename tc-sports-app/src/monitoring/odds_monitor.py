"""
OddsAPI Monitor Runner — Daily health check with off-season guard.

Run standalone:
    python3 /home/workspace/tc-sports-app/src/monitoring/odds_monitor.py

Hooked into 1:30 PM ET automation (TC Pipeline — 1:30PM Slate + Injury + Health Check).
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Import base directly to avoid package __init__ cascade
import importlib.util
_base_path = Path(__file__).parent.parent / "adapters" / "oddsapi" / "base.py"
_spec = importlib.util.spec_from_file_location("oddsapi_base", _base_path)
_base_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base_mod)
OddsAPIMonitor = _base_mod.OddsAPIMonitor
OddsAPIBase = _base_mod.OddsAPIBase
SGOMonitor = _base_mod.SGOMonitor


# ---------------------------------------------------------------------------
# Off-season guard
# ---------------------------------------------------------------------------
# NBA: mid-June through mid-October
# NHL: mid-June through early-October
# WNBA: mid-September through mid-October (off-season)
# MLB: October through March (off-season)
# World Cup: only when FIFA tournament active

OFF_SEASON_SPORTS = ["NBA", "NHL"]  # Always off in July


def is_in_season(sport: str) -> bool:
    """Return True if sport is currently in season."""
    if sport in ("NBA", "NHL"):
        return False  # Off-season until October
    return True


# ---------------------------------------------------------------------------
# Run monitor
# ---------------------------------------------------------------------------

def run_monitor(include_health_ping: bool = True) -> dict:
    """
    Run health checks for both OddsAPI and SGO, gated by in-season guard.

    Returns a status dict with sub-keys for each provider.
    """
    result = {
        "timestamp": datetime.now().isoformat(),
        "in_season": [s for s in ["MLB", "WNBA", "WORLD_CUP", "NFL"] if is_in_season(s)],
        "off_season": ["NBA", "NHL"],
    }

    if not include_health_ping:
        result["status"] = "skip_ping"
        result["skipped"] = True
        result["reason"] = "include_health_ping=False"
        return result

    # --- OddsAPI ---
    odds_key = os.environ.get("THEODDSAPI") or os.environ.get("THE_ODDS_API_KEY")
    if not odds_key:
        result["oddsapi"] = {"status": "no_key", "skipped": True, "reason": "THEODDSAPI secret not set"}
    else:
        o_monitor = OddsAPIMonitor(api_key=odds_key)
        result["oddsapi"] = o_monitor.check_health()

    # --- SGO ---
    sgo_key = os.environ.get("SGO_API_KEY")
    if not sgo_key:
        result["sgo"] = {"status": "no_key", "skipped": True, "reason": "SGO_API_KEY secret not set"}
    else:
        sgo_monitor = SGOMonitor(api_key=sgo_key)
        # Test on the first in-season sport (cheap /sports/ endpoint)
        test_sport = result["in_season"][0] if result["in_season"] else "MLB"
        result["sgo"] = sgo_monitor.check_health(test_sport)

    # Overall status
    o_status = result.get("oddsapi", {}).get("status", "unknown")
    s_status = result.get("sgo", {}).get("status", "unknown")
    if "auth_failed" in (o_status, s_status):
        result["status"] = "auth_failed"
    elif o_status == "rate_limited" and s_status == "rate_limited":
        result["status"] = "rate_limited"
    elif o_status in ("healthy", "rate_limited") or s_status in ("healthy", "rate_limited"):
        result["status"] = "partial" if (o_status != s_status) else "healthy"
    else:
        result["status"] = o_status if o_status != "unknown" else s_status

    if not result["in_season"]:
        result["note"] = "All rotation sports off-season; single health ping only"

    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="OddsAPI + SGO Monitor Runner")
    parser.add_argument(
        "--no-ping",
        action="store_true",
        help="Skip health ping (dry-run guard test only)",
    )
    parser.add_argument(
        "--sport",
        type=str,
        default=None,
        help="Test a specific sport's in-season status (e.g. NBA, NHL, MLB)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print(f"OddsAPI + SGO Monitor — {datetime.now().strftime('%Y-%m-%d %I:%M %p ET')}")
    print("=" * 60)

    if args.sport:
        in_season = is_in_season(args.sport)
        print(f"\n[{args.sport}] in_season = {in_season}")
        if not in_season:
            print(f"  → SKIP: {args.sport} is off-season, no OddsAPI/SGO call")
        else:
            print(f"  → FETCH: {args.sport} active")
        return

    result = run_monitor(include_health_ping=not args.no_ping)

    print(f"\nIn-season  : {result.get('in_season', [])}")
    print(f"Off-season : {result.get('off_season', [])}")
    print(f"Status     : {result.get('status', 'unknown')}")

    if "oddsapi" in result:
        o = result["oddsapi"]
        print(f"\n--- OddsAPI ---")
        print(f"  Status    : {o.get('status', 'n/a')}")
        print(f"  Remaining : {o.get('remaining', 'n/a')}")
        print(f"  Used      : {o.get('used', 'n/a')}")
        print(f"  Daily ct  : {o.get('daily_count', 0)}")
        print(f"  HTTP      : {o.get('http_code', 'n/a')}")

    if "sgo" in result:
        s = result["sgo"]
        print(f"\n--- SGO ---")
        print(f"  Status    : {s.get('status', 'n/a')}")
        print(f"  Sport     : {s.get('sport_tested', 'n/a')}")
        print(f"  Daily ct  : {s.get('daily_count', 0)}")
        print(f"  HTTP      : {s.get('http_code', 'n/a')}")
        if s.get("last_429"):
            print(f"  Last 429  : {s['last_429']}")

    if result.get("note"):
        print(f"\nNote: {result['note']}")

    print("\n--- JSON ---")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
