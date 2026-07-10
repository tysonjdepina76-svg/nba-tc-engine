#!/usr/bin/env python3
"""Runtime health check for TC multi-sport pipeline.
Uses sports_registry as the single source of truth.
Run: python3 Projects/runtime_health_check.py
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sports_registry import REGISTRY, DataSource


def runtime_health_check():
    """Test every registered sport via the registry."""
    issues = []
    sports_tested = 0
    sports_ok = 0

    for sport_key, config in REGISTRY._registry.items():
        sports_tested += 1
        if not config.enabled:
            issues.append(f"⚠️ {sport_key} DISABLED")
            continue

        if config.source == DataSource.OFF_SEASON:
            issues.append(f"⚪ {sport_key} off-season (expected)")
            sports_ok += 1
            continue

        if config.source == DataSource.COMING_SOON:
            issues.append(f"⚠️ {sport_key} not yet wired")
            continue

        if config.source == DataSource.TC_ENGINE:
            try:
                mod = importlib.import_module(config.module)
                if not hasattr(mod, config.fn):
                    issues.append(f"❌ {sport_key}: {config.module}.{config.fn}() missing")
                    continue
                sports_ok += 1
            except ImportError as e:
                issues.append(f"❌ {sport_key}: cannot import {config.module}: {e}")
                continue
            except Exception as e:
                issues.append(f"❌ {sport_key}: import error: {e}")
                continue
            continue

        if config.source == DataSource.BOOK_LINES:
            fetcher = config.line_fetcher or config.fetcher
            if fetcher is None:
                issues.append(f"⚠️ {sport_key}: no fetcher")
            else:
                sports_ok += 1
            continue

    return {
        "total_tested": sports_tested,
        "ok": sports_ok,
        "issues": issues,
        "has_issues": len([i for i in issues if not i.startswith("⚪")]) > 0,
        "status": "✅ ALL PASSED" if not issues else f"⚠️ {len(issues)} issue(s)",
    }


if __name__ == "__main__":
    print("=== TC Runtime Health Check (registry-driven) ===")
    result = runtime_health_check()
    print(f"Sports tested: {result['total_tested']}, OK: {result['ok']}, Status: {result['status']}")
    for issue in result["issues"]:
        print(f"  {issue}")
    sys.exit(1 if result["has_issues"] else 0)