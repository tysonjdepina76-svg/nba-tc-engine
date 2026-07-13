# TC Sports App — Missing Files TODO

Generated 2026-07-13. Disk check vs the 52-file manifest.

## Status
- 47/52 files present
- 13 files missing (down from earlier count after this session's saves)
- Health check: 3/7 OK, 1 error (wnba_tc_engine), 3 off-season (NBA/NFL/NHL)

## Missing files (13)

| # | Path | Type | Notes |
|---|------|------|-------|
| 1 | .gitignore | infra | standard Python gitignore |
| 2 | README.md | docs | project README |
| 3 | Dockerfile | infra | container build |
| 4 | docker-compose.yml | infra | service orchestration |
| 5 | deploy.sh | infra | top-level deploy script (not scripts/deploy.sh) |
| 6 | api/main.py | code | FastAPI entrypoint (needed by deploy.sh) |
| 7 | database/schema.sql | data | 7 tables + 3 views per manifest |
| 8 | scripts/deploy.sh | infra | referenced by top-level deploy.sh |
| 9 | scripts/health_check.sh | infra | bash health check |
| 10 | dashboard/components/tables.py | code | table renderers (overlaps advanced_charts.py) |
| 11 | dashboard/components/charts.py | code | chart renderers (overlaps advanced_charts.py) |
| 12 | sources/espn_odds_fetcher.py | code | ESPN core API odds fetcher |
| 13 | sources/wnba_tc_engine.py | code | WNBA TC engine — **health check is failing on this one** |

## Health check status

```
TC Health Check: 3/7 OK | 3 warnings | 1 errors
  ✅ MLB    - BOOK_LINES (fetcher OK)
  ❌ WNBA   - TC_ENGINE (module load failed: No module named 'sources.wnba_tc_engine')
  ✅ WC     - BOOK_LINES (fetcher OK)
  ✅ SOCCER - BOOK_LINES (fetcher OK)
  ⏸️ NBA    - Disabled: NBA off-season
  ⏸️ NFL    - Disabled: NFL off-season
  ⏸️ NHL    - Disabled: NHL off-season
```

## Recently saved this session

- sources/soccer_tc_engine.py (full)
- sources/utils/bet_tracker.py (full)
- sources/scrapers/soccer_roster_fbref.py (stub — real roster data not yet wired)
- sources/ncaa_tc_engine.py
- sources/nfl_raptor_engine.py
- sources/utils/monitor.py
- sources/utils/redis_cache.py
- dashboard/components/advanced_charts.py
- sources/sports_registry.py, config/columns.py, sources/utils/cache.py, sources/utils/logging.py, runtime_health_check.py (all overwritten with full versions)
