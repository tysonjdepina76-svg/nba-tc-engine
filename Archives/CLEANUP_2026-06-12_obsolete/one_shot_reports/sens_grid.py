#!/usr/bin/env python3
import sys, csv
sys.path.insert(0, '/home/workspace/Projects')
from tc_math import STAT_CONS, SPORT_PROFILE, _combo_line, project_pra, project_pr, project_pa
# Monkey-patch the constants
def trial(pts_c, reb_c, ast_c, wnba_norm, combo_cons, rb_lift):
    STAT_CONS['pts'] = pts_c
    STAT_CONS['reb'] = reb_c
    STAT_CONS['ast'] = ast_c
    SPORT_PROFILE['WNBA']['minutes_norm'] = wnba_norm
    SPORT_PROFILE['WNBA']['reb_ast_lift'] = rb_lift
    SPORT_PROFILE['WNBA']['pra_cons'] = combo_cons
    SPORT_PROFILE['NBA']['pra_cons'] = combo_cons
    rows = list(csv.DictReader(open('/home/workspace/Reports/tc_math_audit_20260610_2257.csv')))
    n = 0
    h = 0
    # TC picks are the unique lines; 2 sides each. Find unique (player, type, dk_line)
    seen = set()
    for r in rows:
        k = (r['player'], r['combo_type'], r['dk_line'])
        if k in seen: continue
        seen.add(k)
        # project based on actual splits
        # We have the actual stat combo. For a real backtest we would need the prior game. Approx: use ACTUAL combo as the projection
        # (this is biased upward; the per-leg audit will show by how much)
        pass
# We need actual splits. fetch them inline.
import requests, re
from pathlib import Path
KEY = ''
for ln in Path('/root/.zo/secrets.env').read_text().splitlines():
    m = re.match(r'^\s*ODDS_API_KEY\s*=\s*["\']?([^"\'\s#]+)', ln)
    if m: KEY = m.group(1)
# Get the ATL@CHI event id
r = requests.get('https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard', params={'dates':'20260609'}, timeout=15)
d = r.json()
eid = None
for ev in d.get('events', []):
    comp = ev['competitions'][0]
    teams = [c['team']['abbreviation'] for c in comp['competitors']]
    if 'ATL' in teams and 'CHI' in teams:
        eid = ev['id']
        break
print('event', eid)
r = requests.get('https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary', params={'event':eid}, timeout=15)
d = r.json()
splits = {}
for grp in d.get('boxscore', {}).get('players', []):
    team = grp.get('team', {}).get('abbreviation', '?')
    for sgrp in grp.get('statistics', []):
        keys = sgrp.get('keys', [])
        if 'points' not in keys: continue
        i_p = keys.index('points')
        i_r = keys.index('rebounds') if 'rebounds' in keys else -1
        i_a = keys.index('assists') if 'assists' in keys else -1
        for ath in sgrp.get('athletes', []):
            name = ath.get('athlete', {}).get('displayName', '?')
            stats = ath.get('stats', [])
            def to_int(x):
                try: return int(x)
                except: return 0
            pts = to_int(stats[i_p]) if i_p < len(stats) else 0
            reb = to_int(stats[i_r]) if 0 <= i_r < len(stats) else 0
            ast = to_int(stats[i_a]) if 0 <= i_a < len(stats) else 0
            if pts + reb + ast < 5: continue
            splits[name] = (team, pts, reb, ast)
print('splits:', len(splits))
for nm, (tm, p, r, a) in list(splits.items())[:5]: print(' ', nm, tm, p, r, a)
# DK closing lines from the audit CSV
dk_lines = {}
for row in csv.DictReader(open('/home/workspace/Reports/tc_math_audit_20260610_2257.csv')):
    k = (row['player'], row['combo_type'])
    if k not in dk_lines: dk_lines[k] = float(row['dk_line'])
print('dk lines:', len(dk_lines))
# Now test configurations. Use ACTUAL as the 'L5 avg' proxy to find the ceiling
# (the under-shoot means TC is more conservative than even the actual; in a true
# pre-game setting the projection would be lower, so this is the UPPER bound)
configs = [
    ('baseline 0.85/0.85/0.85/0.833/0.025', 0.85, 0.85, 0.85, 0.833, 0.85, 0.025),
    ('lift 0.92/0.92/0.92/0.86/0.025',       0.92, 0.92, 0.92, 0.86,  0.90, 0.025),
    ('lift 0.95/0.95/0.95/0.86/0',            0.95, 0.95, 0.95, 0.86,  0.92, 0.0),
    ('lift 0.90/0.90/0.90/0.85/0.02',         0.90, 0.90, 0.90, 0.85,  0.88, 0.02),
    ('lift 0.88/0.90/0.90/0.85/0.02',         0.88, 0.90, 0.90, 0.85,  0.88, 0.02),
    ('combo 0.85/0.85/0.85/0.833/0.025*0.95', 0.85, 0.85, 0.85, 0.833, 0.95*0.85, 0.025),
]
for name, pc, rc, ac, wn, cc, rl in configs:
    STAT_CONS['pts'] = pc; STAT_CONS['reb'] = rc; STAT_CONS['ast'] = ac
    SPORT_PROFILE['WNBA']['minutes_norm'] = wn
    SPORT_PROFILE['WNBA']['reb_ast_lift'] = rl
    SPORT_PROFILE['WNBA']['pra_cons'] = cc
    SPORT_PROFILE['NBA']['pra_cons'] = cc
    over_h = 0; over_n = 0; under_h = 0; under_n = 0
    for (player, ctype), dk in dk_lines.items():
        if player not in splits: continue
        tm, p, r_, a_ = splits[player]
        if ctype == 'PRA': tc = project_pra(p, r_, a_, 'ACTIVE', 'WNBA')
        elif ctype == 'PR': tc = project_pr(p, r_, 'ACTIVE', 'WNBA')
        else: tc = project_pa(p, a_, 'ACTIVE', 'WNBA')
        actual = p + r_ + a_ if ctype == 'PRA' else (p + r_ if ctype == 'PR' else p + a_)
        if tc > dk: over_n += 1
        if tc < dk: under_n += 1
        if tc > dk and actual > dk: over_h += 1
        if tc < dk and actual < dk: under_h += 1
    o_hr = over_h / over_n * 100 if over_n else 0
    u_hr = under_h / under_n * 100 if under_n else 0
    tot_n = over_n + under_n
    tot_h = over_h + under_h
    tot_hr = tot_h / tot_n * 100 if tot_n else 0
    print('%-50s OVER %d/%d %.0f%%  UNDER %d/%d %.0f%%  TOT %d/%d %.0f%%' % (name, over_h, over_n, o_hr, under_h, under_n, u_hr, tot_h, tot_n, tot_hr))
