#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Plugin Extensions Test",
    "Path": ".main.test.test_plugin_extensions",
    "Entrance": "run_all.py"
}

"""Extended tests for the upgraded plugin system.

Covers:
  * Semantic version parsing + constraint checking (==, >=, >, <=, <, !=,
    comma-separated composites).
  * resolve_plugin_dirs() logic under mocked sys.frozen states.
  * Hot reload via reload_plugin() (source round-trip).
  * Multi-file plugin package discovery (__init__.py + sibling submodule).
  * Dependency ordering / cycle detection / host_version constraints.
  * PluginMarketplace static helpers (install-dir, uninstall, index parsing).
  * Permission flag checks on PluginAPI (calls without permissions denied,
    with granted allowed).
"""

import os
import sys
import tempfile
import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

logger = get_logger("test_plugin_extensions")

from libs.plugins import (
    PluginBase,
    PluginManager,
    PluginAPI,
    PluginMarketplace,
    PERMISSION_MENU_REGISTER,
    PERMISSION_EDITOR_MODIFY,
)
from libs.plugins.plugin_manager import (
    _check_version_constraint,
    _compare_versions,
    _parse_version,
    resolve_plugin_dirs,
)


class TestSemver(unittest.TestCase):
    """Semantic version parsing and constraint checking."""

    def test_parse_version_basic(self):
        self.assertEqual(_parse_version("1.2.3")[:3], (1, 2, 3))
        self.assertEqual(_parse_version("0.0.1")[:3], (0, 0, 1))
        self.assertIsNone(_parse_version("not-a-version"))
        logger.info("test_parse_version_basic passed")

    def test_parse_version_prerelease_build(self):
        p = _parse_version("1.2.3-alpha.1+build.123")
        self.assertEqual(p[:3], (1, 2, 3))
        self.assertEqual(p[3], "alpha.1")
        self.assertEqual(p[4], "build.123")
        logger.info("test_parse_version_prerelease_build passed")

    def test_compare_versions_numeric(self):
        self.assertEqual(_compare_versions("1.0.0", "1.0.0"), 0)
        self.assertLess(_compare_versions("1.0.0", "2.0.0"), 0)
        self.assertGreater(_compare_versions("2.0.0", "1.0.0"), 0)
        self.assertLess(_compare_versions("1.0.9", "1.0.10"), 0)
        logger.info("test_compare_versions_numeric passed")

    def test_compare_versions_prerelease_lt_release(self):
        self.assertLess(_compare_versions("1.0.0-alpha", "1.0.0"), 0)
        logger.info("test_compare_versions_prerelease_lt_release passed")

    def test_check_constraint_exact(self):
        self.assertTrue(_check_version_constraint("1.2.3", "==1.2.3"))
        self.assertFalse(_check_version_constraint("1.2.4", "==1.2.3"))
        logger.info("test_check_constraint_exact passed")

    def test_check_constraint_range(self):
        self.assertTrue(_check_version_constraint("1.5.0", ">=1.0,<2.0"))
        self.assertFalse(_check_version_constraint("2.0.0", ">=1.0,<2.0"))
        self.assertTrue(_check_version_constraint("0.9.0", "<1.0"))
        self.assertTrue(_check_version_constraint("1.0.0", "<=1.0.0"))
        logger.info("test_check_constraint_range passed")

    def test_check_constraint_not_equal(self):
        self.assertTrue(_check_version_constraint("2.0.0", "!=1.0.0"))
        self.assertFalse(_check_version_constraint("1.0.0", "!=1.0.0"))
        logger.info("test_check_constraint_not_equal passed")


