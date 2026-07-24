#!/bin/bash
# scripts/run_with_lock.sh
# Advisory lock to prevent overlapping pipeline runs
LOCKFILE="/tmp/tc_pipeline.lock"
LOGFILE="/home/workspace/Projects/logs/cron.log"

# Bail if a run is already in progress
if [ -f "$LOCKFILE" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') SKIP: pipeline already running (lock: $LOCKFILE)" >> "$LOGFILE"
    exit 0
fi

# Cleanup lock on exit (success or failure)
trap "rm -f $LOCKFILE" EXIT
touch "$LOCKFILE"

# Log start
echo "$(date '+%Y-%m-%d %H:%M:%S') START: $*" >> "$LOGFILE"

# Run the actual command
"$@"
RC=$?

# Log end
echo "$(date '+%Y-%m-%d %H:%M:%S') END: $* (exit $RC)" >> "$LOGFILE"
exit $RC
