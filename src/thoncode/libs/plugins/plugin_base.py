#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-plugins",
    "Name": "Thon Code Plugin Base",
    "Path": ".main.libs.plugins.plugin_base",
    "Entrance": "main.py"
}

"""Abstract base class for all Thon Code plugins.

Plugins inherit from PluginBase and override lifecycle methods
(on_load, on_unload) and hook handlers as needed. Each plugin
receives a PluginAPI instance granting controlled access to the
host application's services.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from libs.plugins.plugin_api import PluginAPI


class PluginBase:
    """Base class all Thon Code plugins must inherit.

    Subclasses should set the class attributes ``name``, ``version``,
    and ``description`` for identification, and override ``on_load``
    / ``on_unload`` for lifecycle management. Hook handlers are
    optional methods named ``on_<hook_name>``.
    """

    name: str = "unnamed"
    version: str = "0.1.0"
    description: str = ""
    author: str = ""

    def __init__(self, api: "PluginAPI"):
        """Store the plugin API reference for later use.

        Args:
            api: PluginAPI instance providing access to host services
        """
        self.api = api

    def on_load(self) -> None:
        """Called when the plugin is first loaded.

        Override to perform initialization such as registering
        menu items, setting up resources, or subscribing to hooks.
        """
        pass

    def on_unload(self) -> None:
        """Called when the plugin is being unloaded.

        Override to clean up resources, remove UI elements, or
        save state. Should be safe to call even if on_load failed.
        """
        pass
