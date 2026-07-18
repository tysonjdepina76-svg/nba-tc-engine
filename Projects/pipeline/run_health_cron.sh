#!/bin/bash
cd /home/workspace/Projects && python3 pipeline/health_check.py --repair >> pipeline/cron.log 2>&1
