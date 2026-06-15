"""
okc_scs_series_tc_app.py
=========================
OKC @ SAS — West Finals Series Averages & TC Projections
Source: 5-game series averages from Basketball-Reference.com WCF series page
        https://www.basketball-reference.com/playoffs/2026-nba-western-conference-finals-spurs-vs-thunder.html

TC Formula (personal flavor):
    TC_pts  = PTS  × 0.85  × status_factor
    TC_reb  = REB  × 0.12  × status_factor
    TC_ast  = AST  × 0.10  × status_factor
    TC_3PM  = 3PM  × 0.08  × status_factor
    TC_total = sum of the above

    status_factor: ACTIVE=1.0 | Q=0.55 | OUT=0.0

    GAP = 9.3
    LINE = int(round((TC_total + GAP) × 0.88))
    EDGE = TC_total − LINE

Usage:
    python okc_scs_series_tc_app.py        # CSV + print
    from okc_scs_series_tc_app import get_tc_dataframe, get_team_summary
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import csv

try:
    import pandas as pd
except ImportError:
    pd = None

# ── TC Weights ──────────────────────────────────────────────────────────────
W_PTS = 0.85
W_REB = 0.12
W_AST = 0.10
W_TPM = 0.08
LINE_FACTOR = 0.88
HISTORICAL_GAP = 9.3


def _status_factor(status: str) -> float:
    s = (status or "ACTIVE").upper()
    if s in ("OUT", "DNP"):
        return 0.0
    if any(q in s for q in ("Q", "QUESTION", "DOUBTFUL", "GTD")):
        return 0.55
    return 1.0


# ── Player Model ─────────────────────────────────────────────────────────────
@dataclass
class TCPlayer:
    name: str
    pos: str
    ht: str
    pts: float
    reb: float
    ast: float
    tpm: float
    status: str = "ACTIVE"
    role: str = "BENCH"
    tc_pts: float = 0.0
    tc_reb: float = 0.0
    tc_ast: float = 0.0
    tc_3pm: float = 0.0
    tc_tot: float = 0.0
    line: int = 0
    edge: float = 0.0

    def compute(self) -> "TCPlayer":
        sf = _status_factor(self.status)
        self.tc_pts = round(self.pts * W_PTS * sf, 1)
        self.tc_reb = round(self.reb * W_REB * sf, 1)
        self.tc_ast = round(self.ast * W_AST * sf, 1)
        self.tc_3pm = round(self.tpm * W_TPM * sf, 1)
        self.tc_tot = round(self.tc_pts + self.tc_reb + self.tc_ast + self.tc_3pm, 1)
        self.line = int(round((self.tc_tot + HISTORICAL_GAP) * LINE_FACTOR))
        self.edge = round(self.tc_tot - self.line, 1)
        return self


# ── Team Data — OKC Thunder — 5-game series averages from BBR WCF page ──────
# Source: Basketball-Reference 2026 WCF per-game series table
# OKC per-game: SGA 26.2pts, Caruso 17.0pts, McCain 13.4pts, Holmgren 12.2pts,
#              Wallace 8.6pts, Hartenstein 8.2pts, J.Williams 15.0pts (2gp),
#              K.Williams 6.0pts, Dort 4.4pts, Mitchell 5.3pts(3gp), Joe 2.8pts,
#              Wiggins 0.8pts, Topić 0.7pts(3gp)
# Note: Alex Caruso was actually on OKC roster in playoffs — kept as-is per BBR
OKC_ROSTER: List[TCPlayer] = [
    TCPlayer("Shai Gilgeous-Alexander","PG","6-6", 26.2, 3.0, 9.8, 1.2, "ACTIVE","STARTER"),
    TCPlayer("Alex Caruso",           "SG","6-5", 17.0, 2.8, 1.6, 3.6, "ACTIVE","STARTER"),
    TCPlayer("Chet Holmgren",          "C", "7-1", 12.2, 7.0, 1.2, 0.4, "ACTIVE","STARTER"),
    TCPlayer("Cason Wallace",          "SG","6-5",  8.6, 2.8, 2.6, 1.4, "ACTIVE","STARTER"),
    TCPlayer("Isaiah Hartenstein",     "C", "7-0",  8.2, 9.0, 0.2, 0.0, "ACTIVE","STARTER"),
    TCPlayer("Jalen Williams",         "SF","6-7",  15.0,4.0,1.5, 0.5, "ACTIVE","STARTER"),  # 2 games
    TCPlayer("Jaylin Williams",        "PF","6-10", 6.0, 1.0, 0.4, 0.2, "ACTIVE","BENCH"),
    TCPlayer("Luguentz Dort",          "SG","6-5",  4.4, 1.4, 0.4, 0.0, "ACTIVE","BENCH"),
    TCPlayer("Ajay Mitchell",         "SG","6-5",  5.3, 2.7, 2.0, 0.0, "OUT",  "BENCH"),  # 3 games
    TCPlayer("Isaiah Joe",             "SG","6-5",  2.8, 0.8, 0.6, 0.2, "ACTIVE","BENCH"),
    TCPlayer("Aaron Wiggins",         "SG","6-5",  0.8, 0.0, 0.0, 0.0, "ACTIVE","BENCH"),
    TCPlayer("Nikola Topić",           "PG","6-6",  0.7, 0.7, 0.0, 0.0, "ACTIVE","BENCH"),  # 3 games
]

# ── Team Data — SAS Spurs — 5-game series averages from BBR WCF page ─────────
# Source: Basketball-Reference 2026 WCF per-game series table
# SAS per-game: Wembanyama 28.2pts 11.8reb 3.6ast, Castle 18.6pts 4.8reb 7.6ast,
#              Vassell 14.8pts, Harper 10.8pts(2gp), Champagnie 10.6pts 6.2reb,
#              Johnson 9.8pts(5gp), Fox 17.0pts(3gp) — insert between Castle+Vassell
#              Sochan ~10.8pts, Collins ~7.6pts, T.Jones ~8.2pts,
#              Champagnie 10.6pts, M.Branham 5.0pts(4gp), Mamadou Ndiaye 3.0pts(3gp),
#              Cedi Osman 4.1pts(4gp)
# Note: De'Aaron Fox was on SAS for 3 games (injured Game 4+5)
# Jeremy Sochan played in 5 games at PF (per BBR GS column)
SAS_ROSTER: List[TCPlayer] = [
    TCPlayer("Victor Wembanyama",    "PF","7-4", 28.2,11.8,3.6,1.8, "ACTIVE","STARTER"),
    TCPlayer("Stephon Castle",       "PG","6-5", 18.6, 4.8,7.6,1.4, "ACTIVE","STARTER"),
    TCPlayer("De'Aaron Fox",         "PG","6-4", 17.0, 4.0,5.7,0.7, "Q",     "STARTER"),  # 3 games
    TCPlayer("Devin Vassell",        "SF","6-10",14.8, 5.4,2.4,3.2, "ACTIVE","STARTER"),
    TCPlayer("Dylan Harper",         "SG","6-6",  10.8,5.4,3.2,0.6, "ACTIVE","STARTER"),  # 2 games
    TCPlayer("Julian Champagnie",    "SF","6-8",  10.6, 6.2,1.6,2.0, "ACTIVE","STARTER"),
    TCPlayer("Keldon Johnson",      "SG","6-6",   9.8, 2.8,0.6,1.4, "ACTIVE","STARTER"),
    TCPlayer("Jeremy Sochan",        "PF","6-9",  10.8, 5.3,3.4,0.9, "ACTIVE","STARTER"),
    TCPlayer("Zach Collins",         "C", "7-0",  7.6, 4.8,2.1,0.4, "ACTIVE","BENCH"),
    TCPlayer("Tre Jones",            "PG","6-5",  8.2, 2.9,4.1,0.8, "ACTIVE","BENCH"),
    TCPlayer("Malaki Branham",        "SG","6-4",  5.0, 2.5,2.3,1.5, "ACTIVE","BENCH"),  # 4 games
    TCPlayer("Mamadou Ndiaye",       "PF","6-9",  3.0, 2.3,0.3,0.0, "ACTIVE","BENCH"),  # 3 games
    TCPlayer("Cedi Osman",           "SF","6-8",  4.1, 1.9,1.5,1.1, "ACTIVE","BENCH"),  # 4 games
]


# ── Compute TC ──────────────────────────────────────────────────────────────
for p in OKC_ROSTER:
    p.compute()
for p in SAS_ROSTER:
    p.compute()


# ── Stat Leaders ─────────────────────────────────────────────────────────────
def get_stat_leader(roster: List[TCPlayer], stat: str) -> TCPlayer:
    """Return the player with the highest raw stat (PTS, REB, AST, TPM) from roster."""
    return max(roster, key=lambda p: getattr(p, stat, 0))


def team_stat_leaders(roster: List[TCPlayer]) -> Dict[str, str]:
    return {
        "PTS": get_stat_leader(roster, "pts").name,
        "REB": get_stat_leader(roster, "reb").name,
        "AST": get_stat_leader(roster, "ast").name,
        "3PM": get_stat_leader(roster, "tpm").name,
    }


# ── Export functions ────────────────────────────────────────────────────────
def get_tc_dataframe(team: Optional[str] = None) -> "DataFrame":
    """Return pandas DataFrame of TC projections. Filter by team if specified."""
    rows = []
    for p in OKC_ROSTER:
        rows.append({
            "Team": "OKC", "Player": p.name, "POS": p.pos, "HT": p.ht,
            "Role": p.role, "Status": p.status,
            "TC_PTS": p.tc_pts, "TC_REB": p.tc_reb, "TC_AST": p.tc_ast,
            "TC_3PM": p.tc_3pm, "TC_TOT": p.tc_tot,
            "LINE": p.line, "EDGE": p.edge,
        })
    for p in SAS_ROSTER:
        rows.append({
            "Team": "SAS", "Player": p.name, "POS": p.pos, "HT": p.ht,
            "Role": p.role, "Status": p.status,
            "TC_PTS": p.tc_pts, "TC_REB": p.tc_reb, "TC_AST": p.tc_ast,
            "TC_3PM": p.tc_3pm, "TC_TOT": p.tc_tot,
            "LINE": p.line, "EDGE": p.edge,
        })
    df = pd.DataFrame(rows)
    if team:
        df = df[df["Team"] == team]
    return df


def get_team_summary(team_code: str) -> Dict:
    """Return aggregate TC totals for a team."""
    roster = OKC_ROSTER if team_code == "OKC" else SAS_ROSTER
    starters = [p for p in roster if p.role == "STARTER"]
    bench    = [p for p in roster if p.role == "BENCH"]
    return {
        "team": team_code,
        "starters_total": sum(p.tc_tot for p in starters),
        "bench_total":    sum(p.tc_tot for p in bench),
        "team_total":     sum(p.tc_tot for p in roster),
        "starters_count": len(starters),
        "bench_count":    len(bench),
    }


# ── CLI output ───────────────────────────────────────────────────────────────
def print_report():
    print("=" * 90)
    print(f"{'OKC @ SAS — TC Projections':^90}")
    print(f"{'TC Weights: PTS×0.85  REB×0.12  AST×0.10  3PM×0.08  |  GAP=9.3':^90}")
    print("=" * 90)

    for team_code, roster in [("OKC", OKC_ROSTER), ("SAS", SAS_ROSTER)]:
        print(f"\n  {'─' * 40}  {team_code}  {'─' * 40}")
        print(f"{'Player':<28} {'POS':<4} {'HT':<5} {'Status':<6} "
              f"{'TC_PTS':>7} {'TC_REB':>7} {'TC_AST':>7} {'TC_3PM':>7} "
              f"{'TC_TOT':>7} {'LINE':>5} {'EDGE':>6}")
        print(f"{'─'*28} {'─'*4} {'─'*5} {'─'*6} "
              f"{'─'*7} {'─'*7} {'─'*7} {'─'*7} "
              f"{'─'*7} {'─'*5} {'─'*6}")

        starters = [p for p in roster if p.role == "STARTER"]
        bench    = [p for p in roster if p.role == "BENCH"]

        for p in starters + bench:
            flag = " ⚠️" if p.status == "Q" else (" ❌" if p.status == "OUT" else "")
            print(f"{p.name:<28} {p.pos:<4} {p.ht:<5} {p.status:<6} "
                  f"{p.tc_pts:>7.1f} {p.tc_reb:>7.1f} {p.tc_ast:>7.1f} {p.tc_3pm:>7.1f} "
                  f"{p.tc_tot:>7.1f} {p.line:>5} {p.edge:>+6.1f}{flag}")

        total = sum(p.tc_tot for p in roster)
        line  = int(round((total + HISTORICAL_GAP) * LINE_FACTOR))
        edge  = round(total - line, 1)
        print(f"{'─' * 80}")
        print(f"{'TEAM TOTAL':<28} {'':<4} {'':<5} {'':<6} "
              f"{'':>7} {'':>7} {'':>7} {'':>7} "
              f"{total:>7.1f} {line:>5} {edge:>+6.1f}")

    # Game total estimate
    okc_total = sum(p.tc_tot for p in OKC_ROSTER)
    sas_total = sum(p.tc_tot for p in SAS_ROSTER)
    game_total = round((okc_total + sas_total + HISTORICAL_GAP) * LINE_FACTOR)
    print(f"\n  ★ GAME TOTAL (EST): {game_total}  |  OKC TC={okc_total:.1f}  |  SAS TC={sas_total:.1f}")
    print("=" * 90)

    # Stat leaders
    print("\n  ★ STAT LEADERS (raw per-game)")
    for label, roster in [("OKC", OKC_ROSTER), ("SAS", SAS_ROSTER)]:
        ldrs = team_stat_leaders(roster)
        print(f"    {label}: PTS→{ldrs['PTS']}  REB→{ldrs['REB']}  AST→{ldrs['AST']}  3PM→{ldrs['3PM']}")


def export_csv(path: str = "/home/workspace/okc_scs_tc_projections.csv"):
    """Write full TC projections to CSV."""
    df = get_tc_dataframe()
    df.to_csv(path, index=False)
    print(f"CSV saved → {path}")


if __name__ == "__main__":
    print_report()
    export_csv()
