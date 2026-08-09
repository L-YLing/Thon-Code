import customtkinter as ctk
import tkinter as tk
import tkinter.font as tkfont


class LazyLoader:
    """Universal lazy loader for GUI components and heavy libraries"""
    _instances = {}
    
    @classmethod
    def get(cls, module_path, class_name=None):
        cache_key = f"{module_path}:{class_name}" if class_name else module_path
        if cache_key in cls._instances:
            return cls._instances[cache_key]
        
        module = __import__(module_path, fromlist=[class_name] if class_name else [])
        if class_name:
            result = getattr(module, class_name)
        else:
            result = module
        cls._instances[cache_key] = result
        return result


class EditorUI:
    def __init__(self, parent):
        self.parent = parent
        self.main_frame = ctk.CTkFrame(parent.master, fg_color="transparent")
        
        self.font = ("Consolas", 12)
        if parent.font_ligatures:
            try:
                font_loader = LazyLoader.get('libs', 'font_loader')
                loaded_font = font_loader.load_fira_code_font(parent.master, 12, parent.font_ligatures)
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
        parent._textbox = self.textbox._textbox
        parent._textbox_widget = self.textbox

        self._tk_font = tk.font.Font(family=self.font[0], size=self.font[1])
        parent._textbox.config(font=self._tk_font)
        parent._textbox.tag_config("sel", background="#002346", foreground="white")
        parent._textbox.config(undo=True, maxundo=100)
        parent._textbox.edit_modified(False)
        self.textbox.pack(side="left", fill="both", expand=True)

        self._setup_bindings()

    def _setup_bindings(self):
        parent = self.parent
        parent._textbox.bind("<MouseWheel>", parent._on_scroll)
        parent._textbox.bind("<Button-4>", parent._on_scroll)
        parent._textbox.bind("<Button-5>", parent._on_scroll)
        parent._textbox.bind("<KeyRelease>", parent._on_text_change)
        parent._textbox.bind("<Configure>", parent._update_line_numbers)
        parent._textbox.bind("<<Modified>>", parent._on_modified)

        self.line_numbers._textbox.bind("<Button-1>", parent._on_line_number_click)
        self.line_numbers._textbox.bind("<MouseWheel>", parent._on_line_scroll)
        self.line_numbers._textbox.bind("<Button-4>", parent._on_line_scroll)
        self.line_numbers._textbox.bind("<Button-5>", parent._on_line_scroll)

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
        if not self.parent._textbox:
            return
        
        try:
            line_count = int(self.parent._textbox.index('end-1c').split('.')[0])
        except:
            line_count = 1
        
        lines = [str(i) for i in range(1, line_count + 1)]

        self.line_numbers._textbox.config(state="normal")
        self.line_numbers.delete("1.0", "end")
        self.line_numbers.insert("1.0", "\n".join(lines))
        self.line_numbers._textbox.config(state="disabled")

        self.line_numbers._textbox.yview_moveto(self.parent._textbox.yview()[0])

    def _on_text_change(self, event=None):
        if hasattr(self.parent, '_after_line_id'):
            self.parent.master.after_cancel(self.parent._after_line_id)
        self.parent._after_line_id = self.parent.master.after(50, self.parent._update_line_numbers)

    def _on_modified(self, event=None):
        self.parent._update_line_numbers()
        self.parent._textbox.edit_modified(False)

    def _on_scroll(self, event):
        try:
            if hasattr(event, 'num'):
                if event.num == 4:
                    self.parent._textbox.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.parent._textbox.yview_scroll(1, "units")
            else:
                delta = -1 * (event.delta / 120)
                self.parent._textbox.yview_scroll(int(delta), "units")
        except:
            pass
        self.line_numbers._textbox.yview_moveto(self.parent._textbox.yview()[0])
        return None

    def _on_line_scroll(self, event):
        try:
            if hasattr(event, 'num'):
                if event.num == 4:
                    self.parent._textbox.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.parent._textbox.yview_scroll(1, "units")
            else:
                delta = -1 * (event.delta / 120)
                self.parent._textbox.yview_scroll(int(delta), "units")
        except:
            pass
        self.line_numbers._textbox.yview_moveto(self.parent._textbox.yview()[0])
        return "break"

    def _on_line_number_click(self, event):
        if self.parent.language != "python":
            return
        
        index = self.line_numbers._textbox.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0])
        
        fold_regions = self.parent._get_foldable_regions()
        foldable_starts = [start for start, _ in fold_regions]
        
        if line_num in foldable_starts:
            self.parent.toggle_fold(line_num)
        elif line_num in self.parent._folded_lines:
            self.parent.toggle_fold(line_num)