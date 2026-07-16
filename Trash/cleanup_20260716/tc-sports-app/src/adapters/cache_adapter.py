import os, json, hashlib
from datetime import datetime, timedelta

class CacheAdapter:
    def __init__(self, cache_dir="data/cache", ttl_hours=6):
        self.cache_dir = cache_dir
        self.ttl_hours = ttl_hours
        os.makedirs(cache_dir, exist_ok=True)
        self._memory = {}

    def _path(self, key):
        return os.path.join(self.cache_dir, hashlib.md5(key.encode()).hexdigest() + ".json")

    def get(self, key):
        if key in self._memory:
            data, ts = self._memory[key]
            if datetime.now() - ts < timedelta(hours=self.ttl_hours):
                return data
        p = self._path(key)
        if os.path.exists(p):
            with open(p) as f:
                cached = json.load(f)
            if datetime.now() - datetime.fromisoformat(cached["timestamp"]) < timedelta(hours=self.ttl_hours):
                self._memory[key] = (cached["data"], datetime.now())
                return cached["data"]
        return None

    def set(self, key, value, ttl_seconds=None):
        p = self._path(key)
        with open(p, "w") as f:
            json.dump({"timestamp": datetime.now().isoformat(), "data": value}, f)
        self._memory[key] = (value, datetime.now())
        return True

    def clear(self):
        for f in os.listdir(self.cache_dir):
            os.remove(os.path.join(self.cache_dir, f))
        self._memory.clear()
