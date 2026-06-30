#!/usr/bin/env python3
"""
World Cup Live Stats Fetcher — pulls team-level live stats from ESPN summary
for all in-progress and completed matches. Writes to Daily_Log/wc_live_stats.json.
The /api/worldcup-props route reads this file to inject live stats into the dashboard.

RUN: python3 Projects/wc_live_stats.py
"""
import json, requests, sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log" / "worldcup"
OUTPUT = WORKSPACE / "Daily_Log" / "wc_live_stats.json"

ESPN_SCOREBOARD = 'https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard'
ESPN_SCOREBOARD = 'https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard'

ESPN_TO_STAT = {
    'totalShots': 'shots', 'wonCorners': 'corners', 'foulsCommitted': 'fouls',
    'yellowCards': 'cards', 'saves': 'saves', 'possessionPct': 'possession',
    'totalGoals': 'goals', 'offside': 'offsides', 'tacklesWon': 'tackles',
    'shotsOnTarget': 'shots_on_target', 'totalPasses': 'passes',
}

def fetch_scoreboard():
    r = requests.get(ESPN_SCOREBOARD, headers={'Accept':'application/json'}, timeout=15)
    r.raise_for_status()
    data = r.json()
    matches = []
    for ev in data.get('events', []):
        comp = (ev.get('competitions') or [{}])[0]
        status = ev.get('status', {}).get('type', {})
        teams = []
        for co in comp.get('competitors', []):
            t = co.get('team', {})
            teams.append({'name': t.get('displayName',''), 'abbrev': t.get('abbreviation',''), 'score': str(co.get('score','0')), 'homeAway': co.get('homeAway','')})
        matches.append({'espn_id': str(ev.get('id','')), 'name': ev.get('name',''), 'short_name': ev.get('shortName',''), 'status': status.get('description','Scheduled'), 'status_detail': status.get('shortDetail',''), 'completed': status.get('completed', False), 'period': status.get('period', 0), 'teams': teams})
    return matches

def fetch_team_stats(event_id):
    url = f'https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event={event_id}'
    try:
        r = requests.get(url, headers={'Accept':'application/json'}, timeout=10)
        r.raise_for_status()
        data = r.json()
        bs = data.get('boxscore', {})
        team_stats = {}
        for tb in bs.get('teams', []):
            team = tb.get('team', {})
            team_abbr = team.get('abbreviation', team.get('displayName', '?'))
            mapped = {}
            for s in tb.get('statistics', []):
                espn_name = s.get('name', s.get('label', ''))
                key = ESPN_TO_STAT.get(espn_name, espn_name)
                val = s.get('displayValue', str(s.get('value', '0')))
                mapped[key] = val
            team_stats[team_abbr] = mapped
        return team_stats
    except Exception as e:
        print(f' Stats fetch error {event_id}: {e}')
        return {}

def main():
    now = datetime.now(timezone.utc)
    date_str = now.strftime('%Y%m%d')
    props_path = WORKSPACE / 'Daily_Log' / 'worldcup' / date_str / 'props.json'
    if not props_path.exists():
        print(f'No props.json for {date_str}')
        return
    with open(props_path) as f:
        matches = json.load(f)
    print(f'Loaded {len(matches)} matches from props.json')
    # Fetch live scoreboard for current statuses
    live_matches = fetch_scoreboard()
    print(f'Live scoreboard: {len(live_matches)} events')
    # Fetch stats for all completed or in-progress matches
    stats_cache = {}
    for m in matches:
        status = str(m.get('status', '')).lower()
        is_active = any(kw in status for kw in ('full','progress','half','live','end','1st','2nd','final'))
        if not is_active:
            print(f'  SKIP {m.get("short_name","?")}: status={m.get("status")}')
            continue
        eid = str(m.get('espn_id', ''))
        if not eid:
            print(f'  SKIP {m.get("short_name","?")}: no espn_id')
            continue
        print(f'  Fetching stats for {m.get("short_name","?")} (id={eid})...')
        ts = fetch_team_stats(eid)
        if ts:
            stats_cache[eid] = ts
            short = m.get('short_name', '?')
            for team_abbr, smap in ts.items():
                print(f'    {team_abbr}: {dict(list(smap.items())[:6])}')
    # Write cache
    cache_path = WORKSPACE / 'Daily_Log' / 'worldcup' / date_str / 'live_stats.json'
    with open(cache_path, 'w') as f:
        json.dump({'date': date_str, 'fetched_at': now.isoformat(), 'stats': stats_cache}, f, indent=2, default=str)
    print(f'\nWrote {len(stats_cache)} match stats to {cache_path}')

if __name__ == '__main__':
    main()
