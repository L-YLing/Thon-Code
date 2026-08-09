#! /usr/bin/env python3
import sys
import os

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code",
    "Path": ".main",
    "Entrance": "main.py"
}

def get_assets_path():
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        external_assets = os.path.join(exe_dir, 'assets')
        if os.path.exists(external_assets):
            return external_assets
        return os.path.join(sys._MEIPASS, 'assets')
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

ASSETS_PATH = get_assets_path()

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    sys.tracebacklimit = 0
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

libs_path = os.path.join(base_path, 'libs')
if libs_path not in sys.path:
    sys.path.insert(0, base_path)
    sys.path.insert(0, libs_path)

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import libs.cfg_handle as cfg_handle
import libs.langs_loader as langs_loader


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
    
    @classmethod
    def get_send2trash(cls):
        try:
            return cls.get('send2trash', 'send2trash')
        except ImportError:
            return None


class MainWindow:
    def __init__(self) -> None:
        self.root = ctk.CTk()
        self.root.title("Thon Code")
        self.root.geometry("1200x675")
        self.current_file = None
        self.is_dirty = False
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.last_saved_content = ""

        self._set_icon()
        
        self.left_visible = True
        self.right_visible = True
        self.max_left_width = 350
        self.min_left_width = 120
        self.left_width = 200
        self.right_width = 150

        self.langs_cfg = langs_loader.langs()

        self._configure_grid_weights()
        self._build_menu()
        self._init_components()
        self._setup_tree_style()
        self._load_config()
        self._show_welcome_if_needed()

    def _set_icon(self):
        try:
            icon_path = os.path.join(ASSETS_PATH, 'icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

    def _configure_grid_weights(self) -> None:
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=0)

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        project_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.langs_cfg.main_menu_project, menu=project_menu)
        project_menu.add_command(label=self.langs_cfg.main_menu_project_cfg, command=self.show_project_config)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.langs_cfg.main_menu_file, menu=file_menu)
        file_menu.add_command(label=self.langs_cfg.main_menu_new, accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label=self.langs_cfg.main_menu_open, accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label=self.langs_cfg.main_menu_save, accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label=self.langs_cfg.main_menu_save_as, accelerator="Ctrl+Shift+S", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label=self.langs_cfg.main_menu_exit, accelerator="Ctrl+Q", command=self.exit_app)

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.langs_cfg.main_menu_edit, menu=edit_menu)
        edit_menu.add_command(label=self.langs_cfg.main_menu_cut, accelerator="Ctrl+X", command=self.cut)
        edit_menu.add_command(label=self.langs_cfg.main_menu_copy, accelerator="Ctrl+C", command=self.copy)
        edit_menu.add_command(label=self.langs_cfg.main_menu_paste, accelerator="Ctrl+V", command=self.paste)
        edit_menu.add_separator()
        edit_menu.add_command(label=self.langs_cfg.main_menu_select_all, accelerator="Ctrl+A", command=self.select_all)

        run_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="运行", menu=run_menu)
        run_menu.add_command(label="运行当前文件", accelerator="F5", command=self.run_current_file)
        run_menu.add_command(label="配置运行时...", command=self.configure_runtime)

        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="设置", command=self._open_settings)
        tools_menu.add_command(label="Git Integration", command=self.show_git_integration)
        tools_menu.add_command(label="Directory Structure Viewer", command=self.show_struct_viewer)
        tools_menu.add_command(label="Git集成", accelerator="F3", command=self._open_settings)

    def _open_settings(self):
        SettingsWindow = LazyLoader.get('libs.gui.settings_win', 'SettingsWindow')
        SettingsWindow(self.root, on_settings_changed=self._on_settings_applied)
        self.status_bar.configure(text="语言已更新")

    def _on_settings_applied(self, new_cfg):
        self.reload_config()
    
    def apply_theme(self, theme):
        ctk.set_appearance_mode(theme)

    def reload_config(self):
        cfg_data = cfg_handle.cfg_handle().read_cfg()["data"]
        theme = cfg_data.get("theme", "dark")
        ctk.set_appearance_mode(theme)
        self.langs_cfg = langs_loader.langs()
        self._build_menu()
        self.root.update_idletasks()
        self.status_bar.configure(text="配置已重新加载")

    def reload_language(self):
        self.langs_cfg = langs_loader.langs()
        self._build_menu()
        if hasattr(self, 'welcome_page') and self.welcome_page:
            for child in self.welcome_frame.winfo_children():
                if isinstance(child, ctk.CTkFrame):
                    for sub in child.winfo_children():
                        if isinstance(sub, ctk.CTkButton) and sub.cget("text") in ("新建文件", "打开文件...", "打开文件夹"):
                            pass
            self.search_entry.configure(placeholder_text="搜索项目...")
        self.root.title("Thon Code")

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
        style.map('Treeview', background=[('selected', '#0078D7')])

    def _init_components(self) -> None:
        self.menu_bar = ctk.CTkFrame(self.root, height=40, fg_color="gray20")
        self._create_top_right_controls()
        self.menu_bar.grid(row=0, column=0, columnspan=3, sticky="ew")

        self.paned = ttk.PanedWindow(self.root, orient='horizontal')
        self.paned.grid(row=1, column=0, columnspan=2, sticky="nsew")

        self.left_frame = ctk.CTkFrame(self.paned, fg_color="gray25", width=self.left_width)
        self.paned.add(self.left_frame, weight=0)
        self._build_left_pane()

        self.center_frame = ctk.CTkFrame(self.paned, fg_color="#1e1e1e")
        self.paned.add(self.center_frame, weight=1)
        self._build_center_pane()

        self.paned.bind("<ButtonRelease-1>", self._on_sash_release)

        self.right_frame = ctk.CTkFrame(self.root, fg_color="gray25", width=self.right_width)
        self.right_frame.grid(row=1, column=2, sticky="ns")
        self._build_right_pane()

        self.status_bar = ctk.CTkLabel(self.root, text="就绪", anchor="w", height=25)
        self.status_bar.grid(row=2, column=0, columnspan=3, sticky="ew")

        self.welcome_page = None
        self.welcome_frame = None
        self.welcome_show_check = None

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
        
        TreeManager = LazyLoader.get('libs.gui.tree_manager', 'TreeManager')
        self.tree_manager = TreeManager(
            self.root,
            self.sidebar_frame,
            self.project_root,
            open_file_callback=self.open_file_by_path,
            status_callback=lambda msg: self.status_bar.configure(text=msg)
        )
        self.tree = self.tree_manager.get_tree()

    def _build_center_pane(self):
        EditorManager = LazyLoader.get('libs.gui.editor_manager', 'EditorManager')
        self.editor_manager = EditorManager(
            self.center_frame,
            main_window=self,
            status_callback=lambda msg: self.status_bar.configure(text=msg),
            update_title_callback=self.update_title
        )
        self.editor_widget = self.editor_manager.get_widget()
        self.textbox_widget = self.editor_manager.get_textbox()
        self.editor = self.editor_manager.get_editor_instance()
        
        self.editor_widget.pack(fill="both", expand=True, padx=2, pady=2)
        
        self.textbox_widget._textbox.bind("<Button-3>", self._show_editor_context_menu)
        self.textbox_widget._textbox.bind("<<Modified>>", self.editor_manager._on_modified)

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

    def _ensure_welcome_page(self):
        if self.welcome_page is None:
            WelcomePage = LazyLoader.get('libs.gui.welcome_page', 'WelcomePage')
            self.welcome_page = WelcomePage(
                self.root,
                new_file_callback=self.new_file,
                open_file_callback=self.open_file,
                open_folder_callback=self.open_folder,
                open_recent_callback=self._open_recent_project,
                toggle_welcome_callback=self.toggle_welcome_config
            )
            self.welcome_frame = self.welcome_page.get_frame()
            self.welcome_show_check = self.welcome_page.get_checkbox()
        return self.welcome_page

    def _show_welcome_if_needed(self) -> None:
        cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        show = cfg.get("show_welcome", True)
        if show or not self.current_file:
            self._ensure_welcome_page().place(relx=0, rely=0, relwidth=1, relheight=1)
        else:
            self._ensure_welcome_page().place_forget()

    def hide_welcome(self) -> None:
        if self.welcome_page:
            self.welcome_page.place_forget()

    def _open_recent_project(self, path):
        if os.path.isdir(path):
            self.project_root = path
            self.tree_manager.set_project_root(path)
            self.hide_welcome()
            self.status_bar.configure(text=f"已打开项目: {path}")
            cfg_handle.cfg_handle().add_recent_project(path)
        else:
            messagebox.showerror("错误", "项目路径不存在")

    def toggle_welcome_config(self):
        cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        cfg["show_welcome"] = bool(self.welcome_show_check.get())
        cfg_handle.cfg_handle().write_cfg(cfg)

    def do_search(self) -> None:
        keyword = self.search_entry.get().strip()
        if keyword:
            self.status_bar.configure(text=f"搜索: {keyword} (功能开发中)")
        else:
            self.status_bar.configure(text="请输入搜索关键词")

    def new_file(self):
        self.editor_manager.clear()
        self.current_file = None
        self.is_dirty = False
        self.last_saved_content = ""
        self.update_title()
        self.hide_welcome()

    def open_file_by_path(self, file_path):
        if self.editor_manager.open_file(file_path):
            self.current_file = self.editor_manager.current_file
            self.is_dirty = self.editor_manager.is_dirty
            self.last_saved_content = self.editor_manager.last_saved_content
            self.hide_welcome()
            self.update_title()

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
            cfg_handle.cfg_handle().add_recent_project(folder)
            self.tree_manager.set_project_root(folder)
            self.hide_welcome()
            self.status_bar.configure(text=f"已打开项目: {folder}")
        except Exception as e:
            messagebox.showerror("错误", f"打开文件夹失败：{e}")
            self.status_bar.configure(text=f"打开文件夹失败: {e}")

    def save_file(self):
        if not self.current_file:
            return self.save_as()
        result = self.editor_manager.save_file()
        if result:
            self.current_file = self.editor_manager.current_file
            self.is_dirty = self.editor_manager.is_dirty
            self.last_saved_content = self.editor_manager.last_saved_content
            self.update_title()
        return result

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

    def refresh_tree(self):
        if hasattr(self, 'tree_manager'):
            self.tree_manager.refresh_tree()

    def update_title(self):
        base = "Thon Code"
        if self.current_file:
            name = os.path.basename(self.current_file)
            self.root.title(f"{base} - {name}{'*' if self.is_dirty else ''}")
        else:
            self.root.title(f"{base} - 未命名{'*' if self.is_dirty else ''}")

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

    def _load_config(self):
        cfg = cfg_handle.cfg_handle().read_cfg()["data"]
        show = cfg.get("show_welcome", True)
        if self.welcome_show_check:
            self.welcome_show_check.set(show)
    
    def show_struct_viewer(self):
        """Open directory structure viewer"""
        StructViewerWindow = LazyLoader.get('libs.gui.struct_ui', 'StructViewerWindow')
        StructViewerWindow(
            self.root,
            root_path=self.project_root,
            status_callback=lambda msg: self.status_bar.configure(text=msg)
        )

    def run_current_file(self):
        RunFileDialog = LazyLoader.get('libs.gui.run_file', 'RunFileDialog')
        RunFileDialog(
            self.root,
            self.current_file,
            self.is_dirty,
            save_callback=self.save_file,
            status_callback=lambda msg: self.status_bar.configure(text=msg)
        )

    def show_project_config(self):
        ProjectConfigWindow = LazyLoader.get('libs.gui.project_cfg', 'ProjectConfigWindow')
        ProjectConfigWindow(
            self.root, 
            self.project_root, 
            status_callback=lambda msg: self.status_bar.configure(text=msg)
        )

    def configure_runtime(self):
        ConfigureRuntimeWindow = LazyLoader.get('libs.gui.configure_runtime', 'ConfigureRuntimeWindow')
        ConfigureRuntimeWindow(
            self.root, 
            status_callback=lambda msg: self.status_bar.configure(text=msg)
        )

    def show_git_integration(self):
        """Open Git integration window"""
        GitIntegrationWindow = LazyLoader.get('libs.gui.git_window', 'GitIntegrationWindow')
        GitIntegrationWindow(
            self.root,
            project_root=self.project_root,
            status_callback=lambda msg: self.status_bar.configure(text=msg)
        )

    def _show_editor_context_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="刷新", command=self._refresh_editor_highlight)
        menu.post(event.x_root, event.y_root)

    def _refresh_editor_highlight(self):
        if hasattr(self, 'editor_manager') and self.editor_manager.editor:
            self.editor_manager.editor.highlight_all()
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