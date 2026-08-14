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

Permission flags (declarative, user-approved at load-time):
    PERMISSION_FILESYSTEM_READ    - Read files outside the project
    PERMISSION_FILESYSTEM_WRITE   - Write files outside the project
    PERMISSION_NETWORK            - Open network connections
    PERMISSION_EXECUTE            - Execute external processes
    PERMISSION_CONFIG             - Read/write host configuration
    PERMISSION_EDITOR_MODIFY      - Modify editor content/selection
    PERMISSION_MENU_REGISTER      - Register menu items
    PERMISSION_HOTKEY_BIND        - Bind global keyboard shortcuts
    PERMISSION_HIGHLIGHT_EXTEND   - Extend syntax highlighting rules
    PERMISSION_PLUGIN_MANAGE      - Load/unload other plugins

Dependency declaration example:
    requires = [
        {"name": "core_utils", "version": ">=1.0.0,<2.0.0"},
        {"name": "sdk_base",    "version": "==3.2.1"},
    ]
"""

from typing import TYPE_CHECKING, List, Dict, Optional

if TYPE_CHECKING:
    from libs.plugins.plugin_api import PluginAPI


# Permission constants
PERMISSION_FILESYSTEM_READ = "filesystem:read"
PERMISSION_FILESYSTEM_WRITE = "filesystem:write"
PERMISSION_NETWORK = "network"
PERMISSION_EXECUTE = "execute"
PERMISSION_CONFIG = "config"
PERMISSION_EDITOR_MODIFY = "editor:modify"
PERMISSION_MENU_REGISTER = "ui:menu_register"
PERMISSION_HOTKEY_BIND = "ui:hotkey_bind"
PERMISSION_HIGHLIGHT_EXTEND = "editor:highlight_extend"
PERMISSION_PLUGIN_MANAGE = "plugins:manage"

ALL_PERMISSIONS = (
    PERMISSION_FILESYSTEM_READ,
    PERMISSION_FILESYSTEM_WRITE,
    PERMISSION_NETWORK,
    PERMISSION_EXECUTE,
    PERMISSION_CONFIG,
    PERMISSION_EDITOR_MODIFY,
    PERMISSION_MENU_REGISTER,
    PERMISSION_HOTKEY_BIND,
    PERMISSION_HIGHLIGHT_EXTEND,
    PERMISSION_PLUGIN_MANAGE,
)


class PluginBase:
    """Base class all Thon Code plugins must inherit.

    Subclasses should set the class attributes for identification and
    declarative metadata (permissions, requirements), then override
    ``on_load`` / ``on_unload`` for lifecycle management. Hook handlers
    are optional methods named ``on_<hook_name>``.
    """

    # Identification (required to be overridden)
    name: str = "unnamed"
    version: str = "0.1.0"
    description: str = ""
    author: str = ""

    # Declarative extension metadata
    # Permissions that this plugin *requests*. The actual set granted
    # is a subset chosen by the user (or auto-approved for
    # low-risk flags in unattended runs).
    permissions: List[str] = []

    # Dependencies on other plugins. Each entry is a dict with:
    #   {"name": str, "version": str}
    # version supports the syntax:
    #   ==X.Y.Z (exact), >=X.Y.Z (min), >X.Y.Z, <=X.Y.Z, <X.Y.Z
    #   Multiple constraints can be comma-separated e.g. ">=1.0,<2.0"
    requires: List[Dict[str, str]] = []

    # Optional: Minimum host app version required.
    # Uses the same constraint syntax as ``requires``.
    host_version: str = ""

    # ------------------------------------------------------------------
    def __init__(self, api: "PluginAPI"):
        """Store the plugin API reference for later use.

        Args:
            api: PluginAPI instance providing access to host services
        """
        self.api = api
        # Runtime state – filled in by PluginManager after grant dialog
        self._granted_permissions: set = set()

    # ------------------------------------------------------------------
    # Permission helpers
    # ------------------------------------------------------------------
    def has_permission(self, permission: str) -> bool:
        """Check whether the plugin was granted a specific permission.

        Args:
            permission: One of the PERMISSION_* constants

        Returns:
            bool: True if permission was granted
        """
        return permission in self._granted_permissions

    def grant_permission(self, permission: str) -> None:
        """Internal: record that a permission was granted.

        Called by PluginManager during load after the user confirms the
        grant dialog. Plugins do not call this themselves.
        """
        self._granted_permissions.add(permission)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
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
