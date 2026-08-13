#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-plugins",
    "Name": "Thon Code Plugin API",
    "Path": ".main.libs.plugins.plugin_api",
    "Entrance": "main.py"
}

"""Controlled API surface exposed to plugins.

PluginAPI wraps host application services behind a stable interface
so plugins cannot directly access internal modules. This decoupling
allows the host internals to change without breaking plugins.

Available hooks (plugins implement any subset as on_<hook_name>):
    on_load()              - Plugin loaded, before first use
    on_unload()            - Plugin about to be unloaded
    on_file_open(path)     - A file was opened in the editor
    on_file_save(path)     - A file was saved
    on_file_close(path)    - A file was closed
    on_editor_change(text) - Editor content modified
    on_tree_refresh()      - File tree was refreshed
    on_theme_change(name)  - Theme was switched
    on_project_open(path)  - A project folder was opened
"""

import logging
from typing import Any, Callable, Optional, List


class PluginAPI:
    """Stable API through which plugins interact with the host application.

    The host constructs a PluginAPI and passes it to each plugin on load.
    Plugins use this object to read config, log messages, show status,
    and access editor/tree services without importing host internals.
    """

    def __init__(self, host: Any):
        """Initialize the API with a reference to the host application.

        Args:
            host: The main application window object (MainWindow)
        """
        self._host = host
        self._logger = logging.getLogger("thoncode.plugins.api")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def get_logger(self, name: str) -> logging.Logger:
        """Return a logger for the plugin.

        Args:
            name: Logger name (typically the plugin name)

        Returns:
            logging.Logger: Logger instance configured by the host
        """
        return logging.getLogger(f"thoncode.plugin.{name}")

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def get_config(self) -> dict:
        """Return the current application configuration dictionary.

        Returns:
            dict: Configuration data from config.json
        """
        try:
            return self._host._get_cfg_data()
        except Exception:
            return {}

    def set_config(self, key: str, value: Any) -> bool:
        """Update a configuration key and persist to disk.

        Args:
            key: Config key to update
            value: New value

        Returns:
            bool: True if the config was written successfully
        """
        try:
            cfg = self._host._get_cfg_data()
            cfg[key] = value
            import libs.cfg_handle as cfg_handle
            cfg_handle.cfg_handle().write_cfg(cfg)
            return True
        except Exception as e:
            self._logger.debug("Failed to set config %s: %s", key, e)
            return False

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def show_status(self, message: str) -> None:
        """Display a message in the host's status bar.

        Args:
            message: Status text to display
        """
        try:
            self._host.status_bar.configure(text=message)
        except Exception:
            self._logger.debug("Failed to set status: %s", message)

    # ------------------------------------------------------------------
    # Editor access
    # ------------------------------------------------------------------

    def get_editor_text(self) -> str:
        """Return the current editor content.

        Returns:
            str: Editor text content, or empty string if unavailable
        """
        try:
            if self._host.textbox_widget and self._host.textbox_widget.winfo_exists():
                return self._host.textbox_widget.get("1.0", "end-1c")
        except Exception:
            pass
        return ""

    def set_editor_text(self, text: str) -> None:
        """Replace the editor content with the given text.

        Args:
            text: New editor content
        """
        try:
            if self._host.textbox_widget and self._host.textbox_widget.winfo_exists():
                self._host.textbox_widget.delete("1.0", "end")
                self._host.textbox_widget.insert("1.0", text)
        except Exception:
            self._logger.debug("Failed to set editor text")

    def get_editor_selection(self) -> str:
        """Return the currently selected text in the editor.

        Returns:
            str: Selected text, or empty string if no selection
        """
        try:
            if self._host.textbox_widget and self._host.textbox_widget.winfo_exists():
                return self._host.textbox_widget.selection_get()
        except Exception:
            pass
        return ""

    def insert_editor_text(self, text: str, position: str = "insert") -> None:
        """Insert text at the given position in the editor.

        Args:
            text: Text to insert
            position: Tk index (default "insert" = cursor position)
        """
        try:
            if self._host.textbox_widget and self._host.textbox_widget.winfo_exists():
                self._host.textbox_widget.insert(position, text)
        except Exception:
            self._logger.debug("Failed to insert editor text")

    # ------------------------------------------------------------------
    # Project info
    # ------------------------------------------------------------------

    def get_project_root(self) -> str:
        """Return the current project root directory path.

        Returns:
            str: Project root path
        """
        try:
            return self._host.project_root
        except Exception:
            return ""

    def get_current_file(self) -> Optional[str]:
        """Return the path of the currently open file.

        Returns:
            str or None: Current file path, or None if no file is open
        """
        try:
            return self._host.current_file
        except Exception:
            return None

    def get_recent_projects(self) -> List[str]:
        """Return the list of recently opened project paths.

        Returns:
            list[str]: Recent project paths (most recent first)
        """
        try:
            import libs.cfg_handle as cfg_handle
            return cfg_handle.cfg_handle().get_recent_projects()
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def get_current_theme(self) -> str:
        """Return the current theme name.

        Returns:
            str: Theme name (e.g., 'darkly', 'vscode_dark')
        """
        try:
            from libs.gui import theme
            return theme.get_theme()
        except Exception:
            return ""

    def get_accent_color(self) -> Optional[str]:
        """Return the current accent color override, or None.

        Returns:
            str or None: Hex color string or None if using theme default
        """
        try:
            from libs.gui import theme
            return theme.get_accent_color()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Tree access
    # ------------------------------------------------------------------

    def refresh_file_tree(self) -> None:
        """Trigger a refresh of the file tree."""
        try:
            if self._host.tree_manager:
                self._host.tree_manager.refresh()
        except Exception:
            self._logger.debug("Failed to refresh file tree")

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def get_text(self, key: str) -> str:
        """Get a localized string by dot-separated key.

        Args:
            key: i18n key (e.g., 'status.ready')

        Returns:
            str: Localized text or the key itself if not found
        """
        try:
            return getattr(self._host.langs_cfg, key.replace('.', '_'), key)
        except Exception:
            return key

    # ------------------------------------------------------------------
    # Plugin management
    # ------------------------------------------------------------------

    def get_plugin_names(self) -> List[str]:
        """Return the names of all loaded plugins.

        Returns:
            list[str]: Plugin names
        """
        try:
            if self._host.plugin_manager:
                return self._host.plugin_manager.get_plugin_names()
        except Exception:
            pass
        return []
