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
"""

import logging
from typing import Any, Callable, Optional


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
