#!/bin/bash
# Auto-installer for the cron job (idempotent)
PROJECT_DIR="/home/workspace/sports_pipeline"
CRON_WRAPPER="${PROJECT_DIR}/scripts/run_pipeline_cron.sh"
CRON_SCHEDULE="*/5 * * * *"

# Remove any existing entry first
crontab -l 2>/dev/null | grep -v "${CRON_WRAPPER}" | crontab -

# Add new entry
(crontab -l 2>/dev/null; echo "${CRON_SCHEDULE} ${CRON_WRAPPER}") | crontab -
echo "Cron job installed: ${CRON_SCHEDULE} ${CRON_WRAPPER}"
