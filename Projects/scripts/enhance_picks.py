#!/usr/bin/env python3
"""
WNBA / MLB Prop Enhancer - Game Context + Actual Results.
Applies blowout discount, park factors, pitcher suppression, batting order PA adjustments,
and fills actual/result from hardcoded box scores.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple

# ------------------------------------------------------------
# 1. HARDCODED BOX SCORES (July 16, 2026)
# ------------------------------------------------------------
ACTUAL_STATS: Dict[Tuple[str, str, str], float] = {
    ('Carla Leite', 'PTS', 'POR@WSH'): 14.0,
    ('Frieda Buhner', 'PTS', 'POR@WSH'): 9.0,
    ('Sarah Ashlee Barker', 'PTS', 'POR@WSH'): 10.0,
    ('Serah Williams', 'PTS', 'POR@WSH'): 12.0,
    ('Shakira Austin', 'PTS', 'POR@WSH'): 19.0,
    ('Shakira Austin', 'REB', 'POR@WSH'): 9.0,
    ('A.J. Ewing', 'H', 'PHI@NYM'): 1.0,
    ('A.J. Ewing', 'HR', 'PHI@NYM'): 0.0,
    ('A.J. Ewing', 'R', 'PHI@NYM'): 0.0,
    ('Juan Soto', 'H', 'PHI@NYM'): 1.0,
    ('Juan Soto', 'HR', 'PHI@NYM'): 0.0,
    ('Juan Soto', 'R', 'PHI@NYM'): 0.0,
    ('Tyrone Taylor', 'H', 'PHI@NYM'): 0.0,
    ('Bo Bichette', 'H', 'PHI@NYM'): 0.0,
    ('Francisco Lindor', 'H', 'PHI@NYM'): 0.0,
    ('Carson Benge', 'H', 'PHI@NYM'): 1.0,
    ('Brett Baty', 'H', 'PHI@NYM'): 2.0,
    ('Brett Baty', 'HR', 'PHI@NYM'): 1.0,
    ('Francisco Alvarez', 'H', 'PHI@NYM'): 2.0,
    ('Francisco Alvarez', 'HR', 'PHI@NYM'): 2.0,
}

# ------------------------------------------------------------
# 2. GAME CONTEXT
# ------------------------------------------------------------
KNOWN_ORDERS = {
    'Juan Soto': 2, 'Francisco Lindor': 1, 'Bo Bichette': 3,
    'A.J. Ewing': 4, 'Tyrone Taylor': 7, 'Carson Benge': 5,
    'Brett Baty': 6, 'Francisco Alvarez': 8, 'Jorge Polanco': 4,
    'Jared Young': 6, 'Kyle Schwarber': 1, 'Bryce Harper': 3,
    'Brandon Marsh': 5, 'Alec Bohm': 4, 'Bryson Stott': 6,
    'J.T. Realmuto': 7, 'Gabriel Rincones Jr.': 8, 'Justin Crawford': 9,
    'Trea Turner': 1,
}

GAME_CONTEXT: Dict[str, Dict] = {
    'POR@WSH': {
        'sport': 'WNBA', 'spread': -19.0, 'favorite': 'POR',
        'team_totals': {'POR': 75.0, 'WSH': 56.0}, 'weak_defense_pos': 'PF',
    },
    'NY@DAL': {
        'sport': 'WNBA', 'spread': -3.5, 'favorite': 'NY',
        'team_totals': {'NY': 85.0, 'DAL': 82.0}, 'weak_defense_pos': 'C',
    },
    'PHI@NYM': {
        'sport': 'MLB', 'park': 'Citi Field', 'park_factor_hr': 0.92,
        'pitcher_k9': 10.2, 'pitcher_suppression_h': 0.90, 'pitcher_suppression_r': 0.88,
        'batting_order_pa': {
            1: 1.125, 2: 1.100, 3: 1.075, 4: 1.050,
            5: 1.000, 6: 0.950, 7: 0.900, 8: 0.850, 9: 0.800,
        },
        'team_totals': {'PHI': 1.0, 'NYM': 4.0},
    },
}

# ------------------------------------------------------------
# 3. ENHANCEMENT ENGINE
# ------------------------------------------------------------
def get_batting_order(player_name: str) -> int:
    return KNOWN_ORDERS.get(player_name, 5)

def apply_wnba_rules(row: pd.Series, ctx: Dict) -> Dict:
    adj = float(row['tc_projection'])
    notes = []
    if abs(ctx['spread']) > 12:
        if row.get('role', '') == 'START':
            adj *= 0.85
            notes.append('Blowout -15% starter mins')
        else:
            adj *= 0.95
            notes.append('Blowout -5% bench mins')
    weak_pos = ctx.get('weak_defense_pos')
    if weak_pos and weak_pos in ['C', 'PF'] and row['stat'] in ['PTS', 'REB']:
        if row.get('role', '') == 'START' or row['stat'] == 'REB':
            adj *= 1.10
            notes.append(f'Mismatch vs. weak {weak_pos} +10%')
    return {'adjusted': adj, 'notes': '; '.join(notes)}

def apply_mlb_rules(row: pd.Series, ctx: Dict) -> Dict:
    adj = float(row['tc_projection'])
    notes = []
    if row['stat'] == 'HR':
        pf = ctx.get('park_factor_hr', 1.0)
        adj *= pf
        if pf < 1.0:
            notes.append('Citi Park HR -8%')
    if row['stat'] == 'H':
        adj *= ctx.get('pitcher_suppression_h', 1.0)
        if ctx.get('pitcher_suppression_h', 1.0) < 1.0:
            notes.append('Elite SP H -10%')
    if row['stat'] == 'R':
        adj *= ctx.get('pitcher_suppression_r', 1.0)
        if ctx.get('pitcher_suppression_r', 1.0) < 1.0:
            notes.append('Elite SP R -12%')
    order = get_batting_order(row.get('player', ''))
    pa_mult = ctx.get('batting_order_pa', {}).get(order, 1.0)
    adj *= pa_mult
    if pa_mult != 1.0:
        notes.append(f'Batting order #{order} PA adj {pa_mult:.2f}x')
    return {'adjusted': adj, 'notes': '; '.join(notes)}

def compute_confidence(row: pd.Series, adj_proj: float, orig_proj: float) -> int:
    low_var_stats = ['REB', 'H', 'R']
    high_var_stats = ['HR', 'AST', 'PTS']
    base = 70
    if row['stat'] in low_var_stats:
        base += 20
    elif row['stat'] in high_var_stats:
        base -= 10
    pct_change = abs(adj_proj - orig_proj) / (orig_proj + 0.001)
    if pct_change < 0.05:
        base += 10
    elif pct_change > 0.20:
        base -= 10
    if row.get('role', '') == 'BENCH':
        base -= 5
    return max(10, min(100, base))

def determine_action(stat: str, adj_proj: float, line: float) -> Tuple[str, float]:
    if line <= 0:
        return 'VOID', 0.0
    edge = (adj_proj - line) / line
    if edge <= 0.01:
        return 'AVOID', edge
    if stat in ['HR', 'AST'] and edge < 0.07:
        return 'AVOID', edge
    if edge >= 0.05:
        return 'GO', edge
    return 'AVOID', edge

# ------------------------------------------------------------
# 4. MAIN PROCESSING PIPELINE
# ------------------------------------------------------------
def enhance_picks(df: pd.DataFrame) -> pd.DataFrame:
    df_enh = df.copy()
    # Fill actual & result
    df_enh['actual'] = np.nan
    df_enh['result'] = 'PENDING'
    for idx, row in df_enh.iterrows():
        key = (row['player'], row['stat'], row['matchup'])
        if key in ACTUAL_STATS:
            actual_val = ACTUAL_STATS[key]
            df_enh.at[idx, 'actual'] = actual_val
            line = float(row['market_line'])
            if actual_val > line:
                df_enh.at[idx, 'result'] = 'WIN'
            elif actual_val < line:
                df_enh.at[idx, 'result'] = 'LOSS'
            else:
                df_enh.at[idx, 'result'] = 'PUSH'

    # Enhancement columns
    adj_projs, confs, edges, actions, notes = [], [], [], [], []
    for idx, row in df_enh.iterrows():
        ctx = GAME_CONTEXT.get(row['matchup'], {})
        sport = ctx.get('sport', '')
        orig_proj = float(row['tc_projection'])
        line = float(row['market_line'])
        adj_proj, note = orig_proj, ''
        if sport == 'WNBA' and ctx:
            res = apply_wnba_rules(row, ctx)
            adj_proj, note = res['adjusted'], res['notes']
        elif sport == 'MLB' and ctx:
            res = apply_mlb_rules(row, ctx)
            adj_proj, note = res['adjusted'], res['notes']
        else:
            note = 'No context available'
        adj_projs.append(adj_proj)
        notes.append(note)
        confs.append(compute_confidence(row, adj_proj, orig_proj))
        action, edge = determine_action(row['stat'], adj_proj, line)
        actions.append(action)
        edges.append(edge)

    df_enh['adjusted_projection'] = adj_projs
    df_enh['game_context_note'] = notes
    df_enh['confidence_score'] = confs
    df_enh['action_status'] = actions
    df_enh['true_edge'] = edges

    # Global team total cap
    for matchup, ctx in GAME_CONTEXT.items():
        if 'team_totals' not in ctx:
            continue
        mask = df_enh['matchup'] == matchup
        for team, total in ctx['team_totals'].items():
            team_mask = mask & (df_enh['team'] == team)
            if team_mask.sum() == 0:
                continue
            sum_adj = df_enh.loc[team_mask, 'adjusted_projection'].sum()
            if sum_adj > 0:
                cap = total * 1.05
                if sum_adj > cap:
                    scale = cap / sum_adj
                    df_enh.loc[team_mask, 'adjusted_projection'] *= scale
                    df_enh.loc[team_mask, 'game_context_note'] += '; Cap scaled to team total'

    return df_enh

# ------------------------------------------------------------
# 5. VALIDATION REPORT
# ------------------------------------------------------------
def generate_report(df: pd.DataFrame):
    mask = df['actual'].notna()
    if mask.sum() == 0:
        print("No actual results available to validate.")
        return
    df_test = df[mask].copy()
    orig_w = (df_test['result'] == 'WIN').sum()
    orig_l = (df_test['result'] == 'LOSS').sum()
    orig_p = (df_test['result'] == 'PUSH').sum()
    df_test['enh_result'] = np.where(
        df_test['actual'] > df_test['adjusted_projection'], 'WIN',
        np.where(df_test['actual'] < df_test['adjusted_projection'], 'LOSS', 'PUSH'))
    enh_w = (df_test['enh_result'] == 'WIN').sum()
    enh_l = (df_test['enh_result'] == 'LOSS').sum()
    enh_p = (df_test['enh_result'] == 'PUSH').sum()
    print("=" * 60)
    print("VALIDATION REPORT - JULY 16, 2026")
    print("=" * 60)
    print(f"Total props with actuals: {len(df_test)}")
    print(f"\n--- Original Model (line vs actual) ---")
    print(f"  Wins: {orig_w} | Losses: {orig_l} | Pushes: {orig_p}")
    hit = orig_w / (orig_w + orig_l) if (orig_w + orig_l) > 0 else 0
    print(f"  Hit Rate: {hit:.1%}")
    print(f"\n--- Enhanced Model (adjusted projection vs actual) ---")
    print(f"  Wins: {enh_w} | Losses: {enh_l} | Pushes: {enh_p}")
    hit_enh = enh_w / (enh_w + enh_l) if (enh_w + enh_l) > 0 else 0
    print(f"  Hit Rate: {hit_enh:.1%}")
    for sport in ['WNBA', 'MLB']:
        sub = df_test[df_test['league'] == sport]
        if len(sub) == 0:
            continue
        ow = (sub['result'] == 'WIN').sum()
        ol = (sub['result'] == 'LOSS').sum()
        ew = (sub['enh_result'] == 'WIN').sum()
        el = (sub['enh_result'] == 'LOSS').sum()
        print(f"\n--- {sport} ---")
        print(f"  Original: {ow}W {ol}L ({ow/(ow+ol):.1%})" if (ow+ol) > 0 else f"  Original: {ow}W {ol}L")
        print(f"  Enhanced: {ew}W {el}L ({ew/(ew+el):.1%})" if (ew+el) > 0 else f"  Enhanced: {ew}W {el}L")
    go_picks = df[(df['action_status'] == 'GO') & (df['actual'].isna())]
    print(f"\n--- ENHANCED ACTIONABLE PICKS (GO): {len(go_picks)} ---")
    if len(go_picks) > 0:
        print(go_picks[['matchup', 'team', 'player', 'stat', 'market_line',
                         'adjusted_projection', 'true_edge', 'confidence_score']].to_string(index=False))

if __name__ == '__main__':
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else None
    if csv_path and Path(csv_path).exists():
        df = pd.read_csv(csv_path, on_bad_lines="skip")
        print(f"Loaded {len(df)} picks from {csv_path}")
        df_enhanced = enhance_picks(df)
        out = csv_path.replace('.csv', '_enhanced.csv')
        df_enhanced.to_csv(out, index=False)
        print(f"Enhanced CSV saved as '{out}'")
        generate_report(df_enhanced)
    else:
        print("Usage: python3 scripts/enhance_picks.py <picks.csv>")
