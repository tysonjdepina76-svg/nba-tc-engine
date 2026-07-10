"""Position manager with Kelly Criterion, bankroll protection, exposure limits.

Prevents over-betting on a slate by enforcing per-bet, per-game, and total
exposure caps. Uses fractional Kelly (default 0.25) to be conservative.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Position:
    id: int
    sport: str
    game: str
    player: str
    stat: str
    direction: str
    line: float
    odds: float
    edge: float
    confidence: float
    stake: float
    meta: Dict = field(default_factory=dict)


class PositionManager:
    """Kelly-based position sizing with safety rails."""

    def __init__(
        self,
        bankroll: float = 10000.0,
        max_risk_per_bet: float = 0.05,
        max_total_exposure: float = 0.25,
        kelly_fraction: float = 0.25,
    ):
        self.bankroll = bankroll
        self.max_risk_per_bet = max_risk_per_bet
        self.max_total_exposure = max_total_exposure
        self.kelly_fraction = kelly_fraction
        self.open_positions: List[Position] = []
        self._next_id = 1

    def update_bankroll(self, pnl: float):
        self.bankroll += pnl

    def _kelly_fraction(self, edge: float, odds: float) -> float:
        if odds <= 1.0:
            return 0.0
        b = odds - 1.0
        # Use abs(edge) — sign of edge is direction (UNDER/OVER), magnitude is strength
        p = 0.5 + max(min(abs(edge), 50.0), 0.0) / 100.0
        p = max(min(p, 0.95), 0.05)
        q = 1.0 - p
        kelly = (b * p - q) / b
        return max(0.0, kelly)

    def size(self, edge: float, odds: float, confidence: float = 1.0) -> float:
        """Return stake in dollars. Scales by confidence, capped per-bet."""
        kelly = self._kelly_fraction(edge, odds)
        if kelly <= 0:
            return 0.0
        frac = kelly * self.kelly_fraction * confidence
        stake = self.bankroll * frac
        cap = self.bankroll * self.max_risk_per_bet
        return min(stake, cap)

    def _exposure_in_game(self, game: str) -> float:
        return sum(p.stake for p in self.open_positions if p.game == game)

    def _total_exposure(self) -> float:
        return sum(p.stake for p in self.open_positions)

    def open_position(
        self,
        sport: str,
        game: str,
        player: str,
        stat: str,
        direction: str,
        line: float,
        odds: float,
        edge: float,
        confidence: float = 1.0,
        meta: Optional[Dict] = None,
    ) -> Optional[Position]:
        """Open a position if it passes exposure caps."""
        stake = self.size(edge, odds, confidence)
        if stake < 1.0:
            logger.info(f"Skip {player} {stat}: stake {stake:.2f} below $1 min")
            return None
        if self._exposure_in_game(game) + stake > self.bankroll * self.max_risk_per_bet:
            logger.info(f"Skip {player} {stat}: per-game cap reached")
            return None
        if self._total_exposure() + stake > self.bankroll * self.max_total_exposure:
            logger.info(f"Skip {player} {stat}: total exposure cap reached")
            return None
        pos = Position(
            id=self._next_id,
            sport=sport,
            game=game,
            player=player,
            stat=stat,
            direction=direction,
            line=line,
            odds=odds,
            edge=edge,
            confidence=confidence,
            stake=stake,
            meta=meta or {},
        )
        self._next_id += 1
        self.open_positions.append(pos)
        return pos

    def close_position(self, position_id: int, pnl: float) -> None:
        for i, p in enumerate(self.open_positions):
            if p.id == position_id:
                self.bankroll += pnl
                self.open_positions.pop(i)
                return

    def portfolio(self) -> Dict:
        return {
            "bankroll": self.bankroll,
            "open_positions": len(self.open_positions),
            "total_exposure": self._total_exposure(),
            "exposure_pct": self._total_exposure() / self.bankroll if self.bankroll else 0,
        }
