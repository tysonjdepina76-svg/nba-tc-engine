"""World Cup roster scraper (Wikipedia 2026 FIFA World Cup squads).

Wikipedia is the most reliable source — ESPN/FBref are both gated.
Caches the full 32-team roster in /tmp/tc_cache for 24h.
"""
import os
import re
import requests
from sources.utils.cache import cache_fetch

CACHE_KEY = "wc_rosters_wiki_2026"
SOURCE_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# Map WC team country names to Wikipedia section IDs
TEAM_IDS = {
    "Argentina": "Argentina", "Australia": "Australia", "Brazil": "Brazil",
    "Canada": "Canada", "Cape Verde": "Cape_Verde", "Colombia": "Colombia",
    "Croatia": "Croatia", "Egypt": "Egypt", "England": "England",
    "France": "France", "Germany": "Germany", "Ghana": "Ghana",
    "Haiti": "Haiti", "Iran": "Iran", "Ivory Coast": "Ivory_Coast",
    "Japan": "Japan", "Mexico": "Mexico", "Morocco": "Morocco",
    "Netherlands": "Netherlands", "New Zealand": "New_Zealand",
    "Nigeria": "Nigeria", "Norway": "Norway", "Poland": "Poland",
    "Portugal": "Portugal", "Qatar": "Qatar", "Saudi Arabia": "Saudi_Arabia",
    "Senegal": "Senegal", "South Korea": "South_Korea", "Spain": "Spain",
    "Sweden": "Sweden", "Switzerland": "Switzerland",
    "Turkey": "Turkey", "United States": "United_States", "Uruguay": "Uruguay",
}


def _scrape_all() -> dict:
    """Fetch Wikipedia page and parse all 32 team rosters."""
    if not os.path.exists("/tmp/wc_squads.html"):
        try:
            r = requests.get(SOURCE_URL, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                with open("/tmp/wc_squads.html", "wb") as f:
                    f.write(r.content)
            else:
                return {}
        except Exception:
            return {}
    with open("/tmp/wc_squads.html", encoding="utf-8") as f:
        html = f.read()
    rosters = {}
    for team, section_id in TEAM_IDS.items():
        m = re.search(
            r'<h3 id="' + re.escape(section_id) + r'"[^>]*>(.*?)<h3 id=|<h3 id="' + re.escape(section_id) + r'"[^>]*>(.*?)<h2 id=',
            html, re.DOTALL,
        )
        if not m:
            continue
        section = m.group(1) or m.group(2)
        tables = re.findall(r'<table[^>]*>.*?</table>', section, re.DOTALL)
        if not tables:
            continue
        players = []
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tables[0], re.DOTALL)
        for row in rows[1:]:  # skip header
            cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row, re.DOTALL)
            if len(cells) < 3:
                continue
            text_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            # Skip header / non-player rows
            if not text_cells[2] or text_cells[2] == "Player":
                continue
            players.append({
                "number": text_cells[0],
                "position": text_cells[1],
                "name": text_cells[2],
            })
        if players:
            rosters[team] = players
    return rosters


def fetch_all_rosters() -> dict:
    """Cached: returns dict of team -> list of {number, position, name}."""
    return cache_fetch(CACHE_KEY, _scrape_all, ttl_hours=24)


def fetch_team_roster(team_name: str) -> list:
    """Get a single team's roster (empty list if unknown team)."""
    rosters = fetch_all_rosters()
    return rosters.get(team_name, [])
