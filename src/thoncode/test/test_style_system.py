#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - style_system",
    "Path": ".main.test.test_style_system",
    "Entrance": "main.py"
}

import os
import sys
import json
import tempfile
import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

logger = get_logger("test_style_system")


class StyleSystemTests(unittest.TestCase):
    """Test cases for StyleSystem singleton style configuration manager."""

    def setUp(self):
        """Reset StyleSystem singleton state before each test."""
        from libs.gui_libs.style_system import StyleSystem
        StyleSystem._instance = None
        self.style_system = StyleSystem()
        self.style_system.reset()
        logger.debug("setUp: StyleSystem reset")
        print("[setUp] StyleSystem initialized")

    def test_singleton_pattern(self):
        """Verify StyleSystem follows singleton pattern."""
        from libs.gui_libs.style_system import StyleSystem
        ss1 = StyleSystem()
        ss2 = StyleSystem()
        self.assertIs(ss1, ss2)
        logger.info("singleton_pattern: singleton pattern verified")
        print("[PASS] test_singleton_pattern: Singleton pattern works")

    def test_get_style_default(self):
        """Verify default style can be retrieved."""
        style = self.style_system.get_style("editor")
        self.assertIn("font_family", style)
        self.assertIn("bg", style)
        self.assertIn("fg", style)
        logger.info("get_style_default: default style has expected keys")
        print("[PASS] test_get_style_default: Default style accessible")

    def test_get_value(self):
        """Verify get_value returns correct values with defaults."""
        font = self.style_system.get_value("editor", "font_family")
        self.assertIsInstance(font, str)
        missing = self.style_system.get_value("editor", "nonexistent", "default")
        self.assertEqual(missing, "default")
        logger.info("get_value: get_value works with defaults")
        print("[PASS] test_get_value: get_value works correctly")

    def test_set_style(self):
        """Verify set_style updates configuration."""
        self.style_system.set_style("editor", "bg", "#ff0000")
        value = self.style_system.get_value("editor", "bg")
        self.assertEqual(value, "#ff0000")
        logger.info("set_style: style value updated")
        print("[PASS] test_set_style: Style value updated")

    def test_set_component_style(self):
        """Verify set_component_style updates multiple values."""
        new_style = {"bg": "#111111", "fg": "#eeeeee"}
        self.style_system.set_component_style("editor", new_style)
        self.assertEqual(self.style_system.get_value("editor", "bg"), "#111111")
        self.assertEqual(self.style_system.get_value("editor", "fg"), "#eeeeee")
        logger.info("set_component_style: batch update works")
        print("[PASS] test_set_component_style: Batch style update works")

    def test_register_and_apply_style(self):
        """Verify registering and applying a custom style."""
        custom = {
            "editor": {"bg": "#00ff00", "font_size": 14},
            "tree": {"bg": "#00ff00"}
        }
        self.style_system.register_style("green", custom)
        result = self.style_system.apply_style("green")
        self.assertTrue(result)
        self.assertEqual(self.style_system.get_current_style_name(), "green")
        self.assertEqual(self.style_system.get_value("editor", "bg"), "#00ff00")
        logger.info("register_and_apply_style: custom style registered and applied")
        print("[PASS] test_register_and_apply_style: Custom style applied")

    def test_apply_nonexistent_style(self):
        """Verify applying non-existent style returns False."""
        result = self.style_system.apply_style("nonexistent_style")
        self.assertFalse(result)
        logger.info("apply_nonexistent_style: non-existent style returns False")
        print("[PASS] test_apply_nonexistent_style: Non-existent style handled")

    def test_listener_notification(self):
        """Verify style change listeners are notified."""
        notifications = []
        def on_change():
            notifications.append(True)

        self.style_system.add_listener(on_change)
        self.style_system.set_style("editor", "bg", "#abc")
        self.assertEqual(len(notifications), 1)
        self.style_system.remove_listener(on_change)
        self.style_system.set_style("editor", "bg", "#def")
        self.assertEqual(len(notifications), 1)
        logger.info("listener_notification: listeners notified correctly")
        print("[PASS] test_listener_notification: Listener notification works")

    def test_load_save_file(self):
        """Verify loading and saving styles to JSON file."""
        tmp_dir = tempfile.mkdtemp()
        try:
            file_path = os.path.join(tmp_dir, "test_style.json")
            self.style_system.set_style("editor", "bg", "#aabbcc")
            result = self.style_system.save_to_file(file_path)
            self.assertTrue(result)
            self.assertTrue(os.path.exists(file_path))

            self.style_system.reset()
            self.style_system.load_from_file(file_path)
            self.assertEqual(self.style_system.get_value("editor", "bg"), "#aabbcc")
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.info("load_save_file: file I/O works")
        print("[PASS] test_load_save_file: Style file I/O works")

    def test_reset(self):
        """Verify reset restores default style."""
        self.style_system.set_style("editor", "bg", "#custom")
        self.style_system.reset()
        self.assertEqual(self.style_system.get_current_style_name(), "default")
        self.assertNotEqual(self.style_system.get_value("editor", "bg"), "#custom")
        logger.info("reset: reset restores defaults")
        print("[PASS] test_reset: Reset works correctly")

    def test_tree_style_values(self):
        """Verify tree component has expected style keys."""
        style = self.style_system.get_style("tree")
        expected_keys = ["icon_size", "indent_width", "row_height", "folder_icon", "file_icon"]
        for key in expected_keys:
            self.assertIn(key, style, f"Tree style missing key: {key}")
        logger.info("tree_style_values: tree style has expected keys")
        print("[PASS] test_tree_style_values: Tree style keys present")

    def test_highlight_style_values(self):
        """Verify highlight component has expected color keys."""
        style = self.style_system.get_style("highlight")
        expected_keys = ["keyword", "string", "number", "comment", "function"]
        for key in expected_keys:
            self.assertIn(key, style, f"Highlight style missing key: {key}")
        logger.info("highlight_style_values: highlight style has expected keys")
        print("[PASS] test_highlight_style_values: Highlight style keys present")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing StyleSystem module")
    print("=" * 60)
    unittest.main(verbosity=2)