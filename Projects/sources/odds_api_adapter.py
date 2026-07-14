#!/usr/bin/env python3
"""
Odds API Adapter
"""

import os

class OddsAPIAdapter:
    def __init__(self):
        self.api_key = os.environ.get("ODDS_API_KEY")

    def get_odds(self, sport):
        return {"sport": sport, "odds": []}
