#!/usr/bin/env python3
"""Integrate: add DB writes to daily_picks.py, add /api/picks/top to api/main.py, fix health check."""
import os, re

BASE = os.path.dirname(os.path.abspath(__file__))

def patch_daily_picks():
    path = os.path.join(BASE, "daily_picks.py")
    with open(path, "r") as f:
        content = f.read()

    if "from db_writer import" in content:
        print("daily_picks.py already patched — skipping")
        return

    content = content.replace(
        'sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n\nfrom tc_math_hybrid import determine_pick, SPORT_CONFIGS',
        'sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n\nfrom tc_math_hybrid import determine_pick, SPORT_CONFIGS\nfrom db_writer import write_picks_to_db'
    )

    content = content.replace(
        '        shutil.copy2(csv_file, dashboard_csv)\n        print(f"Synced to {dashboard_csv}")',
        '        shutil.copy2(csv_file, dashboard_csv)\n        print(f"Synced to {dashboard_csv}")\n\n        write_picks_to_db(all_picks, log_date)'
    )

    with open(path, "w") as f:
        f.write(content)
    print("Patched daily_picks.py: added db_writer import + write_picks_to_db call")


def patch_api_main():
    path = os.path.join(BASE, "api", "main.py")
    with open(path, "r") as f:
        content = f.read()

    if "/api/picks/top" in content:
        print("api/main.py already has /api/picks/top — skipping")
    else:
        insert_at = content.rfind('@app.get("/api/v1/benchmark/comparison")')
        if insert_at == -1:
            insert_at = content.rfind('if __name__')
            if insert_at == -1:
                insert_at = len(content)

        new_endpoint = '''
@app.get("/api/picks/top")
def picks_top(sport: Optional[str] = None):
    try:
        from api.picks_endpoint import api_picks_top
        picks = api_picks_top(sport)
        return picks
    except Exception as e:
        return {"error": str(e), "picks": []}
'''

        content = content[:insert_at] + new_endpoint + content[insert_at:]
        with open(path, "w") as f:
            f.write(content)
        print("Added /api/picks/top endpoint to api/main.py")

    if "SELECT COUNT(*) FROM graded_picks" in content:
        print("Health check already queries graded_picks — skipping")
    else:
        content = content.replace(
            'cursor.execute("SELECT COUNT(*) FROM players")\n        player_count = cursor.fetchone()[0]',
            'cursor.execute("SELECT COUNT(*) FROM graded_picks")\n        graded_count = cursor.fetchone()[0]\n        cursor.execute("SELECT COUNT(*) FROM bet_tracking")\n        bet_count = cursor.fetchone()[0]'
        )
        content = content.replace(
            '"players": player_count,',
            '"graded_picks": graded_count,\n            "tracked_bets": bet_count,'
        )
        with open(path, "w") as f:
            f.write(content)
        print("Updated health check to query graded_picks + bet_tracking")


if __name__ == "__main__":
    patch_daily_picks()
    patch_api_main()
    print("\nDone. Run: python daily_picks.py --sport all   then restart uvicorn.")
