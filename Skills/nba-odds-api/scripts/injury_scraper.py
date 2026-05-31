#!/usr/bin/env python3
"""
Injury Report Scraper
Scrapes live injury data for NBA and WNBA from multiple sources.
Tyson Depina | Zo Computer

Usage:
  python3 injury_scraper.py --sport NBA --team NYK
  python3 injury_scraper.py --sport NBA --all
  python3 injury_scraper.py --sport WNBA --all
"""

import requests
import json
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# ── CONFIG ──────────────────────────────────────────────────────────────────
NBA_TEAMS = ["ATL","BOS","BKN","CHA","CHI","CLE","DAL","DEN","DET","GSW",
             "HOU","IND","LAC","LAL","MEM","MIA","MIL","MIN","NOP","NYK",
             "OKC","ORL","PHI","PHX","POR","SAC","SAS","TOR","UTA","WAS"]

WNBA_TEAMS = ["ATL","CHI","CON","DAL","GS","IND","LV","LA","MIN","NY",
              "PHX","POR","SEA","TOR","WSH"]

# Team name mapping: abbreviation → common search name
TEAM_SEARCH_NAMES = {
    "NYK": "New York Knicks", "BKN": "Brooklyn Nets", "BOS": "Boston Celtics",
    "LAL": "Los Angeles Lakers", "GSW": "Golden State Warriors", "LAC": "LA Clippers",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "CHI": "Chicago Bulls",
    "DAL": "Dallas Mavericks", "PHX": "Phoenix Suns", "PHI": "Philadelphia 76ers",
    "DEN": "Denver Nuggets", "CLE": "Cleveland Cavaliers", "BOS": "Boston Celtics",
    "OKC": "Oklahoma City Thunder", "SAS": "San Antonio Spurs", "HOU": "Houston Rockets",
    "ATL": "Atlanta Hawks", "CHA": "Charlotte Hornets", "IND": "Indiana Pacers",
    "MEM": "Memphis Grizzlies", "NOP": "New Orleans Pelicans", "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings", "TOR": "Toronto Raptors", "UTA": "Utah Jazz",
    "WAS": "Washington Wizards", "MIN": "Minnesota Timberwolves", "ORL": "Orlando Magic",
    "DET": "Detroit Pistons", "P": "Probable", "Q": "Questionable",
    "D": "Out", "O": "Out", "GTD": "Questionable"
}

WNBA_SEARCH_NAMES = {
    "NY": "New York Liberty", "LA": "Los Angeles Sparks", "LV": "Las Vegas Aces",
    "GS": "Golden State Warriors", "CON": "Connecticut Sun", "DAL": "Dallas Wings",
    "IND": "Indiana Fever", "CHI": "Chicago Sky", "MIN": "Minnesota Lynx",
    "ATL": "Atlanta Dream", "PHX": "Phoenix Mercury", "POR": "Portland",
    "SEA": "Seattle Storm", "TOR": "Toronto", "WSH": "Washington Mystics"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

CACHE_TTL_SECONDS = 600  # 10 minutes


# ── INJURY STATUS LOOKUP ─────────────────────────────────────────────────────
def parse_status(raw: str) -> tuple[str, str]:
    """Returns (status_code, status_label)."""
    raw = str(raw).upper().strip()
    if re.search(r"\b(OUT|DTD|DOUBTFUL|DISMISSED|NOT PLAYING)\b", raw):
        return "OUT", "OUT"
    if re.search(r"\b(Q|QUESTIONABLE|UNCERTAIN|DOUBTFUL|LIKELY OUT)\b", raw):
        return "Q", "Questionable"
    if re.search(r"\b(P|PROBABLE|HIGHLY LIKELY|EXPECTED)\b", raw):
        return "P", "Probable"
    if re.search(r"\b(GTD|GAME TIME DECISION)\b", raw):
        return "GTD", "Game-Time Decision"
    return "U", "Unknown"


# ── SOURCE 1: ESPN API ──────────────────────────────────────────────────────
def scrape_espn_injuries(sport: str = "NBA") -> List[Dict]:
    """Primary source — ESPN injury API."""
    sport_code = "nba" if sport == "NBA" else "wnba"
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_code}/injuries"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return [{"error": str(e), "source": "ESPN"}]

    injuries = []
    for team_group in data.get("children", []):
        for team in team_group.get("teams", []):
            team_abbr = team.get("abbreviation", "")
            team_name = team.get("displayName", "")
            for athlete in team.get("athletes", []):
                injuries.append({
                    "name": athlete.get("fullName", ""),
                    "position": athlete.get("position", {}).get("abbreviation", ""),
                    "injury": athlete.get("injury", {}).get("description", ""),
                    "status": athlete.get("injury", {}).get("status", ""),
                    "status_code": parse_status(athlete.get("injury", {}).get("status", ""))[0],
                    "team_abbr": team_abbr,
                    "team_name": team_name,
                    "source": "ESPN",
                    "updated": athlete.get("injury", {}).get("date", ""),
                })
    return injuries


