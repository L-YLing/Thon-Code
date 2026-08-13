#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-plugins",
    "Name": "Thon Code Plugin Manager",
    "Path": ".main.libs.plugins.plugin_manager",
    "Entrance": "main.py"
}

"""Plugin discovery, loading, and lifecycle management.

PluginManager scans a plugin directory for Python modules, imports each,
finds PluginBase subclasses, instantiates them with a PluginAPI, and
manages their lifecycle. Hook calls are dispatched to all active plugins
with error isolation so a single plugin failure never crashes the host.
"""

import os
import sys
import logging
import importlib
import importlib.util
from typing import Any, Dict, List, Optional, Type

from libs.plugins.plugin_base import PluginBase
from libs.plugins.plugin_api import PluginAPI

_logger = logging.getLogger("thoncode.plugins.manager")


class PluginManager:
    """Manages plugin discovery, loading, unloading, and hook dispatch.

    Plugins are discovered from a directory (default: ``plugins/`` next
    to the project root). Each ``.py`` file is imported as a module and
    scanned for PluginBase subclasses. The first subclass found is
    instantiated with a shared PluginAPI and its ``on_load`` is called.

    Hook dispatch uses ``call_hook(name, *args)`` which invokes
    ``plugin.on_<name>(*args)`` on every loaded plugin. Exceptions in
    individual plugins are caught and logged so one broken plugin
    doesn't affect others.
    """

    def __init__(self, host: Any = None):
        """Initialize the plugin manager.

        A PluginAPI is always created so plugins can be loaded even
        before the host window is ready (host may be None); PluginAPI
        methods guard all host access with try/except so None is safe.
        Use set_host() once the main window exists to give plugins
        full access to host services.

        Args:
            host: The main application window (MainWindow); may be None
                during early init or testing.
        """
        self._host = host
        self._api: Optional[PluginAPI] = PluginAPI(host)
        self._plugins: Dict[str, PluginBase] = {}
        self._plugin_dir: str = ""

    def set_host(self, host: Any) -> None:
        """Set or update the host application reference.

        Args:
            host: The main application window
        """
        self._host = host
        self._api = PluginAPI(host)

    def discover_and_load(self, plugin_dir: str) -> int:
        """Discover plugins from a directory and load all valid ones.

        Scans for ``.py`` files (excluding ``__init__.py`` and files
        starting with ``_``), imports each as a module, and instantiates
        the first PluginBase subclass found.

        Args:
            plugin_dir: Absolute path to the plugins directory

        Returns:
            int: Number of plugins successfully loaded
        """
        self._plugin_dir = plugin_dir
        if not os.path.isdir(plugin_dir):
            _logger.debug("Plugin directory not found: %s", plugin_dir)
            return 0

        # Ensure plugin directory is importable
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)

        loaded_count = 0
        for filename in sorted(os.listdir(plugin_dir)):
            if not filename.endswith('.py'):
                continue
            if filename.startswith('_') or filename == '__init__.py':
                continue

            module_name = filename[:-3]
            try:
                if self._load_plugin_from_file(module_name, plugin_dir):
                    loaded_count += 1
            except Exception as e:
                _logger.error("Failed to load plugin '%s': %s", module_name, e,
                              exc_info=True)

        _logger.info("Loaded %d plugin(s) from %s", loaded_count, plugin_dir)
        return loaded_count

    def _load_plugin_from_file(self, module_name: str, plugin_dir: str) -> bool:
        """Import a plugin module and instantiate its PluginBase subclass.

        Args:
            module_name: Module name (filename without .py)
            plugin_dir: Directory containing the plugin file

        Returns:
            bool: True if a plugin was successfully loaded
        """
        file_path = os.path.join(plugin_dir, f"{module_name}.py")
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return False

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            _logger.error("Error executing plugin '%s': %s", module_name, e,
                          exc_info=True)
            return False

        # Find the first PluginBase subclass defined in the module
        plugin_class: Optional[Type[PluginBase]] = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                    issubclass(attr, PluginBase) and
                    attr is not PluginBase and
                    attr.__module__ == module.__name__):
                plugin_class = attr
                break

        if plugin_class is None:
            _logger.debug("No PluginBase subclass in '%s'", module_name)
            return False

        try:
            plugin = plugin_class(self._api)
            plugin.on_load()
            self._plugins[plugin.name] = plugin
            _logger.info("Plugin loaded: %s v%s - %s",
                         plugin.name, plugin.version, plugin.description)
            return True
        except Exception as e:
            _logger.error("Error initializing plugin '%s': %s", module_name, e,
                          exc_info=True)
            return False

    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin by name, calling its on_unload lifecycle method.

        Args:
            name: Plugin name (the ``name`` class attribute)

        Returns:
            bool: True if the plugin was found and unloaded
        """
        plugin = self._plugins.pop(name, None)
        if plugin is None:
            return False
        try:
            plugin.on_unload()
        except Exception as e:
            _logger.error("Error unloading plugin '%s': %s", name, e,
                          exc_info=True)
        _logger.info("Plugin unloaded: %s", name)
        return True

    def unload_all(self) -> None:
        """Unload all loaded plugins."""
        for name in list(self._plugins.keys()):
            self.unload_plugin(name)

    def get_plugins(self) -> Dict[str, PluginBase]:
        """Return a copy of the loaded plugins dictionary.

        Returns:
            dict: Mapping of plugin name to PluginBase instance
        """
        return dict(self._plugins)

    def get_plugin_names(self) -> List[str]:
        """Return a list of loaded plugin names.

        Returns:
            list: Plugin name strings
        """
        return list(self._plugins.keys())

    def call_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Dispatch a hook call to all loaded plugins.

        For each plugin, calls ``plugin.on_<hook_name>(*args, **kwargs)``
        if the method exists. Exceptions are caught and logged so one
        plugin's failure doesn't prevent others from receiving the hook.

        Args:
            hook_name: Hook identifier (e.g., 'file_open', 'editor_init')
            *args: Positional arguments to pass to hook handlers
            **kwargs: Keyword arguments to pass to hook handlers

        Returns:
            list: Non-None return values from each plugin's handler
        """
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
