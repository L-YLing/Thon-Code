#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Editor Shortcuts",
    "Path": ".main.libs.gui.editor_shortcuts",
    "Entrance": "main.py"
}

from tkinter import messagebox

import libs.langs_loader as langs_loader


class EditorShortcuts:
    """Manages keyboard shortcuts for the code editor.

    Handles save, undo, redo, indentation, and text selection shortcuts.
    """

    def __init__(self, parent):
        """Initialize the editor shortcuts handler.

        Args:
            parent: CodeEditor instance that owns this handler
        """
        self.parent = parent
        self.lang = langs_loader.langs()

    def _get_text(self, key):
        """Get localized text by dot-separated key.

        Args:
            key: Dot-separated i18n key

        Returns:
            Localized string or the key itself if not found
        """
        return getattr(self.lang, key.replace('.', '_'), key)

    def _on_ctrl_s(self, event):
        """Handle Ctrl+S save shortcut.

        Args:
            event: The keyboard event

        Returns:
            "break" to prevent default handling
        """
        if not self.parent.main_window:
            return "break"

        master = self.parent.main_window
        if master.current_file:
            try:
                content = self.parent._textbox.get("1.0", "end-1c")
                with open(master.current_file, "w", encoding="utf-8") as f:
                    f.write(content)
                master.is_dirty = False
                master.last_saved_content = content
                master.update_title()
                master.status_bar.configure(text=f"{self._get_text('editor.saved')} {master.current_file}")
                self.parent._textbox.edit_modified(False)
                self.parent.current_file = master.current_file
                self.parent._completion_enabled = self.parent._should_enable_completion(self.parent.current_file)
            except Exception as e:
                messagebox.showerror(self._get_text('settings.error_title'), f"{self._get_text('editor.save_failed')}: {e}")
        else:
            if hasattr(master, 'save_as'):
                master.save_as()
        return "break"

    def _on_ctrl_z(self, event):
        """Handle Ctrl+Z undo shortcut.

        Args:
            event: The keyboard event

        Returns:
            "break" to prevent default handling
        """
        try:
            self.parent._textbox.edit_undo()
        except Exception:
            pass
        return "break"

    def _on_ctrl_y(self, event):
        """Handle Ctrl+Y redo shortcut.

        Args:
            event: The keyboard event

        Returns:
            "break" to prevent default handling
        """
        try:
            self.parent._textbox.edit_redo()
        except Exception:
            pass
        return "break"

    def _on_ctrl_shift_z(self, event):
        """Handle Ctrl+Shift+Z redo shortcut.

        Args:
            event: The keyboard event

        Returns:
            "break" to prevent default handling
        """
        try:
            self.parent._textbox.edit_redo()
        except Exception:
            pass
        return "break"

    def on_tab(self, event):
        """Handle Tab key for indentation or completion.

        Args:
            event: The keyboard event

        Returns:
            "break" to prevent default handling
        """
        if self.parent.completion_window and self.parent.completion_window.winfo_ismapped():
            self.parent._select_completion()
            return "break"
        text_widget = self.parent._textbox
        if text_widget.tag_ranges("sel"):
            self._indent_selection(1)
            return "break"
        text_widget.insert("insert", " " * self.parent.tab_size)
        return "break"

    def on_shift_tab(self, event):
        """Handle Shift+Tab for un-indentation.

        Args:
            event: The keyboard event

        Returns:
            "break" to prevent default handling
        """
        if self.parent._textbox.tag_ranges("sel"):
            self._indent_selection(-1)
        return "break"

    def _indent_selection(self, direction):
        """Indent or un-indent the current text selection.

        Args:
            direction: 1 for indent, -1 for un-indent
        """
        text_widget = self.parent._textbox
        start = text_widget.index("sel.first")
        end = text_widget.index("sel.last")
        start_line = int(start.split('.')[0])
        end_line = int(end.split('.')[0])
        if end.split('.')[1] == '0' and end_line > start_line:
            end_line -= 1
        for line in range(start_line, end_line + 1):
            line_start = f"{line}.0"
            line_text = text_widget.get(line_start, f"{line}.end")
            leading_spaces = len(line_text) - len(line_text.lstrip(' '))
            if direction == 1:
                text_widget.insert(line_start, " " * self.parent.tab_size)
            else:
                remove_count = min(leading_spaces, self.parent.tab_size)
                if remove_count > 0:
                    text_widget.delete(line_start, f"{line_start}+{remove_count}c")
        self.parent.highlight_all()

    def select_all(self, event=None):
        """Select all text in the editor.

        Args:
            event: Optional keyboard event

        Returns:
            "break" to prevent default handling
        """
        self.parent._hide_completion()
        self.parent._textbox.tag_add("sel", "1.0", "end")
        return "break"