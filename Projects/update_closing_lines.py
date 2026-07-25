import sqlite3
from datetime import datetime, timedelta
from history_tracker import LineHistoryTracker

def update_closing_lines():
    tracker = LineHistoryTracker()
    conn = sqlite3.connect("data/picks.db")
    cursor = conn.cursor()

    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    cursor.execute("""
        SELECT id, game_key, sport, away_team, home_team,
               dk_spread, dk_ml, dk_total,
               fd_spread, fd_ml, fd_total
        FROM picks
        WHERE game_date <= ?
        AND closing_line IS NULL
    """, (yesterday,))

    picks = cursor.fetchall()

    if not picks:
        print("No completed games found")
        conn.close()
        return

    print(f"Updating closing lines for {len(picks)} games...")

    for pick in picks:
        pick_id, game_key, sport, away, home, dk_spread, dk_ml, dk_total, fd_spread, fd_ml, fd_total = pick

        if dk_spread is not None:
            tracker.record_closing_line(
                pick_id, game_key, 'draftkings',
                dk_spread, dk_ml or 0, dk_total or 0
            )
        elif fd_spread is not None:
            tracker.record_closing_line(
                pick_id, game_key, 'fanduel',
                fd_spread, fd_ml or 0, fd_total or 0
            )

        print(f"  {away} @ {home} - closing spread: {dk_spread or fd_spread}")

    conn.close()
    print("Closing lines updated")

if __name__ == "__main__":
    update_closing_lines()
