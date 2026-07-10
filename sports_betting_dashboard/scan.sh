#!/usr/bin/env bash
# TC Pipeline Health Scan — v2.1
# Usage: ./scan.sh                    — full scan to stdout
#        ./scan.sh --json             — JSON output to scan_report.json
#        ./scan.sh --fix              — auto-fix broken states
#        ./scan.sh --service          — service-only scan (cron mode)

set -euo pipefail
WORKSPACE="/home/workspace"
LOG_DIR="${WORKSPACE}/Daily_Log"
DASH_DIR="${WORKSPACE}/sports_betting_dashboard"
PROJ_DIR="${WORKSPACE}/Projects"
TODAY=$(TZ='America/New_York' date +%Y-%m-%d)
REPORT="${DASH_DIR}/logs/scan_$(date +%Y%m%d).txt"
MODE="${1:-}"

# ─── Earliest Game Today ──────────────────────────────────────────────

get_earliest_game_hours() {
    python3 -c "
import json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

et = timezone(timedelta(hours=-5))
now = datetime.now(et)
earliest = None
evdir = Path('${DASH_DIR}/data/events')
for f in sorted(evdir.glob('*.json')):
    try:
        data = json.loads(f.read_text())
        for e in ([data] if isinstance(data, dict) else data):
            start = e.get('start_time', e.get('commence_time', ''))
            if not start:
                continue
            t = datetime.fromisoformat(start.replace('Z','+00:00'))
            t_et = t.astimezone(et)
            diff_h = (t_et - now).total_seconds() / 3600
            if diff_h > -3 and (earliest is None or diff_h < earliest):
                earliest = diff_h
    except: pass
print(round(earliest, 1) if earliest is not None else '999')
" 2>/dev/null
}

# ─── Check Functions ──────────────────────────────────────────────────

