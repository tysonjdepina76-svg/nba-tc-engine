#!/usr/bin/env python3
"""
NBA Live Monitor — ESPN API
Polls the live NBA scoreboard and saves current game status + player 4-stat box score.
TC note: this monitors live box score source data only; TC prop math is applied separately.
"""
from __future__ import annotations

import csv
import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path

OUT_DIR = Path('/home/workspace/live_sports_scrape')
OUT_DIR.mkdir(parents=True, exist_ok=True)
SCOREBOARD = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard'
SUMMARY = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={event_id}'


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def parse_boxscore(event_id: str) -> list[dict]:
    data = fetch_json(SUMMARY.format(event_id=event_id))
    rows: list[dict] = []
    for team in data.get('boxscore', {}).get('players', []):
        team_abbr = team.get('team', {}).get('abbreviation') or team.get('team', {}).get('shortDisplayName') or ''
        for block in team.get('statistics', []):
            labels = block.get('labels', [])
            athletes = block.get('athletes', [])
            if not labels or not athletes:
                continue
            for item in athletes:
                athlete = item.get('athlete', {})
                vals = item.get('stats', [])
                stat = {lab: vals[i] if i < len(vals) else '' for i, lab in enumerate(labels)}
                name = athlete.get('displayName') or athlete.get('shortName') or ''
                mins = stat.get('MIN', '')
                if not name or not mins or mins in ('0', '0:00'):
                    continue
                made3 = '0'
                if stat.get('3PT'):
                    made3 = str(stat.get('3PT')).split('-')[0]
                rows.append({
                    'team': team_abbr,
                    'player': name,
                    'min': mins,
                    'pts': stat.get('PTS', '0'),
                    'reb': stat.get('REB', '0'),
                    'ast': stat.get('AST', '0'),
                    '3pm': made3,
                })
            break
    return rows


def snapshot() -> dict:
    board = fetch_json(SCOREBOARD)
    games = []
    all_rows = []
    for ev in board.get('events', []):
        comp = (ev.get('competitions') or [{}])[0]
        status = comp.get('status', {})
        stype = status.get('type', {})
        competitors = comp.get('competitors', [])
        teams = {}
        for c in competitors:
            side = c.get('homeAway')
            team = c.get('team', {})
            teams[side] = {
                'abbr': team.get('abbreviation'),
                'name': team.get('displayName'),
                'score': c.get('score'),
                'winner': c.get('winner'),
            }
        event_id = ev.get('id')
        rows = parse_boxscore(event_id) if event_id else []
        all_rows.extend([{**r, 'event_id': event_id} for r in rows])
        games.append({
            'event_id': event_id,
            'name': ev.get('name'),
            'short_name': ev.get('shortName'),
            'date': ev.get('date'),
            'status': stype.get('description') or stype.get('detail'),
            'period': status.get('period'),
            'clock': status.get('displayClock'),
            'away': teams.get('away', {}),
            'home': teams.get('home', {}),
            'leaders': rows,
        })
    return {'updated_at': datetime.now().isoformat(timespec='seconds'), 'games': games, 'rows': all_rows}


def write_outputs(data: dict) -> None:
    (OUT_DIR / 'NBA_Live_Monitor_Latest.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    with (OUT_DIR / 'NBA_Live_Monitor_Latest.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['event_id', 'team', 'player', 'min', 'pts', 'reb', 'ast', '3pm'])
        w.writeheader(); w.writerows(data.get('rows', []))
    lines = [f"# NBA Live Monitor\n", f"Updated: {data['updated_at']}\n"]
    for g in data.get('games', []):
        a, h = g.get('away', {}), g.get('home', {})
        lines.append(f"## {a.get('abbr')} {a.get('score')} @ {h.get('abbr')} {h.get('score')} — {g.get('status')} Q{g.get('period')} {g.get('clock')}\n")
        lines.append('| Team | Player | MIN | PTS | REB | AST | 3PM |\n|---|---|---:|---:|---:|---:|---:|')
        for r in g.get('leaders', []):
            lines.append(f"| {r['team']} | {r['player']} | {r['min']} | {r['pts']} | {r['reb']} | {r['ast']} | {r['3pm']} |")
        lines.append('')
    (OUT_DIR / 'NBA_Live_Monitor_Latest.md').write_text('\n'.join(lines), encoding='utf-8')


def main(interval: int = 60, once: bool = False) -> None:
    while True:
        try:
            data = snapshot()
            write_outputs(data)
            print(f"{data['updated_at']} saved {len(data.get('games', []))} game(s), {len(data.get('rows', []))} player rows", flush=True)
        except Exception as e:
            print(f"ERROR {datetime.now().isoformat(timespec='seconds')}: {e}", flush=True)
        if once:
            break
        time.sleep(interval)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--interval', type=int, default=60)
    p.add_argument('--once', action='store_true')
    args = p.parse_args()
    main(args.interval, args.once)
