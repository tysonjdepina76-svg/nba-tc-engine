#!/usr/bin/env python3
import os
import asyncio
import json
from datetime import datetime
import httpx

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
API_URL = os.environ.get("API_URL", "http://api:8000")


async def send_message(text):
    if not TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})


async def check_and_alert():
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{API_URL}/picks/graded")
        if resp.status_code == 200:
            data = resp.json()
            count = data.get("count", 0)
            if count > 0:
                await send_message(f"TC Engine: {count} graded picks in database")


if __name__ == "__main__":
    asyncio.run(check_and_alert())
