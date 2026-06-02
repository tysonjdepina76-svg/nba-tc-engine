#!/usr/bin/env bash
# Crypto Leverage Sentinel — controller
# Reads the last run, decides if we need to escalate, and emits a one-line
# cadence directive that the automation runner can act on.
#
# Exit codes:
#   0 = normal completion, see stdout for cadence
#   1 = script error
#
# Stdout (single line, JSON):
#   {"cadence": "60s" | "5m", "status": "...", "distance_pct": ..., "alert": "..."}

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/leverage_check.py"
LAST_METRICS="$SCRIPT_DIR/last_metrics.json"

# Run the check
python3 "$PY_SCRIPT" > /tmp/sentinel_run.json 2>> "$SCRIPT_DIR/sentinel.log"

if [ ! -f "$LAST_METRICS" ]; then
    echo "{\"cadence\": \"5m\", \"status\": \"UNKNOWN\", \"distance_pct\": null, \"alert\": \"NO_DATA\"}"
    exit 0
fi

# Parse the last run
STATUS=$(python3 -c "import json; d=json.load(open('$LAST_METRICS')); print(d.get('status',''))")
DISTANCE=$(python3 -c "import json; d=json.load(open('$LAST_METRICS')); print(d.get('distance_to_liq_percent',''))")
ALERT=$(python3 -c "import json; d=json.load(open('$LAST_METRICS')); print(d.get('alert',''))")

# Throttle decision
CADENCE="5m"
if [ "$STATUS" = "CRITICAL" ]; then
    CADENCE="60s"
fi

echo "{\"cadence\": \"$CADENCE\", \"status\": \"$STATUS\", \"distance_pct\": $DISTANCE, \"alert\": \"$ALERT\"}"
