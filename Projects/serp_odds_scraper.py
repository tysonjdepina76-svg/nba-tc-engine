#!/usr/bin/env python3
"""SerpAPI-powered odds scraper — replaces dead Odds API (Business tier maxed).
   
Serp_Api_key exists in environment. This module searches Google for sports
player props odds pages and returns structured results.
"""

import os, json, sys
from serpapi import GoogleSearch

SERPAPI_KEY = os.environ.get("Serp_Api_key", "")

def search_odds(query: str, num_results: int = 10) -> list:
    """Search Google for sports odds via SerpAPI. Returns organic results."""
    if not SERPAPI_KEY:
        print("ERROR: Serp_Api_key not found", file=sys.stderr)
        return []
    params = {"q": query, "api_key": SERPAPI_KEY, "num": num_results, "engine": "google"}
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
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
