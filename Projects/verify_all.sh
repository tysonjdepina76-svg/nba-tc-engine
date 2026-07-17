#!/bin/bash
set -e
echo "=== TC Verification — $(date) ==="
python3 /home/workspace/Projects/runtime_health_check.py
python3 -c "from src.domain.entities import REGISTRY; print('Registry:', REGISTRY.list_enabled())" 2>&1
echo "=== All checks passed ==="
