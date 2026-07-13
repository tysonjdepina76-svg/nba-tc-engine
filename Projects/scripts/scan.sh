#!/usr/bin/env bash
# Quick slate scan for today (offline — no API calls)
set -euo pipefail
TODAY=$(TZ='America/New_York' date +%Y-%m-%d)
cd /home/workspace

echo "=== TC Slate Scan — $TODAY ==="

for sport in WNBA MLB WORLD_CUP; do
    echo ""
    echo "--- $sport slate ---"
    case $sport in
        WNBA)
            python3 -c "
import sys; sys.path.insert(0, 'Projects')
from wnba_tc_engine import get_today_slate
games = get_today_slate('$TODAY')
print(f'  {len(games)} upcoming games')
for g in games[:5]:
    print(f'    {g.get(\"away\",\"?\")} @ {g.get(\"home\",\"?\")} — {g.get(\"status\",\"?\")}')
" 2>&1 | head -10
            ;;
        MLB)
            curl -sf --max-time 5 "https://true.zo.space/api/tc?sport=MLB&mode=live-stats" 2>/dev/null | \
                python3 -c "import sys,json; d=json.load(sys.stdin); g=[x for x in d.get('games',[]) if not x.get('completed',True)]; print(f'  {len(g)} upcoming games'); [print(f'    {x.get(\"name\",\"?\")}') for x in g[:5]]" 2>&1 | head -10
            ;;
        WORLD_CUP)
            curl -sf --max-time 5 "https://true.zo.space/api/tc?sport=WORLD_CUP&mode=live-stats" 2>/dev/null | \
                python3 -c "import sys,json; d=json.load(sys.stdin); g=[x for x in d.get('games',[]) if not x.get('completed',True)]; print(f'  {len(g)} upcoming games'); [print(f'    {x.get(\"name\",\"?\")}') for x in g[:5]]" 2>&1 | head -10
            ;;
    esac
done
