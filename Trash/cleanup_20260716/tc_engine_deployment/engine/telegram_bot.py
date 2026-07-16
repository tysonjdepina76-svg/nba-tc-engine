#!/usr/bin/env python3
import os
import time
import httpx
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_URL = "http://api:8001"
CHECK_INTERVAL = int(os.environ.get("TELEGRAM_CHECK_INTERVAL", "3600"))

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    print("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
    print("Running in standby mode.")
    while True:
        time.sleep(86400)


async def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})


async def health_report():
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{API_URL}/health", timeout=10)
            data = r.json()
            return data
        except Exception as e:
            return {"status": "down", "error": str(e)}


async def run():
    last_report_hour = -1
    while True:
        now = datetime.now()
        hour = now.hour

        if hour != last_report_hour and hour in [9, 13, 18, 22]:
            health = await health_report()
            picks = health.get("picks_today", 0)
            model = "loaded" if health.get("model_loaded") else "unavailable"

            msg = (
                f"*TC Pipeline Health* ({now.strftime('%H:%M ET')})\n"
                f"Status: {health.get('status', 'unknown')}\n"
                f"Picks today: {picks}\n"
                f"ML model: {model}\n"
            )
            await send_telegram(msg)
            last_report_hour = hour

        time.sleep(60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
