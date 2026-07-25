import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

class BacktestEngine:
    def __init__(self, db_path="data/picks.db"):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pick_id INTEGER,
                game_date TEXT,
                sport TEXT,
                pick_type TEXT,
                pick_value REAL,
                closing_line REAL,
                result TEXT,
                profit REAL,
                roi REAL,
                bet_amount REAL DEFAULT 100,
                book TEXT,
                timestamp TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backtest_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT,
                total_picks INTEGER,
                wins INTEGER,
                losses INTEGER,
                pushes INTEGER,
                win_rate REAL,
                total_profit REAL,
                total_roi REAL,
                avg_profit_per_bet REAL,
                best_streak INTEGER,
                worst_streak INTEGER,
                details TEXT
            )
        """)

        conn.commit()
        conn.close()

    def run_backtest(self, sport=None, from_date=None, to_date=None, bet_amount=100.0):
        print(f"\nRUNNING BACKTEST...")
        print(f"   Sport: {sport or 'ALL'}")

        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT p.id, p.game_date, p.sport, p.pick_type, p.pick_value,
                   p.closing_line, p.confidence, p.notes
            FROM picks p
            WHERE p.closing_line IS NOT NULL
        """
        params = []

        if sport:
            query += " AND p.sport = ?"
            params.append(sport)
        if from_date:
            query += " AND p.game_date >= ?"
            params.append(from_date)
        if to_date:
            query += " AND p.game_date <= ?"
            params.append(to_date)

        query += " ORDER BY p.game_date ASC"

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        if df.empty:
            print("   No picks with closing lines found")
            return {"error": "No data available for backtest"}

        print(f"   Found {len(df)} picks with closing lines")

        results = []
        wins = losses = pushes = 0
        total_profit = 0
        current_streak = best_streak = worst_streak = 0

        for idx, row in df.iterrows():
            result, profit = self._simulate_bet(row, bet_amount)

            if result == 'win':
                wins += 1
                current_streak = current_streak + 1 if current_streak > 0 else 1
                best_streak = max(best_streak, current_streak)
            elif result == 'loss':
                losses += 1
                current_streak = current_streak - 1 if current_streak < 0 else -1
                worst_streak = min(worst_streak, current_streak)
            else:
                pushes += 1
                current_streak = 0

            total_profit += profit

            results.append({
                'pick_id': int(row['id']),
                'game_date': row['game_date'],
                'sport': row['sport'],
                'pick_type': row['pick_type'],
                'pick_value': row['pick_value'],
                'closing_line': row['closing_line'],
                'result': result,
                'profit': profit,
                'roi': (profit / bet_amount) * 100,
                'bet_amount': bet_amount,
            })

        total = len(results)
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        avg_profit = total_profit / total if total > 0 else 0

        summary = {
            'run_date': datetime.now().isoformat(),
            'total_picks': total,
            'wins': wins,
            'losses': losses,
            'pushes': pushes,
            'win_rate': round(win_rate, 2),
            'total_profit': round(total_profit, 2),
            'total_roi': round((total_profit / (total * bet_amount)) * 100, 2) if total > 0 else 0,
            'avg_profit_per_bet': round(avg_profit, 2),
            'best_streak': best_streak,
            'worst_streak': worst_streak
        }

        self._store_backtest_results(results, summary)
        return {'summary': summary, 'results': results}

    def _simulate_bet(self, row, bet_amount):
        pick_value = row.get('pick_value', 0)
        closing_line = row.get('closing_line', 0)
        pick_type = str(row.get('pick_type', 'SPREAD')).upper()
        juice = -110

        try:
            if pick_type == 'SPREAD':
                if pick_value < closing_line:
                    return 'win', bet_amount * (100 / abs(juice))
                elif pick_value > closing_line:
                    return 'loss', -bet_amount
                else:
                    return 'push', 0
            elif pick_type == 'MONEYLINE':
                if pick_value < closing_line:
                    return 'win', bet_amount * (100 / abs(pick_value))
                else:
                    return 'loss', -bet_amount
            elif pick_type == 'TOTAL':
                if pick_value < closing_line:
                    return 'win', bet_amount * (100 / abs(juice))
                elif pick_value > closing_line:
                    return 'loss', -bet_amount
                else:
                    return 'push', 0
            else:
                return 'loss', -bet_amount
        except:
            return 'loss', -bet_amount

    def _store_backtest_results(self, results, summary):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for r in results:
            cursor.execute("""
                INSERT INTO backtest_results (
                    pick_id, game_date, sport, pick_type, pick_value,
                    closing_line, result, profit, roi, bet_amount, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (r['pick_id'], r['game_date'], r['sport'], r['pick_type'],
                  r['pick_value'], r['closing_line'], r['result'], r['profit'],
                  r['roi'], r['bet_amount'], datetime.now().isoformat()))

        cursor.execute("""
            INSERT INTO backtest_summary (
                run_date, total_picks, wins, losses, pushes, win_rate,
                total_profit, total_roi, avg_profit_per_bet,
                best_streak, worst_streak, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (summary['run_date'], summary['total_picks'], summary['wins'],
              summary['losses'], summary['pushes'], summary['win_rate'],
              summary['total_profit'], summary['total_roi'],
              summary['avg_profit_per_bet'], summary['best_streak'],
              summary['worst_streak'], json.dumps(summary)))

        conn.commit()
        conn.close()

    def get_performance_by_sport(self):
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT sport, COUNT(*) as total_picks,
                SUM(CASE WHEN result='win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result='loss' THEN 1 ELSE 0 END) as losses,
                ROUND(SUM(profit), 2) as total_profit
            FROM backtest_results
            GROUP BY sport ORDER BY total_profit DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def get_performance_by_confidence(self):
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT 
                CASE 
                    WHEN confidence >= 80 THEN 'High (>80%)'
                    WHEN confidence >= 60 THEN 'Medium (60-80%)'
                    WHEN confidence >= 40 THEN 'Low (40-60%)'
                    ELSE 'Very Low (<40%)'
                END as confidence_level,
                COUNT(*) as total_picks,
                SUM(CASE WHEN result='win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result='loss' THEN 1 ELSE 0 END) as losses,
                ROUND(SUM(profit), 2) as total_profit
            FROM backtest_results
            GROUP BY confidence_level
            ORDER BY total_profit DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def generate_report(self):
        perf = self.get_performance_by_sport()
        lines = []
        lines.append("="*60)
        lines.append("BACKTEST PERFORMANCE REPORT")
        lines.append("="*60)
        if not perf.empty:
            for _, row in perf.iterrows():
                lines.append(f"  {row['sport']}: {row['wins']}W-{row['losses']}L | +${row['total_profit']:.2f}")
        lines.append("="*60)
        return "\n".join(lines)
