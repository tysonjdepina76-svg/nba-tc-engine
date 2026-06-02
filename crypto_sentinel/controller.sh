#!/usr/bin/env bash
# Crypto Leverage Sentinel — controller.
# Runs the risk check once and emits a single-line JSON cadence directive
# the automation runner can act on.
#
# Exit codes:
#   0 = success
#   1 = risk check failed
#
# Stdout (single line, JSON):
#   {"cadence": "60s" | "5m", "status": "...", "distance_pct": ..., "alert": "..."}
#
# Dynamic throttle (per AGENTS.md):
#   - status == "CRITICAL"  -> cadence "60s"
#   - otherwise             -> cadence "5m"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/leverage_check.py"
LAST_METRICS="$SCRIPT_DIR/last_metrics.json"
LOG_FILE="$SCRIPT_DIR/sentinel.log"

# Run the risk check; capture stdout separately from stderr.
if ! python3 "$PY_SCRIPT" > /tmp/sentinel_run.json 2>> "$LOG_FILE"; then
    echo "{\"cadence\": \"5m\", \"status\": \"UNKNOWN\", \"distance_pct\": null, \"alert\": \"RUN_FAILED\"}"
    exit 1
fi

if [ ! -f "$LAST_METRICS" ]; then
    echo "{\"cadence\": \"5m\", \"status\": \"UNKNOWN\", \"distance_pct\": null, \"alert\": \"NO_DATA\"}"
    exit 0
fi

# Read fields without spawning Python a second time.
STATUS=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('status',''))" "$LAST_METRICS")
DISTANCE=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('distance_to_liq_percent',''))" "$LAST_METRICS")
ALERT=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('alert',''))" "$LAST_METRICS")

CADENCE="5m"
if [ "$STATUS" = "CRITICAL" ]; then
    CADENCE="60s"
fi

echo "{\"cadence\": \"$CADENCE\", \"status\": \"$STATUS\", \"distance_pct\": $DISTANCE, \"alert\": \"$ALERT\"}"
