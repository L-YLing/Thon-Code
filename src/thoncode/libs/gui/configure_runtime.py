#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Runtime Config",
    "Path": ".main.libs.gui.configure_runtime",
    "Entrance": "main.py"
}

import sys
import ttkbootstrap as ttkb
from tkinter import ttk
import libs.cfg_handle as cfg_handle
import libs.langs_loader as langs_loader


class ConfigureRuntimeWindow:
    def __init__(self, parent, status_callback=None):
        self.parent = parent
        self.status_callback = status_callback
        self.lang = langs_loader.langs()
        self.cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        self._create_window()
    
    def _get_text(self, key):
        return getattr(self.lang, key.replace('.', '_'), key)
    
    def _create_window(self):
        win = ttkb.Toplevel(self.parent)
        win.title(self._get_text("runtime.title"))
        win.geometry("400x200")
        win.resizable(False, False)
        win.transient(self.parent)
        win.lift()
        win.focus_force()
        self.window = win

        ttk.Label(win, text=self._get_text("runtime.python_path")).pack(pady=(10, 0), anchor="w", padx=20)
        self.py_entry = ttk.Entry(win)
        self.py_entry.insert(0, self.cfg.get("python_path", sys.executable))
        self.py_entry.pack(pady=(0, 10), padx=20)

        ttk.Label(win, text=self._get_text("runtime.run_args")).pack(anchor="w", padx=20)
        self.arg_entry = ttk.Entry(win)
        self.arg_entry.insert(0, self.cfg.get("run_args", ""))
        self.arg_entry.pack(pady=(0, 10), padx=20)

        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text=self._get_text("runtime.save"), command=self._save_config).pack(side="left", padx=10)
        ttk.Button(btn_frame, text=self._get_text("runtime.cancel"), command=win.destroy).pack(side="left", padx=10)

    def _save_config(self):
        self.cfg["python_path"] = self.py_entry.get().strip()
        self.cfg["run_args"] = self.arg_entry.get().strip()
        cfg_handle.cfg_handle().write_cfg(self.cfg)
        self.window.destroy()
        if self.status_callback:
            self.status_callback(self._get_text("runtime.save_success"))