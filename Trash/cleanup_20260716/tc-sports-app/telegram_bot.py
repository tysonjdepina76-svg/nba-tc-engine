import os
import requests
import json
import sqlite3
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(text, parse_mode="HTML"):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("Telegram not configured — skipping")
        return None
    try:
        resp = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": CHANNEL_ID,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        return resp.json()
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return None


def format_pick_message(picks, sport_label="ALL"):
    if not picks:
        return None
    lines = [f"<b>🏆 TC SPORTS — {sport_label} TOP PICKS</b>", ""]
    for i, p in enumerate(picks[:10]):
        player = p.get("player", "?")
        team = p.get("team", "")
        prop = p.get("prop", "")
        edge = p.get("edge", 0)
        line_val = p.get("line", "N/A")
        proj = p.get("projection", 0)
        reason = p.get("reason", p.get("why", ""))
        emoji = "🔥" if float(edge) > 5 else "✅" if float(edge) > 2 else "📊"
        lines.append(
            f"{i+1}. {emoji} <b>{player}</b> ({team}) — {prop} "
            f"Proj: {proj} vs Line: {line_val} | Edge: <b>+{edge}%</b>"
        )
        if reason:
            lines.append(f"   <i>{reason[:120]}</i>")
        lines.append("")
    return "\n".join(lines)


def process_pending_picks():
    picks = load_recent_picks(limit=10)
    if not picks:
        print("No picks to send")
        return
    msg = format_pick_message(picks)
    if msg:
        result = send_message(msg)
        if result and result.get("ok"):
            print(f"Sent {len(picks)} picks to Telegram")
        else:
            print("Telegram send returned error")


def load_recent_picks(limit=10):
    picks = []
    picks_dir = os.path.join(os.path.dirname(__file__), "data", "picks")
    try:
        files = sorted(
            [f for f in os.listdir(picks_dir) if f.endswith(".csv")],
            reverse=True,
        )[:5]
        for fname in files:
            path = os.path.join(picks_dir, fname)
            sport = fname.split("_")[0].upper()
            with open(path) as f:
                lines = f.readlines()
            if len(lines) < 2:
                continue
            headers = lines[0].strip().split(",")
            for line in lines[1 : limit + 1]:
                vals = line.strip().split(",")
                row = dict(zip(headers, vals))
                row["sport"] = sport
                picks.append(row)
        picks.sort(key=lambda x: float(x.get("edge", 0)), reverse=True)
    except Exception as e:
        print(f"load_recent_picks: {e}")
    return picks


if __name__ == "__main__":
    process_pending_picks()
