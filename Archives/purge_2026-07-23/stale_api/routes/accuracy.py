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


@router.get("/profit")
def get_profit(sport: str = Query(None)):
    """Return cumulative profit from bet_tracking."""
    try:
        conn = sqlite3.connect("/home/workspace/Projects/data/tc_pipeline.db")
        if sport:
            row = conn.execute(
                "SELECT SUM(profit) as total, COUNT(*) as bets FROM bet_tracking WHERE sport = ?",
                (sport,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT SUM(profit) as total, COUNT(*) as bets FROM bet_tracking"
            ).fetchone()
        conn.close()
        return {
            "profit": round(row[0], 2) if row and row[0] else 0.0,
            "bets": row[1] if row else 0,
            "sport": sport or "all",
        }
    except Exception as e:
        return {"error": str(e), "profit": 0}


@router.get("/profit/history")
def get_profit_history(days: int = Query(30)):
    """Return daily profit history."""
    try:
        conn = sqlite3.connect("/home/workspace/Projects/data/tc_pipeline.db")
        query = f"""
            SELECT DATE(timestamp) as day, SUM(profit) as daily_profit, COUNT(*) as bets
            FROM bet_tracking
            WHERE timestamp >= DATE('now', '-{days} days')
            GROUP BY DATE(timestamp)
            ORDER BY day
        """
        rows = conn.execute(query).fetchall()
        conn.close()
        return {
            "history": [
                {"date": r[0], "profit": round(r[1], 2), "bets": r[2]}
                for r in rows
            ],
            "days": days,
        }
    except Exception as e:
        return {"error": str(e), "history": []}
