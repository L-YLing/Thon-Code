#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Project Config",
    "Path": ".main.libs.gui.project_cfg",
    "Entrance": "main.py"
}

import os
import sys
import tkinter as tk
import ttkbootstrap as ttkb
from tkinter import ttk, messagebox
import libs.cfg_handle as cfg_handle
from libs.gui import theme
import libs.langs_loader as langs_loader


class ProjectConfigWindow:
    def __init__(self, parent, project_root, status_callback=None):
        self.parent = parent
        self.project_root = project_root
        self.status_callback = status_callback
        self.lang = langs_loader.langs()
        
        if not self.project_root:
            messagebox.showinfo(self._get_text("run.info"), self._get_text("project_cfg.no_project"))
            return
        
        self.cfg = cfg_handle.cfg_handle().get_project_config(self.project_root)
        self._create_window()
    
    def _get_text(self, key):
        return getattr(self.lang, key.replace('.', '_'), key)
    
    def _create_window(self):
        win = ttkb.Toplevel(self.parent)
        win.title(self._get_text("project_cfg.title"))
        win.geometry("480x270")
        win.transient(self.parent)
        win.lift()
        win.focus_force()
        self.window = win

        ttk.Label(win, text=f"{self._get_text('project_cfg.project')}: {os.path.basename(self.project_root)}", font=("微软雅黑", 14)).pack(pady=10)
        ttk.Label(win, text=self._get_text("project_cfg.python_path"), anchor="w").pack(anchor="w", padx=20)
        self.py_entry = ttk.Entry(win)
        self.py_entry.insert(0, self.cfg.get("python_path", sys.executable))
        self.py_entry.pack(pady=(0,10), padx=20)

        ttk.Label(win, text=self._get_text("project_cfg.dependencies"), anchor="w").pack(anchor="w", padx=20)
        colors = theme.get_colors()
        self.deps_text = tk.Text(win, height=10, width=40,
                                 bg=colors["bg"], fg=colors["fg"],
                                 insertbackground=colors["fg"],
                                 selectbackground=colors["sel_bg"],
                                 selectforeground=colors["sel_fg"],
                                 relief="flat", highlightthickness=0)
        self.deps_text.insert("1.0", "\n".join(self.cfg.get("dependencies", [])))
        self.deps_text.pack(pady=(0,10), padx=20)

        ttk.Button(win, text=self._get_text("project_cfg.save"), command=self._save_config).pack(pady=10)

    def _save_config(self):
        self.cfg["python_path"] = self.py_entry.get().strip()
        cfg_handle.cfg_handle().save_project_config(self.project_root, self.cfg)
        self.window.destroy()
        if self.status_callback:
            self.status_callback(self._get_text("project_cfg.save_success"))