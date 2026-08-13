#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Theme",
    "Path": ".main.libs.gui.theme",
    "Entrance": "main.py"
}

import ttkbootstrap as ttkb
from ttkbootstrap.constants import INFO, SUCCESS, WARNING, DANGER, PRIMARY, SECONDARY
from tkinter import ttk
import tkinter as tk

# Theme mapping: maps config theme values to ttkbootstrap theme names
# Config values: "dark" or "light" (backward compatible)
# Extended values: full ttkbootstrap theme names for per-app theme selection
_THEME_MAP: dict = {
    "dark": "darkly",
    "light": "flatly",
    "darkly": "darkly",
    "flatly": "flatly",
    "cyborg": "cyborg",
    "superhero": "superhero",
    "vapor": "vapor",
    "solar": "solar",
    "dracula": "dracula",
    "vscode_dark": "vscode_dark",
}

# Full list of supported ttkbootstrap theme names
ALL_THEMES: list = [
    "darkly", "flatly", "cyborg", "superhero", "vapor", "solar", "dracula", "vscode_dark"
]

# Dark theme identifiers (for color scheme selection)
DARK_THEME_NAMES: tuple = ("darkly", "cyborg", "superhero", "vapor", "solar", "dracula", "vscode_dark")

# Custom themes not built into ttkbootstrap; each maps to a base theme used
# as fallback if the custom theme cannot be registered programmatically.
_CUSTOM_THEME_BASE: dict = {
    "vscode_dark": "darkly",
    "dracula": "darkly",
}

# Current theme name (ttkbootstrap theme name)
_current_theme: str = "darkly"
_style: ttkb.Style | None = None
_custom_themes_registered: bool = False


def _register_custom_themes() -> None:
    """Register custom theme definitions (vscode_dark, dracula) with ttkbootstrap.

    Attempts to register via ttkbootstrap's ThemeDefinition API so the themes
    become first-class citizens. Falls back silently if the API is unavailable
    (older ttkbootstrap versions); apply_theme then uses a base theme with
    ttk.Style color overrides as a graceful degradation path.
    """
    global _custom_themes_registered
    if _custom_themes_registered:
        return
    _custom_themes_registered = True  # Mark first to avoid retry loops

    try:
        from ttkbootstrap.theme import ThemeDefinition
        from ttkbootstrap.constants import DARK
    except ImportError:
        return

    # Color definitions matching ttkbootstrap's theme color schema
    custom_colors = {
        "vscode_dark": {
            'primary': '#0e639c', 'secondary': '#3a3d41',
            'success': '#4ec9b0', 'info': '#75beff',
            'warning': '#ce9178', 'danger': '#f14c4c',
            'light': '#2d2d2d', 'dark': '#1e1e1e',
            'bg': '#1e1e1e', 'fg': '#cccccc',
            'selectbg': '#094771', 'selectfg': '#ffffff',
            'bordercolor': '#3c3c3c', 'inputbg': '#3c3c3c',
            'inputfg': '#cccccc', 'muted': '#7d7d7d',
        },
        "dracula": {
            'primary': '#bd93f9', 'secondary': '#44475a',
            'success': '#50fa7b', 'info': '#8be9fd',
            'warning': '#ffb86c', 'danger': '#ff5555',
            'light': '#44475a', 'dark': '#282a36',
            'bg': '#282a36', 'fg': '#f8f8f2',
            'selectbg': '#44475a', 'selectfg': '#f8f8f2',
            'bordercolor': '#6272a4', 'inputbg': '#44475a',
            'inputfg': '#f8f8f2', 'muted': '#6272a4',
        },
    }

    try:
        style = ttkb.Style()
    except Exception:
        return

    for name, colors in custom_colors.items():
        try:
            definition = ThemeDefinition(name, colors, DARK)
            style.register_theme(definition)
        except Exception:
            try:
                definition = ThemeDefinition(name=name, colors=colors, themetype=DARK)
                style.register_theme(definition)
            except Exception:
                pass


