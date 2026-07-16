"""deepseek_enhancer.py — Enhance TC projections with Zo's built-in DeepSeek V4 Pro.

Uses Zo's /zo/ask API (no separate API key needed — Zo provides DeepSeek V4 Pro natively).
Generates natural-language reasoning for picks.
Falls back to TC-math reasoning when the API is unavailable.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List

import requests

from src.utils.logging import setup_logging

logger = setup_logging("deepseek_enhancer")

ZO_ASK_URL = "https://api.zo.computer/zo/ask"
ZO_TOKEN = os.getenv("ZO_CLIENT_IDENTITY_TOKEN", "")

REASONING_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_MAX_SIZE = 500


def _tc_fallback_reason(
    player: str,
    stat: str,
    tc_projection: float,
    market_line: float,
    edge: float,
    sport: str,
) -> str:
    """Generate a data-driven fallback reason using TC math only (no API call)."""
    direction = "OVER" if edge > 0 else "UNDER"
    gap = abs(tc_projection - market_line)

    if sport.upper() in ("WNBA", "NBA"):
        if stat in ("PTS", "AST", "REB"):
            return (
                f"TC projects {player} at {tc_projection:.1f} {stat} — "
                f"{gap:.1f} {direction} the {market_line:.1f} line "
                f"(edge {edge:+.1f}%, matchup-adjusted)"
            )
        elif stat in ("3PM", "STL", "BLK"):
            return (
                f"TC projects {player} at {tc_projection:.1f} {stat} — "
                f"{direction} {market_line:.1f} (edge {edge:+.1f}%, role-weighted)"
            )
        else:
            return (
                f"TC projects {player} at {tc_projection:.1f} {stat} — "
                f"{direction} line {market_line:.1f} (edge {edge:+.1f}%)"
            )
    elif sport.upper() == "MLB":
        return (
            f"TC projects {player} at {tc_projection:.1f} {stat} — "
            f"{direction} line {market_line:.1f} (edge {edge:+.1f}%)"
        )
    else:
        return (
            f"TC edge {edge:+.1f}% on {player} {stat} "
            f"(proj {tc_projection:.1f} vs line {market_line:.1f})"
        )


def _call_zo_deepseek(prompt: str) -> str | None:
    """Call Zo's built-in DeepSeek V4 Pro. Returns None on failure."""
    if not ZO_TOKEN:
        return None

    try:
        resp = requests.post(
            ZO_ASK_URL,
            headers={
                "authorization": ZO_TOKEN,
                "content-type": "application/json",
            },
            json={
                "input": prompt,
                "model_name": "vercel:deepseek/deepseek-v4-pro",
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("output", "").strip()
        else:
            logger.warning(f"Zo /zo/ask returned {resp.status_code}: {resp.text[:200]}")
            return None
    except requests.RequestException as e:
        logger.error(f"Zo /zo/ask request failed: {e}")
        return None


def enhance_pick(
    player: str,
    stat: str,
    tc_projection: float,
    market_line: float,
    edge: float,
    sport: str,
    team: str = "",
) -> str:
    """Generate a short reasoning sentence for a pick using Zo DeepSeek V4 Pro.

    Falls back to TC-math reasoning when the API is unavailable.
    """
    tc_projection = float(tc_projection)
    market_line = float(market_line)
    edge = float(edge)
    sport = str(sport)

    cache_key = f"{player}:{stat}:{sport}:{tc_projection:.1f}:{market_line:.1f}"
    if cache_key in REASONING_CACHE:
        return REASONING_CACHE[cache_key]["reason"]

    direction = "OVER" if edge > 0 else "UNDER"

    prompt = (
        f"Given this sports betting projection:\n"
        f"- Player: {player} ({team})\n"
        f"- Sport: {sport}\n"
        f"- Stat: {stat}\n"
        f"- Book line: {market_line:.1f}\n"
        f"- TC projection: {tc_projection:.1f}\n"
        f"- Edge: {edge:+.1f}%\n\n"
        f"Write ONE short sentence (max 100 chars) explaining why this player "
        f"might go {direction} the line. Be specific and data-driven. No fluff."
    )

    reason = _call_zo_deepseek(prompt)

    if reason:
        REASONING_CACHE[cache_key] = {"reason": reason, "ts": time.time()}
        _prune_cache()
        return reason

    fallback = _tc_fallback_reason(player, stat, tc_projection, market_line, edge, sport)
    REASONING_CACHE[cache_key] = {"reason": fallback, "ts": time.time()}
    _prune_cache()
    return fallback


def _prune_cache() -> None:
    """Keep the reasoning cache at a manageable size."""
    if len(REASONING_CACHE) > CACHE_MAX_SIZE:
        sorted_keys = sorted(
            REASONING_CACHE.keys(),
            key=lambda k: REASONING_CACHE[k].get("ts", 0),
        )
        for old_key in sorted_keys[: len(sorted_keys) // 2]:
            REASONING_CACHE.pop(old_key, None)


def enhance_picks_batch(
    picks: List[Dict[str, Any]],
    max_concurrent: int = 5,
) -> List[Dict[str, Any]]:
    """Add DeepSeek reasoning to a batch of picks (sequential for rate limits)."""
    enhanced = []
    for pick in picks:
        reason = enhance_pick(
            player=pick.get("player", pick.get("name", "")),
            stat=pick.get("stat", pick.get("prop", "PTS")),
            tc_projection=float(pick.get("tc_projection", pick.get("projection", 0))),
            market_line=float(pick.get("market_line", pick.get("line", 0))),
            edge=float(pick.get("edge", 0)),
            sport=pick.get("sport", "WNBA"),
            team=pick.get("team", ""),
        )
        enhanced.append({**pick, "reason": reason})
        time.sleep(0.2)
    return enhanced
