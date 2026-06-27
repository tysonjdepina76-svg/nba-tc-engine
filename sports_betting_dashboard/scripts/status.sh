#!/usr/bin/env bash
# Quick status check — all subsystems at a glance
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

# Services
for svc in "streamlit:8510" "zo.space:3099"; do
    NAME="${svc%:*}"
    PORT="${svc#*:}"
    STATUS=$(curl -sf --max-time 3 "http://localhost:${PORT}" >/dev/null 2>&1 && echo "UP" || echo "DOWN")
    echo "  $NAME:    $STATUS (:$PORT)"
done

# API routes
for route in /api/tc /api/slate /api/scan /api/backtest /api/combos /api/dk-lines; do
    CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:3099${route}" 2>/dev/null || echo "ERR")
    echo "  $route:  $CODE"
done

# Data freshness — correct odds cache path
ODDS_DIR="${DASH_DIR}/data/odds"
FRESH=$(find "$ODDS_DIR" -name "*.json" -mmin -120 2>/dev/null | wc -l)
TODAY_FILES=$(find "$ODDS_DIR" -name "*.json" -mtime 0 2>/dev/null | wc -l)
echo "  Odds cache:  $FRESH fresh (<2h), $TODAY_FILES from today"

# API limits (correct JSON structure)
STATUS_FILE="${DASH_DIR}/data/account/status.json"
if [ -f "$STATUS_FILE" ]; then
    python3 -c "
import json
d = json.load(open('$STATUS_FILE')).get('data', {})
used = d.get('requests_today', '?')
limit = d.get('daily_limit', '?')
remaining = d.get('remaining', '?')
tier = d.get('tier', '?')
print(f'  API calls:   {used}/{limit} today ({remaining} remaining) [{tier}]')
" 2>/dev/null || echo "  API calls:   N/A"
fi

echo "═══════════════════════════════════════════"