def _apply_color_overrides(theme_name: str) -> None:
    """Apply custom color overrides to ttk widgets for non-standard themes.

    Used as a fallback when a custom theme cannot be registered with
    ttkbootstrap. Overrides common widget styles via ttk.Style.configure so
    the UI still looks correct without a native ttkbootstrap theme.

    Args:
        theme_name: Custom theme name whose colors to apply
    """
    colors = _THEME_COLOR_MAP.get(theme_name)
    if not colors:
        return
    style = ttk.Style()
    bg = colors.get("bg", "#1e1e1e")
    bg_alt = colors.get("bg_alt", "#252526")
    bg_panel = colors.get("bg_panel", "#2b2b2b")
    fg = colors.get("fg", "#d4d4d4")
    sel_bg = colors.get("sel_bg", "#264f78")
    sel_fg = colors.get("sel_fg", "#ffffff")

    style.configure("TFrame", background=bg)
    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("TButton", background=bg_alt, foreground=fg)
    style.map("TButton",
              background=[("active", bg_panel)],
              foreground=[("active", sel_fg)])
    style.configure("TEntry", fieldbackground=bg_alt, foreground=fg)
    style.configure("TCombobox", fieldbackground=bg_alt, foreground=fg)
    style.configure("TLabelframe", background=bg, foreground=fg)
    style.configure("TLabelframe.Label", background=bg, foreground=fg)
    style.configure("TCheckbutton", background=bg, foreground=fg)
    style.configure("TNotebook", background=bg)
    style.configure("TNotebook.Tab", background=bg_alt, foreground=fg)
    style.map("TNotebook.Tab",
              background=[("selected", bg)],
              foreground=[("selected", sel_fg)])


def apply_theme(theme_name: str) -> None:
    """Apply the specified theme.

    For custom themes (vscode_dark, dracula) not built into ttkbootstrap,
    registers them first and falls back to a base theme with color overrides
    if registration fails, so the app never crashes with TclError.

    Args:
        theme_name: Theme name in project config ("dark", "light", or a full
            ttkbootstrap theme name)
    """
    global _current_theme, _style
    mapped = _THEME_MAP.get(theme_name, theme_name if theme_name in ALL_THEMES else "darkly")
    _current_theme = mapped

    # Register custom themes on first use
    _register_custom_themes()

    try:
        _style = ttkb.Style(theme=mapped)
    except Exception:
        # Custom theme not registered; use base theme with color overrides
        base = _CUSTOM_THEME_BASE.get(mapped, "darkly")
        _style = ttkb.Style(theme=base)
        _apply_color_overrides(mapped)


def get_theme() -> str:
    """Get current ttkbootstrap theme name

    Returns:
        str: Theme name (e.g., "darkly")
    """
    return _current_theme


def get_style() -> ttkb.Style:
    """Get current ttkbootstrap Style instance

    Returns:
        ttkb.Style: Global Style instance
    """
    global _style
    if _style is None:
        _style = ttkb.Style(theme=_current_theme)
    return _style


def create_window(theme_name: str = "dark") -> ttkb.Window:
    """Create ttkbootstrap main window.

    For custom themes (vscode_dark, dracula), registers them first and falls
    back to a base theme if registration fails.

    Args:
        theme_name: Theme name in project config ("dark", "light", or a full
            ttkbootstrap theme name)
    Returns:
        ttkb.Window: Main window configured with theme
    """
    mapped = _THEME_MAP.get(theme_name, theme_name if theme_name in ALL_THEMES else "darkly")
    global _current_theme
    _current_theme = mapped
    _register_custom_themes()
    try:
        return ttkb.Window(themename=mapped)
    except Exception:
        base = _CUSTOM_THEME_BASE.get(mapped, "darkly")
        window = ttkb.Window(themename=base)
        _apply_color_overrides(mapped)
        return window


def create_toplevel(parent, title: str = "", theme_name: str | None = None) -> ttkb.Toplevel:
    """Create ttkbootstrap Toplevel window.

    For custom themes, falls back to current theme if the custom theme fails.

    Args:
        parent: Parent window
        title: Window title
        theme_name: Optional theme name, uses current theme by default
    Returns:
        ttkb.Toplevel: Sub-window configured with theme
    """
    effective = theme_name if theme_name else _current_theme
    mapped = _THEME_MAP.get(effective, effective if effective in ALL_THEMES else _current_theme)
    _register_custom_themes()
    try:
        return ttkb.Toplevel(parent, title=title, themename=mapped)
    except Exception:
        base = _CUSTOM_THEME_BASE.get(mapped, _current_theme)
        return ttkb.Toplevel(parent, title=title, themename=base)


def themed_frame(parent, **kwargs) -> ttk.Frame:
    """Create themed Frame

    Args:
        parent: Parent container
        **kwargs: Additional arguments passed to ttk.Frame
    Returns:
        ttk.Frame: Themed frame
    """
    return ttk.Frame(parent, **kwargs)


