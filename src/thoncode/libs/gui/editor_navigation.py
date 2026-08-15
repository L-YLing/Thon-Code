#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Editor Navigation",
    "Path": ".main.libs.gui.editor_navigation",
    "Entrance": "main.py"
}

"""Ctrl+right-click "Go to definition" for the CodeEditor.

Binds to the editor's ``<Button-3>`` (right-click) event with the ``Control``
modifier. When triggered:

1. Identifies the identifier under the cursor via ``<MouseWheel>`` expansion
   (actually we look at the text position of the click and grab the word).
2. Queries :class:`libs.gui.symbol_loader.SymbolLoaderRegistry` for a
   symbol matching that identifier at the import scope of the current file.
3. If found: opens the target file (creating a new editor tab) and
   scrolls + highlights the definition line.

The navigation module is deliberately small and state-less. It talks to
``EditorManager`` (or the main window) through a callback provided at
construction so it does not depend on concrete layout details.
"""

import re
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional, Tuple

from ..i18n import I18N


_IDENT_RE = re.compile(r"[A-Za-z_][\w\.]*")


class EditorNavigation:
    """Attaches Ctrl+right-click go-to-def behaviour to a ``CodeEditor``."""

    def __init__(self, editor,
                 goto_callback: Optional[Callable[[str, Optional[int]], None]] = None):
        """
        Args:
            editor: The :class:`libs.gui.code_editor.CodeEditor` instance.
            goto_callback: Optional callable ``(abs_path, line_no_or_None)``
                invoked when a definition is found outside the current file.
                When not provided, navigation falls back to asking the
                editor's ``main_window`` attribute to open the target.
        """
        self.editor = editor
        self.goto_callback = goto_callback
        self._i18n = I18N.get_instance()
        self._bind_events()

    # ------------------------------------------------------------------
    # Event wiring
    # ------------------------------------------------------------------

    def _bind_events(self) -> None:
        # On X11 Button-3 is context menu; on Windows Button-3 is right too.
        # Both platforms honour Control. We bind on the text widget so the
        # file-save keybinding in EditorShortcuts is unaffected.
        text = self.editor.text if hasattr(self.editor, "text") else self.editor
        text.bind("<Control-Button-3>", self._on_ctrl_right_click, add="+")

        # Also provide a programmatic entry point for users who want to
        # assign custom shortcuts via the plugin keybinding API.
        self.editor._nav_goto_identifier_at = self._goto_identifier_at_position

    # ------------------------------------------------------------------
    # Identifier extraction
    # ------------------------------------------------------------------

    def _word_under_mouse(self, event) -> Tuple[Optional[str], Optional[str]]:
        """Return ``(position_index, identifier_text)`` for the click target.

        The index is a Tk text index (``"line.col"``) usable for scroll
        anchoring. We accept both ``ClassName.method`` and plain tokens.
        """
        text = self.editor.text if hasattr(self.editor, "text") else self.editor
        try:
            idx = text.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return None, None
        # Expand to include letters/digits/_/. in either direction
        start = text.index(f"{idx} wordstart")
        end = text.index(f"{idx} wordend")
        # Tk's notion of "word" splits on '.', so expand manually.
        line, col = map(int, idx.split("."))
        line_text = text.get(f"{line}.0", f"{line}.end")
        if not line_text:
            return idx, None
        # Find the identifier (optionally dotted) that covers column `col`.
        for m in _IDENT_RE.finditer(line_text):
            s, e = m.start(), m.end()
            if s <= col <= e:
                # walk back to capture leading ClassName prefix if click was on the method part
                token = line_text[s:e]
                # Try expanding backwards across '.' to capture full chain
                # We'll only resolve the full chain if possible; otherwise
                # SymbolLoader falls back to partial matching of the last.
                return idx, token
        return idx, None

    # ------------------------------------------------------------------
    # Handler
    # ------------------------------------------------------------------

    def _on_ctrl_right_click(self, event):
        position, identifier = self._word_under_mouse(event)
        if not identifier:
            return
        self._do_navigation(identifier, position)
        return "break"  # suppress context-menu binding

    def _goto_identifier_at_position(self, tk_index: str):
        text = self.editor.text if hasattr(self.editor, "text") else self.editor
        line, col = map(int, tk_index.split("."))
        line_text = text.get(f"{line}.0", f"{line}.end")
        identifier = None
        for m in _IDENT_RE.finditer(line_text):
            s, e = m.start(), m.end()
            if s <= col <= e:
                identifier = line_text[s:e]
                break
        if identifier:
            self._do_navigation(identifier, tk_index)

    def _do_navigation(self, identifier: str, anchor_index: Optional[str]) -> None:
        editor = self.editor
        # Figure out file context
        current_file = getattr(editor, "current_file", None)
        language = getattr(editor, "language", "") or ""
        # live content from the editor, bypassing stale on-disk cache
        text = editor.text if hasattr(editor, "text") else editor
        try:
            live_text = text.get("1.0", "end-1c")
        except Exception:
            live_text = None

        project_root = ""
        try:
            mw = getattr(editor, "main_window", None)
            if mw is not None:
                project_root = getattr(mw, "current_project", "") or \
                    getattr(mw, "project_root", "") or ""
        except Exception:
            project_root = ""

        from libs.gui.symbol_loader import SymbolLoaderRegistry
        reg = SymbolLoaderRegistry.instance()
        symbol = reg.find_definition(identifier, current_file, language,
                                     project_root, live_text)
        if symbol is None:
            messagebox.showinfo(
                self._i18n.get("navigation.title", "Navigation"),
                self._i18n.get(
                    "navigation.not_found",
                    "Could not locate a definition for '{id}'"
                ).format(id=identifier),
                parent=editor.winfo_toplevel(),
            )
            return

        target_file = symbol.get("file") or current_file
        target_line = int(symbol.get("line", 1))

        same_file = bool(target_file and current_file
                         and str(target_file) == str(current_file))
        if same_file:
            # Scroll & highlight inside current editor
            self._jump_in_current(target_line, anchor_index)
        else:
            # Delegate to main window / callback: open target file + jump
            if self.goto_callback:
                self.goto_callback(target_file, target_line)
            else:
                mw = getattr(editor, "main_window", None)
                if mw is not None and hasattr(mw, "open_file"):
                    mw.open_file(target_file, jump_to_line=target_line)
                else:
                    # No way to open another file; warn user.
                    messagebox.showinfo(
                        self._i18n.get("navigation.title", "Navigation"),
                        self._i18n.get(
                            "navigation.need_tab",
                            "Definition is in '{file}' line {line} but this "
                            "view cannot open new tabs."
                        ).format(file=target_file, line=target_line),
                        parent=editor.winfo_toplevel(),
                    )

    # ------------------------------------------------------------------
    # In-editor jump + transient highlight
    # ------------------------------------------------------------------

    def _jump_in_current(self, line: int, anchor_index: Optional[str]) -> None:
        text = self.editor.text if hasattr(self.editor, "text") else self.editor
        try:
            text.see(f"{line}.0")
            text.mark_set("insert", f"{line}.0")
            text.focus_set()
            # Add transient highlight tag
            tag = "nav_highlight"
            if tag not in text.tag_names():
                text.tag_configure(tag, background="#4A90E2", foreground="white")
            text.tag_remove(tag, "1.0", "end")
            start = f"{line}.0"
            end = f"{line}.end"
            text.tag_add(tag, start, end)
            text.after(800, lambda: text.tag_remove(tag, "1.0", "end"))
        except tk.TclError:
            pass
