#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-plugins",
    "Name": "Thon Code Plugin Marketplace Client",
    "Path": ".main.libs.plugins.plugin_marketplace",
    "Entrance": "main.py"
}

"""Plugin marketplace client.

Implements a very small JSON protocol over HTTP(S) so users can point
the IDE at their own registry (URL configurable in settings).

Remote schema (GET {market_url}/index.json):
    {
      "version": 1,
      "plugins": [
        {
          "id": "my-plugin",
          "name": "My Plugin",
          "version": "1.2.0",
          "author": "Someone",
          "description": "...",
          "package_url": "https://.../my-plugin-1.2.0.zip",
          "package_sha256": "(optional) hex digest",
          "requires": [{"name": "...", "version": ">=1.0"}],
          "changelog": "(optional) release notes text",
          "tags": ["(optional)", "tags"],
          "category": "(optional) category name",
          "size_bytes": 12345
        },
        ...
      ]
    }

A *package zip* contains either:
  - a single ``*.py`` file (single-file plugin), or
  - a folder containing a ``__init__.py`` plus sibling modules
    (package plugin).

Installed packages are extracted into the user-writable plugins
directory (next to the executable in frozen builds, or ./plugins in
source runs).
"""

import hashlib
import io
import json
import logging
import os
import shutil
import sys
import urllib.request
import zipfile
from typing import Any, Dict, List, Optional

from libs.plugins.plugin_manager import resolve_plugin_dirs

_logger = logging.getLogger("thoncode.plugins.marketplace")

_DEFAULT_TIMEOUT = 15.0


