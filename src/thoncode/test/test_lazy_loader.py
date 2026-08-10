#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - lazy_loader",
    "Path": ".main.test.test_lazy_loader",
    "Entrance": "main.py"
}

import os
import sys
import time
import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

from libs.gui.lazy_loader import LazyLoader

logger = get_logger("test_lazy_loader")


class LazyLoaderTests(unittest.TestCase):
    """Test cases for LazyLoader lazy loading and unloading"""

    def setUp(self):
        """Clear cache before each test"""
        LazyLoader.clear_cache()
        logger.debug("setUp: cache cleared")
        print("[setUp] LazyLoader cache cleared")

    def tearDown(self):
        """Clear cache after each test"""
        LazyLoader.clear_cache()
        logger.debug("tearDown: cache cleared")

    def test_lazy_get_module(self):
        """Verify lazy loading a module works correctly"""
        module = LazyLoader.get("json")
        self.assertIsNotNone(module)
        self.assertTrue(LazyLoader.is_cached("json"))
        logger.info("lazy_get_module: loaded json module successfully")
        print("[PASS] test_lazy_get_module: Module loaded lazily")

    def test_lazy_get_class(self):
        """Verify lazy loading a class from a module works correctly"""
        # json.JSONEncoder is a class in json module
        cls = LazyLoader.get("json", "JSONEncoder")
        self.assertIsNotNone(cls)
        self.assertTrue(LazyLoader.is_cached("json", "JSONEncoder"))
        logger.info("lazy_get_class: loaded JSONEncoder class successfully")
        print("[PASS] test_lazy_get_class: Class loaded lazily")

    def test_cache_reuse(self):
        """Verify that second get returns cached instance"""
        module1 = LazyLoader.get("json")
        module2 = LazyLoader.get("json")
        self.assertIs(module1, module2)
        logger.info("cache_reuse: cache reuse verified")
        print("[PASS] test_cache_reuse: Cached instance reused")

    def test_unload_module(self):
        """Verify unloading a module removes it from cache"""
        LazyLoader.get("json")
        self.assertTrue(LazyLoader.is_cached("json"))

        result = LazyLoader.unload("json")
        self.assertTrue(result)
        self.assertFalse(LazyLoader.is_cached("json"))
        logger.info("unload_module: module unloaded successfully")
        print("[PASS] test_unload_module: Module unloaded from cache")

    def test_unload_nonexistent(self):
        """Verify unloading a non-existent module returns False"""
        result = LazyLoader.unload("nonexistent_module_xyz")
        self.assertFalse(result)
        logger.info("unload_nonexistent: non-existent module returns False")
        print("[PASS] test_unload_nonexistent: Non-existent module handled")

    def test_clear_cache(self):
        """Verify clearing cache removes all cached entries"""
        LazyLoader.get("json")
        LazyLoader.get("os")
        self.assertTrue(LazyLoader.is_cached("json"))
        self.assertTrue(LazyLoader.is_cached("os"))

        LazyLoader.clear_cache()
        self.assertFalse(LazyLoader.is_cached("json"))
        self.assertFalse(LazyLoader.is_cached("os"))
        logger.info("clear_cache: all entries cleared")
        print("[PASS] test_clear_cache: Cache cleared")

    def test_is_cached_false(self):
        """Verify is_cached returns False for uncached module"""
        self.assertFalse(LazyLoader.is_cached("json"))
        self.assertFalse(LazyLoader.is_cached("json", "JSONEncoder"))
        logger.info("is_cached_false: uncached modules return False")
        print("[PASS] test_is_cached_false: Uncached modules detected correctly")

    def test_lazy_load_performance(self):
        """Verify lazy loading doesn't significantly impact performance"""
        start = time.perf_counter()
        for _ in range(100):
            LazyLoader.get("json")
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 1.0, f"100 loads took {elapsed:.3f}s, expected < 1.0s")
        logger.info(f"lazy_load_performance: 100 loads took {elapsed:.3f}s")
        print(f"[PASS] test_lazy_load_performance: 100 loads in {elapsed:.3f}s")

    def test_unload_then_reload(self):
        """Verify unloading and reloading works correctly"""
        module1 = LazyLoader.get("json")
        self.assertTrue(LazyLoader.unload("json"))

        module2 = LazyLoader.get("json")
        self.assertIsNotNone(module2)
        self.assertTrue(LazyLoader.is_cached("json"))
        logger.info("unload_then_reload: reload after unload works")
        print("[PASS] test_unload_then_reload: Reload after unload successful")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing LazyLoader lazy loading mechanism")
    print("=" * 60)
    unittest.main(verbosity=2)