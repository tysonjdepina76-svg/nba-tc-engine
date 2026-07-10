"""Historical bet tracking with SQLite. Records picks, grades them against
final outcomes, computes hit rate / ROI / CLV."""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = Path("/home/workspace/Projects/data/betting_history.db")


class HistoricalTracker:
    """Track every bet placed, grade outcomes, compute rolling performance."""

    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    sport TEXT,
                    game TEXT,
                    player TEXT,
                    stat TEXT,
                    direction TEXT,
                    line REAL,
                    projection REAL,
                    edge REAL,
                    odds REAL,
                    bookmaker TEXT,
                    stake REAL,
                    status TEXT DEFAULT 'pending',
                    actual_value REAL,
                    profit REAL,
                    graded_at TEXT,
                    meta TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_bets_sport_created ON bets(sport, created_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_bets_status ON bets(status)"
            )

    def record_bet(self, bet: Dict) -> int:
        """Insert a new pending bet. Returns bet id."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO bets (
                    created_at, sport, game, player, stat, direction,
                    line, projection, edge, odds, bookmaker, stake, meta
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.utcnow().isoformat(),
                    bet.get("sport"),
                    bet.get("game"),
                    bet.get("player"),
                    bet.get("stat"),
                    bet.get("direction"),
                    bet.get("line"),
                    bet.get("projection"),
                    bet.get("edge"),
                    bet.get("odds", 1.91),
                    bet.get("bookmaker"),
                    bet.get("stake", 0.0),
                    json.dumps(bet.get("meta", {})),
                ),
            )
            bet_id = cur.lastrowid
        logger.info(f"Recorded bet #{bet_id}: {bet.get('player')} {bet.get('stat')} {bet.get('direction')}")
        return bet_id

    def grade_bet(self, bet_id: int, actual_value: float) -> Dict:
        """Grade a pending bet against the actual stat value.

        For OVER: win if actual > line. For UNDER: win if actual < line.
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT direction, line, odds, stake FROM bets WHERE id = ?", (bet_id,)
            ).fetchone()
            if not row:
                return {"error": f"bet {bet_id} not found"}
            direction, line, odds, stake = row
            if direction == "OVER":
                win = actual_value > line
                push = actual_value == line
            elif direction == "UNDER":
                win = actual_value < line
                push = actual_value == line
            else:
                win, push = False, False

            if push:
                profit = 0.0
                status = "push"
            elif win:
                profit = stake * (odds - 1)
                status = "win"
            else:
                profit = -stake
                status = "loss"

            conn.execute(
                """
                UPDATE bets SET actual_value = ?, profit = ?, status = ?,
                graded_at = ? WHERE id = ?
                """,
                (actual_value, profit, status, datetime.utcnow().isoformat(), bet_id),
            )
        return {"bet_id": bet_id, "status": status, "profit": profit, "actual": actual_value}

    def performance(self, sport: Optional[str] = None, days: int = 30) -> Dict:
        """Compute hit rate, ROI, profit, count over the last N days."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        query = (
            "SELECT status, profit, stake FROM bets "
            "WHERE graded_at IS NOT NULL AND created_at > ?"
        )
        params: List = [cutoff]
        if sport:
            query += " AND sport = ?"
            params.append(sport)
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        if not rows:
            return {"win_rate": 0.0, "roi": 0.0, "total_bets": 0, "total_profit": 0.0}
        wins = sum(1 for s, _, _ in rows if s == "win")
        total_profit = sum(p for _, p, _ in rows)
        total_stake = sum(s for _, _, s in rows) or 1.0
        return {
            "win_rate": wins / len(rows),
            "roi": total_profit / total_stake,
            "total_bets": len(rows),
            "total_profit": total_profit,
            "total_stake": total_stake,
        }

    def pending_bets(self, sport: Optional[str] = None) -> List[Dict]:
        """List pending (ungraded) bets for a sport."""
        query = "SELECT * FROM bets WHERE status = 'pending'"
        params: List = []
        if sport:
            query += " AND sport = ?"
            params.append(sport)
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        cols = [d[0] for d in conn.execute("SELECT * FROM bets LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]
