#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-plugins",
    "Name": "Thon Code Plugins",
    "Path": ".main.libs.plugins",
    "Entrance": "main.py"
}

"""Thon Code plugin system package.

Exports:
    PluginBase: Abstract base class for plugins
    PluginManager: Discovery, loading, and hook dispatch
    PluginAPI: Controlled API surface for plugins
"""

from libs.plugins.plugin_base import (
    PluginBase,
    ALL_PERMISSIONS,
    PERMISSION_CONFIG,
    PERMISSION_EDITOR_MODIFY,
    PERMISSION_FILESYSTEM_READ,
    PERMISSION_FILESYSTEM_WRITE,
    PERMISSION_HIGHLIGHT_EXTEND,
    PERMISSION_HOTKEY_BIND,
    PERMISSION_MENU_REGISTER,
    PERMISSION_NETWORK,
    PERMISSION_EXECUTE,
    PERMISSION_PLUGIN_MANAGE,
)
from libs.plugins.plugin_manager import PluginManager, resolve_plugin_dirs
from libs.plugins.plugin_api import PluginAPI
from libs.plugins.plugin_marketplace import PluginMarketplace

__all__ = [
    "PluginBase",
    "PluginManager",
    "PluginAPI",
    "PluginMarketplace",
    "resolve_plugin_dirs",
    "ALL_PERMISSIONS",
    "PERMISSION_CONFIG",
    "PERMISSION_EDITOR_MODIFY",
    "PERMISSION_FILESYSTEM_READ",
    "PERMISSION_FILESYSTEM_WRITE",
    "PERMISSION_HIGHLIGHT_EXTEND",
    "PERMISSION_HOTKEY_BIND",
    "PERMISSION_MENU_REGISTER",
    "PERMISSION_NETWORK",
    "PERMISSION_EXECUTE",
    "PERMISSION_PLUGIN_MANAGE",
]
