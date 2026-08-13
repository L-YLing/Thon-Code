#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui-libs",
    "Name": "Thon Code Canvas Entry",
    "Path": ".main.libs.gui_libs.widgets.canvas_entry",
    "Entrance": "main.py"
}

"""
Themed entry widget with focus highlight and placeholder support.

Wraps a tk.Entry inside a thin themed border frame. The border lights up
with the accent color when the entry is focused, the placeholder text is
shown in a dim color while the field is empty and unfocused, and all
colors and fonts come from the StyleSystem singleton.
"""

import tkinter as tk
import tkinter.font as tkfont
from typing import Any, Optional

from libs.gui_libs.style_system import StyleSystem
from libs.gui_libs.base import BaseWidget, StyleProvider


class CanvasEntry(BaseWidget, StyleProvider):
    """Themed single-line text entry with placeholder and focus border.

    The entry is wrapped in a 1-pixel border frame whose color switches to
    the accent color on focus. A placeholder string is displayed in a dim
    color whenever the entry is empty and not focused.
    """

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        """Initialize the themed entry.

        Args:
            parent: Parent Tkinter widget.
            **kwargs: Optional configuration. Recognized keys:
                placeholder (str): Placeholder text shown when empty.
                text (str): Initial entry content.
                show (str): Character used to mask input (e.g. '*').
                width (int): Entry width in characters.
                font_family (str): Override the font family.
                font_size (int): Override the font size.
        """
        self._parent = parent
        self._outer: Optional[tk.Frame] = None
        self._entry: Optional[tk.Entry] = None
        self._font: Optional[tkfont.Font] = None

        self._placeholder: str = kwargs.get("placeholder", "")
        self._show_char: str = kwargs.get("show", "")
        self._width: int = int(kwargs.get("width", 24))
        self._font_family_override: Optional[str] = kwargs.get("font_family", None)
        self._font_size_override: Optional[int] = kwargs.get("font_size", None)
        self._initial_text: str = kwargs.get("text", "")

        # Style values (populated by _load_style).
        self._bg: str = "#282c34"
        self._fg: str = "#abb2bf"
        self._fg_dim: str = "#5c6370"
        self._accent: str = "#528bff"
        self._border: str = "#3e4451"
        self._font_family: str = "Microsoft YaHei"
        self._font_size: int = 10
        self._placeholder_shown: bool = False

        self._style_system = StyleSystem()
        super().__init__(parent)

    # ---- BaseWidget implementation ----

    def create_widget(self) -> tk.Frame:
        """Create the border frame and inner entry widget.

        Returns:
            The outer border frame.
        """
        self._load_style()
        family = self._font_family_override or self._font_family
        size = self._font_size_override or self._font_size
        self._font = tkfont.Font(family=family, size=size)

        # Outer frame acts as a 1-pixel themed border.
        self._outer = tk.Frame(self._parent, bg=self._border, bd=0)
        self._entry = tk.Entry(
            self._outer,
            bg=self._bg,
            fg=self._fg,
            insertbackground=self._fg,
            selectbackground=self._accent,
            selectforeground="#ffffff",
            relief="flat",
            bd=0,
            highlightthickness=0,
            borderwidth=0,
            width=self._width,
            font=self._font,
        )
        if self._show_char:
            self._entry.configure(show=self._show_char)

        self._entry.pack(fill="x", padx=1, pady=1)

        self._setup_bindings()
        # Initialize placeholder/initial text state.
        if self._initial_text:
            self._entry.insert(0, self._initial_text)
            self._placeholder_shown = False
        else:
            self._show_placeholder()
        return self._outer

    def pack(self, **kwargs: Any) -> None:
        """Pack the entry into its parent.

        Args:
            **kwargs: Pack configuration options.
        """
        if self._outer:
            self._outer.pack(**kwargs)

    def grid(self, **kwargs: Any) -> None:
        """Grid the entry into its parent.

        Args:
            **kwargs: Grid configuration options.
        """
        if self._outer:
            self._outer.grid(**kwargs)

    def destroy(self) -> None:
        """Destroy the entry and release resources."""
        if self._outer and not self._destroyed:
            self._outer.destroy()
            self._destroyed = True

    def get_widget(self) -> Optional[tk.Frame]:
        """Get the outer border frame.

        Returns:
            The outer frame, or None if not yet created.
        """
        return self._outer

    def get_entry(self) -> Optional[tk.Entry]:
        """Get the inner tk.Entry widget.

        Returns:
            The entry widget, or None if not yet created.
        """
        return self._entry

    # ---- Style loading ----

    def _load_style(self) -> None:
        """Load entry style values from the StyleSystem singleton."""
        ss = self._style_system
        self._bg = ss.get_value("widget", "bg", "#282c34")
        self._fg = ss.get_value("widget", "fg", "#abb2bf")
        self._fg_dim = ss.get_value("widget", "disabled_fg", "#5c6370")
        self._accent = ss.get_value("widget", "accent", "#528bff")
        self._border = ss.get_value("widget", "border", "#3e4451")
        self._font_family = ss.get_value("widget", "font_family", "Microsoft YaHei")
        self._font_size = ss.get_value("widget", "font_size", 10)

    # ---- Event handling ----

    def _setup_bindings(self) -> None:
        """Bind focus and edit events for the border and placeholder."""
        if not self._entry:
            return
        self._entry.bind("<FocusIn>", self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)
        self._entry.bind("<Key>", self._on_key)

    def _on_focus_in(self, event: tk.Event) -> None:
        """Highlight the border with the accent color and clear placeholder.

        Args:
            event: The focus event.
        """
        if self._outer:
            self._outer.configure(bg=self._accent)
        if self._placeholder_shown:
            self._clear_placeholder()

    def _on_focus_out(self, event: tk.Event) -> None:
        """Restore the normal border color and reshow placeholder if empty.

        Args:
            event: The focus event.
        """
        if self._outer:
            self._outer.configure(bg=self._border)
        if self._entry and not self._entry.get():
            self._show_placeholder()

    def _on_key(self, event: tk.Event) -> None:
        """Ensure real typing removes the placeholder styling.

        Args:
            event: The key event.
        """
        if self._placeholder_shown and event.keysym not in (
            "Shift_L", "Shift_R", "Control_L", "Control_R",
            "Alt_L", "Alt_R", "Tab",
        ):
            self._clear_placeholder()

    # ---- Placeholder management ----

    def _show_placeholder(self) -> None:
        """Display the placeholder text in the dim color."""
        if not self._entry or not self._placeholder:
            return
        self._entry.delete(0, tk.END)
        self._entry.configure(fg=self._fg_dim)
        self._entry.insert(0, self._placeholder)
        self._placeholder_shown = True

    def _clear_placeholder(self) -> None:
        """Remove the placeholder text and restore the normal color."""
        if not self._entry:
            return
        self._entry.delete(0, tk.END)
        self._entry.configure(fg=self._fg)
        self._placeholder_shown = False

    # ---- Public API ----

    def get(self) -> str:
        """Return the current entry content.

        Returns an empty string when the placeholder is being shown.

        Returns:
            The current text value.
        """
        if not self._entry:
            return ""
        if self._placeholder_shown:
            return ""
        return self._entry.get()

    def set(self, text: str) -> None:
        """Replace the entry content with the given text.

        Args:
            text: New text value.
        """
        if not self._entry:
            return
        self._clear_placeholder()
        self._entry.delete(0, tk.END)
        self._entry.insert(0, text)
        if not text and self._placeholder and not self._entry.focus_get():
            self._show_placeholder()

    def clear(self) -> None:
        """Clear the entry content and reshow the placeholder if needed."""
        if not self._entry:
            return
        self._clear_placeholder()
        self._entry.delete(0, tk.END)
        if self._placeholder and not self._entry.focus_get():
            self._show_placeholder()

    def set_placeholder(self, placeholder: str) -> None:
        """Update the placeholder text.

        Args:
            placeholder: New placeholder text.
        """
        self._placeholder = placeholder
        if self._entry and not self._entry.get() and not self._entry.focus_get():
            if self._placeholder_shown:
                self._entry.delete(0, tk.END)
            self._show_placeholder()

    # ---- StyleProvider implementation ----

    def apply_style(self, style_name: str) -> None:
        """Apply a named style registered in the StyleSystem.

        Args:
            style_name: Name of the style to apply.
        """
        if self._style_system.apply_style(style_name):
            self._load_style()
            self._refresh_colors()

    def get_style_value(self, key: str, default: Any = None) -> Any:
        """Get a style value from the 'widget' section.

        Args:
            key: Style property key.
            default: Default value if key is not found.

        Returns:
            The style value or the provided default.
        """
        return self._style_system.get_value("widget", key, default)

    def set_style_value(self, key: str, value: Any) -> None:
        """Set a style value on the 'widget' section and refresh.

        Args:
            key: Style property key.
            value: New value.
        """
        self._style_system.set_style("widget", key, value)
        self._load_style()
        self._refresh_colors()

    def _refresh_colors(self) -> None:
        """Apply current style colors to the entry and border."""
        if not self._entry:
            return
        family = self._font_family_override or self._font_family
        size = self._font_size_override or self._font_size
        if self._font:
            self._font.configure(family=family, size=size)
        focused = self._entry.focus_get() is self._entry
        if self._outer:
            self._outer.configure(bg=self._accent if focused else self._border)
        if not self._placeholder_shown:
            self._entry.configure(
                bg=self._bg, fg=self._fg, insertbackground=self._fg,
                selectbackground=self._accent,
            )
        else:
            self._entry.configure(
                bg=self._bg, fg=self._fg_dim, insertbackground=self._fg,
                selectbackground=self._accent,
            )
