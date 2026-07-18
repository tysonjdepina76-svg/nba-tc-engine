#!/bin/bash
CURRENT_DIR=$(pwd)
sed -i "s|/home/workspace/Projects/tc-sports-app|$CURRENT_DIR|g" cron/tc-sports-cron
cp cron/tc-sports-cron /etc/cron.d/tc-sports-cron
chmod 644 /etc/cron.d/tc-sports-cron
echo "Cron installed with path: $CURRENT_DIR"
