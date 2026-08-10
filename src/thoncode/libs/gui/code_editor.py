from tkinter import messagebox
import json
import os
import tkinter.font as tkfont
import tkinter as tk
from libs import font_loader
from libs.gui.lazy_loader import LazyLoader


class CodeEditor:
    def __init__(self, master, main_window=None, language="python", font_ligatures=True, tab_size=4, current_file=None):
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

        # Fold state is stored uniformly in self._folded_lines, EditorFolding no longer maintains an independent dictionary
        self.ui = None
        self.completion = None
        self.folding = None
        self.highlight = None
        self.shortcuts = None
        
        self._init_components()

        self.load_language(language)
        self.highlight_all()

    def _init_components(self):
        EditorUI = LazyLoader.get('libs.gui.editor_ui', 'EditorUI')
        self.ui = EditorUI(self)
        
        EditorCompletion = LazyLoader.get('libs.gui.editor_completion', 'EditorCompletion')
        self.completion = EditorCompletion(self.master)
        
        EditorFolding = LazyLoader.get('libs.gui.editor_folding', 'EditorFolding')
        self.folding = EditorFolding(self)
        
        EditorHighlight = LazyLoader.get('libs.gui.editor_highlight', 'EditorHighlight')
        self.highlight = EditorHighlight(self)
        
        EditorShortcuts = LazyLoader.get('libs.gui.editor_shortcuts', 'EditorShortcuts')
        self.shortcuts = EditorShortcuts(self)

    def _should_enable_completion(self, file_path):
        if not file_path:
            return False
        
        ext = os.path.splitext(file_path)[1].lower()
        completion_supported = {
            '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs', '.rb', '.php',
            '.c', '.cpp', '.h', '.hpp'
        }
        return ext in completion_supported
        
    def load_language(self, language):
        config_dir = "assets/languages"
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
        self.highlight_all()
        self.highlight_matching_bracket()

        self._update_line_numbers()
        if self.current_file:
            self._completion_enabled = self._should_enable_completion(self.current_file)
        if self.completion._after_completion_id:
            self.master.after_cancel(self.completion._after_completion_id)
        self.completion._after_completion_id = self.master.after(100, self._update_completion)
    
    def on_cursor_move(self, event):
        self.highlight_matching_bracket()

    def set_language(self, language):
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
        return self.ui.get_widget()

    def get_textbox(self):
        return self.ui.get_textbox()

    def _update_line_numbers(self, event=None):
        self.ui._update_line_numbers(event)

    def _on_text_change(self, event=None):
        self.ui._on_text_change(event)

    def _on_modified(self, event=None):
        self.ui._on_modified(event)

    def _on_scroll(self, event):
        return self.ui._on_scroll(event)

    def _on_line_scroll(self, event):
        return self.ui._on_line_scroll(event)

    def _on_line_number_click(self, event):
        self.ui._on_line_number_click(event)

    def _get_foldable_regions(self):
        return self.folding._get_foldable_regions()

    def _find_block_end(self, lines, start_line, min_indent):
        return self.folding._find_block_end(lines, start_line, min_indent)

    def toggle_fold(self, line_num):
        self.folding.toggle_fold(line_num)

    def highlight_all(self, event=None):
        """Reapply fold state after syntax highlighting

        highlight_all clears text tags, fold elide tags also need to be rebuilt,
        otherwise folded code will reappear.
        """
        self.highlight.highlight_all(event)
        if self.folding:
            self.folding.apply_all_folds()

    def _highlight_line(self, text_widget, line_num, line_text, in_multiline_comment):
        return self.highlight._highlight_line(text_widget, line_num, line_text, in_multiline_comment)

    def highlight_matching_bracket(self):
        self.highlight.highlight_matching_bracket()

    def find_matching_bracket(self, text_widget, start_idx, open_ch, close_ch):
        return self.highlight.find_matching_bracket(text_widget, start_idx, open_ch, close_ch)

    def _on_ctrl_s(self, event):
        return self.shortcuts._on_ctrl_s(event)

    def _on_ctrl_z(self, event):
        return self.shortcuts._on_ctrl_z(event)

    def _on_ctrl_y(self, event):
        return self.shortcuts._on_ctrl_y(event)

    def _on_ctrl_shift_z(self, event):
        return self.shortcuts._on_ctrl_shift_z(event)

    def on_tab(self, event):
        return self.shortcuts.on_tab(event)

    def on_shift_tab(self, event):
        return self.shortcuts.on_shift_tab(event)

    def _indent_selection(self, direction):
        self.shortcuts._indent_selection(direction)

    def select_all(self, event=None):
        return self.shortcuts.select_all(event)

    def _on_key_press(self, event):
        return self.completion.on_key_press(event)

    def _update_completion(self):
        self.completion._update_completion()

    def _show_completion(self, matches, word_start, prefix):
        self.completion._show_completion(matches, word_start, prefix)

    def _hide_completion(self, event=None):
        self.completion._hide_completion(event)

    def _select_completion(self, event=None):
        self.completion._select_completion(event)