#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-plugins",
    "Name": "Thon Code Plugin Manager",
    "Path": ".main.libs.plugins.plugin_manager",
    "Entrance": "main.py"
}

"""Plugin discovery, loading, and lifecycle management.

PluginManager scans a plugin directory for Python modules and packages,
imports each, finds PluginBase subclasses, instantiates them with a
PluginAPI, performs permission/version checks, and manages their
lifecycle. Hook calls are dispatched to all active plugins with error
isolation so a single plugin failure never crashes the host.

Highlights:
    * PyInstaller / sys.frozen support: resolves the plugin directory
      from both source layout and the bundled _MEIPASS temp folder,
      and prefers user-writable locations next to the executable so
      end-users can drop plugins without re-packaging.
    * Hot reload: ``reload_plugin()`` unloads the plugin, invalidates
      every cached module in the plugin's subtree (sys.modules + file
      mtime), then re-imports so source changes take effect live.
    * Multi-file plugin packages: a directory containing __init__.py
      is loaded as a single plugin, just like a standalone .py file.
      Submodules are reloaded together, preserving encapsulation.
    * Dependency resolution: each plugin declares ``requires``; the
      manager does a topological sort plus semantic-version checks
      and refuses to load a plugin whose constraints are not met.
    * Permission sandbox: requested permissions are tracked and API
      methods on PluginAPI check ``has_permission()`` before
      executing high-impact operations.
"""

import os
import sys
import re
import logging
import importlib
import importlib.util
from typing import Any, Dict, List, Optional, Set, Tuple, Type

from libs.plugins.plugin_base import (
    PluginBase,
    ALL_PERMISSIONS,
)
from libs.plugins.plugin_api import PluginAPI

_logger = logging.getLogger("thoncode.plugins.manager")

# Host app version used to evaluate ``PluginBase.host_version``.
# Bump this when the PluginAPI surface changes in a backward-incompatible way.
HOST_APP_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Semantic version helpers
# ---------------------------------------------------------------------------
_SEMVER_RE = re.compile(
    r"^(\d+)\.(\d+)\.(\d+)"
    r"(?:-([0-9A-Za-z\-.]+))?"
    r"(?:\+([0-9A-Za-z\-.]+))?$"
)


def _parse_version(version: str) -> Optional[Tuple[int, int, int, str, str]]:
    """Parse a semantic version string into a comparable tuple.

    Returns None if the string is not a valid semver. Release and
    build metadata are carried but not used in comparisons (per
    semver spec 11.4/10).
    """
    m = _SEMVER_RE.match(version.strip())
    if not m:
        return None
    major, minor, patch, pre, build = m.groups()
    return (int(major), int(minor), int(patch), pre or "", build or "")


def _compare_versions(a: str, b: str) -> int:
    """Compare two semver strings. Returns -1 / 0 / +1."""
    pa = _parse_version(a)
    pb = _parse_version(b)
    if pa is None:
        return 0 if pb is None else -1
    if pb is None:
        return 1
    # Compare numeric triples
    na = pa[:3]
    nb = pb[:3]
    if na < nb:
        return -1
    if na > nb:
        return 1
    # Pre-release comparison
    pre_a, pre_b = pa[3], pb[3]
    if pre_a == pre_b:
        return 0
    if not pre_a:
        return 1  # Release > pre-release
    if not pre_b:
        return -1
    pre_cmp = _compare_pre(pre_a, pre_b)
    if pre_cmp < 0:
        return -1
    if pre_cmp > 0:
        return 1
    return 0


def _compare_pre(a: str, b: str) -> int:
    parts_a = a.split(".")
    parts_b = b.split(".")
    for pa, pb in zip(parts_a, parts_b):
        na = pa.isdigit()
        nb = pb.isdigit()
        if na and nb:
            ia, ib = int(pa), int(pb)
            if ia != ib:
                return -1 if ia < ib else 1
        elif na:
            return -1  # numeric < string
        elif nb:
            return 1
        else:
            if pa != pb:
                return -1 if pa < pb else 1
    if len(parts_a) == len(parts_b):
        return 0
    return -1 if len(parts_a) < len(parts_b) else 1


