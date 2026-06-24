#!/usr/bin/env bash
# TC Pipeline Health Scan
# Usage: ./scan.sh                    — full scan to stdout
#        ./scan.sh --json             — JSON output to scan_report.json
#        ./scan.sh --fix              — auto-fix broken states
#        ./scan.sh --service          — service-only scan (cron mode)

set -euo pipefail
WORKSPACE="${HOME}/workspace"
LOG_DIR="${WORKSPACE}/Daily_Log"
PROJ_DIR="${WORKSPACE}/Projects"
TODAY=$(date +%Y-%m-%d)
REPORT="${WORKSPACE}/sports_betting_dashboard/logs/scan_$(date +%Y%m%d).txt"
MODE="${1:-}"

# ─── Check Functions ──────────────────────────────────────────────────

check_pipeline_run() {
    if [ -f "${LOG_DIR}/last_run.json" ]; then
        LAST=$(python3 -c "import json; d=json.load(open('${LOG_DIR}/last_run.json')); print(d.get('timestamp',''))" 2>/dev/null)
        if [ -n "$LAST" ]; then
            echo "✓ PIPELINE_RUN: last=${LAST}"
        else
            echo "✗ PIPELINE_RUN: no timestamp in last_run.json"
        fi
    else
        echo "✗ PIPELINE_RUN: last_run.json missing"
    fi
}

