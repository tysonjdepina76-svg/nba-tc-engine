#!/usr/bin/env python3
"""
Cache Adapter
"""

import json
from pathlib import Path

class CacheAdapter:
    def __init__(self):
        self.cache_dir = Path("/home/workspace/data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key):
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            with open(cache_file) as f:
                return json.load(f)
        return None

    def set(self, key, value):
        with open(self.cache_dir / f"{key}.json", "w") as f:
            json.dump(value, f)
