import os
import sys
import customtkinter as ctk
from tkinter import messagebox
import libs.cfg_handle as cfg_handle


class ProjectConfigWindow:
    def __init__(self, parent, project_root, status_callback=None):
        self.parent = parent
        self.project_root = project_root
        self.status_callback = status_callback
        
        if not self.project_root:
            messagebox.showinfo("提示", "请先打开一个项目")
            return
        
        self.cfg = cfg_handle.cfg_handle().get_project_config(self.project_root)
        self._create_window()
    
    def _create_window(self):
        win = ctk.CTkToplevel(self.parent)
        win.title("项目配置")
        win.geometry("400x350")
        win.transient(self.parent)
        win.lift()
        win.focus_force()
        self.window = win

        ctk.CTkLabel(win, text=f"项目: {os.path.basename(self.project_root)}", font=("微软雅黑", 14)).pack(pady=10)
        ctk.CTkLabel(win, text="Python解释器:", anchor="w").pack(anchor="w", padx=20)
        self.py_entry = ctk.CTkEntry(win, width=300)
        self.py_entry.insert(0, self.cfg.get("python_path", sys.executable))
        self.py_entry.pack(pady=(0,10), padx=20)

        ctk.CTkLabel(win, text="依赖库 (来自requirements.txt):", anchor="w").pack(anchor="w", padx=20)
        self.deps_text = ctk.CTkTextbox(win, height=100, width=300)
        self.deps_text.insert("1.0", "\n".join(self.cfg.get("dependencies", [])))
        self.deps_text.pack(pady=(0,10), padx=20)

        ctk.CTkButton(win, text="保存", command=self._save_config).pack(pady=10)

    def _save_config(self):
        self.cfg["python_path"] = self.py_entry.get().strip()
        cfg_handle.cfg_handle().save_project_config(self.project_root, self.cfg)
        self.window.destroy()
        if self.status_callback:
            self.status_callback("项目配置已保存")