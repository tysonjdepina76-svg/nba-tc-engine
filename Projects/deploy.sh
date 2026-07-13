#!/bin/bash
# Top-level deploy.sh — wraps scripts/deploy.sh
set -e
cd "$(dirname "$0")"

if [ -x scripts/deploy.sh ]; then
  bash scripts/deploy.sh
else
  echo "scripts/deploy.sh not found or not executable"
  exit 1
fi
