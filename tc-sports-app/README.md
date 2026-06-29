# TC Sports App

Single source of truth for the TC betting pipeline. Self-healing, self-monitoring.

## Why this exists

Old setup: 8 different engines, no unified entry, silent partial failures, alert spam.
New setup: 1 pipeline, validator gate, circuit breakers, deduplicated alerts.

## Layout

```
tc-sports-app/
├── src/
│   ├── pipeline.py            # ONE entry point
│   ├── data_validator.py      # The GATE - rejects bad data before any alert
│   ├── circuit_breaker.py     # Stops calling dead APIs
│   ├── auto_retry.py          # Exponential backoff
│   ├── alert_deduper.py       # No more alert spam
│   ├── health_check.py        # Validates data, not just HTTP
│   └── snapshot_pre_change.py # Auto-snapshot before edits
├── data/
│   ├── current/
│   └── processed/
├── reports/
│   ├── daily/
│   └── archive/
├── logs/
└── snapshots/
```

## Usage

```bash
# Health check (no API calls, just status)
python3 src/pipeline.py --mode health

# Daily run (validates first, then proceeds)
python3 src/pipeline.py --mode daily

# Validate a picks file
python3 src/pipeline.py --mode validate --input data/picks.json
```

## What changed vs old

| Old | New |
|-----|-----|
| 8 engines | 1 pipeline |
| HTTP 200 = success | Validate data shape |
| Alert on every blip | Dedup within 1hr window |
| Call dead API forever | Circuit breaker (5 fails = open) |
| Fix manually daily | Auto-retry with backoff |
| No rollback | Auto-snapshot before changes |
