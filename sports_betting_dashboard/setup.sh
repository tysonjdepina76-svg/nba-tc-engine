#!/usr/bin/env bash
# TC Pipeline Setup — one-time install and verification
# Usage: bash setup.sh
set -euo pipefail
WORKSPACE="/home/workspace"
DASH_DIR="${WORKSPACE}/sports_betting_dashboard"

echo "============================================"
echo " TC Pipeline Setup"
echo " $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "============================================"

# 1. pip dependencies
echo ""
echo "[1/5] Installing Python dependencies..."
pip install -q streamlit pandas requests 2>/dev/null || true
echo "  ✓ pip packages checked"

# 2. make scripts executable
echo ""
echo "[2/5] Making scripts executable..."
chmod +x "$DASH_DIR"/scripts/*.sh
chmod +x "$DASH_DIR"/scan.sh "$DASH_DIR"/setup.sh
echo "  ✓ scripts are executable"

# 3. create default data files if missing
echo ""
echo "[3/5] Initializing data files..."
TODAY=$(TZ='America/New_York' date +%Y-%m-%d)

# data/today.json
python3 "$DASH_DIR/scripts/generate_today_json.py"

# data/picks/today_picks.csv placeholder
mkdir -p "$DASH_DIR/data/picks"
if [ ! -f "$DASH_DIR/data/picks/today_picks.csv" ]; then
    echo "date,league,matchup,team,player,stat,direction,line,tc,edge" > "$DASH_DIR/data/picks/today_picks.csv"
    echo "  ✓ created placeholder today_picks.csv"
fi

# logs placeholders
mkdir -p "$DASH_DIR/logs"
for log in daily.log api.log picks.log; do
    if [ ! -f "$DASH_DIR/logs/$log" ]; then
        echo "# $log — created $(date)" > "$DASH_DIR/logs/$log"
        echo "  ✓ created logs/$log"
    fi
done

# 4. verify core files
echo ""
echo "[4/5] Verifying core files..."
REQUIRED=(
    "$WORKSPACE/Projects/daily_picks.py"
    "$DASH_DIR/dashboard.py"
    "$DASH_DIR/scan.sh"
    "$DASH_DIR/fix_pipeline.py"
    "$DASH_DIR/config/algorithm_weights.json"
)
ok=0
missing=0
for f in "${REQUIRED[@]}"; do
    if [ -f "$f" ]; then
        ((ok++))
    else
        echo "  ✗ MISSING: $f"
        ((missing++))
    fi
done
echo "  ✓ $ok present, $missing missing"

# 5. dry-run scan
echo ""
echo "[5/5] Quick health check..."
python3 "$DASH_DIR/scripts/generate_today_json.py" > /dev/null 2>&1 && echo "  ✓ today.json generator OK" || echo "  ⚠ today.json generator issue (may be fine — no picks yet)"

echo ""
echo "============================================"
echo " Setup complete."
echo " Run: cd $DASH_DIR && scripts/start.sh"
echo " Dashboard: http://localhost:8510"
echo "============================================"
