"""
NBA Triple Conservative Template v10.0
=======================================
Generalized NBA TC generator — works for any matchup.
T = floor(0.76 × max(L,M))  when |L| < 8
T = floor(0.82 × max(L,M)) when |L| ≥ 8
Edge = L − T  (positive = unders the line = value)
Filters: edge ≥ +3 AND hit_rate ≥ 70%
"""

from dataclasses import dataclass, field
from typing import Literal, Optional
import math

# ─── TC FORMULA ────────────────────────────────────────────────────────────────
def tc_val(L: float, M: float) -> int:
    base = max(L, M)
    mult = 0.82 if abs(L) >= 8 else 0.76
    return int(mult * base)

# ─── DATACLASS ────────────────────────────────────────────────────────────────
@dataclass
class Player:
    team:       str
    name:       str
    pos:        str
    L:          float
    M:          float
    status:     Literal["ACTIVE", "Q", "OUT"] = "ACTIVE"
    actuals:    list[float] = field(default_factory=list)

    def __post_init__(self):
        self._t_raw = tc_val(self.L, self.M)

    @property
    def T(self) -> int:
        if self.status == "OUT":   return 0
        if self.status == "Q":     return int(self._t_raw * 0.55)
        return self._t_raw

    @property
    def edge(self) -> float:
        return self.L - self.T

    @property
    def hit_rate(self) -> float:
        if not self.actuals:
            return 0.65
        hits = sum(1 for a in self.actuals if a >= self.T)
        return hits / len(self.actuals)

    @property
    def valid(self) -> bool:
        return self.edge >= 3.0 and self.hit_rate >= 0.70

    @property
    def dec_odds(self) -> float:
        return self.L / self.T if self.T > 0 else 1.0

    def __str__(self) -> str:
        v = "✅" if self.valid else "⚠️ "
        hr = f"{self.hit_rate:.0%}"
        return (f"{v} {self.name:30s} {self.team:3s} | "
                f"T={self.T:2d} L={self.L:5.1f} E={self.edge:+5.1f} HR={hr} | "
                f"Status={self.status}")


@dataclass
class Game:
    home_team:  str
    away_team:  str
    date:       str
    site:       str = ""          # e.g. "Phoenix, AZ"
    home_line:   Optional[float] = None   # spread for home team (negative = favored)
    total_line: Optional[int] = None      # total points line
    home_notes: str = ""

    def __post_init__(self):
        self.site = self.site or self.home_team

    @property
    def matchup_label(self) -> str:
        return f"{self.away_team} @ {self.home_team}"


# ─── BUILD REPORT ──────────────────────────────────────────────────────────────
def build_report(g: Game, roster: list[Player], top_n: int = 8) -> str:
    lines = [
        f"# NBA TC Report — {g.matchup_label}",
        f"**Date:** {g.date} | **Site:** {g.site}",
        f"**TC Formula:** T = floor(0.76 × max(L,M)) when |L|<8 | T = floor(0.82 × max(L,M)) when |L|≥8",
        "",
        "---",
        "",
        "## Rules",
        "1. T-targets are WHOLE NUMBERS",
        "2. Edge = L − T  (positive = TC unders line = value)",
        "3. Valid pick: edge ≥ +3 AND hit_rate ≥ 70%",
        "4. If edge < +3 or HR < 70% → ⚠️ (not a top play)",
        "",
        "---",
        "",
    ]

    by_team = {}
    for p in roster:
        by_team.setdefault(p.team, []).append(p)

    for team, players in by_team.items():
        lines.append(f"## {team} Roster")
        lines.append(f"{'Player':32s} {'Pos':3s} {'T':>2s} {'L':>5s} {'Edge':>5s} {'HR':>4s} {'Odds':>6s} {'Status':6s}  {'Valid?'}")
        lines.append("-" * 95)
        for p in players:
            odds_str = f"+{p.dec_odds-1:.3f}" if hasattr(p, "dec_odds") else "—"
            valid_str = "✅" if p.valid else "⚠️"
            lines.append(f"{p.name:32s} {p.pos:3s} {p.T:2d} {p.L:5.1f} {p.edge:+5.1f} {p.hit_rate:.0%} {odds_str:>6s} {p.status:6s}  {valid_str}")
        lines.append("")

    # Top valid props
    valid_players = sorted([p for p in roster if p.valid],
                           key=lambda x: x.edge, reverse=True)[:top_n]

    if valid_players:
        lines.append("## Top Valid Props")
        lines.append(f"{'#':2s} {'Player':28s} {'Team':3s} {'T':>2s} {'L':>5s} {'Edge':>5s} {'HR':>4s}")
        lines.append("-" * 60)
        for i, p in enumerate(valid_players, 1):
            lines.append(f" {i:1d}. {p.name:28s} {p.team:3s} {p.T:2d} {p.L:5.1f} {p.edge:+5.1f} {p.hit_rate:.0%}")

        # Build parlay
        odds_product = math.prod(p.dec_odds for p in valid_players)
        gross = odds_product * 10
        lines.append("")
        lines.append(f"**Top Parlay ({len(valid_players)}-leg) | $10 → ${gross:.2f}**")
        for i, p in enumerate(valid_players, 1):
            pick_type = "OVER" if p.edge < 0 else "UNDER"
            lines.append(f"  Leg {i}: {p.name} ({p.team}) {pick_type} {p.L:.1f} → T={p.T}")
        lines.append(f"  Combined odds: +{odds_product-1:.3f}")
    else:
        lines.append("## Top Valid Props")
        lines.append("⚠️ No props cleared the +3 edge / 70% HR filter in this update.")

    # Game leans
    if g.home_line is not None or g.total_line is not None:
        lines.append("")
        lines.append("## Game Leans")
        if g.home_line is not None:
            fav = g.home_team if g.home_line < 0 else g.away_team
            dog = g.away_team if g.home_line < 0 else g.home_team
            lines.append(f"- **Spread:** {fav} {g.home_line:.1f} | {dog} +{abs(g.home_line):.1f}")
        if g.total_line is not None:
            lines.append(f"- **Total:** {g.total_line} (Over / Under)")
        if g.home_notes:
            lines.append(f"- **Notes:** {g.home_notes}")

    return "\n".join(lines)


if __name__ == "__main__":
    # ─── EXAMPLE: OKC @ PHX ──────────────────────────────────────────────────
    game = Game(
        home_team="PHX",
        away_team="OKC",
        date="April 25, 2026",
        site="Phoenix, AZ",
        home_line=-4.5,
        total_line=214,
        home_notes="Game 3 — OKC leads 2-0. Booker motivated (37 pts Game 2). JWill questionable."
    )

    roster = [

        # OKC
        Player("OKC","Shai Gilgeous-Alexander","PG",30.0,32.5, "ACTIVE", [37,37,42,31]),
        Player("OKC","Chet Holmgren","C",17.0,18.5, "ACTIVE", [18,16,14,19]),
        Player("OKC","Jalen Williams","SF",19.0,20.5, "Q",    [22,21,20,18]),
        Player("OKC","Luguentz Dort","SG",11.0,12.3, "ACTIVE", [12,11,13,10]),
        Player("OKC","Isaiah Joe","SG",9.0,10.2,  "ACTIVE", [9,10,8,11]),
        Player("OKC","Ajay Mitchell","PG",8.0,9.1, "ACTIVE", [8,9,7,8]),
        Player("OKC","Isaiah Hartenstein","C",7.0,8.0,"Q",    [6,7,5,8]),
        Player("OKC","Jaylin Williams","PF",5.0,6.0,"ACTIVE", [5,5,6,4]),
        Player("OKC","Kenyan Williams","PF",4.0,4.8,"ACTIVE", [4,3,4,5]),
        Player("OKC","Oso Ighodaro","PF",4.0,4.6, "ACTIVE", [4,3,4,5]),

        # PHX
        Player("PHX","Devin Booker","SG",24.0,26.0, "ACTIVE", [24,21,22,37]),
        Player("PHX","Kevin Durant","SF",22.0,24.5, "ACTIVE", [23,22,24,20]),
        Player("PHX","Dillon Brooks","SF",14.0,16.0, "ACTIVE", [30,14,16,15]),
        Player("PHX","Jalen Green","SG",15.0,17.5, "ACTIVE", [16,15,17,14]),
        Player("PHX","Bradley Beal","SG",12.0,14.0, "ACTIVE", [11,13,10,12]),
        Player("PHX","Oso Ighodaro","PF",7.0,8.0,  "ACTIVE", [7,6,7,8]),
        Player("PHX","Tyus Jones","PG",8.0,9.5,   "ACTIVE", [8,7,9,8]),
        Player("PHX","Grayson Allen","SG",7.0,8.2, "ACTIVE", [7,8,6,7]),
        Player("PHX","Mark Williams","C",10.0,12.0,"OUT",   []),
        Player("PHX","Jordan Goodwin","PG",6.0,7.0, "ACTIVE", [6,5,7,6]),
    ]

    report = build_report(game, roster)
    print(report)

    out_path = f"/home/workspace/NBA_TC_OKC_vs_PHX.md"
    with open(out_path, "w") as f:
        f.write(report)
    print(f"\n✅ Saved: {out_path}")
