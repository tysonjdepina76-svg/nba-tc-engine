#!/usr/bin/env bash
# refresh_daily_data.sh
# -----------------------------------------------------------------------------
# Daily TC pipeline runner.
#
# Replaces a traditional 8:00 AM crontab entry. This workspace runs inside
# gVisor (no cron daemon), so the schedule is enforced by the Zo scheduled
# agent `tc-daily-refresh` (see create_automation tool). The agent invokes
# this script at 8:00 AM ET, which in turn:
#   1. Pulls fresh DraftKings lines (NBA + WNBA) via SGO + ESPN fallback.
#   2. Runs the pregame combos generator to update the pregame dashboards
#      with the new 3-stat combos (PRA, PR, PA) from the fresh lines.
#
# Usage:
#   bash refresh_daily_data.sh
#   bash refresh_daily_data.sh --dry-run     # show what would run, do not execute
#   bash refresh_daily_data.sh --sport NBA   # limit to one sport
#
# Outputs:
#   /home/workspace/Daily_Log/YYYY-MM-DD/combos_<matchup>.{md,json}
#   /home/workspace/Daily_Log/YYYY-MM-DD/dk_scrape_<sport>.json
#   /home/workspace/Daily_Log/refresh_daily_data_<YYYYMMDD>.log
# -----------------------------------------------------------------------------
set -euo pipefail

WORKSPACE="${WORKSPACE:-/home/workspace}"
LOG_ROOT="$WORKSPACE/Daily_Log"
TODAY="$(date -u +%F)"
LOG_DIR="$LOG_ROOT/$TODAY"
LOG_FILE="$LOG_ROOT/refresh_daily_data_$(date -u +%Y%m%d).log"

DRY_RUN=0
SPORT_FILTER=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --sport)   SPORT_FILTER="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$LOG_DIR"
{
  echo "=== refresh_daily_data.sh :: $(date -u +%FT%TZ) ==="
  echo "workspace: $WORKSPACE"
  echo "log_dir:   $LOG_DIR"
  echo "sport:     ${SPORT_FILTER:-BOTH (NBA + WNBA)}"
  echo "dry_run:   $DRY_RUN"
} | tee -a "$LOG_FILE"

# Load env vars from a .env if present (lets scheduled-agent context supply keys)
if [[ -f "$WORKSPACE/.env" ]]; then
  set -a; source "$WORKSPACE/.env"; set +a
  echo "[env] loaded $WORKSPACE/.env" | tee -a "$LOG_FILE"
fi

# Which Python to use
PY="${PY:-python3}"

# 1. DK line scrape
echo "[step 1/2] DK line scrape (SGO + ESPN fallback)" | tee -a "$LOG_FILE"
SPORTS=("NBA" "WNBA")
for sport in "${SPORTS[@]}"; do
  if [[ -n "$SPORT_FILTER" && "$SPORT_FILTER" != "$sport" ]]; then
    echo "  [skip] $sport (filter: $SPORT_FILTER)" | tee -a "$LOG_FILE"
    continue
  fi
  DK_OUT="$LOG_DIR/dk_scrape_${sport}.json"
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "  [dry-run] would run: $PY $WORKSPACE/Projects/daily_picks.py $sport" | tee -a "$LOG_FILE"
  else
    cd "$WORKSPACE"
    "$PY" "$WORKSPACE/Projects/daily_picks.py" "$sport" 2>&1 | tee -a "$LOG_FILE"
    # daily_picks writes /home/workspace/Daily_Log/last_run.json; copy a per-sport snapshot too
    if [[ -f "$LOG_ROOT/last_run.json" ]]; then
      cp "$LOG_ROOT/last_run.json" "$DK_OUT" || true
    fi
  fi
done

# 2. Combos generator (PRA / PR / PA)
echo "[step 2/2] Combos generator (PRA / PR / PA)" | tee -a "$LOG_FILE"
COMBO_ARGS=()
if [[ -n "$SPORT_FILTER" ]]; then
  COMBO_ARGS+=("--sport" "$SPORT_FILTER")
fi
if [[ $DRY_RUN -eq 1 ]]; then
  echo "  [dry-run] would run: $PY $WORKSPACE/Projects/build_pregame_combos.py ${COMBO_ARGS[*]:-}" | tee -a "$LOG_FILE"
else
  cd "$WORKSPACE"
  "$PY" "$WORKSPACE/Projects/build_pregame_combos.py" "${COMBO_ARGS[@]}" 2>&1 | tee -a "$LOG_FILE"
fi

echo "=== refresh_daily_data.sh done :: $(date -u +%FT%TZ) ===" | tee -a "$LOG_FILE"