def themed_button(parent, text: str = "", command=None, style: str = "TButton", **kwargs) -> ttk.Button:
    """Create themed Button

    Args:
        parent: Parent container
        text: Button text
        command: Click callback
        style: ttk style name (e.g., "Accent.TButton" for primary action buttons)
        **kwargs: Additional arguments passed to ttk.Button
    Returns:
        ttk.Button: Themed button
    """
    return ttk.Button(parent, text=text, command=command, style=style, **kwargs)


def themed_label(parent, text: str = "", style: str = "TLabel", **kwargs) -> ttk.Label:
    """Create themed Label

    Args:
        parent: Parent container
        text: Label text
        style: ttk style name
        **kwargs: Additional arguments passed to ttk.Label
    Returns:
        ttk.Label: Themed label
    """
    return ttk.Label(parent, text=text, style=style, **kwargs)


def themed_entry(parent, style: str = "TEntry", **kwargs) -> ttk.Entry:
    """Create themed Entry

    Args:
        parent: Parent container
        style: ttk style name
        **kwargs: Additional arguments passed to ttk.Entry
    Returns:
        ttk.Entry: Themed entry
    """
    return ttk.Entry(parent, style=style, **kwargs)


def themed_text(parent, **kwargs) -> tk.Text:
    """Create themed Text (ttk has no Text component, using tk.Text + theme colors)

    Args:
        parent: Parent container
        **kwargs: Additional arguments passed to tk.Text
    Returns:
        tk.Text: Text box with theme-adapted colors
    """
    colors = get_colors()
    defaults = {
        "bg": colors["bg"],
        "fg": colors["fg"],
        "insertbackground": colors["fg"],
        "selectbackground": colors["sel_bg"],
        "selectforeground": colors["sel_fg"],
        "relief": "flat",
        "borderwidth": 0,
        "highlightthickness": 0,
        "wrap": "none",
    }
    defaults.update(kwargs)
    return tk.Text(parent, **defaults)


def themed_scrollbar(parent, orient="vertical", **kwargs) -> ttk.Scrollbar:
    """Create themed scrollbar

    Args:
        parent: Parent container
        orient: Orientation ("vertical" or "horizontal")
        **kwargs: Additional arguments passed to ttk.Scrollbar
    Returns:
        ttk.Scrollbar: Themed scrollbar
    """
    return ttk.Scrollbar(parent, orient=orient, **kwargs)


def themed_toplevel(parent, **kwargs) -> tk.Toplevel:
    """Create themed Toplevel window with theme-aware background.

    Args:
        parent: Parent widget
        **kwargs: Additional arguments passed to tk.Toplevel
    Returns:
        tk.Toplevel: Toplevel window with theme colors
    """
    colors = get_colors()
    defaults = {"bg": colors["bg_panel"]}
    defaults.update(kwargs)
    return tk.Toplevel(parent, **defaults)


def themed_listbox(parent, **kwargs) -> tk.Listbox:
    """Create themed Listbox with theme-aware colors.

    Args:
        parent: Parent widget
        **kwargs: Additional arguments passed to tk.Listbox
    Returns:
        tk.Listbox: Listbox with theme colors
    """
    colors = get_colors()
    defaults = {
        "bg": colors["bg_panel"],
        "fg": colors["fg"],
        "selectbackground": colors["sel_bg"],
        "selectforeground": colors["sel_fg"],
        "relief": "flat",
        "borderwidth": 0,
        "highlightthickness": 0,
        "activestyle": "none",
        "takefocus": 0,
    }
    defaults.update(kwargs)
    return tk.Listbox(parent, **defaults)


def themed_label_widget(parent, **kwargs) -> tk.Label:
    """Create themed tk.Label with theme-aware colors (for non-ttk labels).

    Args:
        parent: Parent widget
        **kwargs: Additional arguments passed to tk.Label
    Returns:
        tk.Label: Label with theme colors
    """
    colors = get_colors()
    defaults = {
        "bg": colors.get("bg", "#ffffff"),
        "fg": colors.get("fg", "#1e1e1e"),
    }
    defaults.update(kwargs)
    return tk.Label(parent, **defaults)


def themed_menu(parent, **kwargs) -> tk.Menu:
    """Create themed Menu with theme-aware colors.

    Args:
        parent: Parent widget
        **kwargs: Additional arguments passed to tk.Menu
    Returns:
        tk.Menu: Menu with theme colors
    """
    colors = get_colors()
    defaults = {
        "bg": colors["bg_panel"],
        "fg": colors["fg"],
        "activebackground": colors["sel_bg"],
        "activeforeground": colors["sel_fg"],
        "selectcolor": colors["sel_bg"],
        "tearoff": 0,
    }
    defaults.update(kwargs)
    return tk.Menu(parent, **defaults)


