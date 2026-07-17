"""Truth-gated alert API for the TC dashboard.

Uses PostgreSQL when configured and returns an empty, explicit result when the
remote database is unavailable. Projection-only or self-edge rows never appear
as +EV alerts.
"""

import os
from flask import Flask, jsonify

app = Flask(__name__)


def get_connection():
    import psycopg2
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        port=os.getenv("DB_PORT", "5432"),
        connect_timeout=3,
    )


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "tc-alerts", "truth_gate": "enabled"})


@app.get("/api/alerts")
def get_alerts():
    query = """
        SELECT sport, player, prop, period, direction, projection,
               market_line, edge_percent, line_source, timestamp
        FROM truth_engine_logs
        WHERE bet_result = 'Pending'
          AND alert_eligible = 1
          AND line_status = 'REAL_LINE'
          AND market_line IS NOT NULL
          AND edge_percent IS NOT NULL
        ORDER BY edge_percent DESC, timestamp DESC
        LIMIT 10
    """
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        alerts = [
            {
                "sport": row[0],
                "player": row[1],
                "prop": row[2],
                "period": row[3],
                "direction": row[4],
                "projection": row[5],
                "line": row[6],
                "edge": f"+{float(row[7]):.1f}%",
                "source": row[8],
                "timestamp": row[9].isoformat() if row[9] else None,
                "truth": "REAL_LINE",
            }
            for row in rows
        ]
        return jsonify({"alerts": alerts, "count": len(alerts), "truth_gate": "enabled"})
    except Exception:
        app.logger.exception("Alert query failed")
        return jsonify({"alerts": [], "count": 0, "truth_gate": "enabled", "status": "data_unavailable"}), 503
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
