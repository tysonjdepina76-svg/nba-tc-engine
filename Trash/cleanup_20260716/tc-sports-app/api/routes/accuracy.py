import sqlite3, os
import pandas as pd
from fastapi import APIRouter

router = APIRouter()

@router.get("/accuracy")
def get_accuracy(sport: str = None):
    db_path = "/home/workspace/tc-sports-app/data/tc_pipeline.db"
    if not os.path.exists(db_path):
        return {"error": "Database not found", "path": db_path}
    conn = sqlite3.connect(db_path)
    query = """
        SELECT sport,
               ROUND(AVG(ABS(projection - actual)), 2) AS mae,
               ROUND(AVG(projection - actual), 2) AS bias,
               COUNT(*) AS n,
               ROUND(AVG(hit) * 100, 1) AS hit_pct
        FROM graded_picks
        WHERE actual IS NOT NULL AND projection IS NOT NULL
    """
    if sport:
        params = (sport,)
        query += " AND sport = ?"
    else:
        params = ()
    query += " GROUP BY sport"
    try:
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        conn.close()
        return {"error": str(e)}
