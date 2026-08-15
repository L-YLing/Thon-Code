#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Editor",
    "Path": ".main.libs.gui.code_editor",
    "Entrance": "main.py"
}

from tkinter import messagebox
import json
import os
import tkinter.font as tkfont
import tkinter as tk
from libs import font_loader
from libs.gui.lazy_loader import LazyLoader


class CodeEditor:
    """Main code editor component with syntax highlighting and auto-completion.

    Delegates to specialized sub-components for UI rendering, completion,
    folding, highlighting, and keyboard shortcuts.
    """

    def __init__(self, master, main_window=None, language="python", font_ligatures=True, tab_size=4, current_file=None):
        """Initialize the code editor.

        Args:
            master: Parent widget for the editor
            main_window: Reference to the main window
            language: Programming language for syntax highlighting
            font_ligatures: Enable font ligatures in the editor
            tab_size: Number of spaces per indentation level
            current_file: Path to the currently open file
        """
        self.master = master
        self.language = language
        self.tab_size = tab_size
        self.main_window = main_window
        self.current_file = current_file
        self._completion_enabled = self._should_enable_completion(current_file)
        self.groups = []
        self._bracket_tag = None
        self._saving = False
        self.font_ligatures = font_ligatures
        self._folded_lines = {}
        self._fold_markers = {}

        # Fold state stored uniformly in self._folded_lines
        self.ui = None
        self.completion = None
        self.folding = None
        self.highlight = None
        self.shortcuts = None
        self.navigation = None
        # Alias used by navigation / completion modules that inspect the
        # text widget. `self._textbox` continues to be the authoritative
        # handle inside CodeEditor itself.
        self.text = getattr(self, "_textbox", None)

        self._init_components()
        # Re-alias after _init_components because _textbox is created lazily
        self.text = getattr(self, "_textbox", None)

        self.load_language(language)
        self.highlight_all()

    def _init_components(self):
        """Initialize sub-components using lazy loading."""
        EditorUI = LazyLoader.get('libs.gui.editor_ui', 'EditorUI')
        self.ui = EditorUI(self)

        EditorCompletion = LazyLoader.get('libs.gui.editor_completion', 'EditorCompletion')
        self.completion = EditorCompletion(self, self.master)

        EditorFolding = LazyLoader.get('libs.gui.editor_folding', 'EditorFolding')
        self.folding = EditorFolding(self)

        EditorHighlight = LazyLoader.get('libs.gui.editor_highlight', 'EditorHighlight')
        self.highlight = EditorHighlight(self)

        EditorShortcuts = LazyLoader.get('libs.gui.editor_shortcuts', 'EditorShortcuts')
        self.shortcuts = EditorShortcuts(self)

        # Ctrl+right-click navigation / go-to-definition
        try:
            EditorNavigation = LazyLoader.get('libs.gui.editor_navigation', 'EditorNavigation')
            self.navigation = EditorNavigation(
                self,
                goto_callback=self._default_goto_callback,
            )
        except Exception:
            # Navigation is a convenience feature; if it fails to load
            # (e.g. missing i18n module in early boot) the editor still
            # functions normally.
            self.navigation = None

    def _default_goto_callback(self, target_file: str, target_line):
        """Default callback when navigation jumps to another file.

        Delegates to the main_window open_file(..., jump_to_line=...) method
        if present; otherwise does nothing. The navigation module shows a
        user-visible message when the delegate is unavailable.
        """
        mw = self.main_window
        if mw is not None and hasattr(mw, "open_file"):
            try:
                mw.open_file(target_file, jump_to_line=target_line)
            except Exception:
                pass

    def _should_enable_completion(self, file_path):
        """Check if code completion should be enabled for the file type.

        Args:
            file_path: Path to the file to check

        Returns:
            bool: True if completion is supported for this file type
        """
        if not file_path:
            return False
        
        ext = os.path.splitext(file_path)[1].lower()
        completion_supported = {
            '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs', '.rb', '.php',
            '.c', '.cpp', '.h', '.hpp'
        }
        return ext in completion_supported
        
    def load_language(self, language):
        """Load language configuration for syntax highlighting.

        Resolves the language config directory relative to this module so the
        editor works regardless of the current working directory (important
        for packaged builds).

        Args:
            language: Language name (e.g., 'python', 'javascript')
        """
        # Resolve assets/languages relative to this file (src/thoncode/assets/languages).
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_dir = os.path.join(base_dir, "assets", "languages")
        os.makedirs(config_dir, exist_ok=True)
        file_path = os.path.join(config_dir, f"{language}.json")
        if not os.path.exists(file_path):
            self._create_default_language_file(language, file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.groups = data.get("groups", [])
        for g in self.groups:
            self._textbox.tag_config(f"kw_{g['name']}", foreground=g["color"])
        self._textbox.tag_config("comment", foreground="#5C6370")
        self._textbox.tag_config("string", foreground="#98C379")
        self._textbox.tag_config("number", foreground="#D19A66")
        self._textbox.tag_config("function", foreground="#61AFEF")
        self._textbox.tag_config("classname", foreground="#E5C07B")
        self._textbox.tag_config("bracket_match", background="#FFFF00")

        self._folded_lines.clear()

    def _create_default_language_file(self, language, path):
        """Create a default language configuration file.

        Args:
            language: Language name
            path: File path to write the default config to
        """
        if language == "python":
            default = {
                "groups": [
                    {"name": "keyword", "color": "#C678DD", "words": ["and","as","assert","async","await","break","class","continue","def","del","elif","else","except","finally","for","from","global","if","import","in","is","lambda","nonlocal","not","or","pass","raise","return","try","while","with","yield"]},
                    {"name": "builtin", "color": "#61AFEF", "words": ["abs","all","any","bin","bool","bytearray","bytes","callable","chr","classmethod","compile","complex","delattr","dict","dir","divmod","enumerate","eval","exec","filter","float","format","frozenset","getattr","globals","hasattr","hash","help","hex","id","input","int","isinstance","issubclass","iter","len","list","locals","map","max","memoryview","min","next","object","oct","open","ord","pow","print","property","range","repr","reversed","round","set","setattr","slice","sorted","staticmethod","str","sum","super","tuple","type","vars","zip"]},
                    {"name": "constant", "color": "#E5C07B", "words": ["True","False","None","Ellipsis","__debug__"]},
                    {"name": "type", "color": "#98C379", "words": ["str","int","float","bool","list","dict","tuple","set","bytes","bytearray","memoryview","complex","range","slice","object","type"]}
                ]
            }
        else:
            default = {"groups": []}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4, ensure_ascii=False)

    def on_key_release(self, event=None):
        """Handle key release event for highlighting and completion.

        Uses debounced highlight scheduling so rapid keystrokes merge into a
        single highlight pass, keeping typing responsive on large files.

        Args:
            event: The key release event
        """
        # Debounced highlighting (auto-selects viewport vs full by file size).
        self.highlight.schedule_highlight()
        self.highlight_matching_bracket()

        self._update_line_numbers()
        if self.current_file:
            self._completion_enabled = self._should_enable_completion(self.current_file)
        if self.completion._after_completion_id:
            self.master.after_cancel(self.completion._after_completion_id)
        self.completion._after_completion_id = self.master.after(100, self._update_completion)
    
    def on_cursor_move(self, event):
        """Handle cursor movement for bracket matching.

        Args:
            event: The cursor movement event
        """
        self.highlight_matching_bracket()

    def set_language(self, language):
        """Switch the editor's programming language.

        Args:
            language: New language to set
        """
        if self.language != language:
            self.language = language
            self.current_file = None
            for tag in self._textbox.tag_names():
                if tag.startswith("kw_") or tag in ("comment","string","number","function","classname","bracket_match"):
                    self._textbox.tag_delete(tag)
            self.load_language(language)
            self.highlight_all()
            self._update_line_numbers()
        
        self._completion_enabled = self._should_enable_completion(self.current_file)
        if not self._completion_enabled:
            self._hide_completion()

    def get_widget(self):
        """Get the editor's main frame widget.

        Returns:
            The editor frame widget
        """
        return self.ui.get_widget()

    def get_textbox(self):
        """Get the editor's textbox widget.

        Returns:
            The textbox widget
        """
        return self.ui.get_textbox()

    def _update_line_numbers(self, event=None):
        """Update the line number display.

        Args:
            event: Optional event that triggered the update
        """
        self.ui._update_line_numbers(event)

    def _on_text_change(self, event=None):
        """Handle text change events.

        Args:
            event: Optional text change event
        """
        self.ui._on_text_change(event)

    def _on_modified(self, event=None):
        """Handle text modification events.

        Args:
            event: Optional modification event
        """
        self.ui._on_modified(event)

    def _on_scroll(self, event):
        """Handle scroll events.

        Args:
            event: The scroll event
        """
        return self.ui._on_scroll(event)

    def _on_line_scroll(self, event):
        """Handle line number area scroll events.

        Args:
            event: The line scroll event
        """
        return self.ui._on_line_scroll(event)

    def _on_line_number_click(self, event):
        """Handle clicks on the line number area.

        Args:
            event: The click event
        """
        self.ui._on_line_number_click(event)

    def _get_foldable_regions(self):
        """Get all foldable code regions.

        Returns:
            List of foldable regions
        """
        return self.folding._get_foldable_regions()

    def _find_block_end(self, lines, start_line, min_indent):
        """Find the end of a code block for folding.

        Args:
            lines: List of code lines
            start_line: Starting line index
            min_indent: Minimum indentation level

        Returns:
            The end line index of the block
        """
        return self.folding._find_block_end(lines, start_line, min_indent)

    def toggle_fold(self, line_num):
        """Toggle code folding at the specified line.

        Args:
            line_num: Line number to toggle fold at
        """
        self.folding.toggle_fold(line_num)

    def highlight_all(self, event=None):
        """Reapply syntax highlighting and fold state.

        Automatically selects viewport highlighting for large files and full
        highlighting for small files, so explicit refresh requests stay fast
        regardless of document size.

        Args:
            event: Optional event that triggered highlighting
        """
        try:
            total_lines = int(self._textbox.index('end-1c').split('.')[0])
        except Exception:
            total_lines = 1
        if total_lines >= self.highlight.LARGE_FILE_THRESHOLD:
            self.highlight.highlight_visible()
        else:
            self.highlight.highlight_all(event)
        if self.folding:
            self.folding.apply_all_folds()

    def highlight_visible(self):
        """Reapply syntax highlighting to the visible viewport only.

        Used for large files where full-document highlighting would be too slow.
        """
        self.highlight.highlight_visible()
        if self.folding:
            self.folding.apply_all_folds()

    def _highlight_line(self, text_widget, line_num, line_text, in_multiline_comment):
        """Highlight a single line of code.

        Args:
            text_widget: The text widget to highlight
            line_num: Line number to highlight
            line_text: Text content of the line
            in_multiline_comment: Whether the line is in a multi-line comment

        Returns:
            List of highlight ranges
        """
        return self.highlight._highlight_line(text_widget, line_num, line_text, in_multiline_comment)

    def highlight_matching_bracket(self):
        """Highlight matching brackets at the cursor position."""
        self.highlight.highlight_matching_bracket()

    def find_matching_bracket(self, text_widget, start_idx, open_ch, close_ch):
        """Find a matching bracket character.

        Args:
            text_widget: The text widget to search in
            start_idx: Starting index for the search
            open_ch: Opening bracket character
            close_ch: Closing bracket character

        Returns:
            Index of the matching bracket, or None if not found
        """
        return self.highlight.find_matching_bracket(text_widget, start_idx, open_ch, close_ch)

    def _on_ctrl_s(self, event):
        """Handle Ctrl+S (save) keyboard shortcut.

        Args:
            event: The keyboard event

        Returns:
            "break" to prevent default handling
        """
        return self.shortcuts._on_ctrl_s(event)

    def _on_ctrl_z(self, event):
        """Handle Ctrl+Z (undo) keyboard shortcut.

        Args:
            event: The keyboard event

        Returns:
            "break" to prevent default handling
        """
        return self.shortcuts._on_ctrl_z(event)

    def _on_ctrl_y(self, event):
        """Handle Ctrl+Y (redo) keyboard shortcut.

        Args:
            event: The keyboard event

        Returns:
            "break" to prevent default handling
        """
        return self.shortcuts._on_ctrl_y(event)

    def _on_ctrl_shift_z(self, event):
        """Handle Ctrl+Shift+Z (redo) keyboard shortcut.

        Args:
            event: The keyboard event

        Returns:
            "break" to prevent default handling
        """
        return self.shortcuts._on_ctrl_shift_z(event)

    def on_tab(self, event):
        """Handle Tab key for indentation.

        Args:
            event: The keyboard event

        Returns:
            "break" to prevent default handling
        """
        return self.shortcuts.on_tab(event)

    def on_shift_tab(self, event):
        """Handle Shift+Tab for un-indentation.

        Args:
            event: The keyboard event

        Returns:
            "break" to prevent default handling
        """
        return self.shortcuts.on_shift_tab(event)

    def _indent_selection(self, direction):
        """Indent or un-indent the current selection.

        Args:
            direction: 1 for indent, -1 for un-indent
        """
        self.shortcuts._indent_selection(direction)

    def select_all(self, event=None):
        """Select all text in the editor.

        Args:
            event: Optional keyboard event

        Returns:
            "break" to prevent default handling
        """
        return self.shortcuts.select_all(event)

    def _on_key_press(self, event):
        """Handle key press events for completion.

        Args:
            event: The keyboard event

        Returns:
            Result from completion handler
        """
        return self.completion.on_key_press(event)

    def _update_completion(self):
        """Trigger auto-completion update."""
        self.completion._update_completion()

    def _show_completion(self, matches, word_start, prefix):
        """Show the auto-completion popup.

        Args:
            matches: List of completion matches
            word_start: Start position of the word being completed
            prefix: Current prefix text for filtering
        """
        self.completion._show_completion(matches, word_start, prefix)

    def _hide_completion(self, event=None):
        """Hide the auto-completion popup.

        Args:
            event: Optional event that triggered hiding
        """
        self.completion._hide_completion(event)

    def _select_completion(self, event=None):
        """Select the current auto-completion suggestion.

        Args:
            event: Optional event that triggered selection
        """
        self.completion._select_completion(event)