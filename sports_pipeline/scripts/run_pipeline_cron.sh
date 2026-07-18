#!/bin/bash
# Production cron wrapper - hardened for cron's minimal environment
PROJECT_DIR="/home/workspace/sports_pipeline"
PYTHON_CMD="/usr/bin/python3"
LOG_FILE="${PROJECT_DIR}/logs/cron.log"
ENV_FILE="${PROJECT_DIR}/.env"

cd "${PROJECT_DIR}" || { echo "ERROR: Cannot cd to ${PROJECT_DIR}" >&2; exit 1; }
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PYTHONPATH="${PROJECT_DIR}:${PYTHONPATH}"

if [ -f "${ENV_FILE}" ]; then
    set -a
    source "${ENV_FILE}"
    set +a
fi

mkdir -p "$(dirname "${LOG_FILE}")"

if [ -f "${LOG_FILE}" ] && [ "$(stat -c%s "${LOG_FILE}")" -gt 10485760 ]; then
    mv "${LOG_FILE}" "${LOG_FILE}.old"
fi

echo "=================================================" >> "${LOG_FILE}"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting cron run" >> "${LOG_FILE}"

${PYTHON_CMD} main.py run >> "${LOG_FILE}" 2>&1
EXIT_CODE=$?

if [ ${EXIT_CODE} -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS" >> "${LOG_FILE}"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] FAILED (exit ${EXIT_CODE})" >> "${LOG_FILE}"
fi

exit ${EXIT_CODE}
