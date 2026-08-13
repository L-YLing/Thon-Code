#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Styled Dialog",
    "Path": ".main.libs.gui.styled_dialog",
    "Entrance": "main.py"
}

"""Styled input dialogs using ttkbootstrap widgets.

Replaces tkinter's simpledialog with theme-consistent Toplevel dialogs.
Supports both single-line (branch name) and multi-line (commit message) input.
"""

import ttkbootstrap as ttkb
import tkinter as tk
from tkinter import ttk
from typing import Optional

from libs.gui import theme
import libs.langs_loader as langs_loader


class StyledInputDialog:
    """Modal input dialog with ttkbootstrap styling.

    Creates a themed Toplevel window with a label, input field, and
    OK/Cancel buttons. Supports single-line Entry or multi-line Text
    input depending on the ``multiline`` parameter.
    """

    def __init__(self, parent, title: str = "", prompt: str = "",
                 initialvalue: str = "", multiline: bool = False,
                 width: int = 400, height: int = 0):
        """Initialize the styled input dialog.

        Args:
            parent: Parent widget
            title: Window title
            prompt: Label text shown above the input field
            initialvalue: Pre-filled input value
            multiline: If True, use a Text widget; otherwise use Entry
            width: Dialog width in pixels
            height: Dialog height in pixels (0 = auto: 160 single-line, 320 multi-line)
        """
        if height <= 0:
            height = 320 if multiline else 160
        self._result: Optional[str] = None
        self._multiline = multiline

        self.window = ttkb.Toplevel(parent)
        self.window.title(title)
        self.window.geometry(f"{width}x{height}")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()

        colors = theme.get_colors()
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Prompt label
        if prompt:
            ttk.Label(main_frame, text=prompt, anchor="w").pack(
                fill="x", pady=(0, 8))

        # Input field
        if multiline:
            input_frame = ttk.Frame(main_frame)
            input_frame.pack(fill="both", expand=True, pady=(0, 10))
            self._text = tk.Text(
                input_frame, height=5, wrap="word",
                bg=colors["bg_alt"], fg=colors["fg"],
                insertbackground=colors["fg"],
                selectbackground=colors["sel_bg"],
                selectforeground=colors["sel_fg"],
                relief="flat", borderwidth=1,
                highlightthickness=1,
                highlightcolor=colors["accent"],
                highlightbackground=colors["border"],
                font=("Consolas", 10))
            self._text.pack(side="left", fill="both", expand=True)
            scrollbar = ttk.Scrollbar(
                input_frame, orient="vertical", command=self._text.yview)
            scrollbar.pack(side="right", fill="y")
            self._text.configure(yscrollcommand=scrollbar.set)
            if initialvalue:
                self._text.insert("1.0", initialvalue)
            self._text.focus_set()
        else:
            self._var = tk.StringVar(value=initialvalue)
            self._entry = ttk.Entry(main_frame, textvariable=self._var)
            self._entry.pack(fill="x", pady=(0, 10))
            self._entry.focus_set()

        # Button frame
        lang = langs_loader.langs()
        ok_text = getattr(lang, 'dialog_ok', 'OK')
        cancel_text = getattr(lang, 'dialog_cancel', 'Cancel')
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text=ok_text,
                   command=self._on_ok,
                   style="Success.TButton").pack(
            side="right", padx=(5, 0))
        ttk.Button(btn_frame, text=cancel_text,
                   command=self._on_cancel).pack(
            side="right", padx=(0, 5))

        # Handle Enter key for single-line input
        if not multiline:
            self._entry.bind("<Return>", lambda e: self._on_ok())
            self._entry.bind("<KP_Enter>", lambda e: self._on_ok())

        # Handle Escape to cancel
        self.window.bind("<Escape>", lambda e: self._on_cancel())

        self.window.lift()
        self.window.focus_force()

        # Wait for the window to close
        self.window.wait_window()

    def _on_ok(self):
        """Accept the input and close the dialog."""
        if self._multiline:
            self._result = self._text.get("1.0", "end-1c")
        else:
            self._result = self._var.get()
        self.window.destroy()

    def _on_cancel(self):
        """Cancel the dialog without returning a result."""
        self._result = None
        self.window.destroy()

    def get_result(self) -> Optional[str]:
        """Return the entered text, or None if cancelled.

        Returns:
            The user's input string, or None if the dialog was cancelled
        """
        return self._result


def ask_string(parent, title: str, prompt: str = "",
               initialvalue: str = "", multiline: bool = False) -> Optional[str]:
    """Show a styled input dialog and return the result.

    Args:
        parent: Parent widget
        title: Window title
        prompt: Label text shown above the input field
        initialvalue: Pre-filled input value
        multiline: If True, use a multi-line Text widget

    Returns:
        The entered string, or None if cancelled
    """
    dialog = StyledInputDialog(
        parent, title=title, prompt=prompt,
        initialvalue=initialvalue, multiline=multiline)
    return dialog.get_result()