class PluginMarketplace:
    """Client for a user-provided plugin marketplace URL."""

    def __init__(self, market_url: str = "", timeout: float = _DEFAULT_TIMEOUT):
        self.market_url = (market_url or "").rstrip("/")
        self.timeout = timeout
        self._cached_index: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Remote fetch
    # ------------------------------------------------------------------
    def _url(self, path: str) -> str:
        if not self.market_url:
            raise RuntimeError("Marketplace URL is not configured.")
        return f"{self.market_url}/{path.lstrip('/')}"

    def fetch_index(self, force: bool = False) -> Dict[str, Any]:
        """Download and cache the remote index.json.

        Returns:
            Parsed index dict with at least {"plugins": [...]}.
        """
        if self._cached_index is not None and not force:
            return self._cached_index
        if not self.market_url:
            return {"version": 1, "plugins": []}
        url = self._url("/index.json")
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                data = resp.read()
            parsed = json.loads(data.decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("index.json root must be an object")
            parsed.setdefault("plugins", [])
            self._cached_index = parsed
            return parsed
        except Exception as e:
            _logger.warning("Marketplace index fetch failed (%s): %s", url, e)
            return {"version": 1, "plugins": []}

    def list_available(self) -> List[Dict[str, Any]]:
        """Return the list of plugins advertised in the marketplace."""
        return list(self.fetch_index().get("plugins", []))

    # ------------------------------------------------------------------
    # Install / uninstall
    # ------------------------------------------------------------------
    @staticmethod
    def user_writable_plugin_dir(base_path_from_main: str) -> str:
        """Pick a user-writable plugin directory.

        Priority:
          1. plugins/ next to sys.executable (frozen builds, always writable).
          2. base_path_from_main / plugins (source layout).
        Creates the directory if missing.
        """
        target = ""
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            target = os.path.join(exe_dir, "plugins")
        if not target:
            target = os.path.join(base_path_from_main, "plugins")
        os.makedirs(target, exist_ok=True)
        return target

    def install_plugin(self, plugin_entry: Dict[str, Any],
                       install_dir: str,
                       expected_sha256: str = "",
                       category: str = "") -> Dict[str, Any]:
        """Download and extract a plugin package into install_dir.

        Args:
            plugin_entry: One entry from ``list_available()``.
            install_dir: Directory to place the plugin into.
            expected_sha256: Optional SHA256 hex digest override (takes
                precedence over the value in plugin_entry).
            category: Optional subdirectory under ``install_dir``; the
                subdirectory is created if missing and the plugin is
                extracted there instead of flat into ``install_dir``.

        Returns:
            {"status": "ok"|"error", "data": str, "installed_paths": [str]}
        """
        package_url = plugin_entry.get("package_url")
        if not package_url:
            return {"status": "error",
                    "data": "Plugin entry has no package_url",
                    "installed_paths": []}
        sha = expected_sha256 or plugin_entry.get("package_sha256", "")
        try:
            with urllib.request.urlopen(package_url, timeout=self.timeout) as resp:
                blob = resp.read()
        except Exception as e:
            return {"status": "error",
                    "data": f"Download failed: {e}",
                    "installed_paths": []}
        if sha:
            actual = hashlib.sha256(blob).hexdigest()
            if actual.lower() != sha.lower():
                return {"status": "error",
                        "data": f"Checksum mismatch: expected {sha}, got {actual}",
                        "installed_paths": []}

        target_dir = install_dir
        if category:
            target_dir = os.path.join(install_dir, category)
            os.makedirs(target_dir, exist_ok=True)
        try:
            installed = self._extract_plugin_zip(blob, target_dir)
            return {"status": "ok",
                    "data": f"Installed {len(installed)} file(s) to {target_dir}",
                    "installed_paths": installed}
        except Exception as e:
            return {"status": "error",
                    "data": f"Extract failed: {e}",
                    "installed_paths": []}

    @staticmethod
    def categorize_entry(entry: Dict[str, Any]) -> str:
        """Return a category string for the given marketplace entry.

        Tries ``entry["category"]`` first, then the first tag in
        ``entry["tags"]``, and finally falls back to ``"misc"``.
        """
        cat = entry.get("category")
        if cat:
            return str(cat)
        tags = entry.get("tags") or []
        if isinstance(tags, list) and tags:
            return str(tags[0])
        if isinstance(tags, str) and tags:
            return tags
        return "misc"

    @staticmethod
    def _extract_plugin_zip(blob: bytes, install_dir: str) -> List[str]:
        """Validate and extract a plugin zip into install_dir.

        Security: zip slip is mitigated by rejecting any archive entry
        whose resolved path escapes ``install_dir``.
        """
        installed: List[str] = []
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            abs_install = os.path.abspath(install_dir)
            top_level_dirs: set = set()
            for info in zf.infolist():
                if info.is_dir():
                    continue
                target_path = os.path.normpath(os.path.join(abs_install, info.filename))
                if not target_path.startswith(abs_install + os.sep) and target_path != abs_install:
                    raise ValueError(f"Unsafe archive path: {info.filename}")
                parent = os.path.dirname(target_path)
                os.makedirs(parent, exist_ok=True)
                with zf.open(info) as src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                installed.append(target_path)
                top_level = info.filename.split("/", 1)[0]
                top_level_dirs.add(top_level)
        return installed

    # ------------------------------------------------------------------
    # Uninstall helpers (walk-and-delete an installed plugin name).
    # ------------------------------------------------------------------
    @staticmethod
    def uninstall_plugin(name: str, install_dir: str) -> bool:
        """Delete ``name.py`` or directory ``name`` inside ``install_dir``.

        Returns True if anything was actually removed.
        """
        abs_dir = os.path.abspath(install_dir)
        single = os.path.join(abs_dir, name + ".py")
        pkg = os.path.join(abs_dir, name)
        removed = False
        if os.path.isfile(single):
            os.remove(single)
            removed = True
        if os.path.isdir(pkg):
            shutil.rmtree(pkg, ignore_errors=True)
            removed = True
        return removed

    # ------------------------------------------------------------------
    # Compare installed vs. available versions for "updates available".
    # ------------------------------------------------------------------
    def find_updates(self, installed_names_to_versions: Dict[str, str]) -> List[Dict[str, Any]]:
        """Return marketplace entries that are strictly newer than installed."""
        from libs.plugins.plugin_manager import _compare_versions
        updates: List[Dict[str, Any]] = []
        for remote in self.list_available():
            rid = remote.get("id") or remote.get("name")
            if not rid:
                continue
            installed_ver = installed_names_to_versions.get(rid)
            if installed_ver is None:
                continue
            remote_ver = remote.get("version", "0.0.0")
            if _compare_versions(remote_ver, installed_ver) > 0:
                updates.append(remote)
        return updates
