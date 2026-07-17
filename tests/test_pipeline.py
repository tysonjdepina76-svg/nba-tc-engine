import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.domain.entities import REGISTRY
from src.adapters.cache_adapter import CacheAdapter
from src.adapters.line_fetcher import fetch_lines
from src.explanation_engine import generate_explanation

class TestRegistry(unittest.TestCase):
    def test_registry_has_sports(self):
        self.assertIn("mlb", REGISTRY._registry)
        self.assertIn("wnba", REGISTRY._registry)
        self.assertIn("wc", REGISTRY._registry)

    def test_registry_enabled(self):
        enabled = REGISTRY.list_enabled()
        self.assertIn("mlb", enabled)
        self.assertIn("wnba", enabled)
        self.assertIn("wc", enabled)

class TestCacheAdapter(unittest.TestCase):
    def setUp(self):
        self.cache = CacheAdapter(cache_dir="test_cache", ttl_hours=0.1)

    def test_set_get(self):
        self.cache.set("test_key", "test_value")
        self.assertEqual(self.cache.get("test_key"), "test_value")

    def test_delete(self):
        self.cache.set("test_key", "test_value")
        self.cache.delete("test_key")
        self.assertIsNone(self.cache.get("test_key"))

    def tearDown(self):
        import shutil
        shutil.rmtree("test_cache", ignore_errors=True)

class TestLineFetcher(unittest.TestCase):
    def test_fetch_lines_returns_dict(self):
        data = fetch_lines("mlb")
        self.assertIn("source", data)

class TestExplanationEngine(unittest.TestCase):
    def test_generate_explanation(self):
        reason = generate_explanation("Player", "wnba", "pts", 10.0, 9.0, 1.0)
        self.assertIn("Player", reason)
        self.assertIn("10.0", reason)

if __name__ == "__main__":
    unittest.main()
