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
from libs.gui_libs.style_system import StyleSystem


class EditorUI:
    """Editor UI component: Canvas gutter + text box + scroll synchronization.

    Uses a single tk.Text widget for editing and an EditorGutter (tk.Canvas)
    for line numbers and fold indicators. This eliminates the dual-Text
    misalignment issues that arose from synchronizing two independent
    yview states.

    Style configuration is sourced from StyleSystem singleton for
    cross-component consistency.
    """

    def __init__(self, parent):
        """Initialize editor UI

        Args:
            parent: CodeEditor instance
        """
        self.parent = parent
        self.main_frame = ttk.Frame(parent.master)

        # Initialize style system and sync with current theme
        self._style_system = StyleSystem()
        self._style_system.sync_from_theme()

        # Font loading
        self.font = ("Consolas", 12)
        style_font_family = self._style_system.get_value("editor", "font_family", "Consolas")
        style_font_size = self._style_system.get_value("editor", "font_size", 12)
        if parent.font_ligatures:
            try:
                from libs import font_loader
                loaded_font = font_loader.load_fira_code_font(parent.master, style_font_size, parent.font_ligatures)
                font_name = loaded_font.actual('family')
                font_size = int(loaded_font.actual('size'))
                self.font = (font_name, font_size)
            except Exception:
                self.font = (style_font_family, style_font_size)
        else:
            self.font = (style_font_family, style_font_size)

        # Merge theme colors with style system overrides
        colors = theme.get_colors()
        editor_bg = self._style_system.get_value("editor", "bg", colors["bg"])
        editor_fg = self._style_system.get_value("editor", "fg", colors["fg"])
        editor_fg_dim = self._style_system.get_value("editor", "fg_dim", colors["fg_dim"])
        editor_cursor = self._style_system.get_value("editor", "cursor", editor_fg)
        editor_sel_bg = self._style_system.get_value("editor", "selection_bg", colors["sel_bg"])
        editor_sel_fg = self._style_system.get_value("editor", "selection_fg", colors["sel_fg"])

        # Main text box — single tk.Text (no second Text for line numbers).
        self.textbox = tk.Text(
            self.main_frame,
            bg=editor_bg,
            fg=editor_fg,
            insertbackground=editor_cursor,
            selectbackground=editor_sel_bg,
            selectforeground=editor_sel_fg,
            font=self.font,
            wrap="none",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            spacing1=0,
            spacing2=0,
            spacing3=0,
            undo=True,
            maxundo=100,
        )
        parent._textbox = self.textbox
        parent._textbox_widget = self.textbox

        self._tk_font = tkfont.Font(family=self.font[0], size=self.font[1])
        self.textbox.config(font=self._tk_font)
        self.textbox.tag_config("sel", background=editor_sel_bg, foreground=editor_sel_fg)
        self.textbox.edit_modified(False)

        # Canvas-based gutter (replaces the old tk.Text line-number bar).
        # Shares the same Font object as the textbox so line heights match
        # pixel-for-pixel — no yview synchronization needed.
        self.gutter = None
        try:
            from libs.gui_libs.code_editor.editor_gutter import EditorGutter
            self.gutter = EditorGutter(self.main_frame, self.textbox)
            self.gutter.set_font(self._tk_font)
            self.gutter.set_on_fold_click(self._on_gutter_fold_click)
            self.gutter.set_on_line_click(self._on_gutter_line_click)
            self.gutter.pack(side="left", fill="y", padx=(0, 0))
        except Exception:
            # Gutter is a visual aid; if it fails to load the editor still
            # functions normally with just the text widget.
            pass

        self.textbox.pack(side="left", fill="both", expand=True)

        # Debounce handle for viewport highlight triggered by scrolling.
        self._viewport_highlight_after_id = None

        self._setup_bindings()

    def _setup_bindings(self):
        """Bind keyboard, mouse, scroll events on the main text box.

        Scroll sync strategy: every path that can move the text-box viewport
        (mouse wheel, button-4/5, <Configure> resize, arrow up/down and mouse
        selection) is routed through the unified _on_scroll handler so the
        Canvas gutter is refreshed to match the visible lines. Content
        mutations are observed via the <<Modified>> flag and the debounced
        _on_text_change path.
        """
        parent = self.parent
        tb = parent._textbox

        # Unified scroll/viewport handler.
        tb.bind("<MouseWheel>", parent._on_scroll)
        tb.bind("<Button-4>", parent._on_scroll)
        tb.bind("<Button-5>", parent._on_scroll)
        tb.bind("<Configure>", parent._on_scroll)

        # Arrow up/down and mouse selection can shift the visible viewport.
        tb.bind("<KeyRelease-Up>", parent._on_scroll)
        tb.bind("<KeyRelease-Down>", parent._on_scroll)
        tb.bind("<ButtonRelease-1>", parent.on_cursor_move)
        tb.bind("<ButtonRelease-1>", parent._on_scroll, add="+")

        # Content changes (typing, delete, paste, undo/redo) flow through the
        # modified flag; _on_text_change debounces a gutter refresh.
        tb.bind("<<Modified>>", parent._on_modified)
        tb.bind("<KeyRelease>", parent._on_text_change)

        # Also refresh viewport highlight when scrolling over the gutter.
        if self.gutter:
            self.gutter.bind("<MouseWheel>",
                             lambda e: self._schedule_viewport_highlight(),
                             add="+")

        tb.bind("<Control-s>", parent._on_ctrl_s)
        tb.bind("<Control-S>", parent._on_ctrl_s)
        tb.bind("<Control-z>", parent._on_ctrl_z)
        tb.bind("<Control-Z>", parent._on_ctrl_z)
        tb.bind("<Control-y>", parent._on_ctrl_y)
        tb.bind("<Control-Y>", parent._on_ctrl_y)
        tb.bind("<Control-Shift-Z>", parent._on_ctrl_shift_z)
        tb.bind("<Control-Shift-z>", parent._on_ctrl_shift_z)

        tb.bind("<Control-a>", parent.select_all)
        tb.bind("<Control-A>", parent.select_all)
        tb.bind("<KeyRelease>", parent.on_key_release, add="+")
        tb.bind("<FocusIn>", parent.highlight_all)
        tb.bind("<KeyRelease-Left>", parent.on_cursor_move)
        tb.bind("<KeyRelease-Right>", parent.on_cursor_move)
        tb.bind("<Key>", parent._on_key_press)
        tb.bind("<Tab>", parent.on_tab)
        tb.bind("<Shift-Tab>", parent.on_shift_tab)

    def get_widget(self):
        return self.main_frame

    def get_textbox(self):
        return self.textbox

    def _update_line_numbers(self, event=None):
        """Update the Canvas gutter: sync fold state and scroll position.

        Replaces the old dual-Text rebuild (delete+insert+yview_moveto) with
        a single Canvas refresh. The gutter's virtualized renderer only
        touches visible lines, so this is O(visible) not O(total).
        """
        if not self.gutter:
            return
        if self.parent.folding:
            foldable_starts = self.parent.folding._get_foldable_starts()
            self.gutter.update_fold_state(foldable_starts,
                                          self.parent._folded_lines)
        else:
            self.gutter.sync_scroll()

    def _on_text_change(self, event=None):
        """Delay gutter updates on text change to avoid frequent refreshes"""
        if hasattr(self.parent, '_after_line_id'):
            try:
                self.parent.master.after_cancel(self.parent._after_line_id)
            except Exception:
                pass
        self.parent._after_line_id = self.parent.master.after(50, self.parent._update_line_numbers)

    def _on_modified(self, event=None):
        """Update gutter when text modification flag changes"""
        self.parent._update_line_numbers()
        self.parent._textbox.edit_modified(False)

    def _on_scroll(self, event=None):
        """Unified scroll/viewport handler for the main text box.

        Bound to <MouseWheel>/<Button-4>/<Button-5> (which also drive text-box
        line scrolling), to <Configure> (resize, resync only) and to
        <KeyRelease-Up/Down>/<ButtonRelease-1> (viewport shifts). The Canvas
        gutter is refreshed via sync_scroll() so line numbers track the
        visible lines. Events without a usable delta (configure, key release,
        button release) skip the text-box scroll step and only refresh the
        gutter.
        """
        if event is not None:
            try:
                if hasattr(event, 'num') and event.num in (4, 5):
                    direction = -1 if event.num == 4 else 1
                    self.parent._textbox.yview_scroll(direction, "units")
                elif hasattr(event, 'delta') and event.delta:
                    delta = -1 * (event.delta / 120)
                    self.parent._textbox.yview_scroll(int(delta), "units")
            except Exception:
                pass
        self._sync_line_scroll()
        return None

    def _sync_line_scroll(self):
        """Refresh the Canvas gutter to match the text-box scroll position.

        Replaces the old yview_moveto synchronization between two Text
        widgets. The Canvas reads the text-box yview directly and redraws
        only the visible line numbers.
        """
        if self.gutter:
            self.gutter.sync_scroll()
        self._schedule_viewport_highlight()

    def _schedule_viewport_highlight(self):
        """Debounce viewport highlighting during scrolling for large files."""
        try:
            total_lines = int(self.parent._textbox.index('end-1c').split('.')[0])
        except Exception:
            return
        if total_lines < self.parent.highlight.LARGE_FILE_THRESHOLD:
            return
        if self._viewport_highlight_after_id is not None:
            try:
                self.parent.master.after_cancel(self._viewport_highlight_after_id)
            except Exception:
                pass
        self._viewport_highlight_after_id = self.parent.master.after(
            60, self._run_viewport_highlight
        )

    def _run_viewport_highlight(self):
        """Execute the deferred viewport highlight pass."""
        self._viewport_highlight_after_id = None
        try:
            self.parent.highlight.highlight_visible()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Gutter click callbacks (replaces old _on_line_number_click / _on_line_scroll)
    # ------------------------------------------------------------------

    def _on_gutter_fold_click(self, line_num):
        """Handle fold indicator click in the Canvas gutter.

        Args:
            line_num: 1-indexed line number of the clicked fold indicator
        """
        self.parent.toggle_fold(line_num)

    def _on_gutter_line_click(self, line_num):
        """Handle line number click in the Canvas gutter.

        Moves the insert cursor to the clicked line and scrolls it into view.

        Args:
            line_num: 1-indexed line number that was clicked
        """
        try:
            tb = self.parent._textbox
            tb.mark_set("insert", f"{line_num}.0")
            tb.see(f"{line_num}.0")
        except Exception:
            pass
