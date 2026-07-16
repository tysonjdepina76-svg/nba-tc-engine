"""ParlayBuilder — build ranked parlays from today's picks.

Reads picks from Daily_Log/{date}/picks.csv and DK lines from
Daily_Log/{date}/combos_at_*.json (per-matchup DK lines). Combines
prop edges + market lines into 2-8 leg parlays sorted by combined edge.
"""
from __future__ import annotations

import csv
import json
import logging
import math
from collections import defaultdict
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("parlay_builder")

ET = timezone(timedelta(hours=-4))
WORKSPACE = Path("/home/workspace")
DAILY_LOG = WORKSPACE / "Daily_Log"


@dataclass
class Leg:
    player: str
    stat: str
    line: float
    direction: str
    odds: float
    sport: str
    matchup: str
    edge: float = 0.0


@dataclass
class Parlay:
    sport: str
    matchup: str
    legs: List[Leg] = field(default_factory=list)
    combined_edge: float = 0.0
    combined_prob: float = 0.0
    payout_mult: float = 0.0
    legs_count: int = 0
    est_odds: float = 0.0


def _to_float(x, default: float = 0.0) -> float:
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


def _american_to_prob(odds: float) -> float:
    if not odds:
        return 0.5
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return -odds / (-odds + 100.0)


def _american_to_payout(odds: float) -> float:
    if not odds:
        return 1.91
    if odds > 0:
        return 1 + odds / 100.0
    return 1 + 100.0 / -odds


class ParlayBuilder:
    """Build parlays from picks.csv and DK line cache."""

    def __init__(self, date_str: Optional[str] = None):
        self.date_str = date_str or datetime.now(ET).strftime("%Y-%m-%d")
        self.day_dir = DAILY_LOG / self.date_str

    def _load_picks(self) -> List[Leg]:
        csv_path = self.day_dir / "picks.csv"
        if not csv_path.exists():
            return []
        legs: List[Leg] = []
        with csv_path.open(newline="") as f:
            for r in csv.DictReader(f):
                player = r.get("player", "")
                stat = r.get("stat", "")
                if not stat or stat.upper() in ("PENDING", "?"):
                    continue
                legs.append(
                    Leg(
                        player=player,
                        stat=stat,
                        line=_to_float(r.get("line") or r.get("market_line")),
                        direction=(r.get("direction") or "OVER").upper(),
                        odds=_to_float(r.get("odds"), -110),
                        sport=(r.get("league") or r.get("sport") or "UNK").upper(),
                        matchup=(r.get("matchup") or "").upper(),
                        edge=_to_float(r.get("edge")),
                    )
                )
        return legs

    def _load_dk_props(self) -> List[Leg]:
        """Read any per-matchup DK-prop cache file written by run_dk_picks.py."""
        legs: List[Leg] = []
        if not self.day_dir.exists():
            return legs
        for f in self.day_dir.glob("combos_at_*.json"):
            try:
                data = json.loads(f.read_text())
            except Exception:
                continue
            matchup = (data.get("matchup") or f.stem.replace("combos_at_", "")).upper()
            sport = (data.get("sport") or "UNK").upper()
            for prop in data.get("props", []) or []:
                stat = prop.get("stat", "")
                if not stat:
                    continue
                legs.append(
                    Leg(
                        player=prop.get("player", ""),
                        stat=stat,
                        line=_to_float(prop.get("line") or prop.get("market_line")),
                        direction=(prop.get("direction") or "OVER").upper(),
                        odds=_to_float(prop.get("odds"), -110),
                        sport=sport,
                        matchup=matchup,
                        edge=_to_float(prop.get("edge")),
                    )
                )
        return legs

    def _all_legs(self) -> List[Leg]:
        # Combine + dedupe by (player, stat, direction, matchup)
        seen = set()
        out: List[Leg] = []
        for leg in self._load_picks() + self._load_dk_props():
            key = (leg.player.upper(), leg.stat.upper(), leg.direction, leg.matchup)
            if key in seen:
                continue
            seen.add(key)
            if leg.edge == 0:
                continue
            out.append(leg)
        return out

    def build(
        self,
        min_legs: int = 2,
        max_legs: int = 6,
        top_n: int = 10,
        edges: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Parlay]:
        if edges is not None:
            legs = []
            for e in edges:
                legs.append(
                    Leg(
                        player=e.get("player", ""),
                        stat=e.get("stat", ""),
                        line=_to_float(e.get("line")),
                        direction=(e.get("direction") or "OVER").upper(),
                        odds=_to_float(e.get("odds"), -110),
                        sport=(e.get("sport") or "UNK").upper(),
                        matchup=(e.get("matchup") or "").upper(),
                        edge=_to_float(e.get("edge")),
                    )
                )
        else:
            legs = self._all_legs()
        if not legs:
            return []

        by_matchup: Dict[str, List[Leg]] = defaultdict(list)
        by_sport: Dict[str, List[Leg]] = defaultdict(list)
        for leg in legs:
            by_matchup[leg.matchup].append(leg)
            by_sport[leg.sport].append(leg)

        parlays: List[Parlay] = []
        # Same-matchup parlays (highest quality)
        for matchup, group in by_matchup.items():
            sorted_legs = sorted(group, key=lambda L: L.edge, reverse=True)
            n = min(max_legs, len(sorted_legs))
            if n < min_legs:
                continue
            chosen = sorted_legs[:n]
            parlays.append(self._make_parlay(chosen, scope="same_matchup"))

        # Cross-matchup, same-sport parlays (more variety)
        for sport, group in by_sport.items():
            if len(group) < min_legs:
                continue
            sorted_legs = sorted(group, key=lambda L: L.edge, reverse=True)
            # Try a few sizes: min_legs, min_legs+1, max_legs
            for n in (min_legs, min_legs + 1, min(max_legs, len(sorted_legs))):
                if n < min_legs or n > len(sorted_legs):
                    continue
                chosen = sorted_legs[:n]
                # Skip if all same matchup (already covered)
                matchups = {L.matchup for L in chosen}
                if len(matchups) < 2:
                    continue
                parlays.append(self._make_parlay(chosen, scope="cross_matchup"))

        parlays.sort(key=lambda p: (p.combined_edge, p.payout_mult), reverse=True)
        return parlays[:top_n]

    def _make_parlay(self, chosen: List["Leg"], scope: str) -> "Parlay":
        probs = [_american_to_prob(L.odds) for L in chosen]
        payouts = [_american_to_payout(L.odds) for L in chosen]
        p_comb = 1.0
        for x in probs:
            p_comb *= max(min(x, 0.99), 0.01)
        pay_comb = 1.0
        for x in payouts:
            pay_comb *= x
        avg_edge = sum(L.edge for L in chosen) / len(chosen)
        sport = chosen[0].sport
        matchup_label = chosen[0].matchup if scope == "same_matchup" else "MULTI"
        return Parlay(
            sport=sport,
            matchup=matchup_label,
            legs=chosen,
            legs_count=len(chosen),
            combined_edge=round(avg_edge, 2),
            combined_prob=round(p_comb, 4),
            payout_mult=round(pay_comb, 2),
            est_odds=round(pay_comb, 2),
        )

    def save(self, parlays: List[Parlay]) -> Path:
        out = self.day_dir / "parlays.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["sport", "matchup", "legs", "combined_edge", "combined_prob", "payout_mult"])
            for p in parlays:
                leg_str = " | ".join(
                    f"{L.player} {L.stat} {L.direction} {L.line}" for L in p.legs
                )
                w.writerow([p.sport, p.matchup, leg_str, p.combined_edge, p.combined_prob, p.payout_mult])
        return out
