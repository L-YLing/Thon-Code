#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui-libs",
    "Name": "Thon Code Canvas Editor",
    "Path": ".main.libs.gui_libs.code_editor.canvas_editor",
    "Entrance": "main.py"
}

"""
Canvas-based code editor with hybrid tk.Text + Canvas overlay architecture.

Architecture:
- tk.Text: Handles text editing, IME, clipboard, undo/redo, accessibility
- Canvas overlay: Renders line numbers, fold indicators, and custom decorations
- StyleSystem: Provides centralized theming for all visual properties
"""

import os
import json
import tkinter as tk
import tkinter.font as tkfont
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from libs.gui_libs.style_system import StyleSystem
from libs.gui_libs.base import BaseWidget, StyleProvider, EventHandler, LazyLoadable
from libs.gui_libs.code_editor.editor_gutter import EditorGutter


class CanvasCodeEditor(BaseWidget, StyleProvider, EventHandler, LazyLoadable):
    """Highly customizable code editor using Canvas overlays.

    Combines the robustness of tk.Text for text editing with Canvas overlays
    for line numbers, fold indicators, and custom decorations.

    Features:
    - Configurable style system (colors, fonts, spacing)
    - Canvas-based line number bar with click-to-jump
    - Canvas-based fold gutter with expand/collapse indicators
    - Syntax highlighting for multiple languages
    - Auto-completion popup system
    - Customizable key bindings
    - Mouse event handling (click, drag, hover, scroll)
    - Lazy loading support for heavy features
    """

    def __init__(self, parent: tk.Misc, **kwargs) -> None:
        """Initialize the canvas code editor.

        Args:
            parent: Parent widget container
            **kwargs: Additional configuration options
        """
        self._parent = parent
        self._main_frame: Optional[tk.Frame] = None
        self._text_widget: Optional[tk.Text] = None
        self._gutter: Optional[EditorGutter] = None
        self._scrollbar: Optional[tk.Scrollbar] = None
        self._line_numbers: Optional[tk.Canvas] = None
        self._fold_gutter: Optional[tk.Canvas] = None

        self._current_file: Optional[str] = None
        self._language: str = "python"
        self._font_family: str = "Consolas"
        self._font_size: int = 12
        self._tab_size: int = 4
        self._is_dirty: bool = False
        self._last_saved_content: str = ""

        self._folded_lines: Dict[int, int] = {}
        self._fold_regions: List[Tuple[int, int]] = []
        self._highlight_groups: List[Dict[str, Any]] = []
        self._completion_enabled: bool = False
        self._loaded: bool = False

        self._on_file_changed: Optional[Callable[[str], None]] = None
        self._on_text_modified: Optional[Callable[[], None]] = None
        self._on_cursor_moved: Optional[Callable[[], None]] = None

        self._style_system = StyleSystem()
        self._editor_font: Optional[tkfont.Font] = None

        super().__init__(parent)

    def create_widget(self) -> tk.Frame:
        """Create the editor widget hierarchy.

        Returns:
            The main frame containing all editor sub-widgets
        """
        self._main_frame = tk.Frame(self._parent)
        self._apply_style_to_frame()
        self._create_text_widget()
        self._create_gutter()
        self._create_scrollbar()
        self._setup_layout()
        self._setup_bindings()
        self._loaded = True
        self._apply_highlight_tags()
        return self._main_frame

    def _apply_style_to_frame(self) -> None:
        """Apply current style configuration to the main frame."""
        bg = self._style_system.get_value("editor", "bg", "#282c34")
        self._main_frame.configure(bg=bg)

    def _create_text_widget(self) -> None:
        """Create the main tk.Text editing widget."""
        style = self._style_system.get_style("editor")
        bg = style.get("bg", "#282c34")
        fg = style.get("fg", "#abb2bf")
        cursor_color = style.get("cursor", "#528bff")
        sel_bg = style.get("selection_bg", "#264f78")
        sel_fg = style.get("selection_fg", "#ffffff")
        pad_x = style.get("pad_x", 4)
        pad_y = style.get("pad_y", 4)

        self._editor_font = tkfont.Font(
            family=self._font_family,
            size=self._font_size
        )

        self._text_widget = tk.Text(
            self._main_frame,
            bg=bg,
            fg=fg,
            insertbackground=cursor_color,
            selectbackground=sel_bg,
            selectforeground=sel_fg,
            font=self._editor_font,
            wrap="none",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            undo=True,
            maxundo=100,
            padx=pad_x,
            pady=pad_y,
            spacing1=0,
            spacing3=0,
        )

        self._text_widget.tag_config("sel", background=sel_bg, foreground=sel_fg)
        self._text_widget.edit_modified(False)

    def _create_gutter(self) -> None:
        """Create the Canvas-based gutter with line numbers and fold indicators."""
        self._gutter = EditorGutter(
            self._main_frame,
            self._text_widget
        )
        self._gutter.set_on_fold_click(self._on_fold_click)
        self._gutter.set_on_line_click(self._on_line_click)

    def _create_scrollbar(self) -> None:
        """Create the vertical scrollbar."""
        self._scrollbar = tk.Scrollbar(
            self._main_frame,
            orient="vertical",
            command=self._on_scrollbar
        )
        self._text_widget.configure(yscrollcommand=self._scrollbar.set)

    def _setup_layout(self) -> None:
        """Arrange editor widgets in the correct layout."""
        self._gutter.pack(side="left", fill="y")
        self._scrollbar.pack(side="right", fill="y")
        self._text_widget.pack(side="left", fill="both", expand=True)

    def _setup_bindings(self) -> None:
        """Setup keyboard, mouse, and scroll event bindings."""
        tw = self._text_widget

        # Scrolling synchronization
        tw.bind("<MouseWheel>", self._on_mousewheel)
        tw.bind("<Button-4>", lambda e: self._scroll_text(-1))
        tw.bind("<Button-5>", lambda e: self._scroll_text(1))
        tw.bind("<Configure>", lambda e: self._gutter.sync_scroll())

        # Text change events
        tw.bind("<KeyRelease>", self._on_text_change)
        tw.bind("<<Modified>>", self._on_modified)
        tw.bind("<FocusIn>", lambda e: self._refresh_highlight())

        # Cursor movement
        tw.bind("<ButtonRelease-1>", self._on_cursor_move)
        tw.bind("<KeyRelease-Left>", self._on_cursor_move)
        tw.bind("<KeyRelease-Right>", self._on_cursor_move)

        # Key bindings
        tw.bind("<Control-s>", self._on_ctrl_s)
        tw.bind("<Control-S>", self._on_ctrl_s)
        tw.bind("<Control-z>", self._on_ctrl_z)
        tw.bind("<Control-Z>", self._on_ctrl_z)
        tw.bind("<Control-y>", self._on_ctrl_y)
        tw.bind("<Control-Y>", self._on_ctrl_y)
        tw.bind("<Control-Shift-Z>", self._on_ctrl_shift_z)
        tw.bind("<Control-Shift-z>", self._on_ctrl_shift_z)
        tw.bind("<Control-a>", lambda e: self.select_all())
        tw.bind("<Control-A>", lambda e: self.select_all())
        tw.bind("<Tab>", self._on_tab)
        tw.bind("<Shift-Tab>", self._on_shift_tab)
        tw.bind("<Key>", self._on_key_press)

        # Mouse events
        tw.bind("<Button-3>", self._on_context_menu)
        tw.bind("<B1-Motion>", self._on_mouse_drag)
        tw.bind("<Enter>", self._on_mouse_enter)
        tw.bind("<Leave>", self._on_mouse_leave)

    def _on_scrollbar(self, *args) -> None:
        """Handle scrollbar command.

        Args:
            *args: Scrollbar command arguments
        """
        self._text_widget.yview(*args)
        self._gutter.sync_scroll()

    def _on_mousewheel(self, event: tk.Event) -> None:
        """Handle mouse wheel scrolling.

        Args:
            event: The mouse wheel event
        """
        delta = -1 * (event.delta / 120)
        self._scroll_text(int(delta))

    def _scroll_text(self, direction: int) -> None:
        """Scroll text widget and synchronize gutter.

        Args:
            direction: Scroll direction (-1 up, 1 down)
        """
        self._text_widget.yview_scroll(direction, "units")
        self._gutter.sync_scroll()

    def _on_text_change(self, event: tk.Event = None) -> None:
        """Handle text changes with debounced gutter update.

        Args:
            event: Optional event that triggered the change
        """
        if hasattr(self, '_after_line_id'):
            try:
                self._main_frame.after_cancel(self._after_line_id)
            except Exception:
                pass
        self._after_line_id = self._main_frame.after(50, self._gutter.redraw)

    def _on_modified(self, event: tk.Event = None) -> None:
        """Handle <<Modified>> virtual event.

        Args:
            event: Optional event
        """
        self._is_dirty = True
        self._text_widget.edit_modified(False)
        if self._on_text_modified:
            self._on_text_modified()

    def _on_cursor_move(self, event: tk.Event = None) -> None:
        """Handle cursor movement for bracket matching.

        Args:
            event: Optional cursor event
        """
        self._highlight_brackets()
        if self._on_cursor_moved:
            self._on_cursor_moved()

    def _on_key_press(self, event: tk.Event) -> Optional[str]:
        """Handle key press events for completion.

        Args:
            event: The keyboard event

        Returns:
            Optional[str]: 'break' if handled
        """
        if self._completion_enabled and self._should_show_completion():
            return self._handle_completion_key(event)
        return None

    def _on_ctrl_s(self, event: tk.Event) -> str:
        """Handle Ctrl+S save shortcut.

        Args:
            event: The keyboard event

        Returns:
            str: 'break' to prevent default handling
        """
        if self._current_file:
            try:
                content = self.get_content()
                with open(self._current_file, "w", encoding="utf-8") as f:
                    f.write(content)
                self._is_dirty = False
                self._last_saved_content = content
                self._text_widget.edit_modified(False)
            except Exception:
                pass
        return "break"

    def _on_ctrl_z(self, event: tk.Event) -> str:
        """Handle Ctrl+Z undo shortcut.

        Args:
            event: The keyboard event

        Returns:
            str: 'break' to prevent default handling
        """
        try:
            self._text_widget.edit_undo()
        except Exception:
            pass
        return "break"

    def _on_ctrl_y(self, event: tk.Event) -> str:
        """Handle Ctrl+Y redo shortcut.

        Args:
            event: The keyboard event

        Returns:
            str: 'break' to prevent default handling
        """
        try:
            self._text_widget.edit_redo()
        except Exception:
            pass
        return "break"

    def _on_ctrl_shift_z(self, event: tk.Event) -> str:
        """Handle Ctrl+Shift+Z redo shortcut.

        Args:
            event: The keyboard event

        Returns:
            str: 'break' to prevent default handling
        """
        try:
            self._text_widget.edit_redo()
        except Exception:
            pass
        return "break"

    def _on_tab(self, event: tk.Event) -> str:
        """Handle Tab key for indentation.

        Args:
            event: The keyboard event

        Returns:
            str: 'break' to prevent default handling
        """
        if self._text_widget.tag_ranges("sel"):
            self._indent_selection(1)
        else:
            self._text_widget.insert("insert", " " * self._tab_size)
        return "break"

    def _on_shift_tab(self, event: tk.Event) -> str:
        """Handle Shift+Tab for un-indentation.

        Args:
            event: The keyboard event

        Returns:
            str: 'break' to prevent default handling
        """
        if self._text_widget.tag_ranges("sel"):
            self._indent_selection(-1)
        return "break"

    def _indent_selection(self, direction: int) -> None:
        """Indent or un-indent the current text selection.

        Args:
            direction: 1 for indent, -1 for un-indent
        """
        start = self._text_widget.index("sel.first")
        end = self._text_widget.index("sel.last")
        start_line = int(start.split('.')[0])
        end_line = int(end.split('.')[0])
        if end.split('.')[1] == '0' and end_line > start_line:
            end_line -= 1
        for line in range(start_line, end_line + 1):
            line_start = f"{line}.0"
            line_text = self._text_widget.get(line_start, f"{line}.end")
            leading = len(line_text) - len(line_text.lstrip(' '))
            if direction == 1:
                self._text_widget.insert(line_start, " " * self._tab_size)
            else:
                remove = min(leading, self._tab_size)
                if remove > 0:
                    self._text_widget.delete(line_start, f"{line_start}+{remove}c")
        self._refresh_highlight()

    def _on_fold_click(self, line_num: int) -> None:
        """Handle fold indicator click.

        Args:
            line_num: Line number to toggle fold at
        """
        if line_num in self._folded_lines:
            end_line = self._folded_lines.pop(line_num)
            self._show_lines(line_num + 1, end_line)
        elif line_num in self._fold_regions:
            for start, end in self._fold_regions:
                if start == line_num:
                    self._folded_lines[line_num] = end
                    self._hide_lines(line_num + 1, end)
                    break
        self._gutter.set_folded_lines(self._folded_lines)

    def _on_line_click(self, line_num: int) -> None:
        """Handle line number click (jump to line).

        Args:
            line_num: Target line number
        """
        self._text_widget.see(f"{line_num}.0")
        self._text_widget.tag_remove("sel", "1.0", "end")
        self._text_widget.mark_set("insert", f"{line_num}.0")
        self._text_widget.focus_set()

    def _hide_lines(self, start: int, end: int) -> None:
        """Hide (elide) lines in the text widget.

        Args:
            start: Start line (1-indexed)
            end: End line (1-indexed)
        """
        for line in range(start, end + 1):
            self._text_widget.tag_add("folded", f"{line}.0", f"{line}.end+1c")

    def _show_lines(self, start: int, end: int) -> None:
        """Show (un-elide) lines in the text widget.

        Args:
            start: Start line (1-indexed)
            end: End line (1-indexed)
        """
        for line in range(start, end + 1):
            self._text_widget.tag_remove("folded", f"{line}.0", f"{line}.end+1c")

    def _highlight_brackets(self) -> None:
        """Highlight matching brackets at the cursor position."""
        cursor = self._text_widget.index("insert")
        char = self._text_widget.get(cursor, f"{cursor}+1c")
        pairs = {'(': ')', '[': ']', '{': '}'}

        self._text_widget.tag_delete("bracket_match")

        if char in pairs:
            open_ch, close_ch = char, pairs[char]
            match_pos = self._find_matching_bracket(open_ch, close_ch)
            if match_pos:
                self._text_widget.tag_add("bracket_match", cursor, f"{cursor}+1c")
                self._text_widget.tag_add("bracket_match", match_pos, f"{match_pos}+1c")

    def _find_matching_bracket(self, open_ch: str, close_ch: str) -> Optional[str]:
        """Find matching bracket character.

        Args:
            open_ch: Opening bracket character
            close_ch: Closing bracket character

        Returns:
            Index of matching bracket, or None
        """
        cursor = self._text_widget.index("insert")
        before = self._text_widget.get("1.0", cursor)
        full = self._text_widget.get("1.0", "end-1c")
        offset = len(before)
        stack: List[int] = []

        for i, ch in enumerate(full):
            if ch == open_ch:
                stack.append(i)
            elif ch == close_ch:
                if stack:
                    if i == offset:
                        return self._text_widget.index(f"1.0+{stack[-1]}c")
                    popped = stack.pop()
                    if i == offset:
                        return self._text_widget.index(f"1.0+{popped}c")
        return None

    def _refresh_highlight(self) -> None:
        """Reapply syntax highlighting to the entire document."""
        self._text_widget.tag_delete("folded", "1.0", "end")
        self._apply_highlight_tags()
        for start, end in self._folded_lines.items():
            self._hide_lines(start + 1, end)

    def _apply_highlight_tags(self) -> None:
        """Apply syntax highlighting tags based on loaded language groups."""
        if not self._highlight_groups:
            return

        self._clear_highlight_tags()

        content = self.get_content()
        if not content.strip():
            return

        for g in self._highlight_groups:
            tag_name = f"kw_{g.get('name', '')}"
            color = g.get("color", "#abb2bf")
            self._text_widget.tag_config(tag_name, foreground=color)

        for group in self._highlight_groups:
            words = group.get("words", [])
            if not words:
                continue
            tag_name = f"kw_{group.get('name', '')}"
            for word in words:
                self._highlight_word(word, tag_name)

    def _clear_highlight_tags(self) -> None:
        """Remove all syntax highlighting tags."""
        for tag in self._text_widget.tag_names():
            if tag.startswith("kw_") or tag in (
                "comment", "string", "number", "function", "classname",
                "bracket_match", "folded"
            ):
                self._text_widget.tag_delete(tag)

    def _highlight_word(self, word: str, tag: str) -> None:
        """Highlight all occurrences of a word.

        Args:
            word: Word to highlight
            tag: Tag to apply
        """
        start = "1.0"
        while True:
            pos = self._text_widget.search(word, start, stopindex="end", exact=True)
            if not pos:
                break
            end = f"{pos}+{len(word)}c"
            self._text_widget.tag_add(tag, pos, end)
            start = end

    def _should_show_completion(self) -> bool:
        """Check if completion should be shown.

        Returns:
            bool: True if completion popup should be shown
        """
        return self._completion_enabled and self._current_file is not None

    def _handle_completion_key(self, event: tk.Event) -> Optional[str]:
        """Handle key press for completion navigation.

        Args:
            event: The keyboard event

        Returns:
            Optional[str]: 'break' if key was consumed
        """
        # Navigation handled by completion system
        return None

    def _on_context_menu(self, event: tk.Event) -> None:
        """Show context menu on right-click.

        Args:
            event: The mouse event
        """
        pass

    def _on_mouse_drag(self, event: tk.Event) -> None:
        """Handle mouse drag events.

        Args:
            event: The mouse event
        """
        pass

    def _on_mouse_enter(self, event: tk.Event) -> None:
        """Handle mouse enter/hover events.

        Args:
            event: The mouse event
        """
        pass

    def _on_mouse_leave(self, event: tk.Event) -> None:
        """Handle mouse leave events.

        Args:
            event: The mouse event
        """
        pass

    # ---- Public API ----

    def get_content(self) -> str:
        """Get the current editor content.

        Returns:
            Text content of the editor
        """
        if self._text_widget:
            return self._text_widget.get("1.0", "end-1c")
        return ""

    def set_content(self, content: str) -> None:
        """Set the editor content.

        Args:
            content: Text content to set
        """
        if self._text_widget:
            self._text_widget.delete("1.0", "end")
            self._text_widget.insert("1.0", content)
            self._last_saved_content = content
            self._is_dirty = False
            self._text_widget.edit_modified(False)
            self._refresh_highlight()

    def clear(self) -> None:
        """Clear the editor content and reset state."""
        if self._text_widget:
            self._text_widget.delete("1.0", "end")
            self._current_file = None
            self._is_dirty = False
            self._last_saved_content = ""
            self._folded_lines.clear()
            self._text_widget.edit_modified(False)
            self._gutter.redraw()

    def select_all(self) -> str:
        """Select all text in the editor.

        Returns:
            str: 'break' to prevent default handling
        """
        if self._text_widget:
            self._text_widget.tag_add("sel", "1.0", "end")
        return "break"

    def open_file(self, file_path: str) -> bool:
        """Open and load a file into the editor.

        Args:
            file_path: Path to the file to open

        Returns:
            bool: True if file was opened successfully
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self._current_file = file_path
            self.set_content(content)
            self._detect_language(file_path)
            return True
        except Exception:
            return False

    def save_file(self, file_path: Optional[str] = None) -> bool:
        """Save editor content to file.

        Args:
            file_path: Optional path to save to

        Returns:
            bool: True if save was successful
        """
        save_path = file_path or self._current_file
        if not save_path:
            return False
        try:
            content = self.get_content()
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(content)
            self._current_file = save_path
            self._is_dirty = False
            self._last_saved_content = content
            self._text_widget.edit_modified(False)
            return True
        except Exception:
            return False

    def _detect_language(self, file_path: str) -> None:
        """Detect and set language based on file extension.

        Args:
            file_path: Path to the file for language detection
        """
        ext = os.path.splitext(file_path)[1].lower()
        lang_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.html': 'html', '.css': 'css', '.json': 'json',
            '.md': 'markdown', '.c': 'c', '.cpp': 'cpp',
            '.java': 'java', '.go': 'go', '.rs': 'rust',
            '.rb': 'ruby', '.php': 'php', '.sql': 'sql',
            '.sh': 'shell', '.xml': 'xml', '.yaml': 'yaml',
        }
        self._language = lang_map.get(ext, 'text')
        self._load_language_config(self._language)

    def _load_language_config(self, language: str) -> None:
        """Load language configuration for syntax highlighting.

        Args:
            language: Language name
        """
        config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "assets", "languages")
        config_dir = os.path.normpath(config_dir)
        os.makedirs(config_dir, exist_ok=True)
        file_path = os.path.join(config_dir, f"{language}.json")

        if not os.path.exists(file_path):
            self._create_default_language_file(language, file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._highlight_groups = data.get("groups", [])
            self._completion_enabled = language in ('python', 'javascript', 'typescript')
        except (json.JSONDecodeError, IOError):
            self._highlight_groups = []

        self._refresh_highlight()

    def _create_default_language_file(self, language: str, path: str) -> None:
        """Create a default language configuration file.

        Args:
            language: Language name
            path: File path to write to
        """
        defaults = {
            "python": {
                "groups": [
                    {"name": "keyword", "color": "#c678dd", "words": [
                        "and","as","assert","async","await","break","class","continue",
                        "def","del","elif","else","except","finally","for","from",
                        "global","if","import","in","is","lambda","nonlocal","not",
                        "or","pass","raise","return","try","while","with","yield"
                    ]},
                    {"name": "builtin", "color": "#56b6c2", "words": [
                        "abs","all","any","bin","bool","bytearray","bytes","callable",
                        "chr","classmethod","compile","complex","delattr","dict","dir",
                        "divmod","enumerate","eval","exec","filter","float","format",
                        "frozenset","getattr","globals","hasattr","hash","help","hex",
                        "id","input","int","isinstance","issubclass","iter","len",
                        "list","locals","map","max","memoryview","min","next","object",
                        "oct","open","ord","pow","print","property","range","repr",
                        "reversed","round","set","setattr","slice","sorted",
                        "staticmethod","str","sum","super","tuple","type","vars","zip"
                    ]},
                    {"name": "constant", "color": "#56b6c2", "words": ["True","False","None","Ellipsis","__debug__"]},
                    {"name": "type", "color": "#e06c75", "words": [
                        "str","int","float","bool","list","dict","tuple","set","bytes",
                        "bytearray","memoryview","complex","range","slice","object","type"
                    ]}
                ]
            }
        }

        config = defaults.get(language, {"groups": []})
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except IOError:
            pass

    # ---- StyleProvider Implementation ----

    def apply_style(self, style_name: str) -> None:
        """Apply a named style to the editor.

        Args:
            style_name: Name of the style to apply
        """
        if self._style_system.apply_style(style_name) and self._loaded:
            self._load_style_values()
            self._apply_style_to_frame()
            self._gutter._load_style()
            self._gutter.redraw()

    def get_style_value(self, key: str, default: Any = None) -> Any:
        """Get a style value by key.

        Args:
            key: Style property key
            default: Default value

        Returns:
            The style value
        """
        return self._style_system.get_value("editor", key, default)

    def set_style_value(self, key: str, value: Any) -> None:
        """Set a single style property.

        Args:
            key: Style property key
            value: New value
        """
        self._style_system.set_style("editor", key, value)

    def _load_style_values(self) -> None:
        """Load style values into editor instance variables."""
        self._font_family = self._style_system.get_value("editor", "font_family", "Consolas")
        self._font_size = self._style_system.get_value("editor", "font_size", 12)

    # ---- BaseWidget Implementation ----

    def pack(self, **kwargs) -> None:
        """Pack the editor widget into its parent.

        Args:
            **kwargs: Pack configuration options
        """
        if self._main_frame:
            self._main_frame.pack(**kwargs)

    def grid(self, **kwargs) -> None:
        """Grid the editor widget into its parent.

        Args:
            **kwargs: Grid configuration options
        """
        if self._main_frame:
            self._main_frame.grid(**kwargs)

    def destroy(self) -> None:
        """Destroy the editor widget and free resources."""
        if self._main_frame and not self._destroyed:
            self._main_frame.destroy()
            self._destroyed = True

    # ---- LazyLoadable Implementation ----

    def load(self) -> None:
        """Load and initialize the editor on demand."""
        if not self._loaded:
            self.create_widget()

    def unload(self) -> None:
        """Unload and release editor resources."""
        if self._loaded:
            self.destroy()
            self._loaded = False

    @property
    def is_loaded(self) -> bool:
        """Check if the editor is currently loaded.

        Returns:
            bool: True if loaded
        """
        return self._loaded

    @property
    def is_dirty(self) -> bool:
        """Check if the editor has unsaved changes.

        Returns:
            bool: True if content is modified
        """
        return self._is_dirty

    @property
    def current_file(self) -> Optional[str]:
        """Get the path of the currently open file.

        Returns:
            File path or None
        """
        return self._current_file

    # ---- EventHandler Implementation ----

    def on_key_press(self, event: Any) -> Optional[str]:
        """Handle key press events.

        Args:
            event: The keyboard event

        Returns:
            Optional[str]: 'break' if consumed
        """
        return self._on_key_press(event)

    def on_mouse_click(self, event: Any) -> None:
        """Handle mouse click events.

        Args:
            event: The mouse event
        """
        self._on_cursor_move()

    def on_mouse_drag(self, event: Any) -> None:
        """Handle mouse drag events.

        Args:
            event: The mouse event
        """
        self._on_mouse_drag(event)

    def on_mouse_hover(self, event: Any) -> None:
        """Handle mouse hover events.

        Args:
            event: The mouse event
        """
        self._on_mouse_enter(event)

    # ---- Configuration ----

    def set_on_file_changed(self, callback: Callable[[str], None]) -> None:
        """Set callback for file changes.

        Args:
            callback: Function receiving file path
        """
        self._on_file_changed = callback

    def set_on_text_modified(self, callback: Callable[[], None]) -> None:
        """Set callback for text modification events.

        Args:
            callback: Function called when text is modified
        """
        self._on_text_modified = callback

    def set_on_cursor_moved(self, callback: Callable[[], None]) -> None:
        """Set callback for cursor movement events.

        Args:
            callback: Function called when cursor moves
        """
        self._on_cursor_moved = callback

    def get_widget(self) -> Optional[tk.Frame]:
        """Get the underlying Tkinter widget.

        Returns:
            The main frame widget
        """
        return self._main_frame

    def get_text_widget(self) -> Optional[tk.Text]:
        """Get the underlying text widget.

        Returns:
            The tk.Text widget
        """
        return self._text_widget

    def get_gutter(self) -> Optional[EditorGutter]:
        """Get the gutter component.

        Returns:
            The EditorGutter instance
        """
        return self._gutter