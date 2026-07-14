#!/usr/bin/env python3
"""
TC Runtime Health Check - Registry-driven system verification.
"""

import sys
import importlib
from sources.sports_registry import REGISTRY, DataSource

def run_health_check():
    results = {"total": 0, "ok": 0, "warnings": 0, "errors": 0, "details": {}}

    for sport_key, config in REGISTRY._registry.items():
        results["total"] += 1
        if not config.enabled:
            results["details"][sport_key] = {"status": "⏸️", "message": f"Disabled: {config.error_msg or 'off-season'}"}
            results["warnings"] += 1
            continue

        if config.source == DataSource.BOOK_LINES:
            if config.fetcher:
                try:
                    test = config.fetcher()
                    if test:
                        results["details"][sport_key] = {"status": "✅", "message": "BOOK_LINES (fetcher OK)"}
                        results["ok"] += 1
                    else:
                        results["details"][sport_key] = {"status": "⚠️", "message": "BOOK_LINES (fetcher returned empty)"}
                        results["warnings"] += 1
                except Exception as e:
                    results["details"][sport_key] = {"status": "❌", "message": f"BOOK_LINES (fetcher failed: {str(e)})"}
                    results["errors"] += 1
            else:
                results["details"][sport_key] = {"status": "⚠️", "message": "BOOK_LINES (no fetcher)"}
                results["warnings"] += 1

        elif config.source == DataSource.TC_ENGINE:
            if config.module:
                try:
                    importlib.import_module(f"sources.{config.module}")
                    results["details"][sport_key] = {"status": "✅", "message": f"TC_ENGINE (module {config.module} loaded)"}
                    results["ok"] += 1
                except Exception as e:
                    results["details"][sport_key] = {"status": "❌", "message": f"TC_ENGINE (module load failed: {str(e)})"}
                    results["errors"] += 1
            else:
                results["details"][sport_key] = {"status": "❌", "message": "TC_ENGINE (no module specified)"}
                results["errors"] += 1

        else:
            results["details"][sport_key] = {"status": "⏸️", "message": f"{config.source.value} (not implemented)"}
            results["warnings"] += 1

    print(f"\n{'='*60}")
    print(f"TC Health Check: {results['ok']}/{results['total']} OK | {results['warnings']} warnings | {results['errors']} errors")
    print(f"{'='*60}")
    for sport, detail in results["details"].items():
        print(f"  {detail['status']} {sport.upper():6s} - {detail['message']}")
    print(f"{'='*60}\n")
    return results

if __name__ == "__main__":
    sys.exit(0 if run_health_check()["errors"] == 0 else 1)
