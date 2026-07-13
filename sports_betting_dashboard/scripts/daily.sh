#!/usr/bin/env bash
# Daily pipeline runner — syncs data + generates picks + updates dashboard
# Usage: ./daily.sh [--quick]   # --quick skips projections, just refreshes dashboard data
set -euo pipefail
WORKSPACE="/home/workspace"
DASH_DIR="${WORKSPACE}/sports_betting_dashboard"
TODAY=$(date +%Y-%m-%d)
MODE="${1:-}"

echo "=== TC Daily Runner — $(date '+%Y-%m-%d %H:%M:%S %Z') ==="

# 1. Run daily picks (WNBA + MLB + World Cup)
if [ "$MODE" != "--quick" ]; then
    echo "→ Running daily_picks.py (WNBA)..."
    cd "$WORKSPACE" && python3 Projects/daily_picks.py --sport WNBA
    echo "→ Running daily_picks.py (MLB)..."
    cd "$WORKSPACE" && python3 Projects/daily_picks.py --sport MLB
    echo "→ Running daily_picks.py (WORLD_CUP)..."
    cd "$WORKSPACE" && python3 Projects/daily_picks.py --sport WORLD_CUP
fi

# 2. Sync today's picks CSV → dashboard data dir
PICKS_CSV="$WORKSPACE/Daily_Log/$TODAY/picks.csv"
DEST_CSV="$DASH_DIR/data/picks/today_picks.csv"
if [ -f "$PICKS_CSV" ]; then
    # handle case where dest is a symlink to source — use cp --remove-destination
    cp --remove-destination "$PICKS_CSV" "$DEST_CSV"
    echo "✓ picks.csv synced ($(wc -l < "$PICKS_CSV") lines)"
else
    echo "✗ No picks.csv for $TODAY"
fi

# 3. Run health scan
echo "→ Running health scan..."
bash "$DASH_DIR/scan.sh" --service

# 4. Log to daily.log
{
    echo "=== $(date) ==="
    echo "  picks: $(wc -l < "$DASH_DIR/data/picks/today_picks.csv" 2>/dev/null || echo 0) rows"
    echo "  streamlit: $(curl -sf --max-time 3 http://localhost:8510 >/dev/null 2>&1 && echo UP || echo DOWN)"
} >> "$DASH_DIR/logs/daily.log"

echo "Done."
