#!/usr/bin/env bash
# TC Pipeline status (offline — no API calls)
set -euo pipefail
WORKSPACE="/home/workspace"
DASH_DIR="${WORKSPACE}/sports_betting_dashboard"
TODAY=$(TZ='America/New_York' date +%Y-%m-%d)

echo "═══════════════════════════════════════════"
echo " TC Pipeline Status — $(date '+%H:%M:%S %Z')"
echo "═══════════════════════════════════════════"

# Pipeline
LAST=$(python3 -c "import json; d=json.load(open('${WORKSPACE}/Daily_Log/last_run.json')); print(d.get('timestamp','?'))" 2>/dev/null || echo "N/A")
echo "  Pipeline:    last run $LAST"
echo "  Picks today: $(wc -l < "${WORKSPACE}/Daily_Log/${TODAY}/picks.csv" 2>/dev/null || echo 0) rows"

# Dashboard
for port in 8510; do
    if curl -sf --max-time 3 "http://localhost:${port}" >/dev/null 2>&1; then
        echo "  Dashboard:   UP (:$port)"
    else
        echo "  Dashboard:   DOWN (:$port)"
    fi
done

# Backtest summary
if [ -f "${WORKSPACE}/Daily_Log/backtest_results.csv" ]; then
    TOTAL=$(wc -l < "${WORKSPACE}/Daily_Log/backtest_results.csv" 2>/dev/null || echo 0)
    echo "  Backtest:    $TOTAL rows in results"
fi

# Crontab
if command -v crontab >/dev/null; then
    CT=$(crontab -l 2>/dev/null | grep -v '^#' | grep -v '^$' | wc -l || echo 0)
    echo "  Crontab:     $CT active jobs"
else
    echo "  Crontab:     not installed"
fi
