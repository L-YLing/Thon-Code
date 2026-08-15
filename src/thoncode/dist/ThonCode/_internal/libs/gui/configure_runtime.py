import sys
import customtkinter as ctk
import libs.cfg_handle as cfg_handle


class ConfigureRuntimeWindow:
    def __init__(self, parent, status_callback=None):
        self.parent = parent
        self.status_callback = status_callback
        self.cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        self._create_window()
    
    def _create_window(self):
        win = ctk.CTkToplevel(self.parent)
        win.title("配置运行时")
        win.geometry("400x200")
        win.resizable(False, False)
        win.transient(self.parent)
        win.lift()
        win.focus_force()
        self.window = win

        ctk.CTkLabel(win, text="Python解释器路径:").pack(pady=(10, 0), anchor="w", padx=20)
        self.py_entry = ctk.CTkEntry(win, width=300)
        self.py_entry.insert(0, self.cfg.get("python_path", sys.executable))
        self.py_entry.pack(pady=(0, 10), padx=20)

        ctk.CTkLabel(win, text="运行参数（空格分隔）:").pack(anchor="w", padx=20)
        self.arg_entry = ctk.CTkEntry(win, width=300)
        self.arg_entry.insert(0, self.cfg.get("run_args", ""))
        self.arg_entry.pack(pady=(0, 10), padx=20)

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="保存", command=self._save_config).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="取消", command=win.destroy).pack(side="left", padx=10)

    def _save_config(self):
        self.cfg["python_path"] = self.py_entry.get().strip()
        self.cfg["run_args"] = self.arg_entry.get().strip()
        cfg_handle.cfg_handle().write_cfg(self.cfg)
        self.window.destroy()
        if self.status_callback:
            self.status_callback("运行时配置已保存")