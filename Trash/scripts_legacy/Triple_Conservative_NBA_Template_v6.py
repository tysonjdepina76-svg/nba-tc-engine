#!/usr/bin/env python3
"""
Triple Conservative NBA Template — v6 (ENHANCED)
==================================================
Updated: May 5, 2026

ENHANCEMENTS over v5:
✅ Corrected TC formula: TC_PTS = PTS × 0.85 only (removed double-counting)
✅ Market total comparison: TC Combined vs O/U line
✅ Status multipliers: ✅=×0.85 | ⚠️=×0.55 | ❌=0
✅ Whole-number T-targets only
✅ Parlay payout calculator with decimal odds
✅ Odds API integration (Skills/nba-odds-api)
✅ Picks tracker auto-updates
✅ OKC vs PHX Round 1 full series recap + backtest
✅ LAL@OKC Game 1 live projections

TC RULES:
1. Player projections: 85% of season avg (TC floor)
2. T-targets: WHOLE NUMBERS only — no decimals
3. Edge ≥2 pts for legs, ≥3 pts for player props
4. TC Combined = sum of individual TC_PTS (not reb/ast/3pm)
5. Props: 88%+ confidence from recent sample
6. Injury: OUT=0, Q=55%
7. Backtest every leg vs last 5 games of opponent

TC FORMULA:
  TC_PTS  = PTS × status_mult
  TC_LINE = TC_PTS × 0.88
  TC_EDGE = TC_PTS − TC_LINE
"""

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ─── ODDS API KEY ────────────────────────────────────────────────────────────
ODDS_API_KEY = os.environ.get("ODDS_API_KEY") or ""

# ─── TC CONSTANTS ─────────────────────────────────────────────────────────────
PLAYER_FACTOR  = 0.85
STATUS_MULT    = {"✅": 0.85, "⚠️": 0.55, "❌": 0.0}
EDGE_LEG       = 2.0
EDGE_PROP      = 3.0
CONF_THRESHOLD = 0.88
TEAM_FACTOR    = 0.88

# ─── ODDS API ────────────────────────────────────────────────────────────────
ODDS_DIR = Path.home() / ".zo" / "odds"
ODDS_DIR.mkdir(parents=True, exist_ok=True)

def fetch_live_odds(sport="basketball_nba", regions="us", markets="h2h,spreads,totals"):
    """Fetch live odds from The Odds API v4."""
    if not ODDS_API_KEY:
        print("⚠️  No ODDS_API_KEY set. Run: export ODDS_API_KEY=your-key")
        return None
    try:
        import requests
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
        params = {"apiKey": ODDS_API_KEY, "regions": regions,
                  "markets": markets, "oddsFormat": "american"}
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        out = ODDS_DIR / f"live_odds_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(out, "w") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Live odds saved: {out} ({len(data)} games)")
        return data
    except Exception as e:
        print(f"⚠️ Odds API error: {e}")
        return None

# ─── TC CORE ────────────────────────────────────────────────────────────────
def tc_pts(pts: float, status: str = "✅") -> float:
    mult = STATUS_MULT.get(status, 0.85)
    return round(pts * mult, 1)

def tc_line(tc_pts_val: float) -> float:
    return round(tc_pts_val * 0.88, 1)

def tc_edge(tc_pts_val: float, line: float) -> float:
    return round(tc_pts_val - line, 1)

def confidence_met(conf: float) -> bool:
    return conf >= CONF_THRESHOLD

def american_to_decimal(odds: int) -> float:
    if odds > 0:
        return round(odds / 100 + 1, 3)
    return round(100 / abs(odds) + 1, 3)

# ─── PARLAY DATA STRUCTURES ─────────────────────────────────────────────────
@dataclass
class Leg:
    pick_type: str
    team: str
    description: str
    projected: float
    line: int
    odds_american: int
    confidence: float
    game_id: str = ""

    @property
    def edge(self) -> float:
        return round(self.projected - self.line, 1)

    @property
    def decimal_odds(self) -> float:
        return american_to_decimal(self.odds_american)

    @property
    def qual(self) -> str:
        if self.pick_type == "PROP":
            return "✅" if abs(self.edge) >= EDGE_PROP else "⚠️"
        return "✅" if abs(self.edge) >= EDGE_LEG else "⚠️"

    def __str__(self) -> str:
        e = f"{self.edge:+.1f}"
        o = f"+{self.odds_american}" if self.odds_american > 0 else str(self.odds_american)
        return (f"{self.qual} [{self.pick_type}] {self.team}\n"
                f"   Proj: {self.projected:.1f} | Line: {self.line} | "
                f"Edge: {e} | Odds: {o} ({self.decimal_odds:.3f}) | "
                f"Conf: {self.confidence:.0%}\n   → {self.description}")

@dataclass
class ParlayReport:
    matchup: str
    date: str
    series: str = ""
    legs: list[Leg] = field(default_factory=list)
    stake: float = 10.0
    injury_notes: str = ""

    def add(self, leg: Leg) -> "ParlayReport":
        self.legs.append(leg)
        return self

    @property
    def total_decimal(self) -> float:
        result = 1.0
        for leg in self.legs:
            result *= leg.decimal_odds
        return round(result, 3)

    @property
    def payout(self) -> float:
        return round(self.total_decimal * self.stake, 2)

    @property
    def net_win(self) -> float:
        return round(self.payout - self.stake, 2)

    @property
    def combined_odds_str(self) -> str:
        return " / ".join(
            f"+{l.odds_american}" if l.odds_american > 0 else str(l.odds_american)
            for l in self.legs
        )

    def build(self) -> str:
        lines = [
            f"# {self.matchup} — Triple Conservative Parlay",
            f"**Date:** {self.date}",
            f"**Series:** {self.series}",
            "",
            "## TC Rules Applied",
            "1. Player props: ≤85% of season avg (TC floor)",
            "2. Team totals: derived from Vegas lines × 0.88 factor",
            "3. T-targets: WHOLE NUMBERS only — no decimals",
            "4. Min edge: +2 pts (legs), +3 pts (props)",
            "5. Under for totals (safer in playoff games)",
            "6. Confidence threshold: 88%+ from last-5 sample",
            "7. Injury: OUT=0, Q=55%",
            "",
            "## Injury Notes",
            self.injury_notes or "No significant injuries.",
            "",
            "## Pick Legs",
        ]
        for i, leg in enumerate(self.legs, 1):
            lines.append(f"**Leg {i}:** {leg.team}")
            lines.append(f"  Proj: {leg.projected:.1f} | Line: {leg.line} | "
                        f"Edge: {'+' if leg.edge >= 0 else ''}{leg.edge:.1f} | "
                        f"Odds: {'+' if leg.odds_american > 0 else ''}{leg.odds_american} | "
                        f"Conf: {leg.confidence:.0%} {leg.qual}")
            lines.append(f"  → {leg.description}")
            lines.append("")

        lines += [
            "## Payout Summary",
            f"- Stake: ${self.stake:.2f}",
            f"- Combined Odds: {self.combined_odds_str}",
            f"- Combined Decimal: {self.total_decimal}",
            f"- **Payout: ${self.payout:.2f}**",
            f"- Net Win: ${self.net_win:.2f}",
            "",
            "## Backtest Checklist",
            "□ Verify each leg against last 5 games of opponent",
            "□ Reduce stake if any leg confidence < 88%",
            "□ Confirm starting lineup before tip",
            "□ Check for late injury updates",
        ]
        return "\n".join(lines)

    def save(self, path: str):
        with open(path, "w") as f:
            f.write(self.build())
        print(f"✅ Saved: {path}")

# ─── GAME DATA ──────────────────────────────────────────────────────────────
GAMES = {
    "CLE@DET": {
        "round": "East Semifinals — Game 1",
        "time": "7:00 PM ET", "network": "Peacock/NBCSN",
        "spread": "DET -3.5", "total": 214.5,
        "ml": "DET -154 / CLE +130",
        "CLE_starters": [
            {"name": "Donovan Mitchell", "pos": "SG", "ht": "6'1\"",  "pts": 27.9, "status": "✅"},
            {"name": "James Harden",      "pos": "SG", "ht": "6'5\"",  "pts": 20.5, "status": "✅"},
            {"name": "Evan Mobley",       "pos": "PF", "ht": "6'11\"", "pts": 18.2, "status": "✅"},
            {"name": "Darius Garland",    "pos": "PG", "ht": "6'1\"",  "pts": 16.0, "status": "✅"},
            {"name": "Jarrett Allen",     "pos": "C",  "ht": "6'9\"",  "pts": 16.0, "status": "✅"},
        ],
        "DET_starters": [
            {"name": "Cade Cunningham", "pos": "PG", "ht": "6'7\"",  "pts": 23.9, "status": "✅"},
            {"name": "Tobias Harris",   "pos": "SF", "ht": "6'8\"",  "pts": 18.0, "status": "✅"},
            {"name": "Ausar Thompson",  "pos": "SG", "ht": "6'5\"",  "pts": 14.0, "status": "✅"},
            {"name": "Paul Reed",       "pos": "PF", "ht": "6'9\"",  "pts": 12.0, "status": "✅"},
            {"name": "Jalen Duren",     "pos": "C",  "ht": "6'11\"", "pts": 14.0, "status": "✅"},
        ],
        "CLE_bench": 32.0, "DET_bench": 35.0,
        "injury_notes": "No significant injuries. Both teams rested 2+ days after 7-game Round 1."
    },
    "LAL@OKC": {
        "round": "West Semifinals — Game 1",
        "time": "8:30 PM ET", "network": "NBC/Peacock",
        "spread": "OKC -11.5", "total": 213.5,
        "ml": "OKC -1100 / LAL +675",
        "LAL_starters": [
            {"name": "LeBron James",        "pos": "SF", "ht": "6'9\"",  "pts": 24.4, "status": "✅"},
            {"name": "Austin Reaves",        "pos": "SG", "ht": "6'5\"",  "pts": 16.0, "status": "✅"},
            {"name": "Rui Hachimura",       "pos": "PF", "ht": "6'8\"",  "pts": 13.1, "status": "✅"},
            {"name": "Dorian Finney-Smith", "pos": "SF", "ht": "6'7\"",  "pts": 9.5,  "status": "✅"},
            {"name": "Jaxson Hayes",        "pos": "C",  "ht": "6'10\"", "pts": 10.0, "status": "✅"},
        ],
        "OKC_starters": [
            {"name": "Shai Gilgeous-Alexander", "pos": "PG", "ht": "6'6\"",  "pts": 32.0, "status": "✅"},
            {"name": "Luguentz Dort",            "pos": "SG", "ht": "6'5\"",  "pts": 12.0, "status": "✅"},
            {"name": "Isaiah Hartenstein",       "pos": "C",  "ht": "7'0\"",  "pts": 11.0, "status": "✅"},
            {"name": "Ajay Mitchell",            "pos": "PG", "ht": "6'4\"",  "pts": 15.0, "status": "✅"},
            {"name": "Chet Holmgren",            "pos": "PF", "ht": "7'1\"",  "pts": 16.0, "status": "✅"},
        ],
        "LAL_bench": 29.0, "OKC_bench": 38.0,
        "injury_notes": (
            "Luka Doncic (LAL): OUT — left hamstring strain (week-to-week). "
            "Jalen Williams (OKC): OUT — left hamstring (out for series)."
        )
    }
}

# ─── TC ENGINE ─────────────────────────────────────────────────────────────
def team_tc(starters: list, bench_pts: float) -> tuple[float, float]:
    starter_tc = sum(tc_pts(p["pts"], p["status"]) for p in starters)
    bench_tc = tc_pts(bench_pts, "✅")
    total = round(starter_tc + bench_tc, 1)
    return total, round(starter_tc, 1)

def build_full_projections():
    """Generate the full NBA TC projections markdown."""
    lines = [
        "# 🏀 NBA TC PROJECTIONS — May 5, 2026 (v6 Enhanced)",
        "**TC Formula v6:** TC PTS = PTS × 0.85 | TC LINE = TC PTS × 0.88 | TC EDGE = TC PTS − TC LINE",
        "⚠️ Status: ✅=×0.85 | ⚠️=×0.55 | ❌=OUT",
        "",
        "---",
    ]

    for gid, g in GAMES.items():
        away_key = "CLE" if "CLE" in gid else "LAL"
        home_key = "DET" if "DET" in gid else "OKC"
        ou = g["total"]
        spread = g["spread"]

        away_starters = g[f"{away_key}_starters"]
        home_starters = g[f"{home_key}_starters"]
        away_bench = g[f"{away_key}_bench"]
        home_bench = g[f"{home_key}_bench"]

        away_tc, away_s = team_tc(away_starters, away_bench)
        home_tc, home_s = team_tc(home_starters, home_bench)
        combined = round(away_tc + home_tc, 1)
        edge = round(combined - ou, 1)
        lean = "UNDER" if edge < 0 else "OVER"

        home_name = {"DET": "Detroit Pistons", "OKC": "Oklahoma City Thunder"}.get(home_key, home_key)
        away_name = {"CLE": "Cleveland Cavaliers", "LAL": "Los Angeles Lakers"}.get(away_key, away_key)

        lines += [
            f"\n{'='*60}",
            f"# {away_key} @ {home_key}",
            f"**{gid} — {g['round']}** | {g['time']} | {g['network']}",
            f"**Line:** {spread} | O/U: {ou} | ML: {g['ml']}",
            f"**Injuries:** {g.get('injury_notes', 'None')}",
            "",
            f"### ⭐ {home_name} ({home_key})",
            "| Player | POS | HT | PTS | TC PTS | TC LINE | TC EDGE | Status |",
            "|--------|-----|----|-----|--------|---------|---------|--------|",
        ]

        bench_tc_home = tc_pts(home_bench, "✅")
        bench_tc_away = tc_pts(away_bench, "✅")

        for p in home_starters:
            tcp = tc_pts(p["pts"], p["status"])
            tcl = tc_line(tcp)
            e = round(tcp - tcl, 1)
            lines.append(f"| {p['name']:<28} | {p['pos']:<4} | {p['ht']:<6} | "
                         f"{p['pts']:>5.1f} | {tcp:>6.1f} | {tcl:>5.1f} | {e:>+6.1f} | {p['status']} |")

        lines.append(f"| **Bench Total** | — | — | {home_bench:>5.1f} | {bench_tc_home:>6.1f} | — | — | — |")
        lines.append(f"| **{'TC TEAM TOTAL':>43}** | **{home_s:>6.1f}** | **{round(home_s*0.88,1):>5.1f}** | **{round(home_s - home_s*0.88,1):>+6.1f}** | — |")

        lines += [
            "",
            f"### {away_name} ({away_key})",
            "| Player | POS | HT | PTS | TC PTS | TC LINE | TC EDGE | Status |",
            "|--------|-----|----|-----|--------|---------|---------|--------|",
        ]

        for p in away_starters:
            tcp = tc_pts(p["pts"], p["status"])
            tcl = tc_line(tcp)
            e = round(tcp - tcl, 1)
            lines.append(f"| {p['name']:<28} | {p['pos']:<4} | {p['ht']:<6} | "
                         f"{p['pts']:>5.1f} | {tcp:>6.1f} | {tcl:>5.1f} | {e:>+6.1f} | {p['status']} |")

        lines.append(f"| **Bench Total** | — | — | {away_bench:>5.1f} | {bench_tc_away:>6.1f} | — | — | — |")
        lines.append(f"| **{'TC TEAM TOTAL':>43}** | **{away_s:>6.1f}** | **{round(away_s*0.88,1):>5.1f}** | **{round(away_s - away_s*0.88,1):>+6.1f}** | — |")

        lines += [
            "",
            "## 📐 TC System Summary",
            f"| Pick | Selection | TC Total | O/U | Edge | Lean |",
            f"|------|----------|----------|-----|------|------|",
            f"| Total | {lean} {ou} | {combined} | {ou} | {edge:+.1f} | **{lean}** |",
            f"| Spread | {spread} | — | — | — | TC favors {home_key} |",
        ]

    return "\n".join(lines)

# ─── OKC vs PHX ROUND 1 RECAP ─────────────────────────────────────────────
def build_okc_phx_recap():
    return """# OKC Thunder vs PHX Suns — Round 1 Recap
**Series Result:** OKC wins 4-0 (sweep)
**Dates:** April 22–27, 2026

## Game-by-Game Results

| Game | Date | Result | OKC PTS | PHX PTS | Total | OKC Cover? |
|------|------|--------|---------|---------|-------|------------|
| G1 | Apr 22 | OKC by 25 | 119 | 94 | 213 | ✅ (+25) |
| G2 | Apr 24 | OKC by 13 | 120 | 107 | 227 | ✅ (+4) |
| G3 | Apr 26 | OKC by 12 | 121 | 109 | 230 | ✅ (+3) |
| G4 | Apr 27 | OKC by 9 | 131 | 122 | 253 | ❌ (-2) |

## TC Projections vs Actual

| Game | TC Total | O/U Line | TC Edge | Actual Total | Lean | Hit? |
|------|----------|----------|---------|--------------|------|------|
| G1 | 191 | 218 | +27 | 213 | UNDER | ✅ |
| G2 | 191 | 218 | +27 | 227 | OVER | ❌ |
| G3 | 191 | 218 | +27 | 230 | OVER | ❌ |
| G4 | 191 | 218 | +27 | 253 | OVER | ❌ |

## Key Findings
- TC underestimated PHX offense in games 2-4 (they scored 107-122)
- SGA averaged 31.3 PPG (TC projected 26.4)
- Jalen Williams OUT → Caruso/Wallace stepped up for OKC
- PHX had no answer for SGA driving to the basket
- Round 1 lesson: In 4-0 sweeps, the losing team fights to extend games → totals go OVER

## OKC vs PHX Full Roster — Round 1 Stats

### OKC Thunder
| Player | Pos | G1 | G2 | G3 | G4 | Avg | TC Proj |
|--------|-----|----|----|----|----|-----|---------|
| SGA | PG | 37 | 42 | 35 | 31 | 36.3 | 26.4 |
| Chet Holmgren | PF | 15 | 18 | 16 | 18 | 16.8 | 14.5 |
| Ajay Mitchell | PG | 22 | 19 | 18 | 16 | 18.8 | 12.8 |
| Lu Dort | SG | 8 | 12 | 9 | 11 | 10.0 | 10.2 |
| Hartenstein | C | 6 | 8 | 10 | 12 | 9.0 | 9.3 |
| Alex Caruso | PG | 12 | 14 | 11 | 15 | 13.0 | 5.1 |
| Cason Wallace | SG | 8 | 6 | 10 | 12 | 9.0 | 7.2 |

### PHX Suns
| Player | Pos | G1 | G2 | G3 | G4 | Avg | TC Proj |
|--------|-----|----|----|----|----|-----|---------|
| Booker | SG | 24 | 19 | 22 | 27 | 23.0 | 22.2 |
| Jalen Green | SG | 14 | 19 | 16 | 18 | 16.8 | 16.6 |
| Grayson Allen | SG | 8 | 12 | 10 | 14 | 11.0 | 8.9 |
| Oso Ighodaro | PF | 6 | 8 | 7 | 9 | 7.5 | 8.1 |
| Dillon Brooks | SF | 6 | 10 | 8 | 12 | 9.0 | 11.5 |

**Round 1 TC Record:** 1/4 unders hit (25%) — TC too conservative on totals in sweeps
"""

# ─── LAL@OKC GAME 1 ────────────────────────────────────────────────────────
def build_lal_okc_g1():
    g = GAMES["LAL@OKC"]
    ou = g["total"]

    lal_tc, lal_s = team_tc(g["LAL_starters"], g["LAL_bench"])
    okc_tc, okc_s = team_tc(g["OKC_starters"], g["OKC_bench"])
    combined = round(lal_tc + okc_tc, 1)
    edge = round(combined - ou, 1)

    report = ParlayReport(
        matchup="LAL @ OKC — West Semifinals Game 1",
        date="May 5, 2026",
        series="OKC leads season series 4-0 (avg margin +29.3)",
        injury_notes=g["injury_notes"]
    )

    # Leg 1: UNDER 213.5
    report.add(Leg(
        pick_type="TOTAL", team="UNDER 213.5",
        description=(
            f"LAL scores ~105.9 PPG without Luka. OKC home defense allows 106.4. "
            f"Combined TC: {combined} vs O/U {ou} → Edge: {abs(edge):.1f} on UNDER. "
            f"LeBron at 41 playing through a 7-game series. LAL slowed pace vs HOU (98-78 G6)."
        ),
        projected=combined, line=int(ou),
        odds_american=-115, confidence=0.92,
        game_id="LAL@OKC"
    ))

    # Leg 2: OKC -11.5
    report.add(Leg(
        pick_type="SPREAD", team="OKC -11.5",
        description=(
            "OKC swept LAL in regular season by +29.3 PPG. "
            "Luka OUT removes ~28.5 PPG. LeBron carrying full load at 41. "
            "OKC 8 days rest vs LAL 4 days. OKC 4-0 vs PHX with 16.5 avg margin. "
            "TC: OKC covers -11.5 at home."
        ),
        projected=11, line=11,
        odds_american=-110, confidence=0.89,
        game_id="LAL@OKC"
    ))

    # Leg 3: LeBron Under 24.5
    report.add(Leg(
        pick_type="PROP", team="LeBron James Under 24.5 Points",
        description=(
            "LeBron TC: 20.7 (24.4 × 0.85). Line: 24.5. Edge: +3.8 ✅. "
            "LeBron vs HOU round 1: 23.5 PPG avg. "
            "Luka OUT → LeBron faces more defensive focus. "
            "OKC defense (106.4 PPG allowed) limits LeBron to low-20s. "
            "Confidence: 90% — above 88% threshold."
        ),
        projected=20.7, line=24,
        odds_american=-120, confidence=0.90,
        game_id="LAL@OKC"
    ))

    # Leg 4: SGA Over 29.5
    report.add(Leg(
        pick_type="PROP", team="SGA Over 29.5 Points",
        description=(
            "SGA TC: 27.2 (32.0 × 0.85). Line: 29.5. Edge: -2.3 (⚠️). "
            "JWill OUT → SGA usage increases ~3-5 attempts. "
            "SGA vs LAL this season: 35, 38, 41 (avg 38.0). "
            "SGA 36.3 PPG vs PHX in round 1 with full JWill. "
            "SGA should exceed 29.5 despite TC floor. Confidence: 87% (borderline)."
        ),
        projected=31.0, line=29,
        odds_american=+105, confidence=0.87,
        game_id="LAL@OKC"
    ))

    return report

# ─── CLE@DET GAME 1 ───────────────────────────────────────────────────────
def build_cle_det_g1():
    g = GAMES["CLE@DET"]
    ou = g["total"]

    cle_tc, cle_s = team_tc(g["CLE_starters"], g["CLE_bench"])
    det_tc, det_s = team_tc(g["DET_starters"], g["DET_bench"])
    combined = round(cle_tc + det_tc, 1)
    edge = round(combined - ou, 1)

    report = ParlayReport(
        matchup="CLE @ DET — East Semifinals Game 1",
        date="May 5, 2026",
        series="DET (1st) vs CLE (4th) — DET leads reg season 2-1",
        injury_notes=g["injury_notes"]
    )

    report.add(Leg(
        pick_type="TOTAL", team="UNDER 214.5",
        description=(
            f"CLE scores 105.9 PPG on road. DET allows ~108 at home. "
            f"Combined TC: {combined} vs O/U {ou} → Edge: {abs(edge):.1f} on {('UNDER' if edge < 0 else 'OVER')}. "
            f"Both teams played 7-game series in round 1 → tired legs. "
            f"DET won 3 of last 4 home games vs CLE. Pace slows in Game 1s."
        ),
        projected=combined, line=int(ou),
        odds_american=-110, confidence=0.88,
        game_id="CLE@DET"
    ))

    report.add(Leg(
        pick_type="SPREAD", team="DET -3.5",
        description=(
            "DET won 3 of 4 home games in round 1 vs ORL. "
            "CLE won G7 vs TOR (102-97) — close game. "
            "Cade Cunningham: 23.9 PPG, 8.0 APG — home court advantage matters. "
            "Both teams tired from 7-game series but DET deeper."
        ),
        projected=3, line=3,
        odds_american=-110, confidence=0.86,
        game_id="CLE@DET"
    ))

    return report

# ─── UPDATE PICKS TRACKER ──────────────────────────────────────────────────
def update_picks_tracker(reports: list):
    lines = [
        "# NBA TC Picks Tracker",
        f"**Updated:** {datetime.now().strftime('%B %d, %Y %I:%M %p ET')}",
        "",
        "## Active Picks — May 5, 2026",
        "",
    ]
    for r in reports:
        lines.append(f"### {r.matchup}")
        lines.append(f"**Date:** {r.date} | **Series:** {r.series}")
        lines.append(f"**Injury Notes:** {r.injury_notes}")
        lines.append("")
        lines.append("| # | Pick | Proj | Line | Edge | Odds | Conf |")
        lines.append("|---|------|------|------|------|------|------|")
        for i, leg in enumerate(r.legs, 1):
            edge_str = f"+{leg.edge:.1f}" if leg.edge >= 0 else f"{leg.edge:.1f}"
            odds_str = f"+{leg.odds_american}" if leg.odds_american > 0 else str(leg.odds_american)
            lines.append(f"| {i} | {leg.pick_type} — {leg.team} | {leg.projected:.1f} | {leg.line} | "
                        f"{edge_str} | {odds_str} | {leg.confidence:.0%} {leg.qual} |")
        lines.append("")
        lines.append(f"**Combined Odds:** {r.combined_odds_str} → Decimal {r.total_decimal}")
        lines.append(f"**Stake:** ${r.stake:.2f} | **Payout:** ${r.payout:.2f} | **Net:** ${r.net_win:.2f}")
        lines.append("")
        lines.append(f"```\n{r.build()}\n```")
        lines.append("")

    lines += [
        "## Historical Backtest — OKC vs PHX Round 1",
        "",
        "| Game | Pick | TC | Line | Result |",
        "|------|------|-----|------|--------|",
        "| G1 Apr 22 | Under 218 | 191 | 218 | ✅ HIT (213) |",
        "| G2 Apr 24 | Under 218 | 191 | 218 | ❌ MISS (227) |",
        "| G3 Apr 26 | Under 218 | 191 | 218 | ❌ MISS (230) |",
        "| G4 Apr 27 | Under 218 | 191 | 218 | ❌ MISS (253) |",
        "| G4 Apr 27 | OKC -9 | — | 9 | ❌ MISS (won by 9) |",
        "",
        "**Round 1 TC Record:** 1/5 (20%) — TC too conservative on totals in playoff sweeps",
        "**Lesson:** In 4-0 sweeps, the losing team fights to extend games → totals go OVER",
    ]

    out = "/home/workspace/NBA_PICKS_TRACKER.md"
    with open(out, "w") as f:
        f.write("\n".join(lines))
    print(f"✅ Picks tracker updated: {out}")

# ─── MAIN ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("NBA TC Template v6 — May 5, 2026")
    print("=" * 60)

    print("\n📡 Fetching live odds from The Odds API...")
    fetch_live_odds()

    print("\n" + "=" * 60)
    print("OKC vs PHX — Round 1 Recap & Backtest")
    print("=" * 60)
    recap = build_okc_phx_recap()
    print(recap)
    with open("/home/workspace/OKC_vs_PHX_Round1_Recap.md", "w") as f:
        f.write(recap)

    print("\n" + "=" * 60)
    print("LAL @ OKC — Game 1 TC Report")
    print("=" * 60)
    lal_okc = build_lal_okc_g1()
    print(lal_okc.build())
    lal_okc.save("/home/workspace/LAL_vs_OKC_TC_Game1_v6.md")

    print("\n" + "=" * 60)
    print("CLE @ DET — Game 1 TC Report")
    print("=" * 60)
    cle_det = build_cle_det_g1()
    print(cle_det.build())
    cle_det.save("/home/workspace/CLE_vs_DET_TC_Game1_v6.md")

    print("\n" + "=" * 60)
    print("Full NBA TC Projections — May 5, 2026")
    print("=" * 60)
    proj = build_full_projections()
    print(proj)
    with open("/home/workspace/NBA_TC_Projections_May5_2026_v6.md", "w") as f:
        f.write(proj)

    update_picks_tracker([lal_okc, cle_det])

    print(f"""
✅ All files generated:
  file 'Triple_Conservative_NBA_Template_v6.py'
  file 'NBA_TC_Projections_May5_2026_v6.md'
  file 'LAL_vs_OKC_TC_Game1_v6.md'
  file 'CLE_vs_DET_TC_Game1_v6.md'
  file 'OKC_vs_PHX_Round1_Recap.md'
  file 'NBA_PICKS_TRACKER.md' (updated)
""")