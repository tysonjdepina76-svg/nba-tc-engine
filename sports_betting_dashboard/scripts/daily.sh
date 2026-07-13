#!/usr/bin/env bash
# Daily pipeline runner — syncs data + generates picks + updates dashboard
# Usage: ./daily.sh [--quick]   # --quick skips projections, just refreshes dashboard data
set -euo pipefail
WORKSPACE="/home/workspace"
DASH_DIR="${WORKSPACE}/sports_betting_dashboard"
TODAY=$(TZ='America/New_York' date +%Y-%m-%d)
MODE="${1:-}"

echo "=== TC Daily Runner — $(date '+%Y-%m-%d %H:%M:%S %Z') ==="

if [ "$MODE" != "--quick" ]; then
    echo "→ WNBA..."
    cd "$WORKSPACE" && python3 Projects/daily_picks.py --sport wnba
    echo "→ MLB..."
    cd "$WORKSPACE" && python3 Projects/daily_picks.py --sport mlb
    echo "→ World Cup..."
    cd "$WORKSPACE" && python3 Projects/daily_picks.py --sport wc
fi

PICKS_CSV="$WORKSPACE/Daily_Log/$TODAY/picks.csv"
DEST_CSV="$DASH_DIR/data/picks/today_picks.csv"
if [ -f "$PICKS_CSV" ]; then
    cp --remove-destination "$PICKS_CSV" "$DEST_CSV"
    echo "✓ picks.csv synced ($(wc -l < "$PICKS_CSV") lines)"
else
    echo "✗ No picks.csv for $TODAY"
fi

echo "→ Health scan..."
bash "$DASH_DIR/scan.sh" --service

{
    echo "=== $(date) ==="
    echo "  picks: $(wc -l < "$DASH_DIR/data/picks/today_picks.csv" 2>/dev/null || echo 0) rows"
    echo "  streamlit: $(curl -sf --max-time 3 http://localhost:8510 >/dev/null 2>&1 && echo UP || echo DOWN)"
} >> "$DASH_DIR/logs/daily.log"

echo "Done."
