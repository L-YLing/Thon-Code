#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Plugin Manager UI",
    "Path": ".main.libs.gui.plugin_ui",
    "Entrance": "main.py"
}

"""Plugin manager UI window.

Displays all loaded plugins with their name, version, description, and
status. Provides a refresh button to re-discover plugins from the
plugins directory without restarting the application.
"""

import os
import ttkbootstrap as ttkb
from tkinter import ttk
import tkinter as tk
from typing import Any

import libs.langs_loader as langs_loader
from libs.gui import theme


class PluginManagerWindow:
    """Window displaying loaded plugins and their metadata.

    Shows a read-only list of discovered plugins with name, version,
    description, and load status. A refresh button re-runs discovery
    so newly added plugin files are picked up at runtime.
    """

    def __init__(self, parent, plugin_manager: Any):
        """Initialize the plugin manager window.

        Args:
            parent: Parent window
            plugin_manager: PluginManager instance to inspect
        """
        self.parent = parent
        self.plugin_manager = plugin_manager
        self.lang = langs_loader.langs()

        self._create_window()
        self._refresh_list()

    def _get_text(self, key: str) -> str:
        """Get localized text by dot-separated key.

        Args:
            key: Dot-separated i18n key

        Returns:
            Localized string or the key itself if not found
        """
        return getattr(self.lang, key.replace('.', '_'), key)

    def _create_window(self):
        """Create the plugin manager window with a treeview and buttons."""
        self.window = ttkb.Toplevel(self.parent)
        self.window.title(self._get_text("plugins.title"))
        self.window.geometry("600x400")
        self.window.transient(self.parent)
        self.window.lift()
        self.window.focus_force()

        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Header
        ttk.Label(
            main_frame,
            text=self._get_text("plugins.title"),
            font=("Microsoft YaHei", 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        # Plugin treeview
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))

        columns = ("name", "version", "description", "status")
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", height=12)
        self.tree.heading("name", text=self._get_text("plugins.col_name"))
        self.tree.heading("version", text=self._get_text("plugins.col_version"))
        self.tree.heading("description", text=self._get_text("plugins.col_description"))
        self.tree.heading("status", text=self._get_text("plugins.col_status"))
        self.tree.column("name", width=120)
        self.tree.column("version", width=70)
        self.tree.column("description", width=250)
        self.tree.column("status", width=80)

        scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x")

        ttk.Button(
            btn_frame,
            text=self._get_text("plugins.refresh"),
            command=self._on_refresh,
            style="Info.TButton",
        ).pack(side="left", padx=(0, 5))
        ttk.Button(
            btn_frame,
            text=self._get_text("plugins.close"),
            command=self.window.destroy,
        ).pack(side="right")

    def _refresh_list(self):
        """Populate the treeview with current plugin information."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        plugins = self.plugin_manager.get_plugins()
        if not plugins:
            self.tree.insert(
                "", "end",
                values=("-", "-", self._get_text("plugins.none_loaded"), "-"))
            return

        for name, plugin in plugins.items():
            status = self._get_text("plugins.status_loaded")
            self.tree.insert(
                "", "end",
                values=(name, plugin.version, plugin.description, status))

    def _on_refresh(self):
        """Re-discover plugins from the plugins directory."""
        plugin_dir = os.path.join(
            os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))),
            "plugins")
        count = self.plugin_manager.discover_and_load(plugin_dir)
        self._refresh_list()
        msg = self._get_text("plugins.refreshed").format(count=count)
        if hasattr(self.plugin_manager, '_host') and self.plugin_manager._host:
            try:
                self.plugin_manager._host.status_bar.configure(text=msg)
            except Exception:
                pass
