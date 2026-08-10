#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Run File",
    "Path": ".main.libs.gui.run_file",
    "Entrance": "main.py"
}

import os
import sys
import subprocess

from tkinter import messagebox

import libs.cfg_handle as cfg_handle
import libs.langs_loader as langs_loader


class RunFileDialog:
    def __init__(self, parent, current_file, is_dirty, save_callback, status_callback):
        self.parent = parent
        self.current_file = current_file
        self.is_dirty = is_dirty
        self.save_callback = save_callback
        self.status_callback = status_callback
        self.lang = langs_loader.langs()
        self._run()
    
    def _get_text(self, key):
        return getattr(self.lang, key.replace('.', '_'), key)
    
    def _run(self):
        if not self.current_file:
            messagebox.showinfo(self._get_text("run.info"), self._get_text("run.no_file"))
            return
        
        if self.is_dirty:
            if messagebox.askyesno(self._get_text("runtime.save"), self._get_text("run.save_before")):
                self.save_callback()
        
        cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        python_path = cfg.get("python_path", sys.executable)
        run_args = cfg.get("run_args", "")
        cmd = [python_path, self.current_file]
        if run_args:
            cmd.extend(run_args.split())
        
        try:
            if sys.platform == "win32":
                subprocess.Popen(["start", "cmd", "/k"] + cmd, shell=True)
            else:
                terminal = os.environ.get("TERM", "xterm")
                subprocess.Popen([terminal, "-e", " ".join(cmd)])
            if self.status_callback:
                self.status_callback(f"{self._get_text('run.running')} {' '.join(cmd)}")
        except Exception as e:
            messagebox.showerror(self._get_text("settings.error_title"), f"{self._get_text('run.failed')}: {e}")