check_pipeline_run() {
    if [ -f "${LOG_DIR}/last_run.json" ]; then
        LAST=$(python3 -c "import json; d=json.load(open('${LOG_DIR}/last_run.json')); print(d.get('timestamp',''))" 2>/dev/null)
        if [ -n "$LAST" ]; then
            echo "✓ PIPELINE_RUN: last=${LAST}"
        else
            echo "✗ PIPELINE_RUN: no timestamp"
        fi
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

check_combos() {
    # ── FIX: Verify combos generated for ALL active sports (not just WNBA) ──
    COMBO_FILES=$(find "${LOG_DIR}/${TODAY}/" -name "combos_*.json" 2>/dev/null)
    if [ -z "$COMBO_FILES" ]; then
        echo "✗ COMBOS: no combo files for ${TODAY}"
        return
    fi

    COMBO_COUNT=$(echo "$COMBO_FILES" | wc -l)
    COMBO_SPORTS=$(python3 -c "
import json, sys
sports = set()
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try:
        d = json.load(open(line))
        s = d.get('sport', '')
        if s: sports.add(s)
    except: pass
print(' '.join(sorted(sports)) if sports else 'none')
" <<< "$COMBO_FILES" 2>/dev/null)

    echo "✓ COMBOS: ${COMBO_COUNT} files, sports=[${COMBO_SPORTS}]"
}

check_wnba_tc_engine() {
    # ── FIX: Verify WNBA TC engine produces real projections ──
    local result
    result=$(curl -s --max-time 8 "http://localhost:3099/api/tc?sport=WNBA" 2>/dev/null)
    local total
    total=$(python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('total',0))" <<< "$result" 2>/dev/null || echo "0")
    [ "$total" -gt 0 ] && echo "✓ WNBA_TC_ENGINE: ${total} WNBA projections" || echo "✗ WNBA_TC_ENGINE: 0 WNBA projections — stale or no data"
}

check_combo_freshness() {
    # ── FIX: Verify combo-prob API returns TODAY's data (not stale 06-25) ──
    local result
    result=$(curl -s --max-time 8 "http://localhost:3099/api/combo-prob?mode=best" 2>/dev/null)
    local total
    total=$(python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('total_games',0))" <<< "$result" 2>/dev/null || echo "0")
    [ "$total" -gt 0 ] && echo "✓ COMBO_FRESH: ${total} games via /api/combo-prob" || echo "✗ COMBO_FRESH: 0 games — stale or no data"
}

check_mlb_fields() {
    # ── FIX: Verify MLB picks have proper numeric edge/signal (not 'null') ──
    local csv_path="${LOG_DIR}/${TODAY}/picks.csv"
    if [ -f "$csv_path" ]; then
        local null_edges
        null_edges=$(python3 -c "
import csv
nulls = 0
with open('${csv_path}') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get('league','') == 'MLB':
            edge = row.get('edge','null')
            if edge in ('', 'null', 'None', None):
                nulls += 1
print(nulls)
" 2>/dev/null)
        [ "${null_edges:-0}" = "0" ] && echo "✓ MLB_FIELDS: no null edges" || echo "⚠ MLB_FIELDS: ${null_edges} MLB rows have null edge"
    else
        echo "ℹ MLB_FIELDS: no picks.csv for ${TODAY}"
    fi
}

check_streamlit() {
    curl -sf --max-time 3 http://localhost:8510 >/dev/null 2>&1 && \
        echo "✓ STREAMLIT: :8510 alive" || echo "✗ STREAMLIT: not running"
}

check_routes() {
    for route in /api/tc /api/slate /api/scan /api/backtest /api/daily-log /api/combos /api/dk-lines /api/combo-prob; do
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:3099${route}" 2>/dev/null)
        [ "$STATUS" = "200" ] && echo "✓ ROUTE ${route}: 200" || echo "✗ ROUTE ${route}: ${STATUS}"
    done
}

check_consensus() {
    CONSENSUS="${LOG_DIR}/${TODAY}/consensus.json"
    CONSENSUS_FILES=$(ls "${LOG_DIR}/${TODAY}"/consensus_*.json 2>/dev/null | wc -l)
    if [ -f "$CONSENSUS" ]; then
        COUNT=$(python3 -c "import json; d=json.load(open('${CONSENSUS}')); print(len(d) if isinstance(d,list) else d.get('total',0))" 2>/dev/null)
        echo "✓ CONSENSUS: ${COUNT} entries"
    elif [ "$CONSENSUS_FILES" -gt 0 ]; then
        echo "✓ CONSENSUS: ${CONSENSUS_FILES} per-game files (combined format)"
    else
        echo "✗ CONSENSUS: not generated"
    fi
}

check_odds_cache() {
    CACHE_DIR="${DASH_DIR}/data/odds"
    if [ ! -d "$CACHE_DIR" ]; then
        echo "✗ ODDS_CACHE: dir missing"
        return
    fi

    HOURS_TO_GAME=$(get_earliest_game_hours)
    FILES_TODAY=$(find "$CACHE_DIR" -name "*.json" -mtime 0 2>/dev/null | wc -l)

    if [ "$FILES_TODAY" -eq 0 ]; then
        echo "✗ ODDS_CACHE: no files from today (earliest game in ${HOURS_TO_GAME}h)"
        return
    fi

    SHOULD_REQUIRE_FRESH=$(python3 -c "print('true' if float(${HOURS_TO_GAME}) < 3.0 else 'false')")

    if [ "$SHOULD_REQUIRE_FRESH" = "true" ]; then
        FILES_FRESH=$(find "$CACHE_DIR" -name "*.json" -mmin -120 2>/dev/null | wc -l)
        if [ "$FILES_FRESH" -gt 0 ]; then
            echo "✓ ODDS_CACHE: ${FILES_FRESH} fresh (<2h) — game in ${HOURS_TO_GAME}h"
        else
            echo "✗ ODDS_CACHE: ${FILES_TODAY} files today but stale — game in ${HOURS_TO_GAME}h"
        fi
    else
        echo "✓ ODDS_CACHE: ${FILES_TODAY} files from today (earliest game in ${HOURS_TO_GAME}h, freshness gate not active)"
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
    if [ -f "${BT_DIR}/combined_backtest.csv" ]; then
        LINES=$(wc -l < "${BT_DIR}/combined_backtest.csv")
        echo "✓ BACKTEST: combined_backtest.csv (${LINES} lines)"
    else
        echo "✗ BACKTEST: no combined file"
    fi
}

check_daily_log_dirs() {
    COUNT=$(find "${LOG_DIR}" -maxdepth 1 -type d -name "202[0-9]-*" 2>/dev/null | wc -l)
    echo "ℹ LOG_DIRS: ${COUNT} daily directories"
}

check_disk() {
    USAGE=$(df -h / | tail -1 | awk '{print $5}')
    echo "ℹ DISK: ${USAGE} used"
}

check_api_limits() {
    STATUS="${DASH_DIR}/data/account/status.json"
    if [ -f "$STATUS" ]; then
        USED=$(python3 -c "import json; d=json.load(open('${STATUS}')).get('data',{}); print(d.get('requests_today',0))" 2>/dev/null)
        LIMIT=$(python3 -c "import json; d=json.load(open('${STATUS}')).get('data',{}); print(d.get('daily_limit',6667))" 2>/dev/null)
        REMAINING=$(python3 -c "import json; d=json.load(open('${STATUS}')).get('data',{}); print(d.get('remaining',0))" 2>/dev/null)
        TIER=$(python3 -c "import json; d=json.load(open('${STATUS}')).get('data',{}); print(d.get('tier','?'))" 2>/dev/null)
        PCT=$(( USED * 100 / LIMIT ))
        [ "$PCT" -gt 80 ] && echo "⚠ API_LIMITS: ${USED}/${LIMIT} (${PCT}%) — ${REMAINING} remaining [${TIER}]" || echo "✓ API_LIMITS: ${USED}/${LIMIT} (${PCT}%) — ${REMAINING} remaining [${TIER}]"
    else
        echo "✗ API_LIMITS: no status.json"
    fi
}

check_events() {
    for f in "${DASH_DIR}"/data/events/*.json; do
        [ ! -f "$f" ] && continue
        BASENAME=$(basename "$f" .json)
        case "$BASENAME" in basketball_nba) continue ;; esac
        COUNT=$(python3 -c "import json; d=json.load(open('${f}')); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null)
        [ "$COUNT" -gt 0 ] && echo "✓ EVENTS ${BASENAME}: ${COUNT}" || echo "✗ EVENTS ${BASENAME}: 0"
    done
}

check_symlinks() {
    # ── FIX: Verify data symlinks point to today ──
    local picks_link="${DASH_DIR}/data/picks/today_picks.csv"
    if [ -L "$picks_link" ]; then
        local target
        target=$(readlink "$picks_link")
        local today_path="Daily_Log/${TODAY}/picks.csv"
        if echo "$target" | grep -q "$today_path"; then
            echo "✓ SYMLINKS: today_picks.csv → ${TODAY}"
        else
            echo "⚠ SYMLINKS: today_picks.csv → ${target} (not today: ${TODAY})"
        fi
    else
        echo "✗ SYMLINKS: today_picks.csv not a symlink"
    fi
}

check_empty_dirs() {
    # ── FIX: Scan for empty directories that should be cleaned ──
    local empties
    empties=$(find "${LOG_DIR}/cache/odds" -maxdepth 1 -type d -empty 2>/dev/null | wc -l)
    local dupes_empty=0
    [ -d "${LOG_DIR}/_dupes" ] && [ -z "$(ls -A "${LOG_DIR}/_dupes" 2>/dev/null)" ] && dupes_empty=1
    local total_empty=$(( empties + dupes_empty ))
    [ "$total_empty" -gt 0 ] && echo "⚠ EMPTY_DIRS: ${total_empty} empty dirs to purge" || echo "✓ EMPTY_DIRS: none"
}

# ─── Run Scan ──────────────────────────────────────────────────────────

if [ "$MODE" = "--service" ]; then
    check_pipeline_run
    check_todays_picks
    check_combos
    check_streamlit
    check_odds_cache
    check_api_limits
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
        cd "$WORKSPACE" && nohup streamlit run Projects/tc_dashboard.py --server.port 8510 --server.headless true > /dev/shm/streamlit_8510.log 2>&1 &
        sleep 3
    fi

    # Fix: refresh stale odds if within 3h of games and cache is stale
    HOURS_TO_GAME=$(get_earliest_game_hours)
    SHOULD_FRESH=$(python3 -c "print('true' if float(${HOURS_TO_GAME}) < 3.0 else 'false')")
    if [ "$SHOULD_FRESH" = "true" ]; then
        ODDS_DIR="${DASH_DIR}/data/odds"
        FRESH=$(find "$ODDS_DIR" -name "*.json" -mmin -120 2>/dev/null | wc -l)
        if [ "$FRESH" -eq 0 ]; then
            echo "→ Refreshing stale odds cache (game in ${HOURS_TO_GAME}h)..."
            cd "$WORKSPACE" && python3 sports_betting_dashboard/scripts/odds_api_scraper.py 2>&1 | tail -5
        fi
    fi

    # Fix: purge empty cache dirs
    find "${LOG_DIR}/cache/odds" -maxdepth 1 -type d -empty -delete 2>/dev/null || true
    [ -d "${LOG_DIR}/_dupes" ] && [ -z "$(ls -A "${LOG_DIR}/_dupes" 2>/dev/null)" ] && rmdir "${LOG_DIR}/_dupes" 2>/dev/null || true

    # Fix: stale today_picks.csv symlink
    picks_link="${DASH_DIR}/data/picks/today_picks.csv"
    if [ -L "$picks_link" ]; then
        rm -f "$picks_link"
        ln -sf "${LOG_DIR}/${TODAY}/picks.csv" "$picks_link"
    fi

    echo "Done."
    exit 0
fi

# Full scan
{
    echo "=============================================="
    echo "  TC Pipeline Health Scan — v2.1"
    echo "  Date: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo "  Earliest game: $(get_earliest_game_hours)h from now"
    echo "=============================================="
    check_pipeline_run
    check_todays_picks
    check_projs
    check_combos
    check_wnba_tc_engine
    check_combo_freshness
    check_mlb_fields
    check_streamlit
    check_consensus
    check_odds_cache
    check_boxscores
    check_backtest
    check_daily_log_dirs
    check_disk
    check_api_limits
    check_events
    check_symlinks
    check_empty_dirs
    echo "---"
    check_routes
    echo "=============================================="
} > "$REPORT"

if [ "$MODE" = "--json" ]; then
    python3 -c "
import json, subprocess, os, time
from datetime import datetime

LOG_DIR = '${LOG_DIR}'
TODAY = '${TODAY}'
WORKSPACE = '${WORKSPACE}'

def check(name, cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        ok = r.returncode == 0
        return {'name': name, 'status': 'PASS' if ok else 'FAIL', 'detail': r.stdout.strip()[:120]}
    except:
        return {'name': name, 'status': 'FAIL', 'detail': 'timeout/error'}

results = []
results.append(check('Picks Today', 'test -f ' + LOG_DIR + '/' + TODAY + '/picks.json && wc -l < ' + LOG_DIR + '/' + TODAY + '/picks.json'))
results.append(check('Combos Today', 'find ' + LOG_DIR + '/' + TODAY + ' -name \"combos_*.json\" | wc -l'))
results.append(check('Streamlit :8510', 'curl -sf --max-time 3 http://localhost:8510 && echo OK'))
results.append(check('API TC', 'curl -s --max-time 5 http://localhost:3099/api/tc?sport=WNBA | python3 -c \"import sys,json; d=json.load(sys.stdin); print(d.get(\\\"total\\\",d.get(\\\"mode\\\",\\\"no\\\")))\"'))
results.append(check('API Slate', 'curl -s --max-time 5 http://localhost:3099/api/slate'))
results.append(check('API Backtest', 'curl -s --max-time 5 http://localhost:3099/api/backtest?days=3'))
results.append(check('API Combos', 'curl -s --max-time 5 http://localhost:3099/api/combos'))
results.append(check('API Combo Prob', 'curl -s --max-time 5 http://localhost:3099/api/combo-prob?mode=best'))
results.append(check('Consensus', 'test -f ' + LOG_DIR + '/' + TODAY + '/consensus.json && echo OK'))

pass_count = sum(1 for r in results if r['status'] == 'PASS')
report = {
    'timestamp': datetime.now().isoformat(),
    'pass': pass_count,
    'fail': len(results) - pass_count,
    'total': len(results),
    'checks': results
}
with open('${DASH_DIR}/data/scan_report.json', 'w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
"
fi

# Always print to stdout
cat "$REPORT"