check_todays_picks() {
    if [ -f "${LOG_DIR}/${TODAY}/picks.json" ]; then
        COUNT=$(python3 -c "import json; d=json.load(open('${LOG_DIR}/${TODAY}/picks.json')); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null)
        [ "$COUNT" -gt 0 ] && echo "✓ PICKS_TODAY: ${COUNT} picks" || echo "✗ PICKS_TODAY: 0 picks"
    else
        echo "✗ PICKS_TODAY: no picks.json for ${TODAY}"
    fi
}

check_projs() {
    COUNT=$(find "${LOG_DIR}/${TODAY}/" -name "proj_*.json" 2>/dev/null | wc -l)
    [ "$COUNT" -gt 0 ] && echo "✓ PROJ_FILES: ${COUNT} projection files" || echo "✗ PROJ_FILES: none"
}

check_streamlit() {
    curl -sf --max-time 3 http://localhost:8510 >/dev/null 2>&1 && \
        echo "✓ STREAMLIT: :8510 alive" || echo "✗ STREAMLIT: not running"
}

check_routes() {
    for route in /api/tc /api/slate /api/scan /api/backtest /api/daily-log /api/combos /api/dk-lines; do
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:3099${route}" 2>/dev/null)
        [ "$STATUS" = "200" ] && echo "✓ ROUTE ${route}: 200" || echo "✗ ROUTE ${route}: ${STATUS}"
    done
}

check_consensus() {
    CONSENSUS="${LOG_DIR}/${TODAY}/consensus.json"
    if [ -f "$CONSENSUS" ]; then
        COUNT=$(python3 -c "import json; d=json.load(open('${CONSENSUS}')); print(len(d) if isinstance(d,list) else d.get('total',0))" 2>/dev/null)
        echo "✓ CONSENSUS: ${COUNT} entries"
    else
        echo "✗ CONSENSUS: not generated"
    fi
}

check_odds_cache() {
    CACHE_DIR="/tmp/tc_cache/odds"
    if [ -d "$CACHE_DIR" ]; then
        FILES=$(find "$CACHE_DIR" -name "*.json" -mmin -120 2>/dev/null | wc -l)
        [ "$FILES" -gt 0 ] && echo "✓ ODDS_CACHE: ${FILES} fresh (<2h)" || echo "✗ ODDS_CACHE: stale or empty"
    else
        echo "✗ ODDS_CACHE: dir missing"
    fi
}

check_boxscores() {
    BC="${LOG_DIR}/boxscore_registry.json"
    if [ -f "$BC" ]; then
        LAST=$(python3 -c "import json; d=json.load(open('${BC}')); dates=sorted(d.keys()) if isinstance(d,dict) else []; print(dates[-1] if dates else 'none')" 2>/dev/null)
        echo "✓ BOXSCORES: last=${LAST}"
    else
        echo "✗ BOXSCORES: no registry"
    fi
}

check_backtest() {
    BT_DIR="${LOG_DIR}/backtests"
    RECENT=$(find "$BT_DIR" -name "combined_backtest.csv" -newer "$BT_DIR" 2>/dev/null || echo "")
    [ -n "$RECENT" ] && echo "✓ BACKTEST: combined_backtest.csv present" || echo "✗ BACKTEST: no combined file"
}

check_daily_log_dirs() {
    COUNT=$(find "${LOG_DIR}" -maxdepth 1 -type d -name "202[0-9]-*" 2>/dev/null | wc -l)
    echo "ℹ LOG_DIRS: ${COUNT} daily directories"
}

check_disk() {
    USAGE=$(df -h / | tail -1 | awk '{print $5}')
    echo "ℹ DISK: ${USAGE} used"
}

# ─── Run Scan ──────────────────────────────────────────────────────────

if [ "$MODE" = "--service" ]; then
    # Lightweight cron mode
    check_pipeline_run
    check_todays_picks
    check_streamlit
    check_odds_cache
    exit 0
fi

if [ "$MODE" = "--fix" ]; then
    echo "=== AUTO-REPAIR ==="

    # Fix: run pipeline if no picks today
    if [ ! -f "${LOG_DIR}/${TODAY}/picks.json" ]; then
        echo "→ Running daily_picks.py..."
        cd "$WORKSPACE" && python3 Projects/daily_picks.py WNBA MLB 'WORLD CUP' 2>&1 | tail -3
    fi

    # Fix: restart Streamlit if down
    if ! curl -sf --max-time 3 http://localhost:8510 >/dev/null 2>&1; then
        echo "→ Restarting Streamlit..."
        cd "$WORKSPACE" && nohup streamlit run Projects/dashboard.py --server.port 8510 --server.headless true > /dev/shm/streamlit_8510.log 2>&1 &
        sleep 3
    fi

    echo "Done."
    exit 0
fi

# Full scan
{
    echo "=============================================="
    echo " TC Pipeline Health Scan"
    echo " Date: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo "=============================================="
    check_pipeline_run
    check_todays_picks
    check_projs
    check_streamlit
    check_consensus
    check_odds_cache
    check_boxscores
    check_backtest
    check_daily_log_dirs
    check_disk
    echo "---"
    check_routes
    echo "=============================================="
} > "$REPORT"

if [ "$MODE" = "--json" ]; then
    python3 -c "
import json, subprocess, os, time
from datetime import datetime

def check(name, cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        ok = r.returncode == 0 and ('error' not in r.stdout.lower() or '200' in r.stdout)
        return {'name': name, 'status': 'PASS' if ok else 'FAIL', 'detail': r.stdout.strip()[:120]}
    except:
        return {'name': name, 'status': 'FAIL', 'detail': 'timeout/error'}

results = []
results.append(check('Picks Today', 'test -f ${LOG_DIR}/${TODAY}/picks.json && wc -l < ${LOG_DIR}/${TODAY}/picks.json'))
results.append(check('Streamlit :8510', 'curl -sf --max-time 3 http://localhost:8510 && echo OK'))
results.append(check('API TC', 'curl -s --max-time 5 http://localhost:3099/api/tc?sport=WNBA | python3 -c \"import sys,json; d=json.load(sys.stdin); print(d.get(\"total\",d.get(\"mode\",\"no\")))\"'))
results.append(check('API Slate', 'curl -s --max-time 5 http://localhost:3099/api/slate'))
results.append(check('API Backtest', 'curl -s --max-time 5 http://localhost:3099/api/backtest?days=3'))
results.append(check('API Combos', 'curl -s --max-time 5 http://localhost:3099/api/combos'))
results.append(check('Consensus', 'test -f ${LOG_DIR}/${TODAY}/consensus.json && echo OK'))

pass_count = sum(1 for r in results if r['status'] == 'PASS')
report = {
    'timestamp': datetime.now().isoformat(),
    'pass': pass_count,
    'fail': len(results) - pass_count,
    'total': len(results),
    'checks': results
}
with open('${WORKSPACE}/sports_betting_dashboard/data/scan_report.json', 'w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
"
fi

# Always print to stdout
cat "$REPORT"
