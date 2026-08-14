#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Plugin Permission Dialog",
    "Path": ".main.libs.gui.plugin_permission_dialog",
    "Entrance": "main.py"
}

"""Modal dialog for confirming plugin permissions at load-time.

Only invoked when a plugin declares one or more "risky" permissions
(filesystem write, network, execute, config, plugin management). The
user can approve individual flags or deny the load entirely.
"""

import ttkbootstrap as ttkb
import tkinter as tk
from tkinter import ttk
from typing import Iterable, List, Set

from libs.gui import theme
import libs.langs_loader as langs_loader
from libs.plugins.plugin_base import PluginBase, ALL_PERMISSIONS


# Human-readable labels for each permission constant.
_PERMISSION_LABELS = {
    "filesystem:read":       "Read files outside the project",
    "filesystem:write":      "Write files outside the project",
    "network":               "Access the network (HTTP, sockets...)",
    "execute":               "Run external programs / shell commands",
    "config":                "Change application configuration",
    "editor:modify":         "Modify editor content and selections",
    "ui:menu_register":      "Add items to the menu bar",
    "ui:hotkey_bind":        "Bind global keyboard shortcuts",
    "editor:highlight_extend": "Extend syntax highlighting rules",
    "plugins:manage":        "Load / unload other plugins",
}


def show_permission_dialog(
    parent: tk.Misc,
    plugin: PluginBase,
    requested_risky: Iterable[str],
) -> Set[str]:
    """Display a modal asking the user to grant/deny risky permissions.

    Args:
        parent: The parent window (root Tk instance).
        plugin: The plugin requesting permissions.
        requested_risky: Subset of plugin.permissions that are risky.

    Returns:
        Set[str]: Permissions the user explicitly checked. Plugins
        always keep low-risk permissions regardless of this dialog.
        If the user clicks Cancel the returned set is empty, meaning
        every risky permission is refused.
    """
    lang = langs_loader.langs()
    t_get = lambda key: getattr(lang, key.replace('.', '_'), key)

    # ------------------------------------------------------------------
    dlg = ttkb.Toplevel(parent)
    dlg.title(t_get("plugins.perm_title") or "Plugin Permission")
    dlg.geometry("560x440")
    dlg.resizable(True, True)
    dlg.minsize(480, 360)

    # Z-order: make it a proper modal child of the main window.
    dlg.transient(parent)
    dlg.grab_set()
    dlg.lift()
    dlg.focus_force()

    result: Set[str] = set()

    colors = theme.get_colors()
    main_frame = ttk.Frame(dlg)
    main_frame.pack(fill="both", expand=True, padx=18, pady=16)

    # Plugin info header
    header_frame = ttk.Frame(main_frame)
    header_frame.pack(fill="x", pady=(0, 12))
    ttk.Label(
        header_frame,
        text=getattr(plugin, "name", "Unnamed"),
        font=("Microsoft YaHei", 15, "bold"),
    ).pack(anchor="w")
    meta_parts = []
    if getattr(plugin, "version", ""):
        meta_parts.append(f"v{plugin.version}")
    if getattr(plugin, "author", ""):
        meta_parts.append(f"by {plugin.author}")
    if meta_parts:
        ttk.Label(
            header_frame, text="  ".join(meta_parts),
            foreground=colors.get("fg_muted", "#888888"),
        ).pack(anchor="w")
    if getattr(plugin, "description", ""):
        ttk.Label(
            header_frame, text=plugin.description, wraplength=500,
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

    ttk.Separator(header_frame, orient="horizontal").pack(
        fill="x", pady=(12, 0))

    # Scrollable permission list
    list_container = ttk.Frame(main_frame)
    list_container.pack(fill="both", expand=True)

    canvas = tk.Canvas(list_container, highlightthickness=0,
                       background=colors.get("bg_panel", colors.get("bg", "#ffffff")))
    vsb = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas)

    inner.bind("<Configure>",
               lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=vsb.set)

    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    ttk.Label(
        inner,
        text=t_get("plugins.perm_request_header")
             or "The plugin requested the following permissions:",
        font=("Microsoft YaHei", 10, "bold"),
    ).pack(anchor="w", pady=(0, 8))

    check_vars: List[tk.BooleanVar] = []
    check_perms: List[str] = []

    for perm in requested_risky:
        if perm not in ALL_PERMISSIONS:
            continue
        label = _PERMISSION_LABELS.get(perm, perm)
        var = tk.BooleanVar(value=True)  # Default: approved
        row = ttk.Frame(inner)
        row.pack(fill="x", pady=2)
        ttk.Checkbutton(row, text=label, variable=var).pack(anchor="w")
        check_vars.append(var)
        check_perms.append(perm)

    # Buttons
    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(fill="x", pady=(14, 0))

    def _on_ok():
        for var, perm in zip(check_vars, check_perms):
            if var.get():
                result.add(perm)
        dlg.destroy()

    def _on_cancel():
        # Empty result → all risky permissions denied
        dlg.destroy()

    ttk.Button(
        btn_frame, text=t_get("dialog_ok") or "Allow",
        style="Success.TButton", command=_on_ok,
        width=12,
    ).pack(side="right", padx=(8, 0))
    ttk.Button(
        btn_frame, text=t_get("dialog_cancel") or "Deny All",
        command=_on_cancel,
        width=12,
    ).pack(side="right")

    # Wait for the modal
    dlg.wait_window(dlg)
    return result
