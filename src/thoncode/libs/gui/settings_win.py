#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Settings",
    "Path": ".main.libs.gui.settings_win",
    "Entrance": "main.py"
}

import ttkbootstrap as ttkb
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import libs.cfg_handle as cfg_handle
import libs.langs_loader as langs_loader
from libs.gui import theme


class SettingsWindow(ttkb.Toplevel):
    """Settings configuration window for Thon Code.

    Provides controls for language, theme, auto-reload, tab size, and font
    ligatures. Theme and language changes are previewed in real-time; an
    Apply button persists settings without closing the window.
    """

    THEME_COMBO_VALUES = ["darkly", "flatly", "cyborg", "superhero", "vapor", "solar",
                          "dracula", "vscode_dark", "vscode_dark_blue"]
    DARK_THEMES = ["darkly", "cyborg", "superhero", "vapor", "solar",
                   "dracula", "vscode_dark", "vscode_dark_blue"]

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
        self.geometry("800x450")
        self.resizable(False, False)

        self.cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        # Remember the original theme and language so we can restore on Cancel.
        self._original_theme = self._combo_to_current_theme(
            self._current_theme_to_combo(self.cfg.get("theme", "dark")))
        self._original_language = self.cfg.get("language", "zh_cn")

        # Widget references for real-time text refresh
        self._widgets = {}
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
        theme_map = {"dark": "darkly", "light": "flatly"}
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
        """Create all settings UI widgets, storing references for refresh."""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # --- Language ---
        self._widgets['lbl_language'] = ttk.Label(
            main_frame, text=self._get_text("settings.language"), anchor="w")
        self._widgets['lbl_language'].pack(fill="x", pady=(0, 5))
        lang_options = ["zh_cn", "en_us", "en_uk"]
        self.lang_var = tk.StringVar(value=self.cfg.get("language", "zh_cn"))
        lang_combo = ttk.Combobox(
            main_frame, values=lang_options,
            textvariable=self.lang_var, state="readonly")
        lang_combo.pack(anchor="w", pady=(0, 15))
        # Real-time language preview: reload i18n and refresh all texts.
        lang_combo.bind("<<ComboboxSelected>>", self._on_language_preview)

        # --- Theme ---
        self._widgets['lbl_theme'] = ttk.Label(
            main_frame, text=self._get_text("settings.theme"), anchor="w")
        self._widgets['lbl_theme'].pack(fill="x", pady=(0, 5))
        current_theme = self._current_theme_to_combo(self.cfg.get("theme", "dark"))
        self.theme_var = tk.StringVar(value=current_theme)
        theme_combo = ttk.Combobox(
            main_frame, values=self.THEME_COMBO_VALUES,
            textvariable=self.theme_var, state="readonly")
        theme_combo.pack(anchor="w", pady=(0, 15))
        theme_combo.bind("<<ComboboxSelected>>", self._on_theme_preview)

        # --- Accent color (Monet-inspired palette) ---
        self._widgets['lbl_accent'] = ttk.Label(
            main_frame, text=self._get_text("settings.accent_color"), anchor="w")
        self._widgets['lbl_accent'].pack(fill="x", pady=(0, 5))
        accent_frame = ttk.Frame(main_frame)
        accent_frame.pack(fill="x", pady=(0, 15))

        self.accent_var = tk.StringVar(value=self.cfg.get("accent_color", ""))
        # Preset color swatches
        swatch_frame = ttk.Frame(accent_frame)
        swatch_frame.pack(side="left", fill="x", expand=True)
        self._swatch_widgets = []
        for color in theme.ACCENT_PRESETS:
            swatch = tk.Label(
                swatch_frame, width=2, height=1,
                background=color, relief="flat", cursor="hand2",
                highlightthickness=1, highlightbackground="#888888")
            swatch.pack(side="left", padx=1)
            swatch.bind("<Button-1>", lambda e, c=color: self._on_accent_selected(c))
            self._swatch_widgets.append((swatch, color))
        # Custom color button
        ttk.Button(
            accent_frame,
            text=self._get_text("settings.custom_color"),
            command=self._on_custom_color,
            style="Info.TButton",
        ).pack(side="right", padx=(5, 0))
        # Reset button
        ttk.Button(
            accent_frame,
            text=self._get_text("settings.reset_color"),
            command=self._on_reset_color,
        ).pack(side="right", padx=(5, 0))

        # --- Auto reload ---
        self._widgets['lbl_auto_reload'] = ttk.Label(
            main_frame, text=self._get_text("settings.auto_reload"), anchor="w")
        self._widgets['lbl_auto_reload'].pack(fill="x", pady=(0, 5))
        self.reload_var = tk.BooleanVar(value=self.cfg.get("auto_reload", False))
        self._widgets['cb_auto_reload'] = ttk.Checkbutton(
            main_frame,
            text=self._get_text("settings.auto_reload_desc"),
            variable=self.reload_var)
        self._widgets['cb_auto_reload'].pack(anchor="w", pady=(0, 15))

        # --- Tab size ---
        self._widgets['lbl_tab_size'] = ttk.Label(
            main_frame, text=self._get_text("settings.tab_size"), anchor="w")
        self._widgets['lbl_tab_size'].pack(fill="x", pady=(0, 5))
        self.tab_size_var = tk.IntVar(value=self.cfg.get("tab_size", 4))
        ttk.Entry(main_frame, textvariable=self.tab_size_var).pack(anchor="w", pady=(0, 15))

        # --- Font ligatures ---
        self._widgets['lbl_ligatures'] = ttk.Label(
            main_frame, text=self._get_text("settings.font_ligatures"), anchor="w")
        self._widgets['lbl_ligatures'].pack(fill="x", pady=(0, 5))
        self.ligature_var = tk.BooleanVar(value=self.cfg.get("font_ligatures", True))
        self._widgets['cb_ligatures'] = ttk.Checkbutton(
            main_frame,
            text=self._get_text("settings.enable_ligatures"),
            variable=self.ligature_var)
        self._widgets['cb_ligatures'].pack(anchor="w", pady=(0, 20))

        # --- Buttons ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        self._widgets['btn_save'] = ttk.Button(
            btn_frame, text=self._get_text("settings.save"),
            command=self._save_settings)
        self._widgets['btn_save'].pack(side="right", padx=(5, 0))
        self._widgets['btn_apply'] = ttk.Button(
            btn_frame, text=self._get_text("settings.apply"),
            command=self._apply_settings)
        self._widgets['btn_apply'].pack(side="right", padx=(0, 5))
        self._widgets['btn_cancel'] = ttk.Button(
            btn_frame, text=self._get_text("settings.cancel"),
            command=self._cancel)
        self._widgets['btn_cancel'].pack(side="right", padx=(0, 5))

    def _refresh_texts(self):
        """Reload language data and update all widget texts in-place.

        Called after a language change so the settings window itself
        reflects the new language without requiring a restart.
        """
        langs_loader.langs.reload()
        self.lang = langs_loader.langs()
        self.title(self._get_text("settings.title"))
        self._widgets['lbl_language'].configure(text=self._get_text("settings.language"))
        self._widgets['lbl_theme'].configure(text=self._get_text("settings.theme"))
        self._widgets['lbl_accent'].configure(text=self._get_text("settings.accent_color"))
        self._widgets['lbl_auto_reload'].configure(text=self._get_text("settings.auto_reload"))
        self._widgets['cb_auto_reload'].configure(text=self._get_text("settings.auto_reload_desc"))
        self._widgets['lbl_tab_size'].configure(text=self._get_text("settings.tab_size"))
        self._widgets['lbl_ligatures'].configure(text=self._get_text("settings.font_ligatures"))
        self._widgets['cb_ligatures'].configure(text=self._get_text("settings.enable_ligatures"))
        self._widgets['btn_save'].configure(text=self._get_text("settings.save"))
        self._widgets['btn_apply'].configure(text=self._get_text("settings.apply"))
        self._widgets['btn_cancel'].configure(text=self._get_text("settings.cancel"))

    def _on_language_preview(self, event=None):
        """Preview the selected language in real-time by reloading i18n.

        Temporarily writes the language to config so langs_loader.reload()
        picks it up, then refreshes all visible widget texts.
        """
        new_lang = self.lang_var.get()
        if new_lang == self._original_language:
            return
        # Write config so reload() picks up the new language
        self.cfg["language"] = new_lang
        cfg_handle.cfg_handle().write_cfg(self.cfg)
        self._refresh_texts()

    def _on_theme_preview(self, event=None):
        """Apply the selected theme in real-time for immediate visual preview."""
        theme.apply_theme(self.theme_var.get())

    def _on_accent_selected(self, color: str):
        """Apply a preset accent color in real-time.

        Args:
            color: Hex color string from the preset palette
        """
        self.accent_var.set(color)
        theme.apply_accent_color(color)

    def _on_custom_color(self):
        """Open the system color picker for a custom accent color."""
        initial = self.accent_var.get() or "#0078D7"
        result = colorchooser.askcolor(
            color=initial,
            title=self._get_text("settings.custom_color"))
        if result and result[1]:
            color = result[1]
            self.accent_var.set(color)
            theme.apply_accent_color(color)

    def _on_reset_color(self):
        """Reset accent color to the theme's default."""
        self.accent_var.set("")
        theme.apply_accent_color(None)
        # Re-apply theme to restore default primary color
        theme.apply_theme(self.theme_var.get())

    def _apply_settings(self):
        """Save settings to config and apply them without closing the window."""
        self._write_cfg()
        self._original_theme = self._combo_to_current_theme(self.theme_var.get())
        self._original_language = self.lang_var.get()

    def _save_settings(self):
        """Save settings, apply them, and close the window."""
        self._write_cfg()
        self.destroy()

    def _cancel(self):
        """Restore the original theme and language, then close without saving."""
        if self._combo_to_current_theme(self.theme_var.get()) != self._original_theme:
            theme.apply_theme(self._original_theme)
        if self.lang_var.get() != self._original_language:
            self.cfg["language"] = self._original_language
            cfg_handle.cfg_handle().write_cfg(self.cfg)
            langs_loader.langs.reload()
        self.destroy()

    def _write_cfg(self):
        """Write the current settings to config and notify the callback."""
        self.cfg["language"] = self.lang_var.get()
        self.cfg["theme"] = self._combo_to_current_theme(self.theme_var.get())
        self.cfg["accent_color"] = self.accent_var.get()
        self.cfg["auto_reload"] = self.reload_var.get()
        self.cfg["tab_size"] = self.tab_size_var.get()
        self.cfg["font_ligatures"] = self.ligature_var.get()

        result = cfg_handle.cfg_handle().write_cfg(self.cfg)
        if result["status"] == "success":
            if self.on_settings_changed:
                self.on_settings_changed(self.cfg)
        else:
            messagebox.showerror(
                self._get_text("settings.error_title"),
                f"{self._get_text('settings.save_failed')}: {result.get('data', '')}")
