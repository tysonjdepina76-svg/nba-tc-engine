#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-python3}"
LOG_DIR="logs"
DRY_RUN=0
RETRIES=2
ALLOW_OFFLINE=0

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)       DRY_RUN=1; shift ;;
    --retries)       RETRIES="$2"; shift 2 ;;
    --offline)       ALLOW_OFFLINE=1; shift ;;
    --allow-offline) ALLOW_OFFLINE=1; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/tc_pipeline_$(date +%Y%m%d_%H%M%S).log"

MLB_STATUS="live"
WNBA_STATUS="live"
NBA_STATUS="offseason"
NFL_STATUS="preseason"
NHL_STATUS="offseason"

log() { echo "$@" | tee -a "$LOG"; }

run() {
  local desc="$1"
  local cmd="$2"
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY-RUN: $desc"
    return 0
  fi
  log "▶ $desc"
  local n=0
  until [[ $n -ge $RETRIES ]]; do
    if $PYTHON $cmd 2>&1 | tee -a "$LOG"; then
      return 0
    fi
    n=$((n+1))
    log "  retry $n/$RETRIES"
    sleep 2
  done
  log "FAILED: $desc"
  return 1
}

ACTIVE=()
[[ "$MLB_STATUS"  =~ ^(live|preseason)$ ]] && ACTIVE+=("mlb")
[[ "$WNBA_STATUS" =~ ^(live|preseason)$ ]] && ACTIVE+=("wnba")
[[ "$NBA_STATUS"  =~ ^(live|preseason)$ ]] && ACTIVE+=("nba")
[[ "$NFL_STATUS"  =~ ^(live|preseason)$ ]] && ACTIVE+=("nfl")
[[ "$NHL_STATUS"  =~ ^(live|preseason)$ ]] && ACTIVE+=("nhl")

log "=== TC Pipeline started $(date) ==="
log "Active sports: ${ACTIVE[*]:-none}"
log "Dry-run: $DRY_RUN | Retries: $RETRIES | Offline allowed: $ALLOW_OFFLINE"

log ""
log "===== STAGE 1: PREPARE ====="
run "pipeline_audit.py" "pipeline_audit.py" || true
run "update_closing_lines.py" "update_closing_lines.py" || true
log "Prepare stage done"

log ""
log "===== STAGE 2: PREDICT ====="
for sport in "${ACTIVE[@]}"; do
  log ""
  log "--- Sport: $sport ---"
  run "${sport}_recalibration.py (pre)" "${sport}_recalibration.py" || true
  run "gen_${sport}_today.py" "gen_${sport}_today.py" || true
  run "${sport}_recalibration.py (post)" "${sport}_recalibration.py" || true
done
log "Predict stage done"

log ""
log "===== STAGE 3: PUBLISH ====="
run "daily_picks.py --sport all" "daily_picks.py --sport all"
log "Publish stage done"

log ""
log "===== STAGE 4: EVALUATE ====="
run "run_backtest.py --report" "run_backtest.py --report" || true
log "Evaluate stage done"

log ""
log "Full pipeline finished $(date)"
