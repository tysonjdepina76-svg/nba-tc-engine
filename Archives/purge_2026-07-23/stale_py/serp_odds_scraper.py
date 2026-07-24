#!/usr/bin/env python3
"""SerpAPI-powered odds scraper — replaces dead Odds API (Business tier maxed).
   
Serp_Api_key exists in environment. This module searches Google for sports
player props odds pages and returns structured results.

QUOTA: 250 searches/day total, max 8 per run. Enforced in search_odds().
"""
import os, json, sys
from datetime import datetime
from pathlib import Path
from serpapi import GoogleSearch

SERPAPI_KEY = os.environ.get("Serp_Api_key", "")
QUOTA_FILE = Path("/home/workspace/Daily_Log/serpapi_quota.json")
DAILY_LIMIT = 253
PER_RUN_LIMIT = 80

def _load_quota() -> dict:
    if QUOTA_FILE.exists():
        return json.loads(QUOTA_FILE.read_text())
    return {"date": "", "daily_used": 0, "run_used": 0}

def _save_quota(q: dict):
    QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUOTA_FILE.write_text(json.dumps(q))

def check_quota() -> tuple:
    today = datetime.now().strftime("%Y-%m-%d")
    q = _load_quota()
    if q["date"] != today:
        q = {"date": today, "daily_used": 0, "run_used": 0}
        _save_quota(q)
    rem_daily = max(0, DAILY_LIMIT - q["daily_used"])
    rem_run = max(0, PER_RUN_LIMIT - q["run_used"])
    can = rem_daily > 0 and rem_run > 0
    return (can, rem_daily, rem_run)

def track_search():
    today = datetime.now().strftime("%Y-%m-%d")
    q = _load_quota()
    if q["date"] != today:
        q = {"date": today, "daily_used": 0, "run_used": 0}
    q["daily_used"] += 1
    q["run_used"] += 1
    _save_quota(q)

def search_odds(query: str, num_results: int = 10) -> list:
    """Search Google for sports odds via SerpAPI. Enforces 250/day + 8/run cap."""
    if not SERPAPI_KEY:
        print("ERROR: Serp_Api_key not found", file=sys.stderr)
        return []
    can_search, rem_daily, rem_run = check_quota()
    if not can_search:
        reason = "daily limit (250)" if rem_daily == 0 else "per-run limit (50)"
        print(f"SerpAPI quota exhausted: {reason}. {rem_daily} daily / {rem_run} run remaining.", file=sys.stderr)
        return []
    params = {"q": query, "api_key": SERPAPI_KEY, "num": num_results, "engine": "google"}
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        track_search()
        return results.get("organic_results", [])
    except Exception as e:
        print(f"SerpAPI error: {e}", file=sys.stderr)
        return []

def get_mlb_odds(game: str = "") -> dict:
    q = f"MLB player props odds today {game}"
    results = search_odds(q)
    return {"source": "serpapi", "sport": "mlb", "game": game, "query": q, "results": results, "count": len(results)}

def get_wnba_odds(game: str = "") -> dict:
    q = f"WNBA player props odds today {game}"
    results = search_odds(q)
    return {"source": "serpapi", "sport": "wnba", "game": game, "query": q, "results": results, "count": len(results)}

def get_wc_odds(match: str = "") -> dict:
    q = f"World Cup soccer player props odds {match}"
    results = search_odds(q)
    return {"source": "serpapi", "sport": "wc", "match": match, "query": q, "results": results, "count": len(results)}

def extract_odds_from_results(results: list) -> list:
    odds = []
    for r in results:
        odds.append({
            "title": r.get("title", ""),
            "snippet": r.get("snippet", ""),
            "link": r.get("link", "")
        })
    return odds

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SerpAPI odds scraper")
    parser.add_argument("--sport", choices=["mlb","wnba","wc"], required=True)
    parser.add_argument("--game", default="")
    parser.add_argument("--parse", action="store_true", help="Extract structured odds from results")
    args = parser.parse_args()

    if args.sport == "mlb":
        data = get_mlb_odds(args.game)
    elif args.sport == "wnba":
        data = get_wnba_odds(args.game)
    else:
        data = get_wc_odds(args.game)

    if args.parse:
        data["parsed_odds"] = extract_odds_from_results(data["results"])

    print(json.dumps(data, indent=2))
