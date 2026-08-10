#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Settings",
    "Path": ".main.libs.gui.settings_win",
    "Entrance": "main.py"
}

import ttkbootstrap as ttkb
import tkinter as tk
from tkinter import ttk, messagebox
import libs.cfg_handle as cfg_handle
import libs.langs_loader as langs_loader


class SettingsWindow(ttkb.Toplevel):
    """Settings configuration window for Thon Code.
    
    Provides controls for language, theme, auto-reload, tab size,
    and font ligatures settings.
    """

    # Mapping from config theme values to ttkbootstrap theme names
    THEME_COMBO_VALUES = ["darkly", "flatly", "cyborg", "superhero", "vapor", "solar", "dracula", "vscode_dark"]
    DARK_THEMES = ["darkly", "cyborg", "superhero", "vapor", "solar", "dracula", "vscode_dark"]

    def __init__(self, master, on_settings_changed=None):
        """Initialize the settings window.
        
        Args:
            master: Parent window
            on_settings_changed: Callback function when settings are saved
        """
        super().__init__(master)
        self.master = master
        self.on_settings_changed = on_settings_changed

        self.lang = langs_loader.langs()

        self.title(self._get_text("settings.title"))
        self.geometry("400x500")
        self.resizable(False, False)

        self.cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        self._create_widgets()

        self.transient(master)
        self.grab_set()
        self.focus_force()
        self.lift()

    def _get_text(self, key: str) -> str:
        """Get localized text by dot-separated key.
        
        Args:
            key: Dot-separated i18n key (e.g., 'settings.title')
            
        Returns:
            Localized string or the key itself if not found
        """
        return getattr(self.lang, key.replace('.', '_'), key)

    def _current_theme_to_combo(self, theme_value):
        """Convert config theme value to combobox selection.
        
        Args:
            theme_value: Theme value from config ('dark' or 'light')
            
        Returns:
            Matching combobox theme name
        """
        theme_map = {
            "dark": "darkly",
            "light": "flatly",
        }
        return theme_map.get(theme_value, "darkly")

    def _combo_to_current_theme(self, combo_value):
        """Convert combobox selection to config theme value.
        
        Args:
            combo_value: Theme name from combobox
            
        Returns:
            Config theme value ('dark' or 'light')
        """
        if combo_value in self.DARK_THEMES:
            return "dark"
        return "light"

    def _create_widgets(self):
        """Create all settings UI widgets."""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text=self._get_text("settings.language"), anchor="w").pack(fill="x", pady=(0, 5))
        lang_options = ["zh_cn", "en_us", "en_uk"]
        self.lang_var = tk.StringVar(value=self.cfg.get("language", "zh_cn"))
        ttk.Combobox(main_frame, values=lang_options, textvariable=self.lang_var).pack(anchor="w", pady=(0, 15))

        ttk.Label(main_frame, text=self._get_text("settings.theme"), anchor="w").pack(fill="x", pady=(0, 5))
        current_theme = self._current_theme_to_combo(self.cfg.get("theme", "dark"))
        self.theme_var = tk.StringVar(value=current_theme)
        ttk.Combobox(main_frame, values=self.THEME_COMBO_VALUES, textvariable=self.theme_var, state="readonly").pack(anchor="w", pady=(0, 15))

        ttk.Label(main_frame, text=self._get_text("settings.auto_reload"), anchor="w").pack(fill="x", pady=(0, 5))
        self.reload_var = tk.BooleanVar(value=self.cfg.get("auto_reload", False))
        ttk.Checkbutton(
            main_frame,
            text=self._get_text("settings.auto_reload_desc"),
            variable=self.reload_var
        ).pack(anchor="w", pady=(0, 15))

        ttk.Label(main_frame, text=self._get_text("settings.tab_size"), anchor="w").pack(fill="x", pady=(0, 5))
        self.tab_size_var = tk.IntVar(value=self.cfg.get("tab_size", 4))
        ttk.Entry(main_frame, textvariable=self.tab_size_var).pack(anchor="w", pady=(0, 15))

        ttk.Label(main_frame, text=self._get_text("settings.font_ligatures"), anchor="w").pack(fill="x", pady=(0, 5))
        self.ligature_var = tk.BooleanVar(value=self.cfg.get("font_ligatures", True))
        ttk.Checkbutton(
            main_frame,
            text=self._get_text("settings.enable_ligatures"),
            variable=self.ligature_var
        ).pack(anchor="w", pady=(0, 20))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_frame, text=self._get_text("settings.save"), command=self._save_settings).pack(side="right", padx=(5, 0))
        ttk.Button(btn_frame, text=self._get_text("settings.cancel"), command=self.destroy).pack(side="right", padx=(0, 5))

    def _save_settings(self):
        """Save the current settings to configuration file."""
        self.cfg["language"] = self.lang_var.get()
        self.cfg["theme"] = self._combo_to_current_theme(self.theme_var.get())
        self.cfg["auto_reload"] = self.reload_var.get()
        self.cfg["tab_size"] = self.tab_size_var.get()
        self.cfg["font_ligatures"] = self.ligature_var.get()

        result = cfg_handle.cfg_handle().write_cfg(self.cfg)
        if result["status"] == "success":
            if self.on_settings_changed:
                self.on_settings_changed(self.cfg)
            self.destroy()
        else:
            messagebox.showerror(self._get_text("settings.error_title"), 
                                 f"{self._get_text('settings.save_failed')}: {result.get('data', '')}")