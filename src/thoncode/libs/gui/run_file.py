import os
import sys
import subprocess
import customtkinter as ctk

from tkinter import messagebox

import libs.cfg_handle as cfg_handle


class RunFileDialog:
    def __init__(self, parent, current_file, is_dirty, save_callback, status_callback):
        self.parent = parent
        self.current_file = current_file
        self.is_dirty = is_dirty
        self.save_callback = save_callback
        self.status_callback = status_callback
        self._run()
    
    def _run(self):
        if not self.current_file:
            messagebox.showinfo("提示", "请先打开一个文件")
            return
        
        if self.is_dirty:
            if messagebox.askyesno("保存", "文件已修改，是否保存后再运行？"):
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
                self.status_callback(f"运行: {' '.join(cmd)}")
        except Exception as e:
            messagebox.showerror("错误", f"运行失败：{e}")