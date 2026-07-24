"""MLB Integration - Wires ML, Arbitrage, Position Management into daily_picks.

Reads picks from /home/workspace/Projects/picks_mlb.csv (or any sport),
runs PredictiveEngine for confidence, finds arbitrage, sizes positions
with Kelly, records everything in HistoricalTracker.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tracking.historical_tracker import HistoricalTracker
from ml.predictive_engine import PredictiveEngine
from arbitrage.arbitrage_finder import ArbitrageFinder
from trading.position_manager import PositionManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECTS_DIR = Path("/home/workspace/Projects")


class MLBIntegration:
    """Orchestrate historical tracking, ML, arbitrage, and position sizing."""

    def __init__(self, bankroll: float = 10000.0):
        self.history = HistoricalTracker()
        self.engine = PredictiveEngine()
        self.arb = ArbitrageFinder()
        self.position_manager = PositionManager(
            bankroll=10000,
            max_risk_per_bet=0.05,
            max_total_exposure=0.25,
            kelly_fraction=0.25
        )

    def load_picks(self, sport: str) -> pd.DataFrame:
        path = PROJECTS_DIR / f"picks_{sport}.csv"
        if not path.exists():
            logger.error(f"No picks file at {path}")
            return pd.DataFrame()
        return pd.read_csv(path)

    def process(self, sport: str, picks: Optional[pd.DataFrame] = None) -> Dict:
        if picks is None:
            picks = self.load_picks(sport)
        if picks.empty:
            return {"status": "no_picks", "sport": sport}
        picks = picks.copy()
        if "direction" not in picks.columns:
            picks["direction"] = picks["edge"].apply(
                lambda e: "UNDER" if isinstance(e, (int, float)) and e < 0 else "OVER"
            )
        if "odds" not in picks.columns:
            picks["odds"] = 1.91

        results: Dict = {
            "sport": sport,
            "timestamp": datetime.utcnow().isoformat(),
            "total_picks": len(picks),
            "positions": [],
            "portfolio": self.position_manager.portfolio(),
        }

        pick_dicts: List[Dict] = picks.to_dict(orient="records")
        predictions = self.engine.predict(pick_dicts)

        for pick, pred in zip(pick_dicts, predictions):
            edge = float(pick.get("edge", pred["edge_adj"]))
            confidence = float(pred["confidence"])
            # Skip if edge isn't strong (use abs — positive edge on UNDER means line is HIGH vs proj)
            if abs(edge) < 2.0:
                continue
            meta = {
                "projection": pred["projection"],
                "edge_adj": pred["edge_adj"],
                "confidence": confidence,
            }
            pos = self.position_manager.open_position(
                sport=sport,
                game=str(pick.get("game", "MLB")),
                player=str(pick.get("player", "")),
                stat=str(pick.get("stat", "")),
                direction=str(pick.get("direction", "OVER")),
                line=float(pick.get("line", 0.0)),
                odds=float(pick.get("odds", 1.91)),
                edge=edge,
                confidence=confidence,
                meta=meta,
            )
            if pos is None:
                continue
            self.history.record_bet(
                {
                    "sport": sport,
                    "game": pos.game,
                    "player": pos.player,
                    "stat": pos.stat,
                    "direction": pos.direction,
                    "line": pos.line,
                    "projection": pred["projection"],
                    "edge": edge,
                    "odds": pos.odds,
                    "bookmaker": pick.get("bookmaker", "draftkings"),
                    "stake": pos.stake,
                    "meta": meta,
                }
            )
            results["positions"].append(
                {
                    "id": pos.id,
                    "game": pos.game,
                    "player": pos.player,
                    "stat": pos.stat,
                    "direction": pos.direction,
                    "line": pos.line,
                    "edge": edge,
                    "confidence": confidence,
                    "stake": pos.stake,
                }
            )

        results["portfolio"] = self.position_manager.portfolio()
        results["performance"] = self.history.performance(sport=sport)
        return results

    def save(self, results: Dict, sport: str) -> Path:
        out = PROJECTS_DIR / f"results_{sport}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(out, "w") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Saved {out}")
        return out

    def run(self, sport: str) -> Dict:
        logger.info(f"=== {sport.upper()} INTEGRATION RUN ===")
        results = self.process(sport)
        self.save(results, sport)
        logger.info(
            f"Positions: {len(results['positions'])} | "
            f"Bankroll: {results['portfolio']['bankroll']:.2f} | "
            f"Exposure: {results['portfolio']['exposure_pct']*100:.1f}%"
        )
        return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sport", default="mlb")
    p.add_argument("--bankroll", type=float, default=10000.0)
    p.add_argument("--show-positions", action="store_true")
    p.add_argument("--picks", help="Optional picks CSV path", default=None)
    args = p.parse_args()

    integ = MLBIntegration(bankroll=args.bankroll)
    if args.picks:
        df = pd.read_csv(args.picks)
        results = integ.process(args.sport, picks=df)
        integ.save(results, args.sport)
    else:
        results = integ.run(args.sport)

    if args.show_positions and results.get("positions"):
        print(f"\n{'='*60}")
        print(f"  {args.sport.upper()} POSITIONS ({len(results['positions'])})")
        print(f"{'='*60}")
        for pos in results["positions"]:
            print(
                f"  #{pos['id']:>3} {pos['player']:<24} {pos['stat']:<14} "
                f"{pos['direction']:<5} L{pos['line']:>5.1f} "
                f"E{pos['edge']:>+5.1f} C{pos['confidence']:.2f} "
                f"${pos['stake']:>6.2f}"
            )
        print(f"\n  Bankroll: ${results['portfolio']['bankroll']:,.2f}")
        print(f"  Exposure: {results['portfolio']['exposure_pct']*100:.1f}%")
        if results.get("performance", {}).get("total_bets", 0) > 0:
            perf = results["performance"]
            print(f"  Last 30d: {perf['total_bets']} bets | "
                  f"{perf['win_rate']*100:.1f}% win | "
                  f"ROI {perf['roi']*100:+.1f}%")


if __name__ == "__main__":
    main()
