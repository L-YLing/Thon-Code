#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Plugin Manager UI",
    "Path": ".main.libs.gui.plugin_ui",
    "Entrance": "main.py"
}

"""Plugin manager UI window.

Displays all loaded plugins with name, version, description, status,
and exposes:
  * Refresh   – rediscover plugins from disk (does not unload loaded ones)
  * Unload    – calls plugin_manager.unload_plugin() and removes from list
  * Reload    – hot-reload a plugin via plugin_manager.reload_plugin()
  * Marketplace – fetches remote index from the user-configurable URL and
                  lets the user install / update packages.
"""

import os
import ttkbootstrap as ttkb
from tkinter import ttk
import tkinter as tk
from typing import Any, Dict, List

import libs.langs_loader as langs_loader
from libs.gui import theme
from libs.gui.window_helper import (
    ScrollableFrame,
    apply_modal_window_order,
    set_window_minimum_size,
)
from libs.plugins.plugin_marketplace import PluginMarketplace


class PluginManagerWindow:
    """Window displaying loaded plugins and a marketplace tab."""

    def __init__(self, parent, plugin_manager: Any, *,
                 base_path: str = "",
                 marketplace_url: str = "",
                 on_save_marketplace_url=None):
        self.parent = parent
        self.plugin_manager = plugin_manager
        self.lang = langs_loader.langs()
        self._base_path = base_path
        self._marketplace_url = marketplace_url
        self._on_save_marketplace_url = on_save_marketplace_url

        self._create_window()
        self._refresh_list()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_text(self, key: str) -> str:
        return getattr(self.lang, key.replace('.', '_'), key)

    # ------------------------------------------------------------------
    # Window layout
    # ------------------------------------------------------------------
    def _create_window(self):
        self.window = ttkb.Toplevel(self.parent)
        self.window.title(self._get_text("plugins.title"))
        self.window.geometry("900x560")
        set_window_minimum_size(self.window, min_width=720, min_height=480)

        # Z-order + modality applied after widgets exist
        apply_modal_window_order(self.window, self.parent, modal=False)

        outer = ttk.Frame(self.window)
        outer.pack(fill="both", expand=True, padx=12, pady=12)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(
            header,
            text=self._get_text("plugins.title"),
            font=("Microsoft YaHei", 15, "bold"),
        ).pack(side="left")

        # Notebook: Loaded | Marketplace
        nb = ttk.Notebook(outer)
        nb.pack(fill="both", expand=True)

        # --- Loaded plugins tab ---
        loaded_tab = ttk.Frame(nb)
        nb.add(loaded_tab, text=self._get_text("plugins.tab_loaded") or "Installed")
        self._build_loaded_tab(loaded_tab)

        # --- Marketplace tab ---
        market_tab = ttk.Frame(nb)
        nb.add(market_tab, text=self._get_text("plugins.tab_market") or "Marketplace")
        self._build_market_tab(market_tab)

        # --- Footer ---
        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(10, 0))
        ttk.Button(
            footer,
            text=self._get_text("plugins.close") or "Close",
            command=self.window.destroy,
        ).pack(side="right")

    def _build_loaded_tab(self, parent: ttk.Frame):
        body = ScrollableFrame(parent)
        body.pack(fill="both", expand=True)
        root = body.interior

        # Action bar
        bar = ttk.Frame(root)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Button(
            bar,
            text=self._get_text("plugins.refresh") or "Refresh",
            command=self._on_refresh,
            style="Info.TButton",
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            bar,
            text=self._get_text("plugins.unload") or "Unload",
            command=self._on_unload,
            style="Warning.TButton",
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            bar,
            text=self._get_text("plugins.reload") or "Reload",
            command=self._on_reload,
            style="Success.TButton",
        ).pack(side="left")

        # Treeview
        tree_frame = ttk.Frame(root)
        tree_frame.pack(fill="both", expand=True)
        columns = ("name", "version", "author", "description", "status")
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", height=16)
        for col, txt, w in (
            ("name",        self._get_text("plugins.col_name"),        140),
            ("version",     self._get_text("plugins.col_version"),      80),
            ("author",      self._get_text("plugins.col_author"),      110),
            ("description", self._get_text("plugins.col_description"), 280),
            ("status",      self._get_text("plugins.col_status"),       90),
        ):
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="w")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda _e: self._on_reload())

    def _build_market_tab(self, parent: ttk.Frame):
        body = ScrollableFrame(parent)
        body.pack(fill="both", expand=True)
        root = body.interior

        # URL bar
        url_bar = ttk.Frame(root)
        url_bar.pack(fill="x", pady=(0, 8))
        ttk.Label(
            url_bar,
            text=self._get_text("plugins.market_url") or "Marketplace URL:",
            width=16,
        ).pack(side="left")
        self._market_url_var = tk.StringVar(value=self._marketplace_url)
        ttk.Entry(url_bar, textvariable=self._market_url_var
                  ).pack(side="left", fill="x", expand=True, padx=(4, 6))
        ttk.Button(
            url_bar,
            text=self._get_text("plugins.market_save") or "Save URL",
            command=self._on_save_url,
            width=12,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            url_bar,
            text=self._get_text("plugins.market_fetch") or "Refresh List",
            command=self._on_fetch_market,
            style="Info.TButton",
            width=14,
        ).pack(side="left")

        # Action bar
        bar = ttk.Frame(root)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Button(
            bar,
            text=self._get_text("plugins.market_install") or "Install / Update",
            command=self._on_install,
            style="Success.TButton",
        ).pack(side="left", padx=(0, 6))

        # Marketplace treeview
        m_frame = ttk.Frame(root)
        m_frame.pack(fill="both", expand=True)
        columns = ("name", "version", "author", "tags", "description")
        self.market_tree = ttk.Treeview(
            m_frame, columns=columns, show="headings", height=16)
        for col, txt, w in (
            ("name",        self._get_text("plugins.col_name"),                            150),
            ("version",     self._get_text("plugins.col_version"),                          90),
            ("author",      self._get_text("plugins.col_author"),                          120),
            ("tags",        self._get_text("plugins.col_tags") or "Tags",                  100),
            ("description", self._get_text("plugins.col_description"),                     250),
        ):
            self.market_tree.heading(col, text=txt)
            self.market_tree.column(col, width=w, anchor="w")
        vsb = ttk.Scrollbar(m_frame, orient="vertical", command=self.market_tree.yview)
        self.market_tree.configure(yscrollcommand=vsb.set)
        self.market_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._market_cache: List[Dict[str, Any]] = []
        self.market_tree.bind("<<TreeviewSelect>>", self._on_market_select)

        # Details panel (below the treeview)
        details_frame = ttk.LabelFrame(
            root, text=self._get_text("plugins.market_details") or "Details")
        details_frame.pack(fill="x", pady=(8, 0))
        self._market_detail_text = tk.Text(details_frame, height=6, wrap="word",
                                           state="disabled")
        self._market_detail_text.pack(fill="x", padx=4, pady=4)

        self._market_status = ttk.Label(root, text="", anchor="w",
                                        foreground=theme.get_colors().get("fg_muted", "#888"))
        self._market_status.pack(fill="x", pady=(6, 0))

    # ------------------------------------------------------------------
    # Loaded tab actions
    # ------------------------------------------------------------------
    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        plugins = self.plugin_manager.get_plugins()
        if not plugins:
            self.tree.insert(
                "", "end",
                values=("-", "-", "-",
                        self._get_text("plugins.none_loaded") or "None",
                        "-"))
            return
        for name, plugin in plugins.items():
            self.tree.insert(
                "", "end", iid=name,
                values=(name,
                        getattr(plugin, "version", "-"),
                        getattr(plugin, "author", "-"),
                        getattr(plugin, "description", ""),
                        self._get_text("plugins.status_loaded") or "Loaded"))

    def _selected_plugin_name(self) -> str:
        sel = self.tree.selection()
        if not sel:
            return ""
        return sel[0]

    def _on_refresh(self):
        # Re-scan the same plugin dirs (manager preserves already-loaded)
        try:
            dirs = self.plugin_manager.get_plugin_dirs() or []
            if dirs:
                self.plugin_manager.discover_and_load(dirs[0])
            else:
                # Legacy fallback: try base path / plugins
                default = os.path.join(self._base_path or "", "plugins")
                self.plugin_manager.discover_and_load(default)
        except Exception as e:
            self._logger_debug("_on_refresh", e)
        self._refresh_list()
        self._toast(self._get_text("plugins.refreshed").format(count="")
                    if hasattr(self.lang, "plugins_refreshed") else "Plugins refreshed")

    def _on_unload(self):
        name = self._selected_plugin_name()
        if not name:
            return
        if self.plugin_manager.unload_plugin(name):
            self._refresh_list()
            self._toast(self._get_text("plugins.unloaded").format(name=name)
                        if hasattr(self.lang, "plugins_unloaded")
                        else f"Unloaded {name}")
        else:
            self._toast(self._get_text("plugins.unload_fail") or "Unload failed")

    def _on_reload(self):
        name = self._selected_plugin_name()
        if not name:
            return
        if self.plugin_manager.reload_plugin(name):
            self._refresh_list()
            self._toast(self._get_text("plugins.reloaded").format(name=name)
                        if hasattr(self.lang, "plugins_reloaded")
                        else f"Reloaded {name}")
        else:
            self._toast(self._get_text("plugins.reload_fail") or "Reload failed")

    # ------------------------------------------------------------------
    # Marketplace tab actions
    # ------------------------------------------------------------------
    def _market(self) -> PluginMarketplace:
        return PluginMarketplace(self._market_url_var.get())

    def _on_save_url(self):
        url = self._market_url_var.get().strip()
        cb = self._on_save_marketplace_url
        if cb is not None:
            try:
                cb(url)
            except Exception as e:
                self._logger_debug("_on_save_url", e)
        self._market_status.configure(
            text=self._get_text("plugins.market_url_saved") or "URL saved.")

    def _on_fetch_market(self):
        market = self._market()
        self._market_cache = market.list_available()
        for item in self.market_tree.get_children():
            self.market_tree.delete(item)
        for entry in self._market_cache:
            rid = entry.get("id") or entry.get("name", "")
            tags_val = entry.get("tags", "-")
            if isinstance(tags_val, list):
                tags_val = ", ".join(tags_val)
            self.market_tree.insert(
                "", "end", iid=rid,
                values=(entry.get("name", rid),
                        entry.get("version", "-"),
                        entry.get("author", "-"),
                        tags_val,
                        entry.get("description", "")))
        self._market_status.configure(
            text=(self._get_text("plugins.market_fetched") or "Fetched {n} packages.").format(
                n=len(self._market_cache)))

    def _on_market_select(self, _event=None):
        sel = self.market_tree.selection()
        if not sel:
            return
        target_id = sel[0]
        entry = None
        for e in self._market_cache:
            if (e.get("id") or e.get("name", "")) == target_id:
                entry = e
                break
        if entry is None:
            return
        name = entry.get("name", target_id)
        version = entry.get("version", "-")
        author = entry.get("author", "-")
        tags_val = entry.get("tags", "-")
        if isinstance(tags_val, list):
            tags_val = ", ".join(tags_val)
        size_bytes = entry.get("size_bytes", "-")
        description = entry.get("description", "")
        changelog = entry.get("changelog", "-")
        package_url = entry.get("package_url", "-")
        summary = (
            f"Name: {name}\n"
            f"Version: {version}\n"
            f"Author: {author}\n"
            f"Tags: {tags_val}\n"
            f"Size: {size_bytes}\n"
            f"Description: {description}\n"
            f"\n"
            f"Changelog:\n"
            f"{changelog}\n"
            f"\n"
            f"Download URL: {package_url}\n"
        )
        self._market_detail_text.configure(state="normal")
        self._market_detail_text.delete("1.0", "end")
        self._market_detail_text.insert("1.0", summary)
        self._market_detail_text.configure(state="disabled")

    def _on_install(self):
        sel = self.market_tree.selection()
        if not sel:
            self._market_status.configure(
                text=self._get_text("plugins.market_select") or
                     "Select a package first.")
            return
        target_id = sel[0]
        entry = None
        for e in self._market_cache:
            if (e.get("id") or e.get("name", "")) == target_id:
                entry = e
                break
        if entry is None:
            return
        install_dir = PluginMarketplace.user_writable_plugin_dir(self._base_path)
        self._market_status.configure(
            text=(self._get_text("plugins.market_installing") or
                  "Installing {name}...").format(
                      name=entry.get("name", ""),
                      version=entry.get("version", "")))
        self.window.update_idletasks()

        res = self._market().install_plugin(entry, install_dir)
        if res["status"] == "ok":
            # Try to discover-and-load the newly installed plugin.
            try:
                self.plugin_manager.discover_and_load(install_dir)
            except Exception as e:
                self._logger_debug("discover after install", e)
            self._refresh_list()
            self._market_status.configure(
                text=(self._get_text("plugins.market_installed") or
                      "Installed OK — {msg}").format(
                          name=entry.get("name", ""),
                          msg=res["data"]))
        else:
            self._market_status.configure(
                text=(self._get_text("plugins.market_error") or
                      "Install failed — {msg}").format(
                          name=entry.get("name", ""),
                          msg=res["data"]))

    # ------------------------------------------------------------------
    # Small helpers
    # ------------------------------------------------------------------
    def _toast(self, msg: str):
        try:
            if hasattr(self.plugin_manager, '_host') and self.plugin_manager._host:
                host = self.plugin_manager._host
                if hasattr(host, 'status_bar'):
                    host.status_bar.configure(text=msg)
        except Exception:
            pass

    def _logger_debug(self, ctx: str, exc: Exception):
        import logging
        logging.getLogger("thoncode.plugins.ui").debug(
            "%s failed: %s", ctx, exc, exc_info=True)
