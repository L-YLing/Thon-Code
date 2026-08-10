#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code",
    "Path": ".main.libs.gui.editor_ui",
    "Entrance": "main.py"
}

from tkinter import ttk
import tkinter as tk
import tkinter.font as tkfont

from libs.gui.lazy_loader import LazyLoader
from libs.gui import theme


class EditorUI:
    """Editor UI component: line number bar + text box + scroll synchronization

    Migrated to ttk + tk.Text: no longer uses CTkTextbox wrapper layer,
    both line number bar and main text box are tk.Text, unified appearance via theme colors.
    """

    # Line number bar elide tag (independent from main text box but synchronized folding)
    LINE_FOLD_TAG = "line_fold_elided"

    def __init__(self, parent):
        """Initialize editor UI

        Args:
            parent: CodeEditor instance
        """
        self.parent = parent
        self.main_frame = ttk.Frame(parent.master)

        # Font loading
        self.font = ("Consolas", 12)
        if parent.font_ligatures:
            try:
                font_loader = LazyLoader.get('libs', 'font_loader')
                loaded_font = font_loader.load_fira_code_font(parent.master, 12, parent.font_ligatures)
                font_name = loaded_font.actual('family')
                font_size = int(loaded_font.actual('size'))
                self.font = (font_name, font_size)
            except Exception:
                self.font = ("Consolas", 12)

        colors = theme.get_colors()

        # Line number bar — tk.Text with theme colors
        self.line_numbers = tk.Text(
            self.main_frame,
            width=6,
            bg=colors["bg"],
            fg=colors["fg_dim"],
            insertbackground=colors["fg_dim"],
            selectbackground=colors["sel_bg"],
            selectforeground=colors["sel_fg"],
            font=self.font,
            wrap="none",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            state="disabled",
            cursor="arrow",
        )
        self.line_numbers.pack(side="left", fill="y", padx=(0, 0))

        # Main text box — tk.Text with theme colors
        self.textbox = tk.Text(
            self.main_frame,
            bg=colors["bg"],
            fg=colors["fg"],
            insertbackground=colors["fg"],
            selectbackground=colors["sel_bg"],
            selectforeground=colors["sel_fg"],
            font=self.font,
            wrap="none",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            undo=True,
            maxundo=100,
        )
        # Directly set parent reference (no longer has CTkTextbox._textbox middle layer)
        parent._textbox = self.textbox
        parent._textbox_widget = self.textbox

        self._tk_font = tkfont.Font(family=self.font[0], size=self.font[1])
        self.textbox.config(font=self._tk_font)
        self.textbox.tag_config("sel", background=colors["sel_bg"], foreground=colors["sel_fg"])
        self.textbox.edit_modified(False)
        self.textbox.pack(side="left", fill="both", expand=True)

        # Line number bar elide tag configuration
        self.line_numbers.tag_config(self.LINE_FOLD_TAG, elide=True)

        self._setup_bindings()

    def _setup_bindings(self):
        """Bind keyboard, mouse, scroll events"""
        parent = self.parent
        parent._textbox.bind("<MouseWheel>", parent._on_scroll)
        parent._textbox.bind("<Button-4>", parent._on_scroll)
        parent._textbox.bind("<Button-5>", parent._on_scroll)
        parent._textbox.bind("<KeyRelease>", parent._on_text_change)
        parent._textbox.bind("<Configure>", parent._update_line_numbers)
        parent._textbox.bind("<<Modified>>", parent._on_modified)

        self.line_numbers.bind("<Button-1>", parent._on_line_number_click)
        self.line_numbers.bind("<MouseWheel>", parent._on_line_scroll)
        self.line_numbers.bind("<Button-4>", parent._on_line_scroll)
        self.line_numbers.bind("<Button-5>", parent._on_line_scroll)

        parent._textbox.bind("<Control-s>", parent._on_ctrl_s)
        parent._textbox.bind("<Control-S>", parent._on_ctrl_s)
        parent._textbox.bind("<Control-z>", parent._on_ctrl_z)
        parent._textbox.bind("<Control-Z>", parent._on_ctrl_z)
        parent._textbox.bind("<Control-y>", parent._on_ctrl_y)
        parent._textbox.bind("<Control-Y>", parent._on_ctrl_y)
        parent._textbox.bind("<Control-Shift-Z>", parent._on_ctrl_shift_z)
        parent._textbox.bind("<Control-Shift-z>", parent._on_ctrl_shift_z)

        parent._textbox.bind("<Control-a>", parent.select_all)
        parent._textbox.bind("<Control-A>", parent.select_all)
        parent._textbox.bind("<KeyRelease>", parent.on_key_release)
        parent._textbox.bind("<FocusIn>", parent.highlight_all)
        parent._textbox.bind("<ButtonRelease-1>", parent.on_cursor_move)
        parent._textbox.bind("<KeyRelease-Left>", parent.on_cursor_move)
        parent._textbox.bind("<KeyRelease-Right>", parent.on_cursor_move)
        parent._textbox.bind("<Key>", parent._on_key_press)
        parent._textbox.bind("<Tab>", parent.on_tab)
        parent._textbox.bind("<Shift-Tab>", parent.on_shift_tab)

    def get_widget(self):
        return self.main_frame

    def get_textbox(self):
        return self.textbox

    def _update_line_numbers(self, event=None):
        """Update line number bar content, synchronize fold elide state and fold markers

        Line number bar and main text box use the same elide logic:
        - Line numbers corresponding to folded regions are also elided in the line number bar, ensuring visual alignment
        - Foldable lines show ▾ marker, folded lines show ▸ marker
        """
        if not self.parent._textbox:
            return

        # Get total line count
        try:
            line_count = int(self.parent._textbox.index('end-1c').split('.')[0])
        except Exception:
            line_count = 1

        # Get foldable regions and folded state
        fold_regions = []
        folded = self.parent._folded_lines
        if self.parent.folding and self.parent.language == "python":
            fold_regions = self.parent._get_foldable_regions()
        foldable_starts = {start for start, _ in fold_regions}

        # Generate line number text (with fold markers)
        line_texts = []
        for i in range(1, line_count + 1):
            marker = ''
            if i in foldable_starts:
                marker = '▾ ' if i not in folded else '▸ '
            line_texts.append(f"{marker}{i}")

        # Write to line number bar (tk.Text direct operation, no ._textbox middle layer)
        ln = self.line_numbers
        ln.config(state="normal")
        ln.delete("1.0", "end")
        ln.insert("1.0", "\n".join(line_texts))

        # Elide line numbers corresponding to folded regions in the line number bar
        ln.tag_remove(self.LINE_FOLD_TAG, "1.0", "end")
        for start_line, end_line in folded.items():
            if end_line <= line_count:
                ln.tag_add(self.LINE_FOLD_TAG, f"{start_line + 1}.0", f"{end_line + 1}.0")

        ln.config(state="disabled")

        # Synchronize scroll position
        try:
            ln.yview_moveto(self.parent._textbox.yview()[0])
        except Exception:
            pass

    def _on_text_change(self, event=None):
        """Delay line number updates on text change to avoid frequent refreshes"""
        if hasattr(self.parent, '_after_line_id'):
            try:
                self.parent.master.after_cancel(self.parent._after_line_id)
            except Exception:
                pass
        self.parent._after_line_id = self.parent.master.after(50, self.parent._update_line_numbers)

    def _on_modified(self, event=None):
        """Update line numbers when text modification flag changes"""
        self.parent._update_line_numbers()
        self.parent._textbox.edit_modified(False)

    def _on_scroll(self, event):
        """Synchronize line number bar when main text box scrolls"""
        try:
            if hasattr(event, 'num'):
                if event.num == 4:
                    self.parent._textbox.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.parent._textbox.yview_scroll(1, "units")
            else:
                delta = -1 * (event.delta / 120)
                self.parent._textbox.yview_scroll(int(delta), "units")
        except Exception:
            pass
        self._sync_line_scroll()
        return None

    def _on_line_scroll(self, event):
        """Synchronize main text box when line number bar scrolls"""
        try:
            if hasattr(event, 'num'):
                if event.num == 4:
                    self.parent._textbox.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.parent._textbox.yview_scroll(1, "units")
            else:
                delta = -1 * (event.delta / 120)
                self.parent._textbox.yview_scroll(int(delta), "units")
        except Exception:
            pass
        self._sync_line_scroll()
        return "break"

    def _sync_line_scroll(self):
        """Synchronize scroll positions between line number bar and main text box"""
        try:
            self.line_numbers.yview_moveto(self.parent._textbox.yview()[0])
        except Exception:
            pass

    def _on_line_number_click(self, event):
        """Click line number bar: fold/unfold corresponding line"""
        if self.parent.language != "python":
            return

        index = self.line_numbers.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0])

        # Get foldable regions
        fold_regions = self.parent._get_foldable_regions()
        foldable_starts = [start for start, _ in fold_regions]

        # Use parent._folded_lines uniformly to check fold state
        if line_num in foldable_starts or line_num in self.parent._folded_lines:
            self.parent.toggle_fold(line_num)
