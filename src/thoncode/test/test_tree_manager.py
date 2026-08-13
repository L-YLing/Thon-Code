#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - tree_manager",
    "Path": ".main.test.test_tree_manager",
    "Entrance": "main.py"
}

import os
import shutil
import tempfile
import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

logger = get_logger("test_tree_manager")


# ---------------------------------------------------------------------------
# Fake ttk.Treeview for unit testing without Tkinter
# ---------------------------------------------------------------------------
class FakeTree:
    """Minimal ttk.Treeview double recording operations for assertion."""

    def __init__(self):
        self._children = {"": []}
        self._paths = {}
        self._opens = {}
        self._counter = 0
        self.deleted = []
        self.inserted = []

    def get_children(self, item=""):
        return tuple(self._children.get(item, []))

    def insert(self, parent, where, text="", open=False, image=""):
        self._counter += 1
        item = f"I{self._counter}"
        self._children.setdefault(parent, []).append(item)
        self._children.setdefault(item, [])
        self._paths[item] = None
        self._opens[item] = open
        self.inserted.append((parent, text, image))
        return item

    def set(self, item, key, value=None):
        if value is None:
            if key == "path":
                return self._paths.get(item)
            return None
        if key == "path":
            self._paths[item] = value

    def delete(self, item):
        self.deleted.append(item)
        for parent, kids in list(self._children.items()):
            if item in kids:
                kids.remove(item)
        self._children.pop(item, None)
        self._paths.pop(item, None)

    def item(self, item, *args, **kwargs):
        if "open" in kwargs:
            self._opens[item] = kwargs["open"]
        return self._opens.get(item, False)


def make_tree_manager():
    """Create a TreeManager bypassing __init__ (no Tk root needed)."""
    from libs.gui.tree_manager import TreeManager
    tm = TreeManager.__new__(TreeManager)
    tm.project_root = ""
    tm.tree = FakeTree()
    tm._children_loaded = set()
    tm.folder_icon = None
    tm.default_file_icon = None
    tm.file_icons = {}
    return tm


