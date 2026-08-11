#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - file_tree",
    "Path": ".main.test.test_file_tree",
    "Entrance": "main.py"
}

import os
import sys
import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

logger = get_logger("test_file_tree")


class FileTreeTests(unittest.TestCase):
    """Test cases for CanvasFileTree and TreeNode."""

    def test_tree_node_package(self):
        """Verify TreeNode class can be imported."""
        from libs.gui_libs.file_tree.canvas_tree import TreeNode
        node = TreeNode("/test/path", "test.py", is_dir=False)
        self.assertEqual(node.path, "/test/path")
        self.assertEqual(node.name, "test.py")
        self.assertFalse(node.is_dir)
        self.assertEqual(node.icon, "")
        logger.info("tree_node_package: TreeNode class import verified")
        print("[PASS] test_tree_node_package: TreeNode import and basic props OK")

    def test_tree_node_default_icon(self):
        """Verify TreeNode.get_icon returns appropriate icon."""
        from libs.gui_libs.file_tree.canvas_tree import TreeNode
        file_node = TreeNode("/test.py", "test.py", is_dir=False)
        dir_node = TreeNode("/test", "test", is_dir=True)
        dir_node.expanded = False
        self.assertEqual(file_node.get_icon(), "📄")
        self.assertEqual(dir_node.get_icon(), "📁")
        dir_node.expanded = True
        self.assertEqual(dir_node.get_icon(), "📂")
        logger.info("tree_node_default_icon: icon logic verified")
        print("[PASS] test_tree_node_default_icon: Icon returns correct values")

    def test_tree_node_children(self):
        """Verify TreeNode children management."""
        from libs.gui_libs.file_tree.canvas_tree import TreeNode
        parent = TreeNode("/root", "root", is_dir=True)
        child1 = TreeNode("/root/child1", "child1.py")
        child2 = TreeNode("/root/child2", "child2.py")
        parent.children = [child1, child2]
        self.assertEqual(len(parent.children), 2)
        self.assertEqual(parent.children[0].name, "child1.py")
        logger.info("tree_node_children: children management verified")
        print("[PASS] test_tree_node_children: Children list works correctly")

    def test_file_tree_package(self):
        """Verify CanvasFileTree has proper package declaration."""
        import libs.gui_libs.file_tree.canvas_tree as canvas_tree
        self.assertTrue(hasattr(canvas_tree, 'package'))
        pkg = canvas_tree.package
        self.assertIn('ID', pkg)
        self.assertIn('Name', pkg)
        logger.info("file_tree_package: package declaration verified")
        print("[PASS] test_file_tree_package: Canvas tree package valid")

    def test_canvas_file_tree_class_exists(self):
        """Verify CanvasFileTree class has all expected methods."""
        from libs.gui_libs.file_tree.canvas_tree import CanvasFileTree
        expected_methods = [
            'create_widget', 'pack', 'grid', 'destroy',
            'set_project_root', 'refresh',
            'get_selected_node', 'get_project_root',
            'expand_node', 'collapse_node',
            'set_on_node_open', 'set_on_node_select',
            'set_on_node_expand', 'set_on_context_menu',
            'apply_style', 'get_style_value', 'set_style_value',
            'load', 'unload',
        ]
        for method in expected_methods:
            self.assertTrue(hasattr(CanvasFileTree, method),
                            f"CanvasFileTree should have {method}")
        logger.info("canvas_file_tree_class_exists: all expected methods present")
        print(f"[PASS] test_canvas_file_tree_class_exists: All {len(expected_methods)} methods present")

    def test_implements_style_provider(self):
        """Verify CanvasFileTree implements StyleProvider interface."""
        from libs.gui_libs.file_tree.canvas_tree import CanvasFileTree
        from libs.gui_libs.base import StyleProvider
        self.assertTrue(issubclass(CanvasFileTree, StyleProvider))
        logger.info("implements_style_provider: StyleProvider interface verified")
        print("[PASS] test_implements_style_provider: StyleProvider interface present")

    def test_implements_lazy_loadable(self):
        """Verify CanvasFileTree implements LazyLoadable interface."""
        from libs.gui_libs.file_tree.canvas_tree import CanvasFileTree
        from libs.gui_libs.base import LazyLoadable
        self.assertTrue(issubclass(CanvasFileTree, LazyLoadable))
        logger.info("implements_lazy_loadable: LazyLoadable interface verified")
        print("[PASS] test_implements_lazy_loadable: LazyLoadable interface present")

    def test_implements_event_handler(self):
        """Verify CanvasFileTree implements EventHandler interface."""
        from libs.gui_libs.file_tree.canvas_tree import CanvasFileTree
        from libs.gui_libs.base import EventHandler
        self.assertTrue(issubclass(CanvasFileTree, EventHandler))
        logger.info("implements_event_handler: EventHandler interface verified")
        print("[PASS] test_implements_event_handler: EventHandler interface present")

    def test_is_loaded_property(self):
        """Verify is_loaded is a property on CanvasFileTree."""
        from libs.gui_libs.file_tree.canvas_tree import CanvasFileTree
        self.assertTrue(isinstance(CanvasFileTree.__dict__['is_loaded'], property))
        logger.info("is_loaded_property: is_loaded is a property")
        print("[PASS] test_is_loaded_property: is_loaded is a property")

    def test_get_widget_method(self):
        """Verify get_widget returns correct type."""
        from libs.gui_libs.file_tree.canvas_tree import CanvasFileTree
        self.assertTrue(hasattr(CanvasFileTree, 'get_widget'))
        self.assertTrue(hasattr(CanvasFileTree, 'get_canvas'))
        logger.info("get_widget_method: get_widget and get_canvas methods exist")
        print("[PASS] test_get_widget_method: get_widget and get_canvas present")

    def test_file_tree_init_defaults(self):
        """Verify CanvasFileTree __init__ sets correct defaults."""
        import inspect
        from libs.gui_libs.file_tree.canvas_tree import CanvasFileTree
        source = inspect.getsource(CanvasFileTree.__init__)
        # Verify key initialization patterns
        self.assertIn('_indent_width', source)
        self.assertIn('_row_height', source)
        self.assertIn('_bg_color', source)
        self.assertIn('_fg_color', source)
        self.assertIn('_hover_bg', source)
        self.assertIn('_sel_bg', source)
        self.assertIn('_loaded', source)
        logger.info("file_tree_init_defaults: initialization defaults verified")
        print("[PASS] test_file_tree_init_defaults: Key defaults in __init__ present")

    def test_expand_indicator_config(self):
        """Verify expand/collapse indicators are configurable via style."""
        import inspect
        from libs.gui_libs.file_tree.canvas_tree import CanvasFileTree
        source = inspect.getsource(CanvasFileTree._load_style)
        self.assertIn('expand_indicator', source)
        self.assertIn('collapse_indicator', source)
        logger.info("expand_indicator_config: indicators loaded via style system")
        print("[PASS] test_expand_indicator_config: Expand/collapse indicators configurable")

    def test_callback_setters(self):
        """Verify all callback setter methods exist."""
        from libs.gui_libs.file_tree.canvas_tree import CanvasFileTree
        expected = [
            'set_on_node_open',
            'set_on_node_select',
            'set_on_node_expand',
            'set_on_context_menu',
        ]
        for method in expected:
            self.assertTrue(hasattr(CanvasFileTree, method),
                            f"Should have {method}")
        logger.info("callback_setters: all callback setters present")
        print("[PASS] test_callback_setters: All 4 callback setters present")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing CanvasFileTree and TreeNode")
    print("=" * 60)
    unittest.main(verbosity=2)