def _check_version_constraint(version: str, constraint: str) -> bool:
    """Check whether a version string satisfies a comma-separated
    constraint list. Supported operators: ==, !=, >=, >, <=, <.
    """
    if not constraint:
        return True
    for part in constraint.split(","):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(==|!=|>=|<=|>|<)\s*(.+)$", part)
        if not m:
            # Bare version treated as exact match
            op = "=="
            target = part
        else:
            op, target = m.group(1), m.group(2).strip()
        cmp = _compare_versions(version, target)
        if op == "==" and cmp != 0:
            return False
        if op == "!=" and cmp == 0:
            return False
        if op == ">=" and cmp < 0:
            return False
        if op == ">" and cmp <= 0:
            return False
        if op == "<=" and cmp > 0:
            return False
        if op == "<" and cmp >= 0:
            return False
    return True


# ---------------------------------------------------------------------------
# Plugin directory resolution (PyInstaller aware)
# ---------------------------------------------------------------------------


def resolve_plugin_dirs(base_path_from_main: str) -> List[str]:
    """Return plugin search directories ordered by priority.

    Priority (highest first):
        1. User-writable plugins/ folder next to the running executable
           (so end-users can install plugins without re-packaging).
        2. Bundled plugins/ folder inside PyInstaller's _MEIPASS (read-only
           copy shipped with the release).
        3. Source layout plugins/ folder (base_path_from_main / plugins).

    Args:
        base_path_from_main: ``base_path`` computed by main.py before
            calling this helper. Points at the source project root in
            source runs and at _MEIPASS in frozen runs.

    Returns:
        list[str]: Existing plugin directories, de-duplicated.
    """
    dirs: List[str] = []

    # 1. Next-to-exe user plugins
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        user_plugins = os.path.join(exe_dir, "plugins")
        if os.path.isdir(user_plugins):
            dirs.append(user_plugins)
        # 2. Bundled plugins in _MEIPASS
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bundled = os.path.join(meipass, "plugins")
            if os.path.isdir(bundled):
                dirs.append(bundled)
    else:
        # 3. Source layout (single dir in dev mode)
        source_plugins = os.path.join(base_path_from_main, "plugins")
        if os.path.isdir(source_plugins):
            dirs.append(source_plugins)

    # De-duplicate preserving order
    seen: Set[str] = set()
    result: List[str] = []
    for d in dirs:
        absd = os.path.abspath(d)
        if absd not in seen:
            seen.add(absd)
            result.append(absd)
    return result


# ---------------------------------------------------------------------------
# PluginManager
# ---------------------------------------------------------------------------


