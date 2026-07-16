#!/usr/bin/env python3
"""Accuracy API — projection vs actual performance."""
from fastapi import APIRouter, Query
import sqlite3
import pandas as pd
from datetime import datetime

router = APIRouter()


@router.get("/accuracy")
def get_accuracy(sport: str = Query(None)):
    """Return MAE, bias, and hit rate by sport from graded picks."""
    try:
        conn = sqlite3.connect("/home/workspace/Projects/data/tc_pipeline.db")
        query = """
            SELECT sport,
                   ROUND(AVG(ABS(projection - actual)), 3) AS mae,
                   ROUND(AVG(projection - actual), 3) AS bias,
                   ROUND(AVG(CASE WHEN hit = 1 THEN 1.0 ELSE 0.0 END), 3) AS hit_rate,
                   COUNT(*) AS n
            FROM graded_picks
            WHERE actual IS NOT NULL
        """
        if sport:
            query += f" AND sport = '{sport}'"
        query += " GROUP BY sport ORDER BY hit_rate DESC"

        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e), "sport": sport}


@router.get("/accuracy/details")
def get_accuracy_details(
    sport: str = Query(None),
    stat: str = Query(None),
    limit: int = Query(20),
):
    """Return per-stat accuracy breakdown with directional edge."""
    try:
        conn = sqlite3.connect("/home/workspace/Projects/data/tc_pipeline.db")
        clauses = ["actual IS NOT NULL"]
        if sport:
            clauses.append(f"sport = '{sport}'")
        if stat:
            clauses.append(f"stat = '{stat}'")
        where = " AND ".join(clauses)

        query = f"""
            SELECT sport, stat, direction,
                   ROUND(AVG(ABS(projection - actual)), 3) AS mae,
                   ROUND(AVG(projection - actual), 3) AS bias,
                   ROUND(AVG(CASE WHEN hit = 1 THEN 1.0 ELSE 0.0 END), 3) AS hit_rate,
                   COUNT(*) AS n
            FROM graded_picks
            WHERE {where}
            GROUP BY sport, stat, direction
            HAVING n >= 5
            ORDER BY n DESC
            LIMIT {limit}
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}
