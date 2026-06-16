#!/usr/bin/env python3
"""Build WNBA starters/bench/injury-note exports for TC backtesting."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import sys
from datetime import datetime

BASE = pathlib.Path('/home/workspace/wnba_rosters')
OUT_JSON = pathlib.Path('/home/workspace/wnba_rosters/WNBA_BACKTEST_ROSTERS.json')
OUT_PY = pathlib.Path('/home/workspace/wnba_rosters/WNBA_BACKTEST_ROSTERS.py')
OUT_MD = pathlib.Path('/home/workspace/WNBA_BACKTEST_ROSTER_REPORT.md')

CANONICAL = {
    'ATL': ('Atlanta Dream', 'WNBA_ATL_Dream.py'),
    'CHI': ('Chicago Sky', 'WNBA_CHI_Sky.py'),
    'CON': ('Connecticut Sun', 'WNBA_CON_Sun.py'),
    'DAL': ('Dallas Wings', 'WNBA_DAL_Wings.py'),
    'GSV': ('Golden State Valkyries', 'WNBA_GSV_Valkyries.py'),
    'IND': ('Indiana Fever', 'WNBA_IND_Fever.py'),
    'LVA': ('Las Vegas Aces', 'WNBA_LVA_Aces.py'),
    'LAS': ('Los Angeles Sparks', 'WNBA_LAS_Sparks.py'),
    'MIN': ('Minnesota Lynx', 'WNBA_MIN_Lynx.py'),
    'NYL': ('New York Liberty', 'WNBA_NYL_Liberty.py'),
    'PHX': ('Phoenix Mercury', 'WNBA_PHX_Mercury.py'),
    'POR': ('Portland Fire', 'WNBA_POR_Fire.py'),
    'SEA': ('Seattle Storm', 'WNBA_SEA_Storm.py'),
    'TOR': ('Toronto Tempo', 'WNBA_TOR_Tempo.py'),
    'WAS': ('Washington Mystics', 'WNBA_WAS_Mystics.py'),
}

STATUS_NOTE = 'No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.'


def load_module(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = mod
    spec.loader.exec_module(mod)
    return mod


def player_to_dict(p):
    return {
        'name': p.name,
        'pos': p.pos,
        'ht': p.ht,
        'ppg': float(p.ppg),
        'rpg': float(p.rpg),
        'apg': float(p.apg),
        'tpm': float(p.tpm),
        'status': getattr(p, 'status', 'ACTIVE'),
    }


def add_injury_note_to_file(path: pathlib.Path):
    text = path.read_text()
    if 'INJURY_NOTES = []' in text:
        text = text.replace('INJURY_NOTES = []', f'INJURY_NOTES = [\n    {STATUS_NOTE!r},\n]')
        path.write_text(text)
        return True
    return False


def main():
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    report_rows = []
    export = {}
    patched = []
    errors = []

    for code, (team_name, filename) in CANONICAL.items():
        path = BASE / filename
        if not path.exists():
            errors.append(f'{code}: missing {filename}')
            continue

        if add_injury_note_to_file(path):
            patched.append(filename)

        try:
            mod = load_module(path)
            starters = [player_to_dict(p) for p in getattr(mod, 'STARTERS', [])]
            bench = [player_to_dict(p) for p in getattr(mod, 'BENCH', [])]
            injury_notes = list(getattr(mod, 'INJURY_NOTES', [])) or [STATUS_NOTE]
            all_players = starters + bench
            duplicate_names = sorted({p['name'] for p in all_players if [x['name'] for x in all_players].count(p['name']) > 1})

            export[code] = {
                'team_name': team_name,
                'source_file': filename,
                'starters': starters,
                'bench': bench,
                'injury_notes': injury_notes,
                'backtest_ready': len(starters) == 5 and len(bench) >= 5 and len(injury_notes) >= 1 and not duplicate_names,
            }

            report_rows.append({
                'code': code,
                'team': team_name,
                'file': filename,
                'starters': len(starters),
                'bench': len(bench),
                'players': len(all_players),
                'injury_notes': len(injury_notes),
                'duplicates': ', '.join(duplicate_names) if duplicate_names else 'None',
                'status': 'READY' if export[code]['backtest_ready'] else 'CHECK',
            })
        except Exception as exc:
            errors.append(f'{code}: {exc}')

    OUT_JSON.write_text(json.dumps({'generated_at': generated_at, 'teams': export}, indent=2))

    py_lines = [
        '"""WNBA backtest roster export — generated from canonical team files."""',
        f'GENERATED_AT = {generated_at!r}',
        'WNBA_BACKTEST_ROSTERS = ',
        json.dumps(export, indent=4),
        '',
    ]
    OUT_PY.write_text('\n'.join(py_lines))

    md = []
    md.append('# WNBA Backtest Roster Report')
    md.append('')
    md.append(f'**Generated:** {generated_at}')
    md.append('')
    md.append('## Summary')
    md.append('')
    md.append(f'- Canonical teams checked: **{len(CANONICAL)}**')
    md.append(f'- Teams exported: **{len(export)}**')
    md.append(f'- Team files patched with default injury notes: **{len(patched)}**')
    md.append(f'- Errors: **{len(errors)}**')
    md.append('')
    md.append('## Team Readiness')
    md.append('')
    md.append('| Code | Team | Starters | Bench | Total Players | Injury Notes | Duplicates | Status |')
    md.append('|---|---|---:|---:|---:|---:|---|---|')
    for row in report_rows:
        md.append(f"| {row['code']} | {row['team']} | {row['starters']} | {row['bench']} | {row['players']} | {row['injury_notes']} | {row['duplicates']} | {row['status']} |")
    md.append('')
    md.append('## Files Created')
    md.append('')
    md.append('- `wnba_rosters/WNBA_BACKTEST_ROSTERS.json` — JSON export for backtesting engine')
    md.append('- `wnba_rosters/WNBA_BACKTEST_ROSTERS.py` — Python dict export for backtesting engine')
    md.append('- `WNBA_BACKTEST_ROSTER_REPORT.md` — this report')
    md.append('')
    md.append('## Injury Note Standard')
    md.append('')
    md.append(f'> {STATUS_NOTE}')
    md.append('')
    if patched:
        md.append('## Patched Files')
        md.append('')
        for name in patched:
            md.append(f'- `{name}`')
        md.append('')
    if errors:
        md.append('## Errors')
        md.append('')
        for e in errors:
            md.append(f'- {e}')
        md.append('')
    md.append('## Backtesting Engine Contract')
    md.append('')
    md.append('Each team now exposes:')
    md.append('')
    md.append('```python')
    md.append('STARTERS = [Player(...), ...]  # exactly 5')
    md.append('BENCH = [Player(...), ...]')
    md.append('INJURY_NOTES = [...]')
    md.append('```')
    md.append('')
    md.append('The export files normalize every player into: `name`, `pos`, `ht`, `ppg`, `rpg`, `apg`, `tpm`, `status`.')
    OUT_MD.write_text('\n'.join(md))

    print(f'Exported {len(export)} teams')
    print(f'Patched injury notes in {len(patched)} files')
    print(f'Errors: {len(errors)}')
    print(OUT_JSON)
    print(OUT_PY)
    print(OUT_MD)


if __name__ == '__main__':
    main()