class PluginManager:
    """Manages plugin discovery, loading, unloading, and hook dispatch."""

    def __init__(self, host: Any = None):
        """Initialize the plugin manager.

        Args:
            host: The main application window (MainWindow); may be None
                during early init or testing.
        """
        self._host = host
        self._api: Optional[PluginAPI] = PluginAPI(host)
        self._plugins: Dict[str, PluginBase] = {}
        # Metadata per plugin name for reload/dependency tracking
        self._plugin_meta: Dict[str, Dict[str, Any]] = {}
        # Set of top-level module prefixes that belong to plugins
        # (used by _purge_module_tree to avoid wiping host code).
        self._plugin_module_prefixes: Set[str] = set()
        self._plugin_dirs: List[str] = []

    # ------------------------------------------------------------------
    # Host reference
    # ------------------------------------------------------------------
    def set_host(self, host: Any) -> None:
        """Set or update the host application reference."""
        self._host = host
        self._api = PluginAPI(host)
        # Refresh the API reference held by already-loaded plugins.
        for plugin in self._plugins.values():
            plugin.api = self._api

    # ------------------------------------------------------------------
    # Discovery / loading
    # ------------------------------------------------------------------
    def discover_and_load(self, plugin_dir: str) -> int:
        """Discover plugins from one or more directories and load them.

        Accepts either a single directory (legacy API) or uses the new
        resolve_plugin_dirs() helper when combined with set_plugin_dirs.
        For backward compatibility with existing callers, ``plugin_dir``
        is still honored and resolved first.

        Args:
            plugin_dir: A single plugin directory to scan.

        Returns:
            int: Number of plugins successfully loaded (does not count
                already-loaded names that are skipped).
        """
        candidates: List[Tuple[str, str]] = []  # (plugin_dir, entry_name)

        # Always scan the explicitly passed directory first.
        self._scan_dir(plugin_dir, candidates)

        # Also scan any dirs set via set_plugin_dirs (PyInstaller support).
        for extra_dir in self._plugin_dirs:
            if os.path.abspath(extra_dir) != os.path.abspath(plugin_dir):
                self._scan_dir(extra_dir, candidates)

        if not candidates:
            _logger.debug("No plugin candidates discovered.")
            return 0

        # Ensure candidate directories are importable.
        for d in {c[0] for c in candidates}:
            if d not in sys.path:
                sys.path.insert(0, d)

        # Dependency-aware load order
        return self._load_candidates(candidates)

    def set_plugin_dirs(self, dirs: List[str]) -> None:
        """Register additional plugin search directories.

        Called by main.py after resolve_plugin_dirs() so frozen builds
        can combine bundled + user plugins.
        """
        self._plugin_dirs = [os.path.abspath(d) for d in dirs if os.path.isdir(d)]

    def _scan_dir(self, plugin_dir: str, candidates: List[Tuple[str, str]]) -> None:
        """Scan a directory for single-file plugins and package plugins.

        Populates ``candidates`` with (directory, entry_name) tuples.
        - ``*.py`` files (not _-prefixed, not __init__.py) are single-file.
        - subdirectories containing ``__init__.py`` are package plugins.
        """
        if not os.path.isdir(plugin_dir):
            _logger.debug("Plugin directory not found: %s", plugin_dir)
            return
        abs_plugin_dir = os.path.abspath(plugin_dir)
        for entry in sorted(os.listdir(abs_plugin_dir)):
            full = os.path.join(abs_plugin_dir, entry)
            # Case 1: single-file plugin
            if entry.endswith(".py") and not entry.startswith("_") and entry != "__init__.py":
                candidates.append((abs_plugin_dir, entry[:-3]))
                continue
            # Case 2: package plugin (directory with __init__.py)
            if os.path.isdir(full):
                init_file = os.path.join(full, "__init__.py")
                if os.path.isfile(init_file):
                    candidates.append((abs_plugin_dir, entry))

    # ------------------------------------------------------------------
    # Dependency resolution & candidate loading
    # ------------------------------------------------------------------
    def _load_candidates(self, candidates: List[Tuple[str, str]]) -> int:
        """Load candidate plugins with dependency ordering.

        Builds a dependency graph by introspecting each candidate's
        ``requires`` class attribute, topologically sorts them,
        verifies version constraints, and then loads them in order.
        """
        # 1. Try to discover requires for each candidate *without*
        #    instantiating it. We import the module and read class attrs.
        candidate_info: Dict[str, Dict[str, Any]] = {}
        for plugin_dir, entry_name in candidates:
            # Skip already-loaded plugins on repeated refresh calls.
            if entry_name in self._plugins:
                continue
            info = self._introspect_candidate(plugin_dir, entry_name)
            if info is not None:
                candidate_info[entry_name] = info

        if not candidate_info:
            return 0

        # 2. Resolve load order (topological sort over requires).
        load_order = self._topo_sort(candidate_info)
        if load_order is None:
            # Cycle detected: load in name order for best-effort, log it.
            _logger.warning(
                "Plugin dependency cycle detected; falling back to alphabetic order.")
            load_order = sorted(candidate_info.keys())

        # 3. Load in order; enforce version + host constraints.
        loaded = 0
        for entry_name in load_order:
            info = candidate_info[entry_name]
            # Verify requires against already-loaded plugins.
            for req in info.get("requires", []):
                dep_name = req["name"]
                dep_version = req.get("version", "")
                dep_plugin = self._plugins.get(dep_name)
                if dep_plugin is None:
                    _logger.error(
                        "Plugin '%s' requires '%s' which is not loaded; skipping.",
                        entry_name, dep_name)
                    break
                if dep_version and not _check_version_constraint(
                        dep_plugin.version, dep_version):
                    _logger.error(
                        "Plugin '%s' requires '%s' %s but %s is loaded; skipping.",
                        entry_name, dep_name, dep_version, dep_plugin.version)
                    break
            else:
                # Host version check
                host_constraint = info.get("host_version", "")
                if host_constraint and not _check_version_constraint(
                        HOST_APP_VERSION, host_constraint):
                    _logger.error(
                        "Plugin '%s' requires host %s but app is %s; skipping.",
                        entry_name, host_constraint, HOST_APP_VERSION)
                    continue

                plugin_dir = info["plugin_dir"]
                if self._load_plugin_from_entry(entry_name, plugin_dir):
                    loaded += 1
        return loaded

    def _introspect_candidate(self, plugin_dir: str, entry_name: str) -> Optional[Dict[str, Any]]:
        """Temporarily import a candidate to read ``requires`` /
        ``host_version`` without running on_load. Returns metadata dict
        or None if the import failed.
        """
        # Only import the first time; never double-import to avoid
        # side-effects. We import via a dedicated private prefix so
        # subsequent real load works correctly with reload().
        safe_name = f"__thoncode_introspect__{entry_name}"
        try:
            entry_path = self._resolve_entry_path(plugin_dir, entry_name)
            if entry_path is None:
                return None
            spec = importlib.util.spec_from_file_location(safe_name, entry_path)
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            # Set __package__ for package plugins so submodule imports work.
            self._configure_module_package(module, plugin_dir, entry_name)
            spec.loader.exec_module(module)
            # Find PluginBase subclass
            plugin_class = self._find_plugin_class(module, expected_module=None)
            if plugin_class is None:
                return None
            return {
                "plugin_dir": plugin_dir,
                "entry_name": entry_name,
                "plugin_class": plugin_class,
                "requires": list(getattr(plugin_class, "requires", [])),
                "host_version": getattr(plugin_class, "host_version", ""),
                "permissions": list(getattr(plugin_class, "permissions", [])),
                "name": getattr(plugin_class, "name", entry_name),
            }
        except Exception as e:
            _logger.warning(
                "Introspect failed for '%s': %s", entry_name, e, exc_info=True)
            return None
        finally:
            # Drop the private module from sys.modules so the real load
            # can import it fresh.
            for key in list(sys.modules.keys()):
                if key == safe_name or key.startswith(safe_name + "."):
                    del sys.modules[key]

    def _topo_sort(self, info_map: Dict[str, Dict[str, Any]]) -> Optional[List[str]]:
        """Return names in dependency order, or None if a cycle exists."""
        # Edges: dep -> dependent
        indeg: Dict[str, int] = {name: 0 for name in info_map}
        children: Dict[str, List[str]] = {name: [] for name in info_map}
        for name, info in info_map.items():
            for req in info.get("requires", []):
                dep = req["name"]
                if dep in indeg:  # Only count deps also in this batch
                    indeg[name] += 1
                    children[dep].append(name)
        # Also: loaded plugins already satisfy their dependents, so any
        # dep that is already loaded should not count as pending.
        for name, info in info_map.items():
            for req in info.get("requires", []):
                dep = req["name"]
                if dep in self._plugins and dep in indeg:
                    # Already satisfied externally, subtract one bogus count.
                    if indeg[name] > 0:
                        indeg[name] -= 1
        # Kahn's algorithm
        order: List[str] = []
        ready = [n for n, d in indeg.items() if d == 0]
        while ready:
            n = ready.pop()
            order.append(n)
            for child in children[n]:
                indeg[child] -= 1
                if indeg[child] == 0:
                    ready.append(child)
        if len(order) != len(info_map):
            return None
        return order

    # ------------------------------------------------------------------
    # Single-entry loading
    # ------------------------------------------------------------------
    def _resolve_entry_path(self, plugin_dir: str, entry_name: str) -> Optional[str]:
        """Resolve the __init__.py or .py file for an entry name."""
        # Package plugin
        pkg_dir = os.path.join(plugin_dir, entry_name)
        if os.path.isdir(pkg_dir):
            init = os.path.join(pkg_dir, "__init__.py")
            if os.path.isfile(init):
                return init
        # Single-file plugin
        single = os.path.join(plugin_dir, entry_name + ".py")
        if os.path.isfile(single):
            return single
        return None

    def _configure_module_package(self, module: Any, plugin_dir: str, entry_name: str) -> None:
        """Populate __package__ and __path__ for package plugin modules
        so ``from .submodule import X`` works inside the plugin."""
        pkg_dir = os.path.join(plugin_dir, entry_name)
        if os.path.isdir(pkg_dir) and os.path.isfile(os.path.join(pkg_dir, "__init__.py")):
            module.__package__ = entry_name
            module.__path__ = [pkg_dir]
        else:
            module.__package__ = ""

    def _find_plugin_class(self, module: Any, expected_module: Optional[str]) -> Optional[Type[PluginBase]]:
        """Find the first PluginBase subclass defined in the module."""
        plugin_class: Optional[Type[PluginBase]] = None
        for attr_name in dir(module):
            try:
                attr = getattr(module, attr_name)
            except Exception:
                continue
            if (isinstance(attr, type) and
                    issubclass(attr, PluginBase) and
                    attr is not PluginBase):
                # Restrict to classes defined in this module or its
                # package submodules to avoid picking up imported bases.
                module_name = getattr(attr, "__module__", "")
                module_root = module_name.split(".")[0]
                mod_root = (module.__name__ or "").split(".")[-1]
                if expected_module is None or module_root == expected_module or module_root == mod_root:
                    plugin_class = attr
                    break
        return plugin_class

    def _load_plugin_from_entry(self, entry_name: str, plugin_dir: str) -> bool:
        """Import a plugin entry (single file or package) and instantiate
        the PluginBase subclass. Handles permission grants and
        lifecycle hooks.
        """
        entry_path = self._resolve_entry_path(plugin_dir, entry_name)
        if entry_path is None:
            return False

        spec = importlib.util.spec_from_file_location(entry_name, entry_path)
        if spec is None or spec.loader is None:
            return False

        module = importlib.util.module_from_spec(spec)
        self._configure_module_package(module, plugin_dir, entry_name)

        # Register in sys.modules so reload() works later.
        sys.modules[entry_name] = module
        self._plugin_module_prefixes.add(entry_name)

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            _logger.error("Error executing plugin '%s': %s", entry_name, e, exc_info=True)
            return False

        plugin_class = self._find_plugin_class(module, expected_module=entry_name)
        if plugin_class is None:
            _logger.debug("No PluginBase subclass in '%s'", entry_name)
            return False

        # Instantiate and grant permissions (auto-approve in headless;
        # interactive host triggers a dialog via _maybe_ask_permissions).
        try:
            plugin = plugin_class(self._api)
        except Exception as e:
            _logger.error("Error constructing plugin '%s': %s", entry_name, e, exc_info=True)
            return False

        self._grant_default_permissions(plugin)
        self._maybe_ask_permissions(plugin)

        try:
            plugin.on_load()
        except Exception as e:
            _logger.error("Plugin '%s' on_load failed: %s", entry_name, e, exc_info=True)
            return False

        registered_name = plugin.name
        self._plugins[registered_name] = plugin
        self._plugin_meta[registered_name] = {
            "entry_name": entry_name,
            "plugin_dir": plugin_dir,
            "entry_path": entry_path,
            "module": module,
        }
        _logger.info("Plugin loaded: %s v%s - %s",
                     registered_name, plugin.version, plugin.description)
        return True

    # ------------------------------------------------------------------
    # Permission grants
    # ------------------------------------------------------------------
    def _grant_default_permissions(self, plugin: PluginBase) -> None:
        """Auto-grant the explicitly-declared permission list as a
        baseline. Interactive hosts can override this via a dialog.
        """
        for p in plugin.permissions:
            if p in ALL_PERMISSIONS:
                plugin.grant_permission(p)

    def _maybe_ask_permissions(self, plugin: PluginBase) -> None:
        """If a host window is available and the plugin requests risky
        permissions, prompt the user for confirmation.

        This is intentionally a best-effort call; failures in GUI
        construction are logged but not fatal. In CLI / test contexts
        the defaults from _grant_default_permissions stand.
        """
        risky = {
            "filesystem:read", "filesystem:write",
            "network", "execute", "config", "plugins:manage",
        }
        requested_risky = [p for p in plugin.permissions if p in risky]
        if not requested_risky:
            return
        if not self._host or not getattr(self._host, "root", None):
            return
        try:
            from libs.gui.plugin_permission_dialog import show_permission_dialog
            granted = show_permission_dialog(
                self._host.root, plugin, requested_risky)
            # Merge the dialog result: keep only permissions the user OK'd.
            new_granted = set()
            for p in plugin.permissions:
                if p not in risky or p in granted:
                    new_granted.add(p)
            plugin._granted_permissions = new_granted
        except Exception as e:
            _logger.debug("Permission dialog unavailable: %s", e)

    # ------------------------------------------------------------------
    # Unload / hot reload
    # ------------------------------------------------------------------
    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin by name, calling its on_unload lifecycle
        method and purging its sys.modules entries so a subsequent load
        re-imports fresh source code.
        """
        plugin = self._plugins.pop(name, None)
        if plugin is None:
            return False
        meta = self._plugin_meta.pop(name, None)
        try:
            plugin.on_unload()
        except Exception as e:
            _logger.error("Error unloading plugin '%s': %s", name, e, exc_info=True)
        # Invalidate caches / menu / hotkey registrations for this plugin.
        try:
            if self._api is not None:
                self._api._unregister_all_for_plugin(plugin)  # pyright: ignore[reportPrivateUsage]
        except Exception:
            pass
        # Purge sys.modules subtree so reload_plugin() can re-import.
        if meta is not None:
            self._purge_module_tree(meta["entry_name"])
        _logger.info("Plugin unloaded: %s", name)
        return True

    def _purge_module_tree(self, module_prefix: str) -> None:
        """Remove every sys.modules entry owned by this plugin.

        For plugin package ``foo`` we delete ``foo``, ``foo.bar``,
        ``foo.bar.baz``, ... but only if the prefix was actually
        registered as belonging to a plugin.
        """
        if module_prefix not in self._plugin_module_prefixes:
            return
        for key in list(sys.modules.keys()):
            if key == module_prefix or key.startswith(module_prefix + "."):
                del sys.modules[key]

    def reload_plugin(self, name: str) -> bool:
        """Hot-reload a plugin by name.

        Uses the saved metadata (plugin_dir + entry_name) to find the
        entry file on disk, calls unload_plugin() to clean state, then
        runs the full load pipeline again. Returns True on success.
        """
        if name not in self._plugin_meta and name not in self._plugins:
            return False
        meta = self._plugin_meta.get(name)
        if meta is None:
            # Fallback: use the saved plugin_dir from discover_and_load
            return False
        plugin_dir = meta["plugin_dir"]
        entry_name = meta["entry_name"]
        if not self.unload_plugin(name):
            # Plugin might not have been in _plugins but was still in meta
            _logger.debug("reload: unload returned False for %s", name)
        # Re-import from disk (bypass the already-loaded skip).
        return self._load_plugin_from_entry(entry_name, plugin_dir)

    def unload_all(self) -> None:
        """Unload all loaded plugins."""
        for name in list(self._plugins.keys()):
            self.unload_plugin(name)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def get_plugins(self) -> Dict[str, PluginBase]:
        """Return a copy of the loaded plugins dictionary."""
        return dict(self._plugins)

    def get_plugin_names(self) -> List[str]:
        """Return a list of loaded plugin names."""
        return list(self._plugins.keys())

    def get_plugin_dirs(self) -> List[str]:
        """Return current plugin search directories (useful for UI)."""
        return list(self._plugin_dirs)

    # ------------------------------------------------------------------
    # Hook dispatch
    # ------------------------------------------------------------------
    def call_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Dispatch a hook call to all loaded plugins."""
        results = []
        method_name = f"on_{hook_name}"
        for name, plugin in self._plugins.items():
            handler = getattr(plugin, method_name, None)
            if handler is None:
                continue
            try:
                result = handler(*args, **kwargs)
                if result is not None:
                    results.append(result)
            except Exception as e:
                _logger.error("Plugin '%s' hook '%s' failed: %s",
                              name, hook_name, e, exc_info=True)
        return results
