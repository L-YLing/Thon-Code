import tkinter as tk


class EditorCompletion:
    """Code completion popup manager for the editor.

    Manages a completion suggestion listbox window that appears near the cursor
    when the user types matching keywords.

    Args:
        editor: CodeEditor instance providing data source (_textbox, groups, etc.)
        widget_parent: Tkinter widget used as parent for the Toplevel window
    """

    def __init__(self, editor, widget_parent=None):
        """Initialize completion popup.

        Args:
            editor: CodeEditor instance as data source
            widget_parent: Tkinter widget parent for Toplevel; defaults to editor.master
        """
        self.editor = editor
        self.widget_parent = widget_parent if widget_parent else editor.master
        self._is_selecting = False
        self._after_completion_id = None
        self.completion_window = None
        self.completion_listbox = None
        self.completion_matches = []
        self.completion_prefix = ""
        self.completion_word_start = 0
        self._init_completion_window()

    def _init_completion_window(self):
        """Create the completion popup Toplevel window and listbox."""
        self.completion_window = tk.Toplevel(self.widget_parent)
        self.completion_window.wm_overrideredirect(True)
        self.completion_window.wm_attributes("-topmost", True)
        self.completion_window.withdraw()
        self.completion_window.configure(bg="#2b2b2b")

        self.completion_listbox = tk.Listbox(
            self.completion_window,
            bg="#2b2b2b",
            fg="white",
            selectbackground="#0078D7",
            selectforeground="white",
            font=("Microsoft YaHei", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            takefocus=0
        )
        self.completion_listbox.pack(fill="both", expand=True, padx=1, pady=1)
        self.completion_listbox.bind("<ButtonRelease-1>", self._select_completion)
        self.completion_listbox.bind("<Double-Button-1>", self._select_completion)

    def _update_completion(self):
        """Update completion suggestions based on current cursor context."""
        if self._is_selecting:
            return

        if not self.editor._completion_enabled:
            self._hide_completion()
            return

        if not self.editor._textbox.get("1.0", "end-1c").strip():
            self._hide_completion()
            return

        if not self.editor.current_file or not self.editor.current_file.endswith('.py'):
            self._hide_completion()
            return

        text_widget = self.editor._textbox
        cursor = text_widget.index("insert")
        line, col = map(int, cursor.split('.'))
        line_text = text_widget.get(f"{line}.0", f"{line}.end")

        if '#' in line_text[:col] and line_text[:col].rfind('#') >= 0:
            self._hide_completion()
            return
        before = line_text[:col]
        in_string = False
        for i, ch in enumerate(before):
            if ch in ('"', "'") and (i == 0 or before[i-1] != '\\'):
                in_string = not in_string
        if in_string:
            self._hide_completion()
            return

        word_start = col
        while word_start > 0 and (line_text[word_start-1].isalnum() or line_text[word_start-1] == '_'):
            word_start -= 1
        prefix = line_text[word_start:col]
        if not prefix or len(prefix) < 1:
            self._hide_completion()
            return

        all_keywords = []
        for group in self.editor.groups:
            all_keywords.extend(group.get("words", []))
        matches = [kw for kw in all_keywords if kw.startswith(prefix)]
        if not matches:
            self._hide_completion()
            return

        matches = list(dict.fromkeys(matches))[:30]
        self._show_completion(matches, word_start, prefix)

    def _show_completion(self, matches, word_start, prefix):
        """Display the completion popup with matched keywords.

        Args:
            matches: List of matching keyword strings
            word_start: Column index where the completed word begins
            prefix: Current typed prefix string
        """
        self.completion_listbox.delete(0, tk.END)
        for m in matches:
            self.completion_listbox.insert(tk.END, m)
        self.completion_matches = matches
        self.completion_prefix = prefix
        self.completion_word_start = word_start
        self._is_selecting = False

        text_widget = self.editor._textbox
        bbox = text_widget.bbox("insert")
        if bbox:
            x, y, width, height = bbox
            x += text_widget.winfo_rootx()
            y += text_widget.winfo_rooty() + height
            list_height = min(len(matches), 10) * 22 + 4
            self.completion_window.geometry(f"220x{list_height}+{x}+{y}")
            self.completion_window.deiconify()
            self.completion_listbox.selection_clear(0, tk.END)
            self.completion_listbox.selection_set(0)
            self.completion_listbox.see(0)
        else:
            self.completion_window.deiconify()

    def _hide_completion(self, event=None):
        """Hide the completion popup and clear its contents.

        Args:
            event: Optional tkinter event (ignored)
        """
        self._is_selecting = False
        if self.completion_window:
            self.completion_window.withdraw()
            self.completion_listbox.delete(0, tk.END)
            self.completion_matches = []
            self.completion_prefix = ""
            self.completion_listbox.selection_clear(0, tk.END)

    def _select_completion(self, event=None):
        """Apply the currently selected completion suggestion.

        Args:
            event: Optional tkinter event (ignored)
        """
        self._is_selecting = False
        if not self.completion_matches:
            self._hide_completion()
            return
        sel = self.completion_listbox.curselection()
        if not sel:
            if self.completion_matches:
                selected_text = self.completion_matches[0]
            else:
                self._hide_completion()
                return
        else:
            selected_text = self.completion_matches[sel[0]]

        text_widget = self.editor._textbox
        cursor = text_widget.index("insert")
        line, col = map(int, cursor.split('.'))
        start_idx = f"{line}.{col - len(self.completion_prefix)}"
        text_widget.delete(start_idx, cursor)
        text_widget.insert(start_idx, selected_text)
        self._hide_completion()
        self.editor.highlight_all()

    def on_key_press(self, event):
        """Handle keypress events for completion navigation.

        Args:
            event: Tkinter key event

        Returns:
            'break' if the event is consumed, None otherwise
        """
        if self.completion_window and self.completion_window.winfo_ismapped():
            if event.keysym in ('Up', 'Down'):
                if not self.completion_matches:
                    return "break"
                current = self.completion_listbox.curselection()
                idx = current[0] if current else -1
                if event.keysym == 'Up':
                    idx = (idx - 1) % len(self.completion_matches)
                elif event.keysym == 'Down':
                    idx = (idx + 1) % len(self.completion_matches)
                self.completion_listbox.selection_clear(0, tk.END)
                self.completion_listbox.selection_set(idx)
                self.completion_listbox.see(idx)
                self._is_selecting = True
                return "break"
            elif event.keysym == 'Return':
                self._select_completion()
                return "break"
            elif event.keysym == 'Escape':
                self._hide_completion()
                return "break"
        return None