# ── SOURCE 2: SPORTS-REFERENCE ───────────────────────────────────────────────
def scrape_sports_reference_injuries(team_abbr: str, sport: str = "NBA") -> List[Dict]:
    """Secondary source — Sports Reference scrape."""
    sr_teams = {
        "NBA": {"NYK": "new-york-knicks", "BKN": "brooklyn-nets", "BOS": "boston-celtics",
                "LAL": "los-angeles-lakers", "GSW": "golden-state-warriors", "CHI": "chicago-bulls",
                "MIA": "miami-heat", "MIL": "milwaukee-bucks", "DAL": "dallas-mavericks",
                "PHX": "phoenix-suns", "PHI": "philadelphia-76ers", "DEN": "denver-nuggets",
                "CLE": "cleveland-cavaliers", "OKC": "oklahoma-city-thunder", "SAS": "san-antonio-spurs"},
        "WNBA": {"NY": "new-york-liberty", "LA": "los-angeles-sparks", "LV": "las-vegas-aces",
                 "GS": "golden-state-valley", "CON": "connecticut-sun", "MIN": "minnesota-lynx",
                 "IND": "indiana-fever", "CHI": "chicago-sky", "DAL": "dallas-wings",
                 "ATL": "atlanta-dream", "PHX": "phoenix-mercury", "SEA": "seattle-storm"}
    }
    slug = sr_teams.get(sport, {}).get(team_abbr)
    if not slug:
        return []
    url = f"https://www.basketball-reference.com/teams/{sport}/{slug}.html"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception:
        return []
    injuries = []
    # Parse roster table for injury notes
    import re
    # Look for injury designations in roster table (HTML parsing simplified)
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', resp.text, re.DOTALL)
    for row in rows:
        name_match = re.search(r'data-append-csv="(\w+)"[^>]*>([^<]+)<', row)
        injury_match = re.search(r'class="tooltip"[^>]*>([^<]+)</span>', row)
        if injury_match and name_match:
            injuries.append({
                "name": name_match.group(2).strip(),
                "team_abbr": team_abbr,
                "injury": injury_match.group(1).strip(),
                "status": "Unknown",
                "status_code": "U",
                "source": "Basketball Reference",
            })
    return injuries


# ── SOURCE 3: ODDS API INJURY FEED ──────────────────────────────────────────
def fetch_odds_api_injuries(api_key: str, sport: str = "basketball_nba") -> List[Dict]:
    """The Odds API also provides injury data (premium)."""
    if not api_key:
        return []
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/injuries"
    params = {"apiKey": api_key}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return [{"name": i.get("name"), "team": i.get("team"),
                     "description": i.get("description"), "status": i.get("status"),
                     "status_code": parse_status(i.get("status", ""))[0],
                     "source": "Odds API"} for i in data]
    except Exception:
        pass
    return []


# ── CACHE LAYER ──────────────────────────────────────────────────────────────
_injury_cache: Dict[str, tuple[List[Dict], float]] = {}

def get_injuries(sport: str, team_abbr: str = None, use_cache: bool = True) -> List[Dict]:
    """Aggregate injury data from all sources with 10-min cache."""
    cache_key = f"{sport}:{team_abbr or 'ALL'}"
    now = time.time()

    if use_cache and cache_key in _injury_cache:
        data, cached_at = _injury_cache[cache_key]
        if now - cached_at < CACHE_TTL_SECONDS:
            return data

    all_injuries: List[Dict] = []

    # Source 1: ESPN (fastest, most complete)
    espn = scrape_espn_injuries(sport)
    if "error" not in espn[0]:
        all_injuries.extend(espn)

    # Source 2: Sports Reference (team-specific backup)
    if team_abbr:
        sr = scrape_sports_reference_injuries(team_abbr, sport)
        all_injuries.extend(sr)

    # Source 3: Odds API (optional premium)
    odds_key = __import__("os").getenv("ODDS_API_KEY", "")
    sport_code = "basketball_nba" if sport == "NBA" else "basketball_wnba"
    odds = fetch_odds_api_injuries(odds_key, sport_code)
    all_injuries.extend(odds)

    # Deduplicate by name + team
    seen = set()
    deduped = []
    for inj in all_injuries:
        key = (inj.get("name", ""), inj.get("team_abbr", ""))
        if key not in seen and inj.get("name"):
            seen.add(key)
            deduped.append(inj)

    _injury_cache[cache_key] = (deduped, now)
    return deduped


# ── FILTER & FORMAT ───────────────────────────────────────────────────────────
def filter_by_status(injuries: List[Dict], status_filter: str = "ALL") -> List[Dict]:
    if status_filter == "ALL":
        return injuries
    return [i for i in injuries if i.get("status_code", "").upper() == status_filter.upper()]


def get_team_injuries(team_abbr: str, sport: str = "NBA") -> List[Dict]:
    all_inj = get_injuries(sport, team_abbr)
    return [i for i in all_inj if i.get("team_abbr", "").upper() == team_abbr.upper()]


def format_injury_report(injuries: List[Dict], sport: str, team_abbr: str = None) -> str:
    if not injuries:
        return f"✅ No injuries reported for {team_abbr or sport}."

    out = []
    team_name = team_abbr or sport
    out.append(f"🏥 {team_name} INJURY REPORT")
    out.append(f"   Updated: {datetime.now().strftime('%I:%M %p ET')}")
    out.append("")

    # Group by status
    by_status = {"OUT": [], "Q": [], "P": [], "GTD": [], "U": []}
    for inj in injuries:
        code = inj.get("status_code", "U")
        by_status.setdefault(code, []).append(inj)

    label_map = {"OUT": "❌ OUT", "Q": "⚠️ QUESTIONABLE", "P": "✅ PROBABLE",
                 "GTD": "⏳ GAME-TIME DECISION", "U": "❓ UNKNOWN"}

    for code, label in label_map.items():
        items = by_status.get(code, [])
        if items:
            out.append(f"  {label}")
            for i in items:
                injury_desc = i.get("injury", "") or i.get("description", "")
                pos = i.get("position", "")
                pos_str = f" ({pos})" if pos else ""
                injury_str = f" — {injury_desc}" if injury_desc else ""
                out.append(f"    • {i.get('name', 'Unknown')}{pos_str}{injury_str}")
            out.append("")

    return "\n".join(out).strip()


# ── CLI ──────────────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="NBA/WNBA Injury Report Scraper")
    parser.add_argument("--sport", choices=["NBA", "WNBA"], default="NBA")
    parser.add_argument("--team", default=None, help="Team abbreviation (e.g. NYK)")
    parser.add_argument("--all", action="store_true", help="All teams")
    parser.add_argument("--status", default="ALL", help="Filter: OUT, Q, P, GTD")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--cache-bust", action="store_true", help="Skip cache")
    args = parser.parse_args()

    sport = args.sport
    teams = [args.team.upper()] if args.team else (NBA_TEAMS if sport == "NBA" else WNBA_TEAMS)

    all_results = []
    for team in teams:
        injuries = get_injuries(sport, team, use_cache=not args.cache_bust)
        injuries = filter_by_status(injuries, args.status)
        if args.json:
            all_results.append({"team": team, "sport": sport, "injuries": injuries})
        else:
            print(format_injury_report(injuries, sport, team))
            print()

    if args.json:
        print(json.dumps(all_results, indent=2))


if __name__ == "__main__":
    main()