import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class SteamDetector:
    def __init__(self, db_path="data/picks.db"):
        self.db_path = db_path
        self.thresholds = {
            "MLB": {"spread": 0.5, "ml": 10, "total": 0.5},
            "WNBA": {"spread": 0.5, "ml": 10, "total": 0.5},
            "NBA": {"spread": 0.5, "ml": 10, "total": 0.5},
            "NFL": {"spread": 0.5, "ml": 10, "total": 0.5}
        }

    def detect_steam(self, game_key: str, sport: str) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM line_movements 
            WHERE game_key = ? AND sport = ?
            ORDER BY timestamp DESC
            LIMIT 10
        """, (game_key, sport))

        rows = cursor.fetchall()
        conn.close()

        if len(rows) < 3:
            return {"has_steam": False, "message": "Not enough data", "confidence": 0}

        columns = ['id', 'game_key', 'sport', 'book', 'line_type',
                   'line_value', 'direction', 'movement', 'timestamp', 'is_sharp']
        movements = [dict(zip(columns, row)) for row in rows]

        books = {}
        for move in movements:
            book = move['book']
            if book not in books:
                books[book] = {"up": 0, "down": 0}
            if move['direction'] == "UP":
                books[book]["up"] += 1
            elif move['direction'] == "DOWN":
                books[book]["down"] += 1

        up_books = [b for b, d in books.items() if d["up"] > d["down"]]
        down_books = [b for b, d in books.items() if d["down"] > d["up"]]

        if len(up_books) >= 3:
            recent_up = sum(1 for m in movements[:3] if m['direction'] == "UP")
            confidence = round((recent_up / 3) * 100) if len(movements) >= 3 else 50
            return {
                "has_steam": True,
                "direction": "UP",
                "books": up_books,
                "confidence": confidence,
                "movements": movements[:5]
            }
        elif len(down_books) >= 3:
            recent_down = sum(1 for m in movements[:3] if m['direction'] == "DOWN")
            confidence = round((recent_down / 3) * 100) if len(movements) >= 3 else 50
            return {
                "has_steam": True,
                "direction": "DOWN",
                "books": down_books,
                "confidence": confidence,
                "movements": movements[:5]
            }

        return {"has_steam": False, "direction": None, "books": [], "confidence": 0}

    def get_steam_alerts(self, sport: str = None, minutes: int = 60) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat()

        query = """
            SELECT DISTINCT game_key, sport 
            FROM line_movements 
            WHERE timestamp > ?
        """
        params = [cutoff]

        if sport:
            query += " AND sport = ?"
            params.append(sport)

        cursor.execute(query, params)
        games = cursor.fetchall()
        conn.close()

        alerts = []
        for game_key, game_sport in games:
            result = self.detect_steam(game_key, game_sport)
            if result['has_steam']:
                alerts.append({
                    "game_key": game_key,
                    "sport": game_sport,
                    "direction": result['direction'],
                    "books": result['books'],
                    "confidence": result['confidence'],
                    "timestamp": datetime.now().isoformat()
                })

        return alerts