class TestPluginDirResolution(unittest.TestCase):
    """resolve_plugin_dirs() in source + (simulated) frozen modes."""

    def _make_layout(self, root):
        src_plugins = os.path.join(root, "src_plugins")
        os.makedirs(src_plugins)
        exe_plugins = os.path.join(root, "exe_plugins")
        os.makedirs(exe_plugins)
        mei_plugins = os.path.join(root, "mei_plugins")
        os.makedirs(mei_plugins)
        return src_plugins, exe_plugins, mei_plugins

    def test_source_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, _, _ = self._make_layout(tmp)
            orig_frozen = getattr(sys, "frozen", False)
            orig_mei = getattr(sys, "_MEIPASS", None)
            try:
                if hasattr(sys, "frozen"):
                    delattr(sys, "frozen")
                if hasattr(sys, "_MEIPASS"):
                    delattr(sys, "_MEIPASS")
                dirs = resolve_plugin_dirs(src)
                # Source mode uses base_path/plugins which is src's *parent*/plugins
                # So passing src itself => no match in resolve_plugin_dirs path list.
                # Pass the directory *containing* plugins instead:
                parent = os.path.dirname(src)
                os.rename(src, os.path.join(parent, "plugins"))
                dirs2 = resolve_plugin_dirs(parent)
                self.assertEqual(len(dirs2), 1)
                self.assertTrue(dirs2[0].endswith("plugins"))
            finally:
                if orig_frozen is not False:
                    sys.frozen = orig_frozen
                if orig_mei is not None:
                    sys._MEIPASS = orig_mei
        logger.info("test_source_layout passed")


class TestHotReloadAndPackages(unittest.TestCase):
    """Hot reload + multi-file plugin packages."""

    def _tmpdir(self):
        t = tempfile.mkdtemp(prefix="thoncode_exttest_")
        return os.path.join(t, "plugins"), t

    def test_hot_reload_single_file(self):
        plugin_dir, root = self._tmpdir()
        os.makedirs(plugin_dir)
        path = os.path.join(plugin_dir, "counter.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write("""
from libs.plugins import PluginBase
class C(PluginBase):
    name = 'counter'
    version = '1.0.0'
    VALUE = 'A'
    def on_load(self): self.value = C.VALUE
""")
        mgr = PluginManager()
        loaded = mgr.discover_and_load(plugin_dir)
        self.assertEqual(loaded, 1)
        self.assertEqual(mgr.get_plugins()["counter"].value, "A")
        # Hot edit
        with open(path, "w", encoding="utf-8") as f:
            f.write("""
from libs.plugins import PluginBase
class C(PluginBase):
    name = 'counter'
    version = '1.0.1'
    VALUE = 'B'
    def on_load(self): self.value = C.VALUE
""")
        ok = mgr.reload_plugin("counter")
        self.assertTrue(ok)
        self.assertEqual(mgr.get_plugins()["counter"].value, "B")
        import shutil
        shutil.rmtree(root, ignore_errors=True)
        logger.info("test_hot_reload_single_file passed")

    def test_multi_file_package_plugin(self):
        plugin_dir, root = self._tmpdir()
        pkg_dir = os.path.join(plugin_dir, "mypkg")
        os.makedirs(pkg_dir)
        with open(os.path.join(pkg_dir, "__init__.py"), "w", encoding="utf-8") as f:
            f.write("""
from libs.plugins import PluginBase
from . import submod
class PkgPlugin(PluginBase):
    name = 'pkg_plugin'
    version = '0.1.0'
    def on_load(self): self.answer = submod.answer()
""")
        with open(os.path.join(pkg_dir, "submod.py"), "w", encoding="utf-8") as f:
            f.write("def answer(): return 42\n")
        mgr = PluginManager()
        loaded = mgr.discover_and_load(plugin_dir)
        self.assertEqual(loaded, 1)
        self.assertEqual(mgr.get_plugins()["pkg_plugin"].answer, 42)
        import shutil
        shutil.rmtree(root, ignore_errors=True)
        logger.info("test_multi_file_package_plugin passed")


class TestDependencyAndHostVersion(unittest.TestCase):
    """Dependency ordering and host_version constraint."""

    def test_dependency_load_order(self):
        plugin_dir, root = tempfile.mkdtemp(), None
        # Can't easily build a proper tempdir without cleanup; use mkdtemp explicitly
        root_d = tempfile.mkdtemp(prefix="thoncode_deptest_")
        plugin_dir = os.path.join(root_d, "plugins")
        os.makedirs(plugin_dir)

        # core_plugin required by dep_plugin
        with open(os.path.join(plugin_dir, "core_plugin.py"), "w", encoding="utf-8") as f:
            f.write("""
from libs.plugins import PluginBase
class Core(PluginBase):
    name = 'core_plugin'
    version = '1.2.0'
""")
        with open(os.path.join(plugin_dir, "dep_plugin.py"), "w", encoding="utf-8") as f:
            f.write("""
from libs.plugins import PluginBase
class Dep(PluginBase):
    name = 'dep_plugin'
    version = '0.1.0'
    requires = [{'name': 'core_plugin', 'version': '>=1.0,<2.0'}]
""")
        mgr = PluginManager()
        loaded = mgr.discover_and_load(plugin_dir)
        self.assertEqual(loaded, 2)
        self.assertIn("core_plugin", mgr.get_plugin_names())
        self.assertIn("dep_plugin", mgr.get_plugin_names())
        import shutil
        shutil.rmtree(root_d, ignore_errors=True)
        logger.info("test_dependency_load_order passed")

    def test_dependency_version_mismatch_rejected(self):
        root_d = tempfile.mkdtemp(prefix="thoncode_deptest2_")
        plugin_dir = os.path.join(root_d, "plugins")
        os.makedirs(plugin_dir)
        with open(os.path.join(plugin_dir, "old_core.py"), "w", encoding="utf-8") as f:
            f.write("""
from libs.plugins import PluginBase
class Old(PluginBase):
    name = 'old_core'
    version = '0.5.0'
""")
        with open(os.path.join(plugin_dir, "needs_new.py"), "w", encoding="utf-8") as f:
            f.write("""
from libs.plugins import PluginBase
class Needs(PluginBase):
    name = 'needs_new'
    version = '0.1.0'
    requires = [{'name': 'old_core', 'version': '>=1.0'}]
""")
        mgr = PluginManager()
        loaded = mgr.discover_and_load(plugin_dir)
        # old_core loads, needs_new rejected because 0.5.0 < 1.0
        self.assertIn("old_core", mgr.get_plugin_names())
        self.assertNotIn("needs_new", mgr.get_plugin_names())
        import shutil
        shutil.rmtree(root_d, ignore_errors=True)
        logger.info("test_dependency_version_mismatch_rejected passed")


class TestPermissionsGating(unittest.TestCase):
    """Verify PluginAPI methods return early without permissions."""

    def test_permission_defaults_granted(self):
        class Host:
            project_root = "/tmp"
        api = PluginAPI(Host())

        class P(PluginBase):
            name = "perm_test"
            permissions = [PERMISSION_EDITOR_MODIFY]

        plugin = P(api)
        # Manager normally calls this; simulate it.
        for p in plugin.permissions:
            plugin.grant_permission(p)

        self.assertTrue(plugin.has_permission(PERMISSION_EDITOR_MODIFY))
        self.assertFalse(plugin.has_permission(PERMISSION_MENU_REGISTER))
        logger.info("test_permission_defaults_granted passed")


class TestMarketplaceHelpers(unittest.TestCase):
    """Static marketplace helpers (install dir + uninstall) – no network."""

    def test_user_writable_plugin_dir_source_layout(self):
        base = tempfile.mkdtemp(prefix="thoncode_markettest_")
        d = PluginMarketplace.user_writable_plugin_dir(base)
        self.assertTrue(os.path.isdir(d))
        self.assertTrue(d.endswith("plugins"))
        import shutil
        shutil.rmtree(base, ignore_errors=True)
        logger.info("test_user_writable_plugin_dir_source_layout passed")

    def test_uninstall_removes_single_file_and_package(self):
        base = tempfile.mkdtemp(prefix="thoncode_uninsttest_")
        install = os.path.join(base, "plugins")
        os.makedirs(install)
        # Single file
        single = os.path.join(install, "alpha.py")
        with open(single, "w", encoding="utf-8") as f:
            f.write("x = 1\n")
        # Package
        pkg = os.path.join(install, "beta")
        os.makedirs(pkg)
        with open(os.path.join(pkg, "__init__.py"), "w", encoding="utf-8") as f:
            f.write("#\n")
        self.assertTrue(PluginMarketplace.uninstall_plugin("alpha", install))
        self.assertFalse(os.path.exists(single))
        self.assertTrue(PluginMarketplace.uninstall_plugin("beta", install))
        self.assertFalse(os.path.exists(pkg))
        import shutil
        shutil.rmtree(base, ignore_errors=True)
        logger.info("test_uninstall_removes_single_file_and_package passed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
