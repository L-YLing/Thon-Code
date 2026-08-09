from tkinter import messagebox

import customtkinter as ctk
import json
import os
import tkinter.font as tkfont
import tkinter as tk
from libs import font_loader

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
        self._folded_lines = {}
        self._fold_markers = {}
        self.bracket_pairs = {'(': ')', '[': ']', '{': '}'}

        self.main_frame = ctk.CTkFrame(master, fg_color="transparent")
        
        self.font = ("Consolas", 12)
        if font_ligatures:
            try:
                from libs import font_loader
                loaded_font = font_loader.load_fira_code_font(master, 12, font_ligatures)
                font_name = loaded_font.actual('family')
                font_size = int(loaded_font.actual('size'))
                self.font = (font_name, font_size)
            except:
                self.font = ("Consolas", 12)
        else:
            self.font = ("Consolas", 12)

        self.line_numbers = ctk.CTkTextbox(
            self.main_frame,
            width=50,
            fg_color="#1e1e1e",
            text_color="#858585",
            font=self.font,
            wrap="none",
            state="disabled"
        )
        self.line_numbers.pack(side="left", fill="y", padx=(0, 0))
        
        self.textbox = ctk.CTkTextbox(self.main_frame, wrap="none", font=self.font)
        self._textbox = self.textbox._textbox

        self._tk_font = tk.font.Font(family=self.font[0], size=self.font[1])
        self._textbox.config(font=self._tk_font)
        self._textbox.tag_config("sel", background="#002346", foreground="white")
        self._textbox.config(undo=True, maxundo=100)
        self._textbox.edit_modified(False)
        self.textbox.pack(side="left", fill="both", expand=True)

        self._textbox.bind("<MouseWheel>", self._on_scroll)
        self._textbox.bind("<Button-4>", self._on_scroll)
        self._textbox.bind("<Button-5>", self._on_scroll)
        self._textbox.bind("<KeyRelease>", self._on_text_change)
        self._textbox.bind("<Configure>", self._update_line_numbers)
        self._textbox.bind("<<Modified>>", self._on_modified)

        self.line_numbers._textbox.bind("<Button-1>", self._on_line_number_click)
        
        self.line_numbers._textbox.bind("<MouseWheel>", self._on_line_scroll)
        self.line_numbers._textbox.bind("<Button-4>", self._on_line_scroll)
        self.line_numbers._textbox.bind("<Button-5>", self._on_line_scroll)

        self.completion_window = None
        self.completion_listbox = None
        self.completion_matches = []
        self.completion_prefix = ""
        self.completion_word_start = 0
        self._after_completion_id = None
        self._is_selecting = False
        self._init_completion_window()

        self._textbox.bind("<Control-s>", self._on_ctrl_s)
        self._textbox.bind("<Control-S>", self._on_ctrl_s)
        self._textbox.bind("<Control-z>", self._on_ctrl_z)
        self._textbox.bind("<Control-Z>", self._on_ctrl_z)
        self._textbox.bind("<Control-y>", self._on_ctrl_y)
        self._textbox.bind("<Control-Y>", self._on_ctrl_y)
        self._textbox.bind("<Control-Shift-Z>", self._on_ctrl_shift_z)
        self._textbox.bind("<Control-Shift-z>", self._on_ctrl_shift_z)

        self._textbox.bind("<Control-a>", self.select_all)
        self._textbox.bind("<Control-A>", self.select_all)
        self._textbox.bind("<KeyRelease>", self.on_key_release)
        self._textbox.bind("<FocusIn>", self.highlight_all)
        self._textbox.bind("<ButtonRelease-1>", self.on_cursor_move)
        self._textbox.bind("<KeyRelease-Left>", self.on_cursor_move)
        self._textbox.bind("<KeyRelease-Right>", self.on_cursor_move)
        self._textbox.bind("<Key>", self._on_key_press)
        self._textbox.bind("<Tab>", self.on_tab)
        self._textbox.bind("<Shift-Tab>", self.on_shift_tab)

        self.load_language(language)
        self.highlight_all()

    def _on_line_number_click(self, event):
        if self.language != "python":
            return
        
        index = self.line_numbers._textbox.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0])
        
        fold_regions = self._get_foldable_regions()
        foldable_starts = [start for start, _ in fold_regions]
        
        if line_num in foldable_starts:
            self.toggle_fold(line_num)
        elif line_num in self._folded_lines:
            self.toggle_fold(line_num)

    def _get_foldable_regions(self):
        if self.language != "python":
            return []
        
        content = self._textbox.get("1.0", "end-1c")
        lines = content.splitlines()
        fold_regions = []
        stack = []
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            if stripped.startswith('def ') or stripped.startswith('async def '):
                base_indent = len(line) - len(line.lstrip(' '))
                end_line = self._find_block_end(lines, i, base_indent + 4)
                if end_line > i:
                    fold_regions.append((i, end_line))
            
            elif stripped.startswith('class '):
                base_indent = len(line) - len(line.lstrip(' '))
                end_line = self._find_block_end(lines, i, base_indent + 4)
                if end_line > i:
                    fold_regions.append((i, end_line))
            
            elif any(ch in line for ch in '({['):
                pass
        
        return fold_regions

    def _on_line_scroll(self, event):
        try:
            if hasattr(event, 'num'):
                if event.num == 4:
                    self._textbox.yview_scroll(-1, "units")
                elif event.num == 5:
                    self._textbox.yview_scroll(1, "units")
            else:
                delta = -1 * (event.delta / 120)
                self._textbox.yview_scroll(int(delta), "units")
        except:
            pass
        self.line_numbers._textbox.yview_moveto(self._textbox.yview()[0])
        
        return "break"

    def _find_block_end(self, lines, start_line, min_indent):
        """查找代码块的结束行"""
        if start_line >= len(lines):
            return start_line
        
        # 从下一行开始查找
        for i in range(start_line, len(lines)):
            line = lines[i]
            if not line.strip():  # 空行跳过
                continue
            
            # 计算缩进
            indent = len(line) - len(line.lstrip(' '))
            
            # 如果缩进小于最小缩进，说明块结束
            if indent < min_indent:
                return i
        
        return len(lines)

    def toggle_fold(self, line_num):
        if line_num in self._folded_lines:
            end_line = self._folded_lines.pop(line_num)
            self._textbox.edit_modified(False)
            self._update_line_numbers()
            self.highlight_all()
        else:
            fold_regions = self._get_foldable_regions()
            for start, end in fold_regions:
                if start == line_num and end > start + 1:
                    self._folded_lines[start] = end
                    self._textbox.edit_modified(False)
                    self._update_line_numbers()
                    self.highlight_all()
                    break

    def _update_line_numbers(self, event=None):
        if not self._textbox:
            return
        
        try:
            line_count = int(self._textbox.index('end-1c').split('.')[0])
        except:
            line_count = 1
        
        lines = [str(i) for i in range(1, line_count + 1)]

        self.line_numbers._textbox.config(state="normal")
        self.line_numbers.delete("1.0", "end")
        self.line_numbers.insert("1.0", "\n".join(lines))
        self.line_numbers._textbox.config(state="disabled")

        self.line_numbers._textbox.yview_moveto(self._textbox.yview()[0])

    def _on_text_change(self, event=None):
        if hasattr(self, '_after_line_id'):
            self.master.after_cancel(self._after_line_id)
        self._after_line_id = self.master.after(50, self._update_line_numbers)

    def _on_modified(self, event=None):
        self._update_line_numbers()
        self._textbox.edit_modified(False)

    def _on_scroll(self, event):
        try:
            if hasattr(event, 'num'):
                if event.num == 4:
                    self._textbox.yview_scroll(-1, "units")
                elif event.num == 5:
                    self._textbox.yview_scroll(1, "units")
            else:
                delta = -1 * (event.delta / 120)
                self._textbox.yview_scroll(int(delta), "units")
        except:
            pass
        self.line_numbers._textbox.yview_moveto(self._textbox.yview()[0])
        
        return None

    def _should_enable_completion(self, file_path):
        if not file_path:
            return False
        
        ext = os.path.splitext(file_path)[1].lower()
        # 支持自动补全的扩展名
        completion_supported = {
            '.py', 
            '.js', 
            '.jsx', 
            '.ts', 
            '.tsx', 
            '.java', 
            '.go', 
            '.rs', 
            '.rb', 
            '.php',
            '.c', 
            '.cpp', 
            '.h', 
            '.hpp'
        }
        return ext in completion_supported

    def _on_ctrl_s(self, event):
        if not self.main_window:
            return "break"
        
        master = self.main_window
        if master.current_file:
            try:
                content = self._textbox.get("1.0", "end-1c")
                with open(master.current_file, "w", encoding="utf-8") as f:
                    f.write(content)
                master.is_dirty = False
                master.last_saved_content = content
                master.update_title()
                master.status_bar.configure(text=f"已保存: {master.current_file}")
                self._textbox.edit_modified(False)
                # 同步当前文件路径
                self.current_file = master.current_file
                self._completion_enabled = self._should_enable_completion(self.current_file)
                print(f"已保存: {master.current_file}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败：{e}")
        else:
            if hasattr(master, 'save_as'):
                master.save_as()
        return "break"

    def _on_ctrl_z(self, event):
        """Ctrl+Z 撤销"""
        print("Ctrl+Z 被捕获")
        try:
            self._textbox.edit_undo()
        except tk.TclError:
            pass
        return "break"

    def _on_ctrl_y(self, event):
        """Ctrl+Y 重做"""
        print("Ctrl+Y 被捕获")
        try:
            self._textbox.edit_redo()
        except tk.TclError:
            pass
        return "break"

    def _on_ctrl_shift_z(self, event):
        """Ctrl+Shift+Z 重做"""
        print("Ctrl+Shift+Z 被捕获")
        try:
            self._textbox.edit_redo()
        except tk.TclError:
            pass
        return "break"

    def get_widget(self):
        return self.main_frame

    def get_textbox(self):
        return self.textbox

    def _init_completion_window(self):
        self.completion_window = tk.Toplevel(self.master)
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
            font=("微软雅黑", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            takefocus=0
        )
        self.completion_listbox.pack(fill="both", expand=True, padx=1, pady=1)
        self.completion_listbox.bind("<ButtonRelease-1>", self._select_completion)
        self.completion_listbox.bind("<Double-Button-1>", self._select_completion)

    def _on_key_press(self, event):
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

    def on_tab(self, event):
        if self.completion_window and self.completion_window.winfo_ismapped():
            self._select_completion()
            return "break"
        text_widget = self._textbox
        if text_widget.tag_ranges("sel"):
            self._indent_selection(1)
            return "break"
        text_widget.insert("insert", " " * self.tab_size)
        return "break"

    def on_shift_tab(self, event):
        if self._textbox.tag_ranges("sel"):
            self._indent_selection(-1)
        return "break"

    def _indent_selection(self, direction):
        text_widget = self._textbox
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
                text_widget.insert(line_start, " " * self.tab_size)
            else:
                remove_count = min(leading_spaces, self.tab_size)
                if remove_count > 0:
                    text_widget.delete(line_start, f"{line_start}+{remove_count}c")
        self.highlight_all()

    def _update_completion(self):
        if self._is_selecting:
            return

        if not self._completion_enabled:
            self._hide_completion()
            return

        if not self._textbox.get("1.0", "end-1c").strip():
            self._hide_completion()
            return
            
        if not self.current_file or not self.current_file.endswith('.py'):
            self._hide_completion()
            return

        text_widget = self._textbox
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
        for group in self.groups:
            all_keywords.extend(group.get("words", []))
        matches = [kw for kw in all_keywords if kw.startswith(prefix)]
        if not matches:
            self._hide_completion()
            return

        matches = list(dict.fromkeys(matches))[:30]
        self._show_completion(matches, word_start, prefix)

    def _show_completion(self, matches, word_start, prefix):
        self.completion_listbox.delete(0, tk.END)
        for m in matches:
            self.completion_listbox.insert(tk.END, m)
        self.completion_matches = matches
        self.completion_prefix = prefix
        self.completion_word_start = word_start
        self._is_selecting = False

        bbox = self._textbox.bbox("insert")
        if bbox:
            x, y, width, height = bbox
            x += self._textbox.winfo_rootx()
            y += self._textbox.winfo_rooty() + height
            list_height = min(len(matches), 10) * 22 + 4
            self.completion_window.geometry(f"220x{list_height}+{x}+{y}")
            self.completion_window.deiconify()
            self.completion_listbox.selection_clear(0, tk.END)
            self.completion_listbox.selection_set(0)
            self.completion_listbox.see(0)
        else:
            self.completion_window.deiconify()

    def _hide_completion(self, event=None):
        self._is_selecting = False
        if self.completion_window:
            self.completion_window.withdraw()
            self.completion_listbox.delete(0, tk.END)
            self.completion_matches = []
            self.completion_prefix = ""
            self.completion_listbox.selection_clear(0, tk.END)

    def _select_completion(self, event=None):
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

        text_widget = self._textbox
        cursor = text_widget.index("insert")
        line, col = map(int, cursor.split('.'))
        start_idx = f"{line}.{col - len(self.completion_prefix)}"
        text_widget.delete(start_idx, cursor)
        text_widget.insert(start_idx, selected_text)
        self._hide_completion()
        self.highlight_all()

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
        self._fold_markers.clear()

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
        if self._after_completion_id:
            self.master.after_cancel(self._after_completion_id)
        self._after_completion_id = self.master.after(100, self._update_completion)
    
    def on_cursor_move(self, event):
        self.highlight_matching_bracket()

    def highlight_all(self, event=None):
        text_widget = self._textbox
        content = text_widget.get("1.0", "end-1c")
        if not content.strip():
            for tag in text_widget.tag_names():
                if tag.startswith("kw_") or tag in ("comment","string","number","function","classname"):
                    text_widget.tag_delete(tag)
            return

        for g in self.groups:
            text_widget.tag_config(f"kw_{g['name']}", foreground=g["color"])
        text_widget.tag_config("comment", foreground="#5C6370")
        text_widget.tag_config("string", foreground="#98C379")
        text_widget.tag_config("number", foreground="#D19A66")
        text_widget.tag_config("function", foreground="#61AFEF")
        text_widget.tag_config("classname", foreground="#E5C07B")

        lines = content.splitlines(keepends=True)
        line_num = 1
        in_multiline_comment = False
        for line in lines:
            in_multiline_comment = self._highlight_line(text_widget, line_num, line, in_multiline_comment)
            line_num += 1

    def _highlight_line(self, text_widget, line_num, line_text, in_multiline_comment):
        n = len(line_text)
        i = 0
        in_string = False
        string_char = None
        in_comment = False

        if in_multiline_comment:
            end_idx = line_text.find('"""')
            if end_idx == -1:
                text_widget.tag_add("comment", f"{line_num}.0", f"{line_num}.end")
                return True
            else:
                text_widget.tag_add("comment", f"{line_num}.0", f"{line_num}.{end_idx+3}")
                i = end_idx + 3
                in_multiline_comment = False

        while i < n:
            ch = line_text[i]

            if not in_string and not in_comment and line_text[i:i+3] == '"""':
                start_comment = i
                end_comment = line_text.find('"""', i+3)
                if end_comment == -1:
                    text_widget.tag_add("comment", f"{line_num}.{start_comment}", f"{line_num}.end")
                    return True
                else:
                    text_widget.tag_add("comment", f"{line_num}.{start_comment}", f"{line_num}.{end_comment+3}")
                    i = end_comment + 3
                    continue

            if not in_comment and ch in ('"', "'"):
                if not in_string:
                    in_string = True
                    string_char = ch
                    start_str = i
                    i += 1
                    continue
                elif ch == string_char:
                    if i > 0 and line_text[i-1] == '\\':
                        i += 1
                        continue
                    else:
                        text_widget.tag_add("string", f"{line_num}.{start_str}", f"{line_num}.{i+1}")
                        in_string = False
                        i += 1
                        continue

            if not in_string and not in_comment and ch == '#':
                in_comment = True
                start_comment = i
                i += 1
                continue

            if in_string:
                i += 1
                continue
            if in_comment:
                text_widget.tag_add("comment", f"{line_num}.{start_comment}", f"{line_num}.end")
                break

            if ch.isdigit() or (ch == '.' and i+1 < n and line_text[i+1].isdigit()):
                start = i
                while i < n and (line_text[i].isdigit() or line_text[i] == '.'):
                    i += 1
                text_widget.tag_add("number", f"{line_num}.{start}", f"{line_num}.{i}")
                continue

            if ch.isalnum() or ch == '_':
                start = i
                while i < n and (line_text[i].isalnum() or line_text[i] == '_'):
                    i += 1
                word = line_text[start:i]
                matched = False
                for g in self.groups:
                    if word in g["words"]:
                        text_widget.tag_add(f"kw_{g['name']}", f"{line_num}.{start}", f"{line_num}.{i}")
                        matched = True
                        break
                if not matched:
                    j = i
                    while j < n and line_text[j].isspace():
                        j += 1
                    if j < n and line_text[j] == '(':
                        text_widget.tag_add("function", f"{line_num}.{start}", f"{line_num}.{i}")
                    prev_word = line_text[:start].strip().split()[-1] if line_text[:start].strip() else ""
                    if prev_word == "class":
                        text_widget.tag_add("classname", f"{line_num}.{start}", f"{line_num}.{i}")
                continue
            else:
                i += 1
        return False

    # 括号匹配
    def highlight_matching_bracket(self):
        text_widget = self._textbox
        try:
            text_widget.tag_delete("bracket_match")
        except:
            pass
        cursor_index = text_widget.index("insert")
        char = text_widget.get(cursor_index, f"{cursor_index}+1c")
        if char in self.bracket_pairs:
            open_char = char
            close_char = self.bracket_pairs[open_char]
            match_pos = self.find_matching_bracket(text_widget, cursor_index, open_char, close_char)
            if match_pos:
                text_widget.tag_add("bracket_match", cursor_index, f"{cursor_index}+1c")
                text_widget.tag_add("bracket_match", match_pos, f"{match_pos}+1c")
                text_widget.tag_config("bracket_match", background="#FFFF00")

    def find_matching_bracket(self, text_widget, start_idx, open_ch, close_ch):
        before = text_widget.get("1.0", start_idx)
        full_text = text_widget.get("1.0", "end-1c")
        offset = len(before)
        stack = []
        for i, ch in enumerate(full_text):
            if ch == open_ch:
                stack.append(i)
            elif ch == close_ch:
                if stack:
                    if i == offset:
                        return text_widget.index(f"1.0+{stack[-1]}c")
                    popped = stack.pop()
                    if i == offset:
                        return text_widget.index(f"1.0+{popped}c")
        return None

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

    def select_all(self, event=None):
        self._hide_completion()
        self._textbox.tag_add("sel", "1.0", "end")
        return "break"