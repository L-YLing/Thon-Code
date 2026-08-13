#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Plugin Manager Test",
    "Path": ".main.test.test_plugin_manager",
    "Entrance": "run_all.py"
}

"""Tests for the plugin system: discovery, loading, hooks, and error isolation.

Creates temporary plugin files, verifies the PluginManager discovers and
loads them, tests hook dispatch, and ensures a broken plugin doesn't
affect others.
"""

import os
import sys
import tempfile
import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

logger = get_logger("test_plugin_manager")

from libs.plugins import PluginBase, PluginManager, PluginAPI


class TestPluginManager(unittest.TestCase):
    """Test suite for the plugin system."""

    def setUp(self):
        """Create a temp plugin directory with sample plugins."""
        self._tmp_dir = tempfile.mkdtemp(prefix="thoncode_test_plugins_")
        self._plugin_dir = os.path.join(self._tmp_dir, "plugins")
        os.makedirs(self._plugin_dir)

        # Create a valid plugin file
        valid_plugin = '''#! /usr/bin/env python3
from libs.plugins import PluginBase

class GoodPlugin(PluginBase):
    name = "good_plugin"
    version = "1.0.0"
    description = "A test plugin"

    def __init__(self, api):
        super().__init__(api)
        self.loaded = False
        self.hook_called = False

    def on_load(self):
        self.loaded = True

    def on_file_open(self, file_path):
        self.hook_called = True
        self.last_path = file_path

    def on_unload(self):
        self.loaded = False
'''
        with open(os.path.join(self._plugin_dir, "good_plugin.py"), "w",
                  encoding="utf-8") as f:
            f.write(valid_plugin)

        # Create a broken plugin (syntax error)
        with open(os.path.join(self._plugin_dir, "bad_plugin.py"), "w",
                  encoding="utf-8") as f:
            f.write("this is not valid python !!!\n")

        # Create a plugin without a PluginBase subclass
        with open(os.path.join(self._plugin_dir, "no_class.py"), "w",
                  encoding="utf-8") as f:
            f.write("x = 42\n")

        # Create a file starting with _ (should be ignored)
        with open(os.path.join(self._plugin_dir, "_hidden.py"), "w",
                  encoding="utf-8") as f:
            f.write("# should not be loaded\n")

    def tearDown(self):
        """Remove temp directory and clean up sys.path."""
        import shutil
        shutil.rmtree(self._tmp_dir, ignore_errors=True)
        if self._plugin_dir in sys.path:
            sys.path.remove(self._plugin_dir)

    def test_discover_loads_valid_plugin(self):
        """PluginManager should discover and load the valid plugin."""
        mgr = PluginManager()
        count = mgr.discover_and_load(self._plugin_dir)
        self.assertEqual(count, 1)
        self.assertIn("good_plugin", mgr.get_plugin_names())
        logger.info("test_discover_loads_valid_plugin passed")

    def test_loaded_plugin_on_load_called(self):
        """The plugin's on_load should be called during loading."""
        mgr = PluginManager()
        mgr.discover_and_load(self._plugin_dir)
        plugins = mgr.get_plugins()
        self.assertTrue(plugins["good_plugin"].loaded)
        logger.info("test_loaded_plugin_on_load_called passed")

    def test_hook_dispatch(self):
        """call_hook should dispatch to plugins that define the handler."""
        mgr = PluginManager()
        mgr.discover_and_load(self._plugin_dir)
        results = mgr.call_hook("file_open", "/test/path.py")
        plugins = mgr.get_plugins()
        self.assertTrue(plugins["good_plugin"].hook_called)
        self.assertEqual(plugins["good_plugin"].last_path, "/test/path.py")
        logger.info("test_hook_dispatch passed")

    def test_hook_missing_handler_no_error(self):
        """call_hook should not error if no plugin defines the handler."""
        mgr = PluginManager()
        mgr.discover_and_load(self._plugin_dir)
        results = mgr.call_hook("nonexistent_hook")
        self.assertEqual(results, [])
        logger.info("test_hook_missing_handler_no_error passed")

    def test_broken_plugin_doesnt_crash(self):
        """A syntax-error plugin should be skipped, not crash the manager."""
        mgr = PluginManager()
        count = mgr.discover_and_load(self._plugin_dir)
        # Only good_plugin should load; bad_plugin and no_class should be skipped
        self.assertEqual(count, 1)
        logger.info("test_broken_plugin_doesnt_crash passed")

    def test_unload_plugin(self):
        """unload_plugin should call on_unload and remove from registry."""
        mgr = PluginManager()
        mgr.discover_and_load(self._plugin_dir)
        self.assertTrue(mgr.unload_plugin("good_plugin"))
        self.assertNotIn("good_plugin", mgr.get_plugin_names())
        logger.info("test_unload_plugin passed")

    def test_unload_nonexistent_plugin(self):
        """Unloading a non-existent plugin should return False."""
        mgr = PluginManager()
        self.assertFalse(mgr.unload_plugin("does_not_exist"))
        logger.info("test_unload_nonexistent_plugin passed")

    def test_plugin_api_with_host(self):
        """PluginAPI should provide access to host services."""
        class MockHost:
            def __init__(self):
                self.project_root = "/test/root"
                self.current_file = "/test/root/file.py"
                self.status_bar = type("MockBar", (), {"configure": lambda self, **kw: None})()

        host = MockHost()
        api = PluginAPI(host)
        self.assertEqual(api.get_project_root(), "/test/root")
        self.assertEqual(api.get_current_file(), "/test/root/file.py")
        api.show_status("test")  # Should not raise
        logger.info("test_plugin_api_with_host passed")

    def test_plugin_api_text_lookup(self):
        """PluginAPI.get_text should return i18n strings or the key fallback."""
        class MockHost:
            langs_cfg = type("MockLangs", (), {"status_ready": "Ready"})()

        api = PluginAPI(MockHost())
        self.assertEqual(api.get_text("status.ready"), "Ready")
        self.assertEqual(api.get_text("nonexistent.key"), "nonexistent.key")
        logger.info("test_plugin_api_text_lookup passed")

    def test_hidden_file_not_loaded(self):
        """Files starting with _ should not be loaded as plugins."""
        mgr = PluginManager()
        mgr.discover_and_load(self._plugin_dir)
        self.assertNotIn("_hidden", mgr.get_plugin_names())
        logger.info("test_hidden_file_not_loaded passed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