class TreeManagerTests(unittest.TestCase):
    """Test cases for TreeManager performance optimizations."""

    def test_package_declaration(self):
        """Verify tree_manager has proper package declaration."""
        import libs.gui.tree_manager as mod
        self.assertTrue(hasattr(mod, 'package'))
        self.assertEqual(mod.package['ID'], 'thon-code-gui')
        logger.info("package_declaration: package dict verified")
        print("[PASS] test_package_declaration: package dict verified")

    def test_ignored_dirs_constant(self):
        """Verify IGNORED_DIRS filters common heavy directories."""
        from libs.gui.tree_manager import TreeManager
        for d in ('__pycache__', '.git', 'node_modules', '.idea'):
            self.assertIn(d, TreeManager.IGNORED_DIRS)
        logger.info("ignored_dirs_constant: heavy dirs filtered")
        print("[PASS] test_ignored_dirs_constant: heavy dirs filtered")

    def test_list_sorted_dirs_first(self):
        """Verify directories appear before files in sorted output."""
        tm = make_tree_manager()
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "zdir"))
            os.makedirs(os.path.join(d, "adir"))
            open(os.path.join(d, "afile.py"), "w").close()
            open(os.path.join(d, "zfile.py"), "w").close()
            entries = tm._list_sorted(d)
            is_dirs = [e[2] for e in entries]
            # All True (dirs) should precede all False (files).
            self.assertEqual(is_dirs, sorted(is_dirs, reverse=True))
            self.assertEqual(entries[0][0], "adir")
            self.assertEqual(entries[1][0], "zdir")
            self.assertEqual(entries[2][0], "afile.py")
            self.assertEqual(entries[3][0], "zfile.py")
        logger.info("list_sorted_dirs_first: directories sorted before files")
        print("[PASS] test_list_sorted_dirs_first: directories sorted before files")

    def test_list_sorted_filters_ignored(self):
        """Verify ignored and hidden entries are excluded."""
        tm = make_tree_manager()
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "__pycache__"))
            os.makedirs(os.path.join(d, ".hidden"))
            open(os.path.join(d, ".gitignore"), "w").close()
            open(os.path.join(d, "visible.py"), "w").close()
            entries = tm._list_sorted(d)
            names = [e[0] for e in entries]
            self.assertEqual(names, ["visible.py"])
        logger.info("list_sorted_filters_ignored: ignored/hidden entries excluded")
        print("[PASS] test_list_sorted_filters_ignored: ignored/hidden entries excluded")

    def test_list_sorted_case_insensitive(self):
        """Verify sorting is case-insensitive."""
        tm = make_tree_manager()
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "Banana.py"), "w").close()
            open(os.path.join(d, "apple.py"), "w").close()
            open(os.path.join(d, "Cherry.py"), "w").close()
            entries = tm._list_sorted(d)
            names = [e[0] for e in entries]
            self.assertEqual(names, ["apple.py", "Banana.py", "Cherry.py"])
        logger.info("list_sorted_case_insensitive: case-insensitive order")
        print("[PASS] test_list_sorted_case_insensitive: case-insensitive order")

    def test_list_sorted_permission_error_returns_empty(self):
        """Verify PermissionError yields an empty list instead of raising."""
        tm = make_tree_manager()
        with tempfile.TemporaryDirectory() as d:
            sub = os.path.join(d, "noperm")
            os.makedirs(sub)
            try:
                os.chmod(sub, 0o000)
                entries = tm._list_sorted(sub)
                self.assertEqual(entries, [])
            finally:
                os.chmod(sub, 0o755)
        logger.info("list_sorted_permission_error: returns empty on PermissionError")
        print("[PASS] test_list_sorted_permission_error: returns empty on PermissionError")

    def test_insert_node_directory(self):
        """Verify directory insertion sets folder icon and path."""
        tm = make_tree_manager()
        node = tm._insert_node("ROOT", "src", "/p/src", True)
        self.assertEqual(tm.tree._paths[node], "/p/src")
        logger.info("insert_node_directory: directory node created with path")
        print("[PASS] test_insert_node_directory: directory node created with path")

    def test_insert_node_file(self):
        """Verify file insertion stores the path."""
        tm = make_tree_manager()
        node = tm._insert_node("ROOT", "main.py", "/p/main.py", False)
        self.assertEqual(tm.tree._paths[node], "/p/main.py")
        logger.info("insert_node_file: file node created with path")
        print("[PASS] test_insert_node_file: file node created with path")

    def test_refresh_children_inserts_new_only(self):
        """Verify refresh inserts only newly added entries."""
        tm = make_tree_manager()
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "a.py"), "w").close()
            # Initial population.
            tm._refresh_children("ROOT", d)
            initial = set(tm.tree.get_children("ROOT"))
            self.assertEqual(len(initial), 1)
            # Add a new file.
            open(os.path.join(d, "b.py"), "w").close()
            tm._refresh_children("ROOT", d)
            after = set(tm.tree.get_children("ROOT"))
            self.assertEqual(len(after), 2)
            # Original node preserved.
            self.assertTrue(initial.issubset(after))
        logger.info("refresh_children_inserts_new_only: new entry added, existing kept")
        print("[PASS] test_refresh_children_inserts_new_only: new entry added, existing kept")

    def test_refresh_children_deletes_removed(self):
        """Verify refresh deletes entries removed from disk."""
        tm = make_tree_manager()
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "gone.py")
            open(f, "w").close()
            tm._refresh_children("ROOT", d)
            self.assertEqual(len(tm.tree.get_children("ROOT")), 1)
            os.remove(f)
            tm._refresh_children("ROOT", d)
            self.assertEqual(len(tm.tree.get_children("ROOT")), 0)
            self.assertEqual(len(tm.tree.deleted), 1)
        logger.info("refresh_children_deletes_removed: removed entry deleted")
        print("[PASS] test_refresh_children_deletes_removed: removed entry deleted")

    def test_refresh_children_preserves_existing_node_identity(self):
        """Verify unchanged entries keep their tree item id across refresh."""
        tm = make_tree_manager()
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "keep.py"), "w").close()
            tm._refresh_children("ROOT", d)
            before = tm.tree.get_children("ROOT")[0]
            # Refresh without filesystem change.
            tm._refresh_children("ROOT", d)
            after = tm.tree.get_children("ROOT")[0]
            self.assertEqual(before, after)
            # No deletions or insertions on a no-op refresh.
            self.assertEqual(len(tm.tree.deleted), 0)
        logger.info("refresh_children_preserves_identity: unchanged node id preserved")
        print("[PASS] test_refresh_children_preserves_identity: unchanged node id preserved")

    def test_refresh_children_recurses_into_loaded_dirs(self):
        """Verify refresh recurses into already-loaded subdirectories."""
        tm = make_tree_manager()
        with tempfile.TemporaryDirectory() as d:
            sub = os.path.join(d, "pkg")
            os.makedirs(sub)
            open(os.path.join(sub, "a.py"), "w").close()
            # Populate root.
            tm._refresh_children("ROOT", d)
            pkg_item = tm.tree.get_children("ROOT")[0]
            # Simulate the subdirectory having been loaded (expanded).
            tm._children_loaded.add(pkg_item)
            tm._refresh_children(pkg_item, sub)
            self.assertEqual(len(tm.tree.get_children(pkg_item)), 1)
            # Add file in subdir and refresh root; recursion should pick it up.
            open(os.path.join(sub, "b.py"), "w").close()
            tm._refresh_children("ROOT", d)
            self.assertEqual(len(tm.tree.get_children(pkg_item)), 2)
        logger.info("refresh_children_recurses: subdir refresh recursed correctly")
        print("[PASS] test_refresh_children_recurses: subdir refresh recursed correctly")


if __name__ == "__main__":
    unittest.main(verbosity=2)
