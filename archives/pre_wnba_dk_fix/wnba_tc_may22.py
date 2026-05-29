"""
WNBA Enhanced TC Projections — May 22, 2026
Live DraftKings lines via ESPN scoreboard + WNBA master roster
"""
import ast, re, json
from dataclasses import dataclass

@dataclass
class Player:
    name: str; pos: str; ht: str
    ppg: float; rpg: float; apg: float; tpm: float
    status: str = "ACTIVE"; injury: str = ""

# ── Parse WNBA_MASTER_ROSTER.PY ──────────────────────────────────────────────
raw = open('/home/workspace/wnba_rosters/WNBA_MASTER_ROSTER.py').read()
STARTERS = {}; BENCH = {}
cur_section = None; cur_team = None

for line in raw.split('\n'):
    hm = re.match(r"^#\s+([A-Z]{2,4})\s+—\s+", line)
    if hm:
        cur_team = hm.group(1); cur_section = None
    sm = re.match(r'^\s*(STARTERS|BENCH)_([A-Z]{2,4})\s+\=', line)
    if sm and cur_team:
        cur_section = (sm.group(1), sm.group(2))
    if 'Player(' not in line or not cur_section:
        continue
    try:
        start = line.index('Player(')
        end   = line.rindex(')') + 1
        call  = line[start:end]
        # Raw file uses actual backslash chars in height: 6\'0\" → 6'0"
        call_clean = call.replace("\\'", "'").replace('\\"', '"')
        tree = ast.parse(call_clean, mode='eval')
        args = tree.body.args
        vals  = [arg.value for arg in args if isinstance(arg, ast.Constant)]
        if len(vals) >= 7:
            p = Player(
                name=str(vals[0]), pos=str(vals[1]), ht=str(vals[2]),
                ppg=float(vals[3]), rpg=float(vals[4]),
                apg=float(vals[5]), tpm=float(vals[6])
            )
            key = cur_section[1]
            if cur_section[0] == 'STARTERS':
                STARTERS.setdefault(key, []).append(p)
            else:
                BENCH.setdefault(key, []).append(p)
    except Exception:
        pass

# ── TC Engine ───────────────────────────────────────────────────────────────────
PF = 0.85   # TC player factor
LF = 0.88   # Line factor
QF = 0.55   # Questionable factor

# Live DraftKings lines from ESPN scoreboard (May 22, 2026)
GAMES = [
    ('DAL','ATL', 173.5, -5.5),
    ('GS', 'IND', 167.5, -5.5),
    ('CON','SEA', 165.5, -1.5),
]

TN = {
    'ATL':'Dream','CHI':'Sky','CON':'Sun','DAL':'Wings','GS':'Valkyries',
    'IND':'Fever','LAS':'Sparks','LVA':'Aces','MIN':'Lynx','NY':'Liberty',
    'PHX':'Mercury','POR':'Fire','SEA':'Storm','TOR':'Tempo','WAS':'Mystics'
}

def tcp(p):
    w = PF
    if p.status == 'Q':   w = PF * QF
    elif p.status == 'OUT': w = 0
    return round(p.ppg * w, 1)

def lnp(p): return round(p.ppg * LF, 1)

def tpmp(p):
    w = PF
    if p.status == 'Q':   w = PF * QF
    elif p.status == 'OUT': w = 0
    return round(p.tpm * w, 1)

def btc(a): return sum(tcp(p) for p in STARTERS[a] + BENCH[a])

def mi(home, away, total, spread):
    """Derive market-implied team totals from spread + total."""
    fav = home if spread < 0 else away
    und = away if spread < 0 else home
    fv  = abs(spread)
    fi  = round((total + fv) / 2, 1)
    ui  = round((total - fv) / 2, 1)
    if fav == home:
        fi = round(fi * 1.008, 1)
    return {fav: fi, und: ui}

# ── Generate Projections ─────────────────────────────────────────────────────
S = []
print("=" * 75)
print(" WNBA ENHANCED TC — MAY 22, 2026 (LIVE DRAFTKINGS LINES)")
print("=" * 75)

for aw, hm, tot, spr in GAMES:
    awtc  = btc(aw);  hmtc  = btc(hm)
    m     = mi(hm, aw, tot, spr)
    awmi  = m[aw];   hmmi  = m[hm]
    comb  = round(awtc + hmtc, 1)
    lean  = "UNDER" if comb < tot else "OVER"
    tae   = round(awtc - awmi, 1)
    hme   = round(hmtc - hmmi, 1)
    te    = round(comb  - tot,  1)

    print(f"\n{'═' * 75}")
    print(f" {TN[aw]} ({aw}) @ {TN[hm]} ({hm})")
    print(f" DraftKings: Spread {spr:+.1f} | Total o{tot}")
    print(f" TC Combined={comb} | Market={tot} | Edge={te:+.1f} → {lean}")
    print(f" Market Implied: {aw}={awmi} | {hm}={hmmi}")
    print(f" Team Market Edges: {aw} {tae:+.1f} | {hm} {hme:+.1f}")
    print(f"{'═' * 75}")

    for ab, lbl in [(aw, 'AWAY'), (hm, 'HOME')]:
        print(f"\n  {lbl} STARTERS:")
        print(f"  {'Player':<22} {'POS':>4} {'HT':>6} {'TC':>6} {'LINE':>6} {'EDGE':>6} {'TPM':>5} {'STS':>8}")
        print(f"  {'─' * 70}")
        for p in sorted(STARTERS[ab], key=lambda x: -tcp(x)):
            tc = tcp(p); ln = lnp(p); e = round(tc - ln, 1); tp = tpmp(p)
            print(f"  {p.name:<22} {p.pos:>4} {p.ht:>6} {tc:>6.1f} {ln:>6.1f} {e:>+6.1f} {tp:>5.1f} {p.status:>8}")
        rot = [p for p in sorted(BENCH[ab], key=lambda x: -tcp(x))[:5] if tcp(p) > 0]
        if rot:
            print(f"\n  ROTATION BENCH:")
            for p in rot:
                print(f"  {p.name:<22} {p.pos:>4} TC:{tcp(p):>5.1f} TPM:{tpmp(p):>4.1f}")

    S.append({
        'away': aw, 'home': hm, 'total': tot, 'spread': spr,
        'away_tc': awtc, 'home_tc': hmtc,
        'combined': comb, 'total_edge': te, 'lean': lean,
        'away_mi': awmi, 'home_mi': hmmi,
        'away_edge': tae, 'home_edge': hme
    })

# ── TC System Summary Table ────────────────────────────────────────────────────
print(f"\n{'=' * 75}")
print(" TC SYSTEM SUMMARY TABLE — MAY 22, 2026")
print(f"{'=' * 75}")
print(f" {'Game':<18} {'TC':>8} {'Mkt':>8} {'Edge':>8}  {'Lean':<10} {'AwayTC':>8} {'AwayMkt':>8} {'AwayEdge':>9}")
print(f" {'─' * 18} {'─' * 8} {'─' * 8} {'─' * 8}  {'─' * 10} {'─' * 8} {'─' * 8} {'─' * 9}")
for g in S:
    print(f" {g['home']} {g['away']:<12} {g['combined']:>8.1f} {g['total']:>8.1f} {g['total_edge']:>+8.1f}  {g['lean']:<10} {g['away_tc']:>8.1f} {g['away_mi']:>8.1f} {g['away_edge']:>+9.1f}")

print(f"\n{'=' * 75}")
print(" TC FORMULA: TC=PPG×0.85  |  LINE=PPG×0.88  |  EDGE=TC−LINE")
print(" MARKET IMPLIES: (Total±Spread)/2×1.008 (home court adj)")
print(" STATUS: ACTIVE=×0.85  |  Q=×0.55  |  OUT→0  |  RPM×0.85")
print(f"{'=' * 75}")

with open('/home/workspace/wnba_tc_may22_projections.json', 'w') as f:
    json.dump(S, f, indent=2)

# ── Validation ────────────────────────────────────────────────────────────────
print("\n[DAL STARTERS VALIDATION]")
for p in sorted(STARTERS['DAL'], key=lambda x: -x.ppg):
    print(f"  {p.name:<22} PPG={p.ppg:5.1f}  TC={tcp(p):5.1f}")

print("\n[IND STARTERS VALIDATION]")
for p in sorted(STARTERS['IND'], key=lambda x: -x.ppg):
    print(f"  {p.name:<22} PPG={p.ppg:5.1f}  TC={tcp(p):5.1f}")

print(f"\n✅ Teams parsed: {sorted(STARTERS.keys())}")
print(f"✅ File saved: wnba_tc_may22_projections.json")