#! /usr/bin/env python3
import sys
import os

def get_assets_path():
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        external_assets = os.path.join(exe_dir, 'assets')
        if os.path.exists(external_assets):
            return external_assets
        return os.path.join(sys._MEIPASS, 'assets')
    else:
        # Development Environment
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

# Set folder `assets` path
ASSETS_PATH = get_assets_path()

# Add libs to the path
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

libs_path = os.path.join(base_path, 'libs')
if libs_path not in sys.path:
    sys.path.insert(0, base_path)
    sys.path.insert(0, libs_path)

if getattr(sys, 'frozen', False):
    # Disable debugging after packaging
    sys.tracebacklimit = 0

libs_path = os.path.join(base_path, 'libs')
if libs_path not in sys.path:
    sys.path.insert(0, base_path)
    sys.path.insert(0, libs_path)

import customtkinter as ctk
import tkinter as tk

from tkinter import filedialog, messagebox, ttk

import shutil
import subprocess

import libs.cfg_handle as cfg_handle
import libs.langs_loader as langs_loader
from libs.gui.code_editor import CodeEditor

try:
    import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

langs_cfg = langs_loader.langs()

class MainWindow:
    def __init__(self) -> None:
        self.root = ctk.CTk()
        self.root.title("Thon Code")
        self.root.geometry("1200x675")
        self.current_file = None
        self.is_dirty = False
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.last_saved_content = ""

        try:
            icon_path = os.path.join(ASSETS_PATH, 'icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass
        
        self.left_visible = True
        self.right_visible = True
        self.max_left_width = 350
        self.min_left_width = 120
        self.left_width = 200
        self.right_width = 150

        self._configure_grid_weights()
        self._create_menu()
        self._init_components()
        self._setup_tree_style()
        self._load_config()
        self._show_welcome_if_needed()

    def _configure_grid_weights(self) -> None:
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_columnconfigure(0, weight=0)   # 左侧
        self.root.grid_columnconfigure(1, weight=1)   # 中间
        self.root.grid_columnconfigure(2, weight=0)   # 右侧

    def _create_menu(self) -> None:
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        project_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=langs_cfg.main_root_project, menu=project_menu)
        project_menu.add_command(label=langs_cfg.main_root_project_cfg, command=self.show_project_config)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=langs_cfg.main_root_file, menu=file_menu)
        file_menu.add_command(label=langs_cfg.main_root_new, accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label=langs_cfg.main_root_open, accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label=langs_cfg.main_root_save, accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label=langs_cfg.main_root_save_as, accelerator="Ctrl+Shift+S", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label=langs_cfg.main_root_exit, accelerator="Ctrl+Q", command=self.exit_app)

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=langs_cfg.main_root_edit, menu=edit_menu)
        edit_menu.add_command(label="剪切", accelerator="Ctrl+X", command=self.cut)
        edit_menu.add_command(label="复制", accelerator="Ctrl+C", command=self.copy)
        edit_menu.add_command(label="粘贴", accelerator="Ctrl+V", command=self.paste)
        edit_menu.add_separator()
        edit_menu.add_command(label="全选", accelerator="Ctrl+A", command=self.select_all)

        run_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="运行", menu=run_menu)
        run_menu.add_command(label="运行当前文件", accelerator="F5", command=self.run_current_file)
        run_menu.add_command(label="配置运行时...", command=self.configure_runtime)

    def _setup_tree_style(self) -> None:
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview",
                        background="#2b2b2b",
                        foreground="white",
                        fieldbackground="#2b2b2b",
                        font=('微软雅黑', 10),
                        rowheight=20)
        style.configure("Treeview.Heading",
                        background="#1e1e1e",
                        foreground="white")
        # 选中
        style.map('Treeview', background=[('selected', '#0078D7')])

    def _init_components(self) -> None:
        self.menu_bar = ctk.CTkFrame(self.root, height=40, fg_color="gray20")
        self._create_top_right_controls()
        self.menu_bar.grid(row=0, column=0, columnspan=3, sticky="ew")

        # PanedWindow
        self.paned = ttk.PanedWindow(self.root, orient='horizontal')
        self.paned.grid(row=1, column=0, columnspan=2, sticky="nsew")

        self.left_frame = ctk.CTkFrame(self.paned, fg_color="gray25", width=self.left_width)
        self.paned.add(self.left_frame, weight=0)
        self._build_left_pane()

        self.center_frame = ctk.CTkFrame(self.paned, fg_color="#1e1e1e")
        self.paned.add(self.center_frame, weight=1)
        self._build_center_pane()

        # 分隔条拖动事件
        self.paned.bind("<ButtonRelease-1>", self._on_sash_release)

        # 独立右侧框架
        self.right_frame = ctk.CTkFrame(self.root, fg_color="gray25", width=self.right_width)
        self.right_frame.grid(row=1, column=2, sticky="ns")
        self._build_right_pane()

        self.status_bar = ctk.CTkLabel(self.root, text="就绪", anchor="w", height=25)
        self.status_bar.grid(row=2, column=0, columnspan=3, sticky="ew")

        self.welcome_frame = ctk.CTkFrame(self.root, fg_color="#1e1e1e")
        self._create_welcome_page()
        self.welcome_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _create_top_right_controls(self) -> None:
        container = ctk.CTkFrame(self.menu_bar, fg_color="gray20")
        container.pack(side="right", padx=10, pady=5)

        self.left_toggle_btn = ctk.CTkButton(container, text="◀", width=30,
                                             command=self.toggle_left_pane)
        self.left_toggle_btn.pack(side="left", padx=(0, 5))

        self.right_toggle_btn = ctk.CTkButton(container, text="▶", width=30,
                                              command=self.toggle_right_pane)
        self.right_toggle_btn.pack(side="left", padx=(0, 10))

        self.search_entry = ctk.CTkEntry(container, width=200, placeholder_text="搜索项目...")
        self.search_entry.pack(side="left", padx=(0, 5))

        search_btn = ctk.CTkButton(container, text="🔍", width=30, command=self.do_search)
        search_btn.pack(side="left")

    def _build_left_pane(self):
        self.sidebar_frame = ctk.CTkFrame(self.left_frame, fg_color="gray25")
        self.sidebar_frame.pack(fill="both", expand=True, padx=2, pady=2)
        self._load_icons()
        self.tree = ttk.Treeview(self.sidebar_frame, selectmode="browse",
                                 columns=("path",), show="tree")
        self.tree.column("path", width=0, stretch=False)
        self.tree.heading("path", text="")
        self.tree.pack(fill="both", expand=True, padx=3, pady=3)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<Button-3>", self.on_tree_right_click)
        self.populate_tree()

    def _build_center_pane(self):
        self.editor()
        self.editor_widget.pack(in_=self.center_frame, fill="both", expand=True, padx=2, pady=2)

    def _build_right_pane(self):
        self.sidebar_right = ctk.CTkFrame(self.right_frame, fg_color="gray25")
        self.sidebar_right.pack(fill="both", expand=True, padx=2, pady=2)
        label = ctk.CTkLabel(self.sidebar_right, text="右侧面板", text_color="gray")
        label.pack(expand=True)

    def toggle_left_pane(self):
        if self.left_visible:
            self.paned.forget(self.left_frame)
            self.left_visible = False
            self.left_toggle_btn.configure(text="▶")
        else:
            self.paned.insert(0, self.left_frame, weight=0)
            self.left_visible = True
            self.left_toggle_btn.configure(text="◀")
        if self.left_visible:
            self._limit_left_width()

    def toggle_right_pane(self):
        if self.right_visible:
            self.right_frame.grid_remove()
            self.right_visible = False
            self.right_toggle_btn.configure(text="◀")
        else:
            self.right_frame.grid()
            self.right_visible = True
            self.right_toggle_btn.configure(text="▶")

    def _on_sash_release(self, event):
        if self.left_visible:
            self._limit_left_width()

    def _limit_left_width(self):
        if not self.left_visible:
            return
        try:
            pos = self.paned.sashpos(0)
        except:
            return
        if pos > self.max_left_width:
            self.paned.sashpos(0, self.max_left_width)
        elif pos < self.min_left_width:
            self.paned.sashpos(0, self.min_left_width)
        self.left_width = self.paned.sashpos(0)

    def do_search(self) -> None:
        keyword = self.search_entry.get().strip()
        if keyword:
            self.status_bar.configure(text=f"搜索: {keyword} (功能开发中)")
        else:
            self.status_bar.configure(text="请输入搜索关键词")

    def _create_welcome_page(self) -> None:
        card = ctk.CTkFrame(self.welcome_frame, fg_color="#2d2d2d", corner_radius=10)
        card.place(relx=0.5, rely=0.4, anchor="center")

        title = ctk.CTkLabel(card, text="Thon Code", font=("微软雅黑", 28, "bold"))
        title.pack(pady=(30, 10))

        subtitle = ctk.CTkLabel(card, text="开始编写代码", font=("微软雅黑", 14))
        subtitle.pack(pady=(0, 20))

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="新建文件", width=150, command=self.new_file).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="打开文件...", width=150, command=self.open_file).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="打开文件夹", width=150, command=self.open_folder).pack(side="left", padx=10)

        recent_label = ctk.CTkLabel(card, text="最近打开", font=("微软雅黑", 12), anchor="w")
        recent_label.pack(pady=(20, 5), padx=20, anchor="w")

        # 从配置读取最近项目
        recent_projects = cfg_handle.cfg_handle().get_recent_projects()
        if recent_projects:
            for proj in recent_projects[:5]:
                btn = ctk.CTkButton(card, text=os.path.basename(proj), fg_color="transparent",
                                    command=lambda path=proj: self._open_recent_project(path))
                btn.pack(pady=2, padx=20, anchor="w")
        else:
            no_recent = ctk.CTkLabel(card, text="暂无最近项目", font=("微软雅黑", 10), text_color="gray")
            no_recent.pack(pady=5, padx=20, anchor="w")

        config_frame = ctk.CTkFrame(card, fg_color="transparent")
        config_frame.pack(pady=(20, 30))

        self.welcome_show_check = ctk.CTkCheckBox(config_frame, text="每次启动显示欢迎页",
                                                  command=self.toggle_welcome_config)
        self.welcome_show_check.select()

    def _open_recent_project(self, path):
        if os.path.isdir(path):
            self.project_root = path
            self.refresh_tree()
            self.hide_welcome()
            self.status_bar.configure(text=f"已打开项目: {path}")
            # 更新最近列表（置顶）
            cfg_handle.cfg_handle().add_recent_project(path)
        else:
            messagebox.showerror("错误", "项目路径不存在")

    def toggle_welcome_config(self):
        cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        cfg["show_welcome"] = bool(self.welcome_show_check.get())
        cfg_handle.cfg_handle().write_cfg(cfg)

    def _show_welcome_if_needed(self) -> None:
        cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        show = cfg.get("show_welcome", True)
        if show or not self.current_file:
            self.welcome_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        else:
            self.welcome_frame.place_forget()

    def hide_welcome(self) -> None:
        self.welcome_frame.place_forget()

    def populate_tree(self, parent="", path=None):
        expanded_paths = self._get_expanded_paths()
        for item in self.tree.get_children():
            self.tree.delete(item)

        if path is None:
            path = self.project_root
            node = self.tree.insert(parent, "end", text=os.path.basename(path), open=True)
            self.tree.set(node, "path", path)
            self._add_children(node, path)
        else:
            node = self.tree.insert(parent, "end", text=os.path.basename(path), open=False)
            self.tree.set(node, "path", path)
            self._add_children(node, path)

        self._restore_expanded_paths(expanded_paths)

    def _get_expanded_paths(self):
        expanded = []
        def collect(item):
            if self.tree.item(item, 'open'):
                path = self.tree.set(item, "path")
                if path:
                    expanded.append(path)
            for child in self.tree.get_children(item):
                collect(child)
        for root in self.tree.get_children():
            collect(root)
        return expanded

    def _restore_expanded_paths(self, expanded_paths):
        def restore(item):
            path = self.tree.set(item, "path")
            if path in expanded_paths:
                self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                restore(child)
        for root in self.tree.get_children():
            restore(root)

    def _load_icons(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_dir = os.path.join(base_dir, "assets", "images")
        target_size = (16, 16)

        folder_path = os.path.join(icon_dir, "folder.png")
        self.folder_icon = self._load_icon_with_resize(folder_path, target_size)
        if self.folder_icon is None:
            print(f"警告: 文件夹图标不存在: {folder_path}")

        default_icon_path = os.path.join(icon_dir, "file.png")
        self.default_file_icon = self._load_icon_with_resize(default_icon_path, target_size)
        if self.default_file_icon is None:
            print(f"警告: 默认文件图标不存在: {default_icon_path}")

        self.file_icons = {}
        if os.path.exists(icon_dir):
            for filename in os.listdir(icon_dir):
                if filename.startswith("file_") and filename.endswith(".png"):
                    ext = filename[5:-4]
                    if ext:
                        full_path = os.path.join(icon_dir, filename)
                        icon = self._load_icon_with_resize(full_path, target_size)
                        if icon:
                            self.file_icons[ext] = icon

    def _load_icon_with_resize(self, file_path, target_size=(16, 16)):
        if not file_path or not os.path.exists(file_path):
            return None
        if HAS_PIL:
            try:
                img = Image.open(file_path)
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Pillow缩放失败: {e}，回退到原始尺寸")
                return tk.PhotoImage(file=file_path)
        else:
            return tk.PhotoImage(file=file_path)

    def _add_children(self, parent, path):
        try:
            items = sorted(os.listdir(path))
        except PermissionError:
            return
        for name in items:
            full_path = os.path.join(path, name)
            if name.startswith('.') or name in ('__pycache__', '.git', '.idea', '.vscode', 'node_modules', 'dist', 'build'):
                continue

            if os.path.isdir(full_path):
                icon = self.folder_icon
                node = self.tree.insert(parent, "end", text=name, open=False, image=icon if icon else '')
                self.tree.set(node, "path", full_path)
                self._add_children(node, full_path)
            else:
                _, ext = os.path.splitext(name)
                ext = ext.lstrip('.').lower()
                if ext in self.file_icons:
                    icon = self.file_icons[ext]
                else:
                    icon = self.default_file_icon
                node = self.tree.insert(parent, "end", text=name, image=icon if icon else '')
                self.tree.set(node, "path", full_path)

    def refresh_tree(self):
        self.populate_tree()

    def on_tree_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self._right_click_item = item
            self._right_click_path = self.tree.set(item, "path")
        else:
            self._right_click_item = None
            self._right_click_path = self.project_root

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="刷新", command=self.refresh_tree)
        menu.add_separator()
        menu.add_command(label="新建文件", command=self.menu_new_file)
        menu.add_command(label="新建文件夹", command=self.menu_new_folder)
        menu.add_separator()
        menu.add_command(label="重命名", command=self.menu_rename)
        menu.add_command(label="删除", command=self.menu_delete)
        menu.add_command(label="移动到回收站", command=self.menu_move_to_trash)
        menu.post(event.x_root, event.y_root)

    def menu_new_file(self):
        parent_path = self._right_click_path if self._right_click_item else self.project_root
        if os.path.isfile(parent_path):
            parent_path = os.path.dirname(parent_path)
        dialog = ctk.CTkInputDialog(text="输入文件名（含扩展名）：", title="新建文件")
        name = dialog.get_input()
        if not name:
            return
        full_path = os.path.join(parent_path, name)
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                pass
            self.refresh_tree()
        except Exception as e:
            messagebox.showerror("错误", f"创建文件失败：{e}")

    def menu_new_folder(self):
        parent_path = self._right_click_path if self._right_click_item else self.project_root
        if os.path.isfile(parent_path):
            parent_path = os.path.dirname(parent_path)
        dialog = ctk.CTkInputDialog(text="输入文件夹名称：", title="新建文件夹")
        name = dialog.get_input()
        if not name:
            return
        full_path = os.path.join(parent_path, name)
        try:
            os.mkdir(full_path)
            self.refresh_tree()
        except Exception as e:
            messagebox.showerror("错误", f"创建文件夹失败：{e}")

    def menu_rename(self):
        if not self._right_click_item:
            return
        old_path = self._right_click_path
        old_name = os.path.basename(old_path)
        dialog = ctk.CTkInputDialog(text="输入新名称：", title="重命名", initialvalue=old_name)
        new_name = dialog.get_input()
        if not new_name or new_name == old_name:
            return
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        try:
            os.rename(old_path, new_path)
            self.refresh_tree()
            if self.current_file and self.current_file == old_path:
                self.current_file = new_path
                self.update_title()
        except Exception as e:
            messagebox.showerror("错误", f"重命名失败：{e}")

    def menu_delete(self):
        if not self._right_click_item:
            return
        path = self._right_click_path
        if not messagebox.askyesno("确认删除", f"确定要永久删除 {os.path.basename(path)} 吗？"):
            return
        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
            self.refresh_tree()
            if self.current_file and self.current_file == path:
                self.current_file = None
                self.editor_widget.delete("1.0", "end")
                self.update_title()
        except Exception as e:
            messagebox.showerror("错误", f"删除失败：{e}")

    def menu_move_to_trash(self):
        if not self._right_click_item:
            return
        path = self._right_click_path
        if not messagebox.askyesno("确认", f"确定将 {os.path.basename(path)} 移动到回收站吗？"):
            return
        try:
            if HAS_SEND2TRASH:
                send2trash.send2trash(path)
            else:
                if messagebox.askyesno("未安装 send2trash", "未安装 send2trash 库，将永久删除文件。是否继续？"):
                    if os.path.isfile(path):
                        os.remove(path)
                    else:
                        shutil.rmtree(path)
                else:
                    return
            self.refresh_tree()
            if self.current_file and self.current_file == path:
                self.current_file = None
                self.editor_widget.delete("1.0", "end")
                self.update_title()
        except Exception as e:
            messagebox.showerror("错误", f"操作失败：{e}")

    def on_tree_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        item = selected[0]
        path = self.tree.set(item, "path")
        if path and os.path.isfile(path):
            self.open_file_by_path(path)

    def new_file(self):
        self.editor_widget.delete("1.0", "end")
        self.current_file = None
        self.is_dirty = False
        self.last_saved_content = ""
        if hasattr(self, 'editor'):
            self.editor.current_file = None
        self.update_title()
        self.hide_welcome()

    def open_file_by_path(self, file_path):
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.editor_widget.delete("1.0", "end")
            self.editor_widget.insert("1.0", content)
            self.current_file = file_path
            self.last_saved_content = content
            self.is_dirty = False
            self.update_title()
            self.status_bar.configure(text=f"已打开: {file_path}")
            self.hide_welcome()
            if hasattr(self, 'editor'):
                self.editor.current_file = file_path
            self.update_title()
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件：{e}")

    def editor(self) -> None:
        cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        ligatures = cfg.get("font_ligatures", True)
        tab_size = cfg.get("tab_size", 4)
        
        self.editor = CodeEditor(self.root, main_window=self, language="python", 
                                font_ligatures=ligatures, tab_size=tab_size)
        self.editor_widget = self.editor.get_widget()
        self.editor.current_file = None
        self.editor_widget._textbox.bind("<<Modified>>", self.on_editor_modified)
        self.editor_widget._textbox.edit_modified(False)
        self.editor_widget._textbox.bind("<Button-3>", self._show_editor_context_menu)

    def on_editor_modified(self, event):
        current_content = self.editor_widget.get("1.0", "end-1c")
        self.is_dirty = (current_content != self.last_saved_content)
        self.update_title()
        self.editor_widget._textbox.edit_modified(False)

    def update_title(self):
        base = "Thon Code"
        if self.current_file:
            name = os.path.basename(self.current_file)
            self.root.title(f"{base} - {name}{'*' if self.is_dirty else ''}")
        else:
            self.root.title(f"{base} - 未命名{'*' if self.is_dirty else ''}")

    def new_file(self):
        self.editor_widget.delete("1.0", "end")
        self.current_file = None
        self.is_dirty = False
        self.last_saved_content = ""
        self.update_title()
        self.hide_welcome()

    def open_file(self):
        file_path = filedialog.askopenfilename(
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if file_path:
            self.open_file_by_path(file_path)

    def open_folder(self):
        folder = filedialog.askdirectory(title="选择项目文件夹")
        if not folder:
            self.status_bar.configure(text="未选择文件夹")
            return
        if not os.path.isdir(folder):
            messagebox.showerror("错误", "所选路径不是有效目录")
            return
        try:
            self.project_root = folder
            # 记录最近项目
            cfg_handle.cfg_handle().add_recent_project(folder)
            self.refresh_tree()
            self.hide_welcome()
            self.status_bar.configure(text=f"已打开项目: {folder}")
        except Exception as e:
            messagebox.showerror("错误", f"打开文件夹失败：{e}")
            self.status_bar.configure(text=f"打开文件夹失败: {e}")

    def save_file(self):
        if not self.current_file:
            return self.save_as()
        
        try:
            content = self.editor_widget.get("1.0", "end-1c")
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"正在保存: {self.current_file}")
            print(f"内容长度: {len(content)}")
            self.is_dirty = False
            self.last_saved_content = content
            self.update_title()
            self.status_bar.configure(text=f"已保存: {self.current_file}")
            self.editor_widget._textbox.edit_modified(False)
            # 强制重置编辑器内部状态
            if hasattr(self, 'editor'):
                self.editor._saving = False
            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{e}")
            return False

    def save_as(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if not file_path:
            return False
        
        try:
            content = self.editor_widget.get("1.0", "end-1c")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            self.current_file = file_path
            self.is_dirty = False
            self.last_saved_content = content
            self.update_title()
            self.status_bar.configure(text=f"已保存: {file_path}")
            self.refresh_tree()
            self.hide_welcome()
            self.editor_widget._textbox.edit_modified(False)
            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{e}")
            return False

    def exit_app(self):
        self.root.quit()

    def cut(self):
        self.editor_widget.event_generate("<<Cut>>")

    def copy(self):
        self.editor_widget.event_generate("<<Copy>>")

    def paste(self):
        self.editor_widget.event_generate("<<Paste>>")

    def select_all(self):
        self.editor_widget.focus_set()
        self.editor_widget.event_generate("<Control-a>")

    def run_current_file(self):
        if not self.current_file:
            messagebox.showinfo("提示", "请先打开一个文件")
            return
        if self.is_dirty:
            if messagebox.askyesno("保存", "文件已修改，是否保存后再运行？"):
                self.save_file()
        cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        python_path = cfg.get("python_path", sys.executable)
        run_args = cfg.get("run_args", "")
        cmd = [python_path, self.current_file]
        if run_args:
            cmd.extend(run_args.split())
        try:
            if sys.platform == "win32":
                subprocess.Popen(["start", "cmd", "/k"] + cmd, shell=True)
            else:
                terminal = os.environ.get("TERM", "xterm")
                subprocess.Popen([terminal, "-e", " ".join(cmd)])
            self.status_bar.configure(text=f"运行: {' '.join(cmd)}")
        except Exception as e:
            messagebox.showerror("错误", f"运行失败：{e}")

    def configure_runtime(self):
        cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        win = ctk.CTkToplevel(self.root)
        win.title("配置运行时")
        win.geometry("400x200")
        win.resizable(False, False)
        # 设为顶级窗口并获取焦点
        win.transient(self.root)
        win.lift()
        win.focus_force()

        ctk.CTkLabel(win, text="Python解释器路径:").pack(pady=(10, 0), anchor="w", padx=20)
        py_entry = ctk.CTkEntry(win, width=300)
        py_entry.insert(0, cfg.get("python_path", sys.executable))
        py_entry.pack(pady=(0, 10), padx=20)

        ctk.CTkLabel(win, text="运行参数（空格分隔）:").pack(anchor="w", padx=20)
        arg_entry = ctk.CTkEntry(win, width=300)
        arg_entry.insert(0, cfg.get("run_args", ""))
        arg_entry.pack(pady=(0, 10), padx=20)

        def save_config():
            cfg["python_path"] = py_entry.get().strip()
            cfg["run_args"] = arg_entry.get().strip()
            cfg_handle.cfg_handle().write_cfg(cfg)
            win.destroy()
            self.status_bar.configure(text="运行时配置已保存")

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="保存", command=save_config).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="取消", command=win.destroy).pack(side="left", padx=10)

    def _load_config(self):
        cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        show = cfg.get("show_welcome", True)
        self.welcome_show_check.select() if show else self.welcome_show_check.deselect()

    def show_project_config(self):
        """显示当前项目的配置（解释器、依赖）"""
        if not self.project_root:
            messagebox.showinfo("提示", "请先打开一个项目")
            return
        cfg = cfg_handle.cfg_handle().get_project_config(self.project_root)
        # 创建弹窗显示信息
        win = ctk.CTkToplevel(self.root)
        win.title("项目配置")
        win.geometry("400x350")
        win.transient(self.root)
        win.lift()
        win.focus_force()

        ctk.CTkLabel(win, text=f"项目: {os.path.basename(self.project_root)}", font=("微软雅黑", 14)).pack(pady=10)
        ctk.CTkLabel(win, text="Python解释器:", anchor="w").pack(anchor="w", padx=20)
        py_entry = ctk.CTkEntry(win, width=300)
        py_entry.insert(0, cfg.get("python_path", sys.executable))
        py_entry.pack(pady=(0,10), padx=20)

        ctk.CTkLabel(win, text="依赖库 (来自requirements.txt):", anchor="w").pack(anchor="w", padx=20)
        deps_text = ctk.CTkTextbox(win, height=100, width=300)
        deps_text.insert("1.0", "\n".join(cfg.get("dependencies", [])))
        deps_text.pack(pady=(0,10), padx=20)

        def save_project_config():
            cfg["python_path"] = py_entry.get().strip()
            cfg_handle.cfg_handle().save_project_config(self.project_root, cfg)
            win.destroy()
            self.status_bar.configure(text="项目配置已保存")

        ctk.CTkButton(win, text="保存", command=save_project_config).pack(pady=10)

    def _show_editor_context_menu(self, event):
        """编辑器右键菜单"""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="刷新", command=self._refresh_editor_highlight)
        menu.post(event.x_root, event.y_root)

    def _refresh_editor_highlight(self):
        if hasattr(self, 'editor') and self.editor:
            self.editor.highlight_all()
            self.status_bar.configure(text="就绪")    

if __name__ == "__main__":
    cfg_handle.cfg_handle().check_cfg_file()
    cfg_data = cfg_handle.cfg_handle().read_cfg()["data"]
    if "show_welcome" not in cfg_data:
        cfg_data["show_welcome"] = True
    if "python_path" not in cfg_data:
        cfg_data["python_path"] = sys.executable
    if "run_args" not in cfg_data:
        cfg_data["run_args"] = ""
    cfg_handle.cfg_handle().write_cfg(cfg_data)

    main_window = MainWindow()
    main_window.root.mainloop()