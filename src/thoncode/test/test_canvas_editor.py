#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - canvas_editor",
    "Path": ".main.test.test_canvas_editor",
    "Entrance": "main.py"
}

import os
import sys
import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

logger = get_logger("test_canvas_editor")


class CanvasEditorTests(unittest.TestCase):
    """Test cases for CanvasCodeEditor component."""

    def test_package_declaration(self):
        """Verify canvas_editor has proper package declaration."""
        import libs.gui_libs.code_editor.canvas_editor as canvas_editor
        self.assertTrue(hasattr(canvas_editor, 'package'))
        pkg = canvas_editor.package
        self.assertIn('ID', pkg)
        self.assertIn('Name', pkg)
        logger.info("package_declaration: canvas_editor package verified")
        print("[PASS] test_package_declaration: Package declaration valid")

    def test_editor_gutter_package(self):
        """Verify editor_gutter has proper package declaration."""
        import libs.gui_libs.code_editor.editor_gutter as gutter
        self.assertTrue(hasattr(gutter, 'package'))
        logger.info("editor_gutter_package: editor_gutter package verified")
        print("[PASS] test_editor_gutter_package: Gutter package valid")

    def test_canvas_editor_class_exists(self):
        """Verify CanvasCodeEditor class can be imported."""
        from libs.gui_libs.code_editor.canvas_editor import CanvasCodeEditor
        expected_methods = [
            'create_widget', 'pack', 'grid', 'destroy',
            'get_content', 'set_content', 'clear',
            'open_file', 'save_file', 'select_all',
            'apply_style', 'get_style_value', 'set_style_value',
            'load', 'unload', 'on_key_press',
        ]
        for method in expected_methods:
            self.assertTrue(hasattr(CanvasCodeEditor, method),
                            f"CanvasCodeEditor should have {method}")
        logger.info("canvas_editor_class_exists: all expected methods present")
        print(f"[PASS] test_canvas_editor_class_exists: All {len(expected_methods)} methods present")

    def test_editor_gutter_class_exists(self):
        """Verify EditorGutter class can be imported."""
        from libs.gui_libs.code_editor.editor_gutter import EditorGutter
        expected_methods = [
            'set_foldable_regions', 'set_folded_lines',
            'get_folded_lines', 'sync_scroll', 'redraw',
            'set_on_line_click', 'set_on_fold_click',
        ]
        for method in expected_methods:
            self.assertTrue(hasattr(EditorGutter, method),
                            f"EditorGutter should have {method}")
        logger.info("editor_gutter_class_exists: all expected methods present")
        print(f"[PASS] test_editor_gutter_class_exists: All {len(expected_methods)} methods present")

    def test_implements_style_provider(self):
        """Verify CanvasCodeEditor implements StyleProvider interface."""
        from libs.gui_libs.code_editor.canvas_editor import CanvasCodeEditor
        from libs.gui_libs.base import StyleProvider
        self.assertTrue(issubclass(CanvasCodeEditor, StyleProvider))
        logger.info("implements_style_provider: StyleProvider interface implemented")
        print("[PASS] test_implements_style_provider: StyleProvider interface present")

    def test_implements_lazy_loadable(self):
        """Verify CanvasCodeEditor implements LazyLoadable interface."""
        from libs.gui_libs.code_editor.canvas_editor import CanvasCodeEditor
        from libs.gui_libs.base import LazyLoadable
        self.assertTrue(issubclass(CanvasCodeEditor, LazyLoadable))
        logger.info("implements_lazy_loadable: LazyLoadable interface implemented")
        print("[PASS] test_implements_lazy_loadable: LazyLoadable interface present")

    def test_implements_event_handler(self):
        """Verify CanvasCodeEditor implements EventHandler interface."""
        from libs.gui_libs.code_editor.canvas_editor import CanvasCodeEditor
        from libs.gui_libs.base import EventHandler
        self.assertTrue(issubclass(CanvasCodeEditor, EventHandler))
        logger.info("implements_event_handler: EventHandler interface implemented")
        print("[PASS] test_implements_event_handler: EventHandler interface present")

    def test_is_dirty_property(self):
        """Verify is_dirty is a property on CanvasCodeEditor."""
        from libs.gui_libs.code_editor.canvas_editor import CanvasCodeEditor
        self.assertTrue(isinstance(CanvasCodeEditor.__dict__['is_dirty'], property))
        logger.info("is_dirty_property: is_dirty is a property")
        print("[PASS] test_is_dirty_property: is_dirty is a property")

    def test_current_file_property(self):
        """Verify current_file is a property on CanvasCodeEditor."""
        from libs.gui_libs.code_editor.canvas_editor import CanvasCodeEditor
        self.assertTrue(isinstance(CanvasCodeEditor.__dict__['current_file'], property))
        logger.info("current_file_property: current_file is a property")
        print("[PASS] test_current_file_property: current_file is a property")

    def test_language_detection_map(self):
        """Verify language detection covers common extensions."""
        from libs.gui_libs.code_editor.canvas_editor import CanvasCodeEditor
        source = ''
        import inspect
        source = inspect.getsource(CanvasCodeEditor._detect_language)
        expected_exts = ['.py', '.js', '.ts', '.html', '.css', '.json']
        for ext in expected_exts:
            self.assertIn(ext, source, f"Language detection should cover {ext}")
        logger.info("language_detection_map: language detection covers common extensions")
        print("[PASS] test_language_detection_map: Common extensions covered")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing CanvasCodeEditor and EditorGutter")
    print("=" * 60)
    unittest.main(verbosity=2)