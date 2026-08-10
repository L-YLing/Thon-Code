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

# Current theme name (ttkbootstrap theme name)
_current_theme: str = "darkly"
_style: ttkb.Style | None = None


def apply_theme(theme_name: str) -> None:
    """Apply the specified theme

    Args:
        theme_name: Theme name in project config ("dark", "light", or a full ttkbootstrap theme name)
    """
    global _current_theme, _style
    mapped = _THEME_MAP.get(theme_name, theme_name if theme_name in ALL_THEMES else "darkly")
    _current_theme = mapped
    _style = ttkb.Style(theme=mapped)


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
    """Create ttkbootstrap main window

    Args:
        theme_name: Theme name in project config ("dark", "light", or a full ttkbootstrap theme name)
    Returns:
        ttkb.Window: Main window configured with theme
    """
    mapped = _THEME_MAP.get(theme_name, theme_name if theme_name in ALL_THEMES else "darkly")
    global _current_theme
    _current_theme = mapped
    return ttkb.Window(themename=mapped)


def create_toplevel(parent, title: str = "", theme_name: str | None = None) -> ttkb.Toplevel:
    """Create ttkbootstrap Toplevel window

    Args:
        parent: Parent window
        title: Window title
        theme_name: Optional theme name, uses current theme by default
    Returns:
        ttkb.Toplevel: Sub-window configured with theme
    """
    effective = theme_name if theme_name else _current_theme
    mapped = _THEME_MAP.get(effective, effective if effective in ALL_THEMES else _current_theme)
    return ttkb.Toplevel(parent, title=title, themename=mapped)


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
