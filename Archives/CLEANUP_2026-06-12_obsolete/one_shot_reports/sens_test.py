import sys
sys.path.insert(0, '/home/workspace/Projects')
from tc_math import project_pra, project_pr, project_pa, STAT_CONS, SPORT_PROFILE
print('STAT_CONS:', STAT_CONS)
print('WNBA profile:', SPORT_PROFILE['WNBA'])
print('factor (0.85*0.85*0.85)*0.833 =', round(0.85*0.85*0.85*0.833, 3))
# Angel Reese: 23pts, 13reb, 2ast -> raw PRA 38
for cons_pts, cons_reb, cons_ast, lift, norm in [
    (0.85, 0.85, 0.85, 0.025, 40/48),
    (0.92, 0.92, 0.92, 0.02, 0.86),
    (0.95, 0.95, 0.95, 0.0, 0.88),
    (0.90, 0.90, 0.90, 0.0, 0.87),
]:
    p = project_pra(23, 13, 2, 'ACTIVE', 'WNBA')
    p2 = (23*cons_pts + 13*cons_reb*(1+lift) + 2*cons_ast*(1+lift)) * norm
    print(f' cons={cons_pts}/{cons_reb}/{cons_ast} lift={lift} norm={norm:.3f} -> TC={p}  alt={round(p2,2)}')