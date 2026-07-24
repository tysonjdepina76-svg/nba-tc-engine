#!/bin/bash
# scripts/health_check.sh — verify the TC stack is healthy
set -e

cd "$(dirname "$0")/.."

echo "🏥 TC Health Check"
echo "=================="

# Python
echo -n "Python:         "; python3 --version

# Health registry
echo -n "Registry:       "
python3 runtime_health_check.py > /dev/null 2>&1 && echo "OK" || echo "FAIL"

# Disk space
echo -n "Disk free:      "; df -h . | tail -1 | awk '{print $4}'

# Memory
echo -n "Memory free:    "; free -h | grep Mem | awk '{print $7}'

# Ports
for port in 8000 8510; do
  echo -n "Port $port:       "
  if (echo > /dev/tcp/127.0.0.1/$port) 2>/dev/null; then
    echo "OPEN"
  else
    echo "closed"
  fi
done

echo "=================="
