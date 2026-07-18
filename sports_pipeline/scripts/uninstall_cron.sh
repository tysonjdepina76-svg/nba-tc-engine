#!/bin/bash
# Removes the cron job
CRON_WRAPPER="/home/workspace/sports_pipeline/scripts/run_pipeline_cron.sh"
crontab -l 2>/dev/null | grep -v "${CRON_WRAPPER}" | crontab -
echo "Cron job removed."
