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

from libs.plugins.plugin_base import PluginBase
from libs.plugins.plugin_manager import PluginManager
from libs.plugins.plugin_api import PluginAPI

__all__ = ["PluginBase", "PluginManager", "PluginAPI"]
