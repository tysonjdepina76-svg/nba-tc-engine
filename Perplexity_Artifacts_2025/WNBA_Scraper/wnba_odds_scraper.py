#!/usr/bin/env python3
"""
WNBA Odds Scraper - All 11 Books
Endpoints: DK, FD, MGM, Caesars, BetRivers, Fanatics, Bovada, BetUS, BetOnline, LowVig, MyBookie
"""

import json
import time
import random
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WNBAOddsScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json'})
        self.results = {}
        self.today = datetime.now().strftime("%Y-%m-%d")

        # 11 books with their endpoints
        self.books = {
            'DraftKings': {
                'url': f'https://sportsbook.draftkings.com/leagues/basketball/wnba?startDate={self.today}',
                'type': 'api'
            },
            'FanDuel': {
                'url': f'https://www.fanduel.com/api/odds/v1/wnba/events?date={self.today}',
                'type': 'api'
            },
            'BetMGM': {
                'url': f'https://sports.ny.betmgm.com/api/v1/events?league=WNBA&date={self.today}',
                'type': 'api'
            },
            'Caesars': {
                'url': f'https://www.caesars.com/sportsbook/api/v1/events?league=WNBA&date={self.today}',
                'type': 'api'
            },
            'BetRivers': {
                'url': f'https://www.betrivers.com/api/sportsbook/odds?league=wnba&date={self.today}',
                'type': 'api'
            },
            'Fanatics': {
                'url': f'https://www.fanatics.com/api/sportsbook/wnba/odds?date={self.today}',
                'type': 'html'
            },
            'Bovada': {
                'url': f'https://www.bovada.lv/services/sports/event/v2/events/description?leagueId=31&date={self.today}',
                'type': 'api'
            },
            'BetUS': {
                'url': f'https://www.betus.com/api/sportsbook/odds?league=WNBA&date={self.today}',
                'type': 'html'
            },
            'BetOnline': {
                'url': f'https://www.betonline.ag/api/sportsbook/wnba/odds?date={self.today}',
                'type': 'api'
            },
            'LowVig': {
                'url': f'https://www.lowvig.com/api/odds/wnba?date={self.today}',
                'type': 'api'
            },
            'MyBookie': {
                'url': f'https://www.mybookie.ag/api/sportsbook/wnba/odds?date={self.today}',
                'type': 'selenium'
            }
        }

    def get_headers(self):
        """Generate rotating headers"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }

    def fetch_api(self, url, retries=3):
        """Fetch API endpoint with retry logic"""
        for attempt in range(retries):
            try:
                headers = self.get_headers()
                response = self.session.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    return response.json() if 'application/json' in response.headers.get('Content-Type', '') else response.text
                elif response.status_code == 403:
                    logger.warning(f"Rate limited on {url}, waiting 5s...")
                    time.sleep(5)
                    continue
                else:
                    logger.warning(f"Status {response.status_code} on {url}")
                    time.sleep(2)
            except Exception as e:
                logger.error(f"Attempt {attempt+1} failed for {url}: {str(e)}")
                time.sleep(3)
        return None

    def fetch_html(self, url):
        """Fetch HTML with rotating proxies"""
        try:
            headers = self.get_headers()
            response = self.session.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                return BeautifulSoup(response.text, 'html.parser')
            return None
        except Exception as e:
            logger.error(f"HTML fetch failed for {url}: {str(e)}")
            return None

    def fetch_selenium(self, url):
        """Fetch with Selenium for JavaScript-rendered content"""
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument(f'user-agent={self.ua.random}')

            driver = webdriver.Chrome(options=options)
            driver.get(url)

            # Wait for odds to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "event"))
            )

            html = driver.page_source
            driver.quit()
            return BeautifulSoup(html, 'html.parser')
        except Exception as e:
            logger.error(f"Selenium failed for {url}: {str(e)}")
            return None

    def parse_draftkings(self, data):
        """Parse DraftKings API response"""
        games = []
        try:
            if isinstance(data, dict) and 'events' in data:
                for event in data['events']:
                    if event.get('status') == 'Scheduled':
                        games.append({
                            'home': event.get('home', ''),
                            'away': event.get('away', ''),
                            'spread': event.get('spread', {}),
                            'moneyline': event.get('moneyline', {}),
                            'total': event.get('overUnder', {})
                        })
        except Exception as e:
            logger.error(f"DK parse error: {str(e)}")
        return games

    def parse_fanduel(self, data):
        """Parse FanDuel API response"""
        games = []
        try:
            if isinstance(data, dict) and 'events' in data:
                for event in data['events']:
                    games.append({
                        'home': event.get('homeTeam', ''),
                        'away': event.get('awayTeam', ''),
                        'spread': event.get('spread', {}),
                        'moneyline': event.get('moneyline', {}),
                        'total': event.get('total', {})
                    })
        except Exception as e:
            logger.error(f"FD parse error: {str(e)}")
        return games

    def parse_betmgm(self, data):
        """Parse BetMGM API response"""
        games = []
        try:
            if isinstance(data, dict) and 'events' in data:
                for event in data['events']:
                    games.append({
                        'home': event.get('homeTeam', ''),
                        'away': event.get('awayTeam', ''),
                        'spread': event.get('spread', {}),
                        'moneyline': event.get('moneyline', {}),
                        'total': event.get('overUnder', {})
                    })
        except Exception as e:
            logger.error(f"MGM parse error: {str(e)}")
        return games

    def parse_caesars(self, data):
        """Parse Caesars API response"""
        games = []
        try:
            if isinstance(data, dict) and 'data' in data:
                for event in data['data'].get('events', []):
                    games.append({
                        'home': event.get('homeTeam', ''),
                        'away': event.get('awayTeam', ''),
                        'spread': event.get('spread', {}),
                        'moneyline': event.get('moneyline', {}),
                        'total': event.get('total', {})
                    })
        except Exception as e:
            logger.error(f"Caesars parse error: {str(e)}")
        return games

    def parse_betrivers(self, data):
        """Parse BetRivers API response"""
        games = []
        try:
            if isinstance(data, dict) and 'events' in data:
                for event in data['events']:
                    games.append({
                        'home': event.get('homeTeam', ''),
                        'away': event.get('awayTeam', ''),
                        'spread': event.get('pointSpread', {}),
                        'moneyline': event.get('moneyline', {}),
                        'total': event.get('overUnder', {})
                    })
        except Exception as e:
            logger.error(f"BetRivers parse error: {str(e)}")
        return games

    def parse_fanatics_html(self, soup):
        """Parse Fanatics HTML"""
        games = []
        try:
            if soup:
                for event in soup.find_all('div', class_='event-card'):
                    try:
                        teams = event.find_all('span', class_='team-name')
                        home = teams[1].text.strip() if len(teams) > 1 else ''
                        away = teams[0].text.strip() if teams else ''

                        odds = event.find_all('div', class_='odds')
                        games.append({
                            'home': home,
                            'away': away,
                            'spread': {'value': odds[1].text.strip() if len(odds) > 1 else ''},
                            'moneyline': {'home': odds[3].text.strip() if len(odds) > 3 else '', 'away': odds[2].text.strip() if len(odds) > 2 else ''},
                            'total': {'value': odds[4].text.strip() if len(odds) > 4 else ''}
                        })
                    except Exception as e:
                        logger.error(f"Fanatics event parse error: {str(e)}")
        except Exception as e:
            logger.error(f"Fanatics parse error: {str(e)}")
        return games

    def parse_bovada(self, data):
        """Parse Bovada API response"""
        games = []
        try:
            if isinstance(data, list):
                for event in data:
                    try:
                        comps = event.get('competitors', [])
                        home = ''
                        away = ''
                        for c in comps:
                            if c.get('home') is True:
                                home = c.get('name', '')
                            else:
                                away = c.get('name', '')

                        games.append({
                            'home': home,
                            'away': away,
                            'spread': event.get('spread', {}),
                            'moneyline': event.get('moneyline', {}),
                            'total': event.get('total', {})
                        })
                    except Exception as e:
                        logger.error(f"Bovada event parse error: {str(e)}")
        except Exception as e:
            logger.error(f"Bovada parse error: {str(e)}")
        return games

    def parse_betus_html(self, soup):
        """Parse BetUS HTML"""
        games = []
        try:
            if soup:
                for event in soup.find_all('div', class_='game-line'):
                    try:
                        teams = event.find_all('span', class_='team')
                        home = teams[1].text.strip() if len(teams) > 1 else ''
                        away = teams[0].text.strip() if teams else ''

                        spread = event.find('span', class_='spread-val')
                        ml = event.find_all('span', class_='ml-val')
                        total = event.find('span', class_='total-val')

                        games.append({
                            'home': home,
                            'away': away,
                            'spread': {'value': spread.text.strip() if spread else ''},
                            'moneyline': {'home': ml[1].text.strip() if len(ml) > 1 else '', 'away': ml[0].text.strip() if ml else ''},
                            'total': {'value': total.text.strip() if total else ''}
                        })
                    except Exception as e:
                        logger.error(f"BetUS event parse error: {str(e)}")
        except Exception as e:
            logger.error(f"BetUS parse error: {str(e)}")
        return games

    def parse_betonline(self, data):
        """Parse BetOnline API response"""
        games = []
        try:
            if isinstance(data, dict) and 'events' in data:
                for event in data['events']:
                    games.append({
                        'home': event.get('homeTeam', ''),
                        'away': event.get('awayTeam', ''),
                        'spread': event.get('spread', {}),
                        'moneyline': event.get('moneyline', {}),
                        'total': event.get('overUnder', {})
                    })
        except Exception as e:
            logger.error(f"BetOnline parse error: {str(e)}")
        return games

    def parse_lowvig(self, data):
        """Parse LowVig API response"""
        games = []
        try:
            if isinstance(data, dict) and 'events' in data:
                for event in data['events']:
                    games.append({
                        'home': event.get('home_team', ''),
                        'away': event.get('away_team', ''),
                        'spread': event.get('spread', {}),
                        'moneyline': event.get('moneyline', {}),
                        'total': event.get('total', {})
                    })
        except Exception as e:
            logger.error(f"LowVig parse error: {str(e)}")
        return games

    def parse_mybookie_selenium(self, soup):
        """Parse MyBookie Selenium-rendered content"""
        games = []
        try:
            if soup:
                for event in soup.find_all('div', class_='event'):
                    try:
                        teams = event.find_all('div', class_='team-name')
                        home = teams[1].text.strip() if len(teams) > 1 else ''
                        away = teams[0].text.strip() if teams else ''

                        odds_blocks = event.find_all('div', class_='odds-cell')
                        games.append({
                            'home': home,
                            'away': away,
                            'spread': {'value': odds_blocks[0].text.strip() if odds_blocks else ''},
                            'moneyline': {'home': odds_blocks[2].text.strip() if len(odds_blocks) > 2 else '', 'away': odds_blocks[1].text.strip() if len(odds_blocks) > 1 else ''},
                            'total': {'value': odds_blocks[3].text.strip() if len(odds_blocks) > 3 else ''}
                        })
                    except Exception as e:
                        logger.error(f"MyBookie event parse error: {str(e)}")
        except Exception as e:
            logger.error(f"MyBookie parse error: {str(e)}")
        return games

    def scrape_all_books(self):
        """Scrape all 11 books"""
        logger.info("Starting WNBA odds scrape across 11 books...")

        parsers = {
            'DraftKings': (self.fetch_api, self.parse_draftkings),
            'FanDuel': (self.fetch_api, self.parse_fanduel),
            'BetMGM': (self.fetch_api, self.parse_betmgm),
            'Caesars': (self.fetch_api, self.parse_caesars),
            'BetRivers': (self.fetch_api, self.parse_betrivers),
            'Fanatics': (self.fetch_html, self.parse_fanatics_html),
            'Bovada': (self.fetch_api, self.parse_bovada),
            'BetUS': (self.fetch_html, self.parse_betus_html),
            'BetOnline': (self.fetch_api, self.parse_betonline),
            'LowVig': (self.fetch_api, self.parse_lowvig),
            'MyBookie': (self.fetch_selenium, self.parse_mybookie_selenium)
        }

        for book_name, config in self.books.items():
            logger.info(f"Scraping {book_name}...")
            fetcher, parser = parsers[book_name]

            try:
                data = fetcher(config['url'])
                if data:
                    games = parser(data)
                    self.results[book_name] = {
                        'success': True,
                        'game_count': len(games),
                        'games': games
                    }
                    logger.info(f"{book_name}: {len(games)} games found")
                else:
                    self.results[book_name] = {
                        'success': False,
                        'error': 'No data returned'
                    }
                    logger.warning(f"{book_name}: No data returned")
            except Exception as e:
                self.results[book_name] = {
                    'success': False,
                    'error': str(e)
                }
                logger.error(f"{book_name} failed: {str(e)}")

            time.sleep(random.uniform(1, 3))

        return self.results

    def save_results(self, output_path=None):
        """Save results to JSON file"""
        if output_path is None:
            output_path = f'/home/workspace/Daily_Log/{self.today}/wnba_odds_all_books.json'

        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        output = {
            'date': self.today,
            'scrape_time': datetime.now().isoformat(),
            'books_count': len(self.books),
            'results': self.results
        }

        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        logger.info(f"Results saved to {output_path}")
        return output_path

    def run(self):
        """Main run method"""
        self.scrape_all_books()
        output_path = self.save_results()

        successful = sum(1 for r in self.results.values() if r.get('success'))
        total_games = sum(r.get('game_count', 0) for r in self.results.values())

        summary = {
            'output_path': output_path,
            'books_succeeded': successful,
            'books_failed': len(self.books) - successful,
            'total_games_scraped': total_games
        }

        logger.info(f"Summary: {summary}")
        return summary


if __name__ == '__main__':
    scraper = WNBAOddsScraper()
    summary = scraper.run()
    print(json.dumps(summary, indent=2))
