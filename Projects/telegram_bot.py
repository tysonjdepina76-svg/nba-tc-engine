#!/usr/bin/env python3
"""Telegram bot notifications for TC picks. Reads reason from picks DB."""

import os
import sqlite3
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL = os.environ.get("TELEGRAM_CHANNEL_ID", "")

def send_telegram(message: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHANNEL:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": TELEGRAM_CHANNEL,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False

def process_pending_picks():
    """Send unsent picks from DB to Telegram."""
    db_path = os.path.join(os.path.dirname(__file__), "data/picks.db")
    if not os.path.exists(db_path):
        return 0
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM picks WHERE sent = 0 ORDER BY edge DESC LIMIT 10")
    rows = cur.fetchall()
    sent = 0
    for row in rows:
        player = row["player"]
        league = row.get("league", row.get("sport", "?"))
        stat = row.get("stat", "projection")
        edge = row.get("edge", 0)
        direction = row.get("direction", "OVER")
        reason = row.get("reason", "No explanation")
        msg = f"🏆 {player} ({league}) — {direction} {stat}\nEdge: +{edge}%\n{reason}"
        if send_telegram(msg):
            cur.execute("UPDATE picks SET sent = 1 WHERE id = ?", (row["id"],))
            sent += 1
    conn.commit()
    conn.close()
    return sent

if __name__ == "__main__":
    count = process_pending_picks()
    print(f"Sent {count} picks to Telegram")
