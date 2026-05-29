"""
Yahoo Sports NBA Odds Scraper
Fetches live spread, total, and moneyline lines from Yahoo Sports
and feeds them into the Triple Conservative pipeline.
"""
import re
import json
import urllib.request
from dataclasses import dataclass

YAHOO_ODDS_URL = "https://sports.yahoo.com/nba/odds/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

@dataclass
class GameLine:
    away_team: str
    home_team: str
    spread: float       # positive = home fav (e.g. +7)
    total: float
    away_ml: int
    home_ml: int
    source: str = "Yahoo Sports"

    def __repr__(self):
        return (f"GameLine({self.away_team} @ {self.home_team} | "
                f"SPR: {'+' if self.spread > 0 else ''}{self.spread} | "
                f"U/O: {self.total} | ML: {self.away_ml}/{self.home_ml})")


def fetch_yahoo_html(url: str = YAHOO_ODDS_URL) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_yahoo_odds_page(html: str) -> list[GameLine]:
    """
    Parse Yahoo Sports odds page for NBA game lines.
    Yahoo structures its odds data in JSON blobs inside <script> tags.
    We extract spread, total, and moneyline by regex-matching known patterns.
    """
    games = []

    # Yahoo embeds game data in a JSON-like blob with keys like:
    # "matchups":[...{"awayTeam":{"name":"..."},"homeTeam":{"name":"..."},
    #               "spread":"...","total":"...",...}]
    # Look for script tags containing 'NBA' + 'spread' + 'total' together.
    patterns = [
        # Pattern 1: standard matchup data blocks
        re.compile(
            r'game\s*[:\-]\s*\{[^}]*?(?:spread|total|odds)[^}]*?\}',
            re.IGNORECASE | re.DOTALL
        ),
        # Pattern 2: look for the data in a large JSON blob
        re.compile(
            r'(?:spreads?|totals?|odds)\s*[:=]\s*["\']?([+\-]?\d+\.?\d*)',
            re.IGNORECASE
        ),
    ]

    # Strategy: extract all <script> blocks, find the one with NBA odds data
    script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)

    nba_block = None
    for block in script_blocks:
        if any(kw in block.lower() for kw in ["nba", "basketball", "spread", "total", "odds"]):
            if len(block) > 500 and ("@" in block or "vs" in block.lower()):
                nba_block = block
                break

    if nba_block:
        # Extract spread values
        spread_matches = re.findall(r'(?:spread|Spread)\s*[:=]\s*["\']?([+\-]?\d+\.?\d*)', nba_block)
        total_matches  = re.findall(r'(?:total|Total|U/O|ou)\s*[:=]\s*["\']?(\d+\.?\d*)', nba_block)
        ml_matches     = re.findall(r'(?:ml|moneyline|Moneyline)\s*[:=]?\s*([+\-]?\d+)', nba_block)

        print(f"[DEBUG] Found {len(spread_matches)} spread values: {spread_matches[:6]}")
        print(f"[DEBUG] Found {len(total_matches)} total values: {total_matches[:6]}")
        print(f"[DEBUG] Found {len(ml_matches)} ML values: {ml_matches[:6]}")
        print(f"[DEBUG] NBA block preview (500 chars): {nba_block[:500]}")

    # Alternative: parse team names directly from HTML
    teams_found = re.findall(
        r'alt="([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s*(?:LOGO|logo|image)"',
        html
    )
    # Deduplicate
    seen = set()
    uniq_teams = []
    for t in teams_found:
        if t not in seen and len(t) > 2:
            seen.add(t)
            uniq_teams.append(t)

    print(f"[DEBUG] Teams found in page: {uniq_teams}")

    return games


def parse_from_scoreboard(html: str) -> list[GameLine]:
    """
    Parse the Yahoo Sports scoreboard page which has cleaner structured data.
    The scoreboard at /nba/scoreboard/ shows game cards with odds embedded.
    """
    games = []

    # Extract game matchup blocks — each game card has data with team abbreviations
    # e.g. "PHI", "NY", "MIN", "SA", "OKC", "PHX"
    team_pattern = re.compile(r'\b([A-Z]{2,3})\b')
    number_pattern = re.compile(
        r'(?:[+\-]?\d+\.?\d*)\s*(?:spread|SPR|spr)\b|'
        r'\b(?:[+\-]?\d+\.?\d*)\s*(?:total|U/O|ou)\b|'
        r'\b\d+\.?\d*\s*(?:over|under|O/U)\b',
        re.IGNORECASE
    )

    # Look for structured data in <script> tags
    json_scripts = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    for script in json_scripts:
        try:
            data = json.loads(script)
            if isinstance(data, dict):
                if "name" in data and ("NBA" in str(data.get("name","")) or "game" in str(data.get("name","")).lower()):
                    print(f"[DEBUG] JSON-LD: {json.dumps(data, indent=2)[:1000]}")
        except:
            pass

    # Also look for all script tags with game data
    all_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    for script in all_scripts:
        if len(script) > 1000 and ("spread" in script.lower() or "total" in script.lower()):
            # Extract team abbreviations (2-3 letter codes)
            teams = re.findall(r'\b([A-Z]{2,3})\b', script)
            # Extract numbers that look like odds
            numbers = re.findall(r'\b([+\-]?\d{1,3})\b', script)
            if len(teams) >= 4 and len(numbers) > 4:
                print(f"[DEBUG] Large script with {len(teams)} team refs, {len(numbers)} number refs")
                print(f"[DEBUG] Teams sample: {teams[:20]}")
                print(f"[DEBUG] Numbers sample: {numbers[:30]}")
                break

    return games


def scrape_yahoo() -> list[GameLine]:
    """Main entry point — fetch Yahoo Sports odds and parse."""
    print("Fetching Yahoo Sports NBA odds...")
    html = fetch_yahoo_html()

    print("Parsing from scoreboard structure...")
    games = parse_from_scoreboard(html)

    if not games:
        print("Trying alternate parse...")
        games = parse_yahoo_odds_page(html)

    print(f"\nTotal games found: {len(games)}")
    for g in games:
        print(f"  {g}")

    return games


if __name__ == "__main__":
    scrape_yahoo()
