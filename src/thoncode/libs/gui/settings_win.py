# libs/gui/settings_win.py
import customtkinter as ctk
import libs.cfg_handle as cfg_handle
from tkinter import messagebox

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, on_settings_changed=None):
        super().__init__(master)
        self.master = master
        self.on_settings_changed = on_settings_changed

        self.title("设置")
        self.geometry("400x500")
        self.resizable(False, False)

        self.cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        self._create_widgets()

        self.transient(master)
        self.grab_set()
        self.focus_force()
        self.lift()

    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 语言
        ctk.CTkLabel(main_frame, text="界面语言", anchor="w").pack(fill="x", pady=(0, 5))
        lang_options = ["zh_cn", "en_us", "en_uk"]
        self.lang_var = ctk.StringVar(value=self.cfg.get("language", "zh_cn"))
        ctk.CTkOptionMenu(main_frame, values=lang_options, variable=self.lang_var, width=200).pack(anchor="w", pady=(0, 15))

        # 主题（不再实时切换）
        ctk.CTkLabel(main_frame, text="主题", anchor="w").pack(fill="x", pady=(0, 5))
        self.theme_var = ctk.StringVar(value=self.cfg.get("theme", "dark"))
        theme_switch = ctk.CTkSwitch(
            main_frame,
            text="暗色模式",
            variable=self.theme_var,
            onvalue="dark",
            offvalue="light",
            command=lambda: None  # 空命令，不执行任何操作
        )
        theme_switch.pack(anchor="w", pady=(0, 15))

        # 自动重载
        ctk.CTkLabel(main_frame, text="自动重载配置", anchor="w").pack(fill="x", pady=(0, 5))
        self.reload_var = ctk.BooleanVar(value=self.cfg.get("auto_reload", False))
        ctk.CTkSwitch(
            main_frame,
            text="启用自动重载（保存设置后自动生效）",
            variable=self.reload_var,
            onvalue=True,
            offvalue=False
        ).pack(anchor="w", pady=(0, 15))

        # Tab 大小
        ctk.CTkLabel(main_frame, text="Tab 缩进空格数", anchor="w").pack(fill="x", pady=(0, 5))
        self.tab_size_var = ctk.IntVar(value=self.cfg.get("tab_size", 4))
        ctk.CTkEntry(main_frame, width=60, textvariable=self.tab_size_var).pack(anchor="w", pady=(0, 15))

        # 字体连字
        ctk.CTkLabel(main_frame, text="启用字体连字（需 Fira Code 已安装）", anchor="w").pack(fill="x", pady=(0, 5))
        self.ligature_var = ctk.BooleanVar(value=self.cfg.get("font_ligatures", True))
        ctk.CTkSwitch(
            main_frame,
            text="启用连字",
            variable=self.ligature_var,
            onvalue=True,
            offvalue=False
        ).pack(anchor="w", pady=(0, 20))

        # 按钮
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))
        ctk.CTkButton(btn_frame, text="保存", command=self._save_settings, width=100).pack(side="right", padx=(5, 0))
        ctk.CTkButton(btn_frame, text="取消", command=self.destroy, width=100).pack(side="right", padx=(0, 5))

    def _save_settings(self):
        self.cfg["language"] = self.lang_var.get()
        self.cfg["theme"] = self.theme_var.get()
        self.cfg["auto_reload"] = self.reload_var.get()
        self.cfg["tab_size"] = self.tab_size_var.get()
        self.cfg["font_ligatures"] = self.ligature_var.get()

        result = cfg_handle.cfg_handle().write_cfg(self.cfg)
        if result["status"] == "success":
            if self.on_settings_changed:
                self.on_settings_changed(self.cfg)
            self.destroy()
        else:
            messagebox.showerror("错误", f"保存设置失败：{result.get('data', '')}")