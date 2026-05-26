"""
Triple Conservative NBA Template v9.0
=====================================
Individual player props — full 20-player roster scan.
For each player: compute T, edge, hit_rate, odds, valid flag.
Filter: edge ≥ +3 AND hit_rate ≥ 75% → VALID
Output: ranked report with all players + top parlay builder.
"""

from dataclasses import dataclass
from typing import Literal

# ─── TC FORMULA ────────────────────────────────────────────────────────────────
def tc_val(L: float, M: float) -> int:
    """Standard TC: floor(0.76 × max(L,M)) when |L| < 8, else 0.82 × max(L,M)."""
    base = max(L, M)
    mult = 0.82 if abs(L) >= 8 else 0.76
    return int(mult * base)

# ─── DATA ──────────────────────────────────────────────────────────────────────
@dataclass
class Player:
    team:       str
    name:       str
    pos:        str
    L:          float    # betting line (points)
    M:          float    # max/season avg
    status:     Literal["ACTIVE", "Q", "OUT"] = "ACTIVE"
    # Backtest actuals (4-game sample) for hit-rate calculation
    actuals:    list[float] = None   # e.g. [37, 37, 42, 31] for SGA

    def __post_init__(self):
        if self.actuals is None:
            self.actuals = []
        self._t_raw = tc_val(self.L, self.M)

    @property
    def T(self) -> int:
        if self.status == "OUT":
            return 0
        if self.status == "Q":
            return int(self._t_raw * 0.55)
        return self._t_raw

    @property
    def edge(self) -> float:
        """Positive = TC unders the line (value play)."""
        return self.L - self.T

    @property
    def hit_rate(self) -> float:
        if not self.actuals:
            return 0.65  # default when no backtest
        hits = sum(1 for a in self.actuals if a >= self.T)
        return hits / len(self.actuals)

    @property
    def valid(self) -> bool:
        return self.edge >= 3.0 and self.hit_rate >= 0.75

    @property
    def dec_odds(self) -> float:
        """American -150 → 1.667, -210 → 1.476, etc."""
        if self.L <= 0:
            return abs(self.L) / 100 + 1.0
        return self.L / 100 + 1.0

    def leg_str(self, label="PTS") -> str:
        pick = "Under" if self.T < self.L else "Over"
        return f"{self.name} {pick} {self.L:.0f} (T={self.T})"


# ─── ROSTERS ───────────────────────────────────────────────────────────────────
OKC_ROSTER = [
    # name, pos, L, M, status, actuals (4-game)
    Player("OKC", "Shai Gilgeous-Alexander", "PG",  33, 32.5, "ACTIVE", [37,37,42,31]),
    Player("OKC", "Chet Holmgren",            "C",   17, 18.5, "ACTIVE", [14,15,16,17]),
    Player("OKC", "Jalen Williams",           "SF",  20, 20.5, "Q",     [18,17,19,16]),
    Player("OKC", "Luguentz Dort",            "SG",  12, 12.3, "ACTIVE", [10,11,9,12]),
    Player("OKC", "Isaiah Joe",               "SG",   9, 10.2, "ACTIVE", [8,9,10,11]),
    Player("OKC", "Ajay Mitchell",           "PG",   8,  9.1, "ACTIVE", [7,8,9,6]),
    Player("OKC", "Isaiah Hartenstein",       "C",    8,  8.0, "Q",     [5,6,7,5]),
    Player("OKC", "Jaylin Williams",          "PF",   6,  6.0, "ACTIVE", [5,6,4,5]),
    Player("OKC", "Kenyan Williams",          "PF",   4,  4.8, "ACTIVE", [3,4,4,3]),
    Player("OKC", "Oso Ighodaro",             "PF",   4,  4.6, "ACTIVE", [4,3,5,4]),
]

PHX_ROSTER = [
    Player("PHX", "Devin Booker",             "SG",  27, 26.2, "ACTIVE", [24,21,22,37]),
    Player("PHX", "Kevin Durant",            "SF",  23, 24.5, "ACTIVE", [20,19,21,22]),
    Player("PHX", "Jalen Green",             "SG",  16, 17.5, "ACTIVE", [14,15,13,16]),
    Player("PHX", "Dillon Brooks",           "SF",  15, 16.0, "ACTIVE", [12,30,11,13]),
    Player("PHX", "Bradley Beal",            "SG",  13, 14.0, "ACTIVE", [11,10,12,9]),
    Player("PHX", "Tyus Jones",              "PG",   9,  9.5, "ACTIVE", [8,9,8,7]),
    Player("PHX", "Grayson Allen",           "SG",   8,  8.2, "ACTIVE", [7,8,6,7]),
    Player("PHX", "Mark Williams",           "C",   10, 12.0, "OUT",    []),
    Player("PHX", "Oso Ighodaro",            "PF",   5,  5.8, "ACTIVE", [4,5,4,3]),
    Player("PHX", "Jordan Goodwin",          "PG",   6,  7.0, "ACTIVE", [5,6,4,5]),
]

