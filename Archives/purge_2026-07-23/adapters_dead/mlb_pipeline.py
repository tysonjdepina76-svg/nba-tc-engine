"""MLB cross-model edge pipeline.

Reads your real picks.csv (date,league,matchup,team,player,role,stat,direction,
market_line,tc_projection,edge,...) and computes game-level cross edges so the
dashboard can rank where the pitcher + batter signals agree.
"""
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.adapters.odds_api_adapter import OddsAPIAdapter

logger = logging.getLogger(__name__)

LEAGUE_FILTER = "MLB"
TOP_LEGS_PER_GAME = 5


class MLBPipeline:
    """MLB cross-model edge pipeline — safe on quota-exhausted Odds API."""

    def __init__(self, picks_csv_path: str = "picks.csv"):
        self.picks_path = Path(picks_csv_path)
        self.adapter = OddsAPIAdapter()

    # ------------------------------------------------------------------ load
    def load_game_outline(self, league: str = LEAGUE_FILTER) -> pd.DataFrame:
        if not self.picks_path.exists():
            logger.error("picks.csv missing at %s", self.picks_path)
            return pd.DataFrame()
        try:
            df = pd.read_csv(self.picks_path)
        except Exception as e:
            logger.error("read_csv failed: %s", e)
            return pd.DataFrame()
        df = df[df["league"].str.upper() == league.upper()].copy()
        df["edge"] = pd.to_numeric(df.get("edge"), errors="coerce").fillna(0.0)
        df["market_line"] = pd.to_numeric(df.get("market_line"), errors="coerce")
        df["tc_projection"] = pd.to_numeric(df.get("tc_projection"), errors="coerce")
        logger.info("Loaded %d %s rows from %s", len(df), league, self.picks_path)
        return df

    # ------------------------------------------------------------------ live
    def get_live_odds_for_game(self, game: str, bookmakers=None) -> Dict:
        if not game or "@" not in game:
            return {}
        away, home = game.split("@", 1)
        try:
            events = self.adapter.get_events(sport="baseball", league="usa-mlb")
        except Exception as e:
            logger.warning("Odds API events failed: %s", e)
            return {}
        for ev in events:
            if (ev.get("away_team", "").lower() == away.lower()
                    and ev.get("home_team", "").lower() == home.lower()):
                try:
                    return self.adapter.get_event_odds(
                        ev.get("id"),
                        bookmakers=",".join(bookmakers or ["draftkings", "fanduel"]),
                    )
                except Exception as e:
                    logger.warning("Odds API event_odds failed: %s", e)
                    return {}
        return {}

    # -------------------------------------------------------------- cross-edge
    def calculate_cross_edges(self, df: pd.DataFrame) -> Dict[str, Dict]:
        if df.empty:
            return {}
        out: Dict[str, Dict] = {}
        for game, gdf in df.groupby("matchup"):
            pitching = gdf[gdf["role"] == "P"]
            batting = gdf[gdf["role"] != "P"]
            cross = float(gdf["edge"].sum())
            pitch = float(pitching["edge"].sum())
            bat = float(batting["edge"].sum())
            legs = []
            for _, r in gdf.iterrows():
                legs.append({
                    "player": r.get("player"),
                    "stat": r.get("stat"),
                    "direction": r.get("direction"),
                    "line": float(r.get("market_line") or 0),
                    "proj": float(r.get("tc_projection") or 0),
                    "edge": float(r.get("edge") or 0),
                    "type": "P" if r.get("role") == "P" else "B",
                })
            legs = sorted(legs, key=lambda x: x["edge"])[:TOP_LEGS_PER_GAME]
            out[game] = {
                "game": game,
                "cross_score": round(cross, 1),
                "pitching_score": round(pitch, 1),
                "batting_score": round(bat, 1),
                "total_legs": int(len(gdf)),
                "top_legs": legs,
                "has_pitching": len(pitching) > 0,
                "has_batting": len(batting) > 0,
            }
        return out

    # ---------------------------------------------------------------- best
    def get_best_bets(self, min_cross_edge: float = -20.0) -> List[Dict]:
        df = self.load_game_outline()
        if df.empty:
            return []
        edges = self.calculate_cross_edges(df)
        ranked = [v for v in edges.values() if v["cross_score"] <= min_cross_edge]
        ranked.sort(key=lambda x: x["cross_score"])
        # try live odds (non-fatal if quota is dead)
        for bet in ranked:
            odds = self.get_live_odds_for_game(bet["game"])
            bet["live_odds_available"] = bool(odds)
            if odds:
                bet["current_lines"] = self.extract_current_lines(odds)
        return ranked

    # ----------------------------------------------------------- helpers
    @staticmethod
    def extract_current_lines(odds: Dict) -> Dict:
        lines = {}
        for book, data in (odds.get("bookmakers") or {}).items():
            for market in data.get("markets", []):
                for outc in market.get("outcomes", []):
                    player = outc.get("description") or outc.get("name", "")
                    lines[f"{book}_{player}"] = {
                        "line": outc.get("point"),
                        "price": outc.get("price"),
                    }
        return lines

    def export_best_bets(self, output_path: str = "best_bets.json",
                         min_cross_edge: float = -20.0) -> Dict:
        bets = self.get_best_bets(min_cross_edge=min_cross_edge)
        payload = {
            "timestamp": datetime.now().isoformat(),
            "total_games": len(bets),
            "bets": bets,
        }
        try:
            with open(output_path, "w") as f:
                json.dump(payload, f, indent=2)
            logger.info("Exported %d best bets to %s", len(bets), output_path)
        except Exception as e:
            logger.error("export failed: %s", e)
        return payload

    def close(self):
        try:
            self.adapter.close()
        except Exception:
            import logging as _log
            _log.getLogger(__name__).debug("exception", exc_info=True)


if __name__ == "__main__":
    p = MLBPipeline("picks.csv")
    out = p.export_best_bets("best_bets.json", min_cross_edge=-20.0)
    print(json.dumps({"total_games": out["total_games"]}, indent=2))
    p.close()