# Theme-related color constants for non-ttk components (e.g., tk.Text, tk.Menu)
COLORS_DARK: dict = {
    "bg": "#1e1e1e",
    "bg_alt": "#252526",
    "bg_panel": "#2b2b2b",
    "fg": "#d4d4d4",
    "fg_dim": "#858585",
    "accent": "#0078D7",
    "border": "#3e3e42",
    "sel_bg": "#264f78",
    "sel_fg": "#ffffff",
}

COLORS_VSCODE_DARK: dict = {
    "bg": "#1e1e1e",
    "bg_alt": "#252526",
    "bg_panel": "#2b2b2b",
    "fg": "#d4d4d4",
    "fg_dim": "#858585",
    "accent": "#0098ff",
    "border": "#3e3e42",
    "sel_bg": "#264f78",
    "sel_fg": "#ffffff",
    "status_bar": "#007acc",
    "title_bar": "#323233",
    "sidebar": "#333333",
    "activity_bar": "#333333",
    "editor_group": "#252526",
}

COLORS_FLATLY: dict = {
    "bg": "#ffffff",
    "bg_alt": "#f8f9fa",
    "bg_panel": "#e9ecef",
    "fg": "#212529",
    "fg_dim": "#6c757d",
    "accent": "#007bff",
    "border": "#dee2e6",
    "sel_bg": "#b6d4fe",
    "sel_fg": "#000000",
}

COLORS_CYBORG: dict = {
    "bg": "#060606",
    "bg_alt": "#0f0f0f",
    "bg_panel": "#151515",
    "fg": "#c5c8c6",
    "fg_dim": "#5d6d7e",
    "accent": "#2a9fd6",
    "border": "#222222",
    "sel_bg": "#2a9fd6",
    "sel_fg": "#ffffff",
}

COLORS_SUPERHERO: dict = {
    "bg": "#2b2b2b",
    "bg_alt": "#363636",
    "bg_panel": "#3f3f3f",
    "fg": "#bdbdbd",
    "fg_dim": "#6c757d",
    "accent": "#2780e3",
    "border": "#4a4a4a",
    "sel_bg": "#2780e3",
    "sel_fg": "#ffffff",
}

COLORS_VAPOR: dict = {
    "bg": "#9c0d4f",
    "bg_alt": "#890b46",
    "bg_panel": "#750a3d",
    "fg": "#f8b3cd",
    "fg_dim": "#e87aa8",
    "accent": "#b880d9",
    "border": "#600a33",
    "sel_bg": "#b880d9",
    "sel_fg": "#ffffff",
}

COLORS_SOLAR: dict = {
    "bg": "#002b36",
    "bg_alt": "#073642",
    "bg_panel": "#0a3a46",
    "fg": "#93a1a1",
    "fg_dim": "#586e75",
    "accent": "#268bd2",
    "border": "#073642",
    "sel_bg": "#268bd2",
    "sel_fg": "#ffffff",
}

COLORS_DRACULA: dict = {
    "bg": "#282a36",
    "bg_alt": "#343746",
    "bg_panel": "#44475a",
    "fg": "#f8f8f2",
    "fg_dim": "#6272a4",
    "accent": "#bd93f9",
    "border": "#44475a",
    "sel_bg": "#bd93f9",
    "sel_fg": "#ffffff",
}

COLORS_LIGHT: dict = {
    "bg": "#ffffff",
    "bg_alt": "#f5f5f5",
    "bg_panel": "#e8e8e8",
    "fg": "#1e1e1e",
    "fg_dim": "#6a6a6a",
    "accent": "#0078D7",
    "border": "#cccccc",
    "sel_bg": "#cfe8ff",
    "sel_fg": "#000000",
}

# Map theme names to their color schemes
_THEME_COLOR_MAP: dict = {
    "darkly": COLORS_DARK,
    "flatly": COLORS_FLATLY,
    "cyborg": COLORS_CYBORG,
    "superhero": COLORS_SUPERHERO,
    "vapor": COLORS_VAPOR,
    "solar": COLORS_SOLAR,
    "dracula": COLORS_DRACULA,
    "vscode_dark": COLORS_VSCODE_DARK,
}


def get_colors() -> dict:
    """Get color scheme of the current theme.

    Returns:
        dict: Dictionary containing color keys like bg/fg/accent/sel_bg
    """
    return _THEME_COLOR_MAP.get(_current_theme, COLORS_DARK)