ALL_PLAYERS = OKC_ROSTER + PHX_ROSTER


# ─── REPORT BUILD ──────────────────────────────────────────────────────────────
def build_table(players: list[Player], title: str) -> list[str]:
    lines = [
        f"\n### {title}",
        f"| # | Player | Pos | L | M | T | Edge | Hit% | Valid | Odds |",
        f"|---|--------|-----|---|---|---|---|------|-------|-------|------|",
    ]
    for i, p in enumerate(players, 1):
        v = "✅" if p.valid else "⚠️ "
        actuals_str = str(p.actuals) if p.actuals else "n/a"
        lines.append(
            f"| {i} | **{p.name}** ({p.team}) | {p.pos} | "
            f"{p.L:.0f} | {p.M:.1f} | **{p.T}** | "
            f"{p.edge:+.1f} | {p.hit_rate:.0%} | {v} | "
            f"{p.L:.0f} {p.T} |"
        )
    return lines


def build_top_parlay(players: list[Player], label: str) -> list[str]:
    valid = [p for p in players if p.valid]
    # sort by edge descending
    valid.sort(key=lambda p: p.edge, reverse=True)
    top = valid[:6]  # max 6 legs

    dec_odds = 1.0
    for p in top:
        dec_odds *= p.dec_odds

    lines = [
        f"\n### 🏇 {label} — Top Valid Props",
        "",
    ]
    for i, p in enumerate(top, 1):
        pick = "UNDER" if p.T < p.L else "OVER"
        lines.append(
            f"**Leg {i}:** {p.name} ({p.team}) — {pick} {p.L:.0f} pts  "
            f"| T={p.T} | Edge={p.edge:+.1f} | HR={p.hit_rate:.0%}"
        )

    gross = dec_odds * 10
    lines += [
        "",
        f"**Parlay:** {len(top)}-leg | Odds: +{dec_odds-1:.3f} | $10 → ${gross:.2f} | "
        f"Net: +${gross-10:.2f}",
    ]
    return lines


def build_full_report():
    lines = [
        "# NBA TC — Individual Props Report v9.0",
        "## OKC vs PHX | April 25, 2026 — Game 3",
        "",
        "## TC Rules (v9.0)",
        "- **T** = floor(0.76 × max(L,M)) when |L| < 8; floor(0.82 × max(L,M)) when |L| ≥ 8",
        "- **Edge** = L − T  (positive = TC unders the line = value)",
        "- **Valid** = Edge ≥ +3 AND Hit% ≥ 75%",
        "- **Q-status** → T × 0.55 (50% haircut for questionable players)",
        "- **OUT** → T = 0, exclude from parlays",
        "",
        "## OKC Thunder Roster",
    ]
    lines += build_table(OKC_ROSTER, "OKC Players")

    lines += [
        "",
        "## PHX Suns Roster",
    ]
    lines += build_table(PHX_ROSTER, "PHX Players")

    # Top parlays
    lines += build_top_parlay(OKC_ROSTER, "OKC Top Props")
    lines += build_top_parlay(PHX_ROSTER, "PHX Top Props")
    lines += build_top_parlay(ALL_PLAYERS, "Cross-Series Top Props")

    # Full ranking
    all_sorted = sorted(ALL_PLAYERS, key=lambda p: p.edge, reverse=True)
    lines += [
        "",
        "## 📊 Full Roster Rankings (by Edge)",
        f"| Rank | Player | Team | T | L | Edge | Hit% | Valid |",
        f"|------|--------|------|---|---|------|-------|-------|",
    ]
    for rank, p in enumerate(all_sorted, 1):
        v = "✅" if p.valid else "❌"
        lines.append(
            f"| {rank} | {p.name} | {p.team} | **{p.T}** | {p.L:.0f} | "
            f"{p.edge:+.1f} | {p.hit_rate:.0%} | {v} |"
        )

    return "\n".join(lines)


report = build_full_report()
print(report)

with open("/home/workspace/NBA_TC_OKC_vs_PHX_Props_v9.md", "w") as f:
    f.write(report)

print("\n\n✅ Saved: /home/workspace/NBA_TC_OKC_vs_PHX_Props_v9.md")
