# pyright: reportAttributeAccessIssue=false
#! /usr/bin/env python3

import sys
import os
import time
import logging

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code",
    "Path": ".main",
    "Entrance": "main.py"
}

def get_assets_path():
    """Get the path to the assets directory.
    
    Returns:
        str: Path to the assets directory, handling both frozen (PyInstaller) and source modes.
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        external_assets = os.path.join(exe_dir, 'assets')
        if os.path.exists(external_assets):
            return external_assets
        return os.path.join(sys._MEIPASS, 'assets') # pyright: ignore[reportAttributeAccessIssue]
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

ASSETS_PATH = get_assets_path()

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS # pyright: ignore[reportAttributeAccessIssue]
    sys.tracebacklimit = 0
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

libs_path = os.path.join(base_path, 'libs')
if libs_path not in sys.path:
    sys.path.insert(0, base_path)
    sys.path.insert(0, libs_path)

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import ttkbootstrap as ttkb
import libs.cfg_handle as cfg_handle
import libs.langs_loader as langs_loader
from libs.gui import theme
from libs.gui.lazy_loader import LazyLoader


class MainWindow:
    """Main application window for Thon Code IDE.
    
    Manages the editor, project tree, menus, and status bar.
    Provides i18n support through langs_cfg for all user-visible strings.
    """

    def __init__(self) -> None:
        """Initialize the main window.

        Sets up theme, UI components, i18n, and loads configuration.
        Records startup performance metrics for optimization tracking.
        """
        self._startup_start = time.perf_counter()
        self._logger = logging.getLogger("thoncode.main")

        # Initialize plugin system (host reference set after window creation)
        from libs.plugins import PluginManager
        self.plugin_manager = PluginManager()

        # Read config to determine theme (cached once; reused by _get_cfg_data
        # to avoid repeated disk reads during startup).
        cfg_handle.cfg_handle().check_cfg_file()
        self._cached_cfg_data = cfg_handle.cfg_handle().read_cfg()["data"]
        cfg_data = self._cached_cfg_data
        cfg_theme = cfg_data.get("theme", "dark")

        # Create ttkbootstrap themed main window
        self.root = theme.create_window(cfg_theme)
        self.root.title("Thon Code")
        self.root.geometry("1200x675")
        self.current_file = None
        self.is_dirty = False
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.last_saved_content = ""

        self._set_icon()

        # Initialize async task runner for non-blocking I/O
        from libs.gui.async_utils import AsyncTaskRunner
        AsyncTaskRunner.initialize(self.root)

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
        # Defer welcome-page creation to the first idle tick so the main
        # window paints first and startup time excludes welcome-page build cost.
        self.root.after(0, self._show_welcome_if_needed)

        self._startup_end = time.perf_counter()
        self._startup_time = self._startup_end - self._startup_start
        self._logger.info("Startup completed in %.3fs", self._startup_time)

        # Load plugins after UI is ready so plugins can access host services.
        # PyInstaller-aware: prefer user-writable dir next to .exe, fall back
        # to the bundled _MEIPASS copy (frozen) or source plugins/ folder.
        from libs.plugins.plugin_manager import resolve_plugin_dirs
        self.plugin_manager.set_host(self)
        all_plugin_dirs = resolve_plugin_dirs(base_path)
        # Also make sure the legacy <base_path>/plugins location is scanned
        # in case resolve_plugin_dirs returned an empty list in edge cases.
        legacy_plugin_dir = os.path.join(base_path, "plugins")
        if os.path.isdir(legacy_plugin_dir):
            abs_legacy = os.path.abspath(legacy_plugin_dir)
            if abs_legacy not in {os.path.abspath(d) for d in all_plugin_dirs}:
                all_plugin_dirs.append(abs_legacy)
        self.plugin_manager.set_plugin_dirs(all_plugin_dirs)
        if all_plugin_dirs:
            # Pass the highest-priority directory as the primary; any
            # extras are scanned via set_plugin_dirs().
            self.plugin_manager.discover_and_load(all_plugin_dirs[0])
        else:
            self.plugin_manager.discover_and_load(legacy_plugin_dir)

        print(f"[ThonCode] Startup time: {self._startup_time:.3f}s (lazy editor loading)")

    def get_text(self, key: str) -> str:
        """Get localized text by dot-separated key.
        
        Args:
            key: Dot-separated i18n key (e.g., 'status.ready')
            
        Returns:
            Localized string or the key itself if not found
        """
        return getattr(self.langs_cfg, key.replace('.', '_'), key)

    @property
    def startup_time(self) -> float:
        """Get the startup time in seconds.
        
        Returns:
            float: Startup time in seconds
        """
        return self._startup_time

    @property
    def is_editor_loaded(self) -> bool:
        """Check if the editor manager is currently loaded.
        
        Returns:
            bool: True if editor manager is loaded
        """
        return self.editor_manager is not None

    def _set_icon(self):
        """Set the application icon from assets."""
        try:
            icon_path = os.path.join(ASSETS_PATH, 'icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

    def _configure_grid_weights(self) -> None:
        """Configure grid row and column weights for the main layout."""
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=0)

    def _build_menu(self):
        """Build the top menu bar with all menu items using i18n."""
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
        menubar.add_cascade(label=self.langs_cfg.main_menu_run, menu=run_menu)
        run_menu.add_command(label=self.langs_cfg.main_menu_run_file, accelerator="F5", command=self.run_current_file)
        run_menu.add_command(label=self.langs_cfg.main_menu_run_config, command=self.configure_runtime)

        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.langs_cfg.main_menu_tools, menu=tools_menu)
        tools_menu.add_command(label=self.langs_cfg.main_menu_settings, command=self._open_settings)
        tools_menu.add_command(label=self.langs_cfg.main_menu_structure_viewer, command=self.show_struct_viewer)
        tools_menu.add_command(label=self.langs_cfg.main_menu_git_integration, accelerator="F3", command=self.show_git_integration)
        tools_menu.add_separator()
        tools_menu.add_command(label=self.langs_cfg.plugins_title, command=self.show_plugin_manager)

    def _open_settings(self):
        """Open the settings window and update status bar."""
        SettingsWindow = LazyLoader.get('libs.gui.settings_win', 'SettingsWindow')
        SettingsWindow(self.root, on_settings_changed=self._on_settings_applied)
        self.status_bar.configure(text=self.langs_cfg.status_language_updated)

    def _on_settings_applied(self, new_cfg):
        """Handle settings change callback by reloading config.
        
        Args:
            new_cfg: Updated configuration data
        """
        self.reload_config()

    def apply_theme(self, theme_name):
        """Apply a theme by name.
        
        Args:
            theme_name: Name of the theme to apply
        """
        theme.apply_theme(theme_name)

    def reload_config(self):
        """Reload configuration, re-apply theme, and refresh UI."""
        cfg_data = self._get_cfg_data(force_refresh=True)
        theme_name = cfg_data.get("theme", "dark")
        theme.apply_theme(theme_name)
        # Apply accent color override if set in config
        accent = cfg_data.get("accent_color", "")
        if accent:
            theme.apply_accent_color(accent)
        # Reload i18n strings from the (possibly changed) config language
        langs_loader.langs.reload()
        self.langs_cfg = langs_loader.langs()
        self._build_menu()
        self.root.update_idletasks()
        self.status_bar.configure(text=self.langs_cfg.status_config_reloaded)
        # Notify plugins that the theme changed
        self.plugin_manager.call_hook("theme_change", theme_name)

    def reload_language(self):
        """Reload language settings and rebuild UI."""
        self.langs_cfg = langs_loader.langs()
        self._build_menu()
        self.root.title("Thon Code")

    def _setup_tree_style(self) -> None:
        """Configure Treeview style based on ttkbootstrap theme colors."""
        style = ttk.Style()
        colors = theme.get_colors()
        style.configure("Treeview",
                        background=colors["bg_panel"],
                        foreground=colors["fg"],
                        fieldbackground=colors["bg_panel"],
                        font=('Microsoft YaHei', 10),
                        rowheight=20)
        style.configure("Treeview.Heading",
                        background=colors["bg"],
                        foreground=colors["fg"])
        style.map('Treeview', background=[('selected', colors["accent"])])

    def _init_components(self) -> None:
        """Initialize all UI components: menu bar, panes, and status bar."""
        self.menu_bar = ttk.Frame(self.root)
        self.menu_bar.configure(height=40)
        self._create_top_right_controls()
        self.menu_bar.grid(row=0, column=0, columnspan=3, sticky="ew")

        self.paned = ttk.PanedWindow(self.root, orient='horizontal')
        self.paned.grid(row=1, column=0, columnspan=2, sticky="nsew")

        self.left_frame = ttk.Frame(self.paned)
        self.left_frame.configure(width=self.left_width)
        self.paned.add(self.left_frame, weight=0)
        self._build_left_pane()

        self.center_frame = ttk.Frame(self.paned)
        self.paned.add(self.center_frame, weight=1)
        self._build_center_pane()

        self.paned.bind("<ButtonRelease-1>", self._on_sash_release)

        self.right_frame = ttk.Frame(self.root)
        self.right_frame.configure(width=self.right_width)
        self.right_frame.grid(row=1, column=2, sticky="ns")
        self._build_right_pane()

        self.status_bar = ttk.Label(self.root, text=self.langs_cfg.status_ready, anchor="w")
        self.status_bar.grid(row=2, column=0, columnspan=3, sticky="ew")

        self.welcome_page = None
        self.welcome_frame = None
        self.welcome_show_check = None

    def _create_top_right_controls(self) -> None:
        """Create top-right controls: pane toggles and search."""
        container = ttk.Frame(self.menu_bar)
        container.pack(side="right", padx=10, pady=5)

        self.left_toggle_btn = ttk.Button(container, text="◀", width=3,
                                          command=self.toggle_left_pane)
        self.left_toggle_btn.pack(side="left", padx=(0, 5))

        self.right_toggle_btn = ttk.Button(container, text="▶", width=3,
                                           command=self.toggle_right_pane)
        self.right_toggle_btn.pack(side="left", padx=(0, 10))

        self.search_entry = ttk.Entry(container, width=30)
        self.search_entry.pack(side="left", padx=(0, 5))

        search_btn = ttk.Button(container, text="🔍", width=3, command=self.do_search)
        search_btn.pack(side="left")

    def _build_left_pane(self):
        """Build the left pane with the project tree."""
        self.sidebar_frame = ttk.Frame(self.left_frame)
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
        """Build the center pane: a ttk.Notebook containing the welcome tab
        and zero or more editor tabs (via EditorTabManager).
        """
        self.editor_placeholder = ttk.Frame(self.center_frame)
        self.editor_placeholder.pack(fill="both", expand=True, padx=0, pady=(0, 0))
        # Eagerly create EditorTabManager (notebook + welcome slot) so the
        # welcome page has a home tab from boot.
        EditorTabManager = LazyLoader.get('libs.gui.editor_tab_manager',
                                          'EditorTabManager')
        self.tab_manager = EditorTabManager(
            self.editor_placeholder,
            main_window=self,
            status_callback=lambda msg: self.status_bar.configure(text=msg),
            update_title_callback=self.update_title,
            get_welcome_frame=self._lazy_get_welcome_frame,
            hide_welcome_callback=self.hide_welcome,
            plugin_hook_callback=self._tab_plugin_hook,
        )
        # Aliases kept for backward compatibility with single-editor
        # code paths (cut/copy/paste, menus, etc.). They are refreshed
        # by TabManager._sync_host_state on every tab change / file open.
        self.editor_manager = None
        self.editor_widget = None
        self.textbox_widget = None
        self.editor = None

    def _lazy_get_welcome_frame(self):
        """Called by TabManager when the welcome tab is selected for the
        first time. Creates the WelcomePage lazily and returns its frame."""
        self._ensure_welcome_page()
        return self.welcome_frame

    def _tab_plugin_hook(self, hook_name: str, arg: str) -> None:
        """Thin proxy between TabManager events and the plugin manager."""
        if self.plugin_manager is not None:
            try:
                self.plugin_manager.call_hook(hook_name, arg)
            except Exception:
                pass

    def _build_right_pane(self):
        """Build the right pane with a placeholder label."""
        self.sidebar_right = ttk.Frame(self.right_frame)
        self.sidebar_right.pack(fill="both", expand=True, padx=2, pady=2)
        label = ttk.Label(self.sidebar_right, text=self.langs_cfg.main_right_panel)
        label.pack(expand=True)

    def toggle_left_pane(self):
        """Toggle visibility of the left pane."""
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
        """Toggle visibility of the right pane."""
        if self.right_visible:
            self.right_frame.grid_remove()
            self.right_visible = False
            self.right_toggle_btn.configure(text="◀")
        else:
            self.right_frame.grid()
            self.right_visible = True
            self.right_toggle_btn.configure(text="▶")

    def _on_sash_release(self, event):
        """Handle sash release event to enforce pane width limits.
        
        Args:
            event: The sash release event
        """
        if self.left_visible:
            self._limit_left_width()

    def _limit_left_width(self):
        """Enforce min/max width constraints on the left pane."""
        if not self.left_visible:
            return
        try:
            pos = self.paned.sashpos(0)
        except Exception:
            return
        if pos > self.max_left_width:
            self.paned.sashpos(0, self.max_left_width)
        elif pos < self.min_left_width:
            self.paned.sashpos(0, self.min_left_width)
        self.left_width = self.paned.sashpos(0)

    def _ensure_welcome_page(self):
        """Ensure the welcome page is initialized and return it.
        
        Returns:
            WelcomePage: The welcome page instance
        """
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
        return self.welcome_page

    def _show_welcome_if_needed(self) -> None:
        """On first idle tick: show the welcome tab if the config says so.

        With the new tabbed layout the welcome page lives permanently as
        tab index 0 of ``EditorTabManager.notebook``, so we just select it
        at startup when the user hasn't opened any file yet or when the
        configuration opts in to showing it.
        """
        cfg = self._get_cfg_data()
        show = cfg.get("show_welcome", True)
        if not show and self.current_file:
            return
        if self.tab_manager is not None:
            try:
                from libs.gui.editor_tab_manager import EditorTabManager as _ETM
                self.tab_manager._activate_tab(_ETM.WELCOME_TAB_ID)
            except Exception:
                pass

    def hide_welcome(self) -> None:
        """No-op in tabbed layout: welcome is always reachable via its tab.

        Kept so legacy callers don't break. The caller's intent is "stop
        showing welcome and focus the editor", which we implement by
        stealing focus onto the active editor if possible.
        """
        try:
            if self.textbox_widget and self.textbox_widget.winfo_exists():
                self.textbox_widget.focus_set()
        except Exception:
            pass

    def show_welcome(self) -> None:
        """Switch to the welcome tab."""
        if self.tab_manager is not None:
            try:
                from libs.gui.editor_tab_manager import EditorTabManager as _ETM
                self.tab_manager._activate_tab(_ETM.WELCOME_TAB_ID)
            except Exception:
                pass

    def _open_recent_project(self, path):
        """Open a recently used project by path.
        
        Args:
            path: Path to the project directory
        """
        if os.path.isdir(path):
            self.project_root = path
            self.tree_manager.set_project_root(path)
            self.hide_welcome()
            self.status_bar.configure(text=f"{self.langs_cfg.status_opened_project} {path}")
            cfg_handle.cfg_handle().add_recent_project(path)
        else:
            messagebox.showerror(self.langs_cfg.settings_error_title, self.langs_cfg.status_project_not_found)

    def toggle_welcome_config(self):
        """Toggle the show-on-start welcome page setting."""
        cfg = self._get_cfg_data(force_refresh=True)
        cfg["show_welcome"] = self.welcome_page.get_check_state()
        cfg_handle.cfg_handle().write_cfg(cfg)
        # Keep the in-memory cache in sync with the just-written file.
        self._cached_cfg_data = cfg

    def do_search(self) -> None:
        """Search for files in the project tree matching the keyword.

        Walks the file tree and selects the first item whose name contains
        the search keyword (case-insensitive). If the tree is available,
        the match is scrolled into view and focus is set so the user can
        press F3/Enter to open it.
        """
        keyword = self.search_entry.get().strip()
        if not keyword:
            self.status_bar.configure(text=self.langs_cfg.search_enter_keyword)
            return

        if not self.tree_manager:
            self.status_bar.configure(text=self.langs_cfg.search_dev)
            return

        tree = self.tree_manager.get_tree()
        kw_lower = keyword.lower()
        match = self._search_tree_recursive(tree, "", kw_lower)
        if match:
            tree.selection_set(match)
            tree.focus(match)
            tree.see(match)
            path = tree.set(match, "path")
            self.status_bar.configure(
                text=f"{self.langs_cfg.search}: {os.path.basename(path)}")
        else:
            self.status_bar.configure(
                text=f"{self.langs_cfg.search}: '{keyword}' - {self.langs_cfg.search_no_result}")

    def _search_tree_recursive(self, tree, parent, kw_lower):
        """Recursively search tree items for a name matching the keyword.

        Args:
            tree: The ttk.Treeview widget
            parent: Parent item id to search under ("" for root)
            kw_lower: Lowercase search keyword

        Returns:
            The first matching item id, or None if no match found
        """
        for item in tree.get_children(parent):
            text = tree.item(item, "text")
            if text and kw_lower in text.lower():
                return item
            # Recurse into children
            result = self._search_tree_recursive(tree, item, kw_lower)
            if result:
                return result
        return None

    def new_file(self):
        """Clear the editor and prepare for a new file in a new tab."""
        mgr = self.tab_manager.new_file()
        # Bind context menu and <<Modified>> handlers for the fresh editor
        try:
            tb = mgr.get_textbox()
            tb.bind("<Button-3>", self._show_editor_context_menu, add="+")
        except Exception:
            pass
        self.hide_welcome()

    def open_file_by_path(self, file_path, jump_to_line=None):
        """Open a file by its path (adds / activates a tab).

        Args:
            file_path: Absolute path to the file to open
            jump_to_line: Optional 1-based line number to jump to after
                opening (used by Ctrl+right-click go-to-definition).
        """
        ok = self.tab_manager.open_file(file_path, jump_to_line=jump_to_line)
        if ok:
            active_mgr = self.tab_manager.get_active_manager()
            if active_mgr is not None:
                try:
                    tb = active_mgr.get_textbox()
                    tb.bind("<Button-3>", self._show_editor_context_menu, add="+")
                except Exception:
                    pass

    def open_file(self):
        """Open a file using a file dialog."""
        file_path = filedialog.askopenfilename(
            defaultextension=".*",
            filetypes=[
                ("Python files", "*.py"),
                ("Java files", "*.java"),
                ("Rust files", "*.rs"),
                ("C/C++ files", "*.c;*.cpp;*.h;*.hpp"),
                ("JavaScript / TypeScript", "*.js;*.jsx;*.ts;*.tsx"),
                ("Markdown", "*.md"),
                ("JSON", "*.json"),
                ("All files", "*.*"),
            ]
        )
        if file_path:
            self.open_file_by_path(file_path)

    def open_folder(self):
        """Open a project folder using a directory dialog."""
        folder = filedialog.askdirectory(title=self.langs_cfg.main_select_folder)
        if not folder:
            self.status_bar.configure(text=self.langs_cfg.status_no_folder)
            return
        if not os.path.isdir(folder):
            messagebox.showerror(self.langs_cfg.settings_error_title, self.langs_cfg.status_invalid_dir)
            return
        try:
            self.project_root = folder
            cfg_handle.cfg_handle().add_recent_project(folder)
            self.tree_manager.set_project_root(folder)
            self.hide_welcome()
            self.status_bar.configure(text=f"{self.langs_cfg.status_opened_project} {folder}")
            # Notify plugins that a project was opened
            self.plugin_manager.call_hook("project_open", folder)
        except Exception as e:
            messagebox.showerror(self.langs_cfg.settings_error_title, f"{self.langs_cfg.status_open_failed}: {e}")
            self.status_bar.configure(text=f"{self.langs_cfg.status_open_failed}: {e}")

    def save_file(self):
        """Save the active editor tab. Falls back to save_as when untitled.

        TabManager is the canonical source of truth for which tab is active;
        after a successful save the tab label is refreshed and the host
        state (current_file / is_dirty) is synced automatically.
        """
        if self.tab_manager is None:
            return False
        # Ensure the active manager state is pushed to legacy aliases.
        self.tab_manager._sync_host_state()
        if not self.current_file:
            return self.save_as()
        ok = self.tab_manager.save_current()
        if ok:
            self.status_bar.configure(text=f"{self.langs_cfg.status_saved} {self.current_file}")
            self.tab_manager.refresh_all_labels()
        return ok

    def save_as(self):
        """Save the active tab under a new path via the system save-as dialog.

        Returns:
            bool: True if save was successful
        """
        if self.tab_manager is None:
            return False
        self.tab_manager._sync_host_state()
        file_path = filedialog.asksaveasfilename(
            defaultextension=".*",
            filetypes=[
                ("Python files", "*.py"),
                ("Java files", "*.java"),
                ("Rust files", "*.rs"),
                ("C/C++ files", "*.c;*.cpp;*.h;*.hpp"),
                ("All files", "*.*"),
            ]
        )
        if not file_path:
            return False
        ok = self.tab_manager.save_as_current(file_path)
        if ok:
            self.status_bar.configure(text=f"{self.langs_cfg.status_saved} {file_path}")
            self.refresh_tree()
            self.tab_manager.refresh_all_labels()
            self.hide_welcome()
        else:
            messagebox.showerror(self.langs_cfg.settings_error_title,
                                 self.langs_cfg.editor_save_failed)
        return ok

    def refresh_tree(self):
        """Refresh the project tree view."""
        if hasattr(self, 'tree_manager'):
            self.tree_manager.refresh()

    def update_title(self):
        """Update the window title with the current file name."""
        base = "Thon Code"
        if self.current_file:
            name = os.path.basename(self.current_file)
            self.root.title(f"{base} - {name}{'*' if self.is_dirty else ''}")
        else:
            self.root.title(f"{base} - {self.langs_cfg.status_untitled}{'*' if self.is_dirty else ''}")

    def exit_app(self):
        """Exit the application, unload plugins, and release async resources."""
        self.plugin_manager.unload_all()
        from libs.gui.async_utils import AsyncTaskRunner
        AsyncTaskRunner.shutdown()
        self.root.quit()

    def cut(self):
        """Cut selected text in the editor."""
        if self.textbox_widget and self.textbox_widget.winfo_exists():
            self.textbox_widget.event_generate("<<Cut>>")

    def copy(self):
        """Copy selected text in the editor."""
        if self.textbox_widget and self.textbox_widget.winfo_exists():
            self.textbox_widget.event_generate("<<Copy>>")

    def paste(self):
        """Paste text from clipboard into the editor."""
        if self.textbox_widget and self.textbox_widget.winfo_exists():
            self.textbox_widget.event_generate("<<Paste>>")

    def select_all(self):
        """Select all text in the editor."""
        if self.textbox_widget and self.textbox_widget.winfo_exists():
            self.textbox_widget.focus_set()
            self.textbox_widget.event_generate("<Control-a>")

    def _get_cfg_data(self, force_refresh: bool = False) -> dict:
        """Return cached configuration data, refreshing from disk on demand.

        Avoids repeated disk reads at startup; later mutation paths pass
        force_refresh=True to pick up external or just-written changes.

        Args:
            force_refresh: Re-read config.json from disk when True

        Returns:
            dict: The "data" section of the configuration
        """
        if force_refresh or getattr(self, "_cached_cfg_data", None) is None:
            self._cached_cfg_data = cfg_handle.cfg_handle().read_cfg()["data"]
        return self._cached_cfg_data

    def _load_config(self):
        """Load configuration and update welcome page state."""
        cfg = self._get_cfg_data()
        show = cfg.get("show_welcome", True)
        if self.welcome_page:
            self.welcome_page.set_check_state(show)

    def show_struct_viewer(self):
        """Open the directory structure viewer window."""
        StructViewerWindow = LazyLoader.get('libs.gui.struct_ui', 'StructViewerWindow')
        StructViewerWindow(
            self.root,
            root_path=self.project_root,
            status_callback=lambda msg: self.status_bar.configure(text=msg)
        )

    def run_current_file(self):
        """Open the run file dialog for the current file."""
        RunFileDialog = LazyLoader.get('libs.gui.run_file', 'RunFileDialog')
        RunFileDialog(
            self.root,
            self.current_file,
            self.is_dirty,
            save_callback=self.save_file,
            status_callback=lambda msg: self.status_bar.configure(text=msg)
        )

    def show_project_config(self):
        """Open the project configuration window."""
        ProjectConfigWindow = LazyLoader.get('libs.gui.project_cfg', 'ProjectConfigWindow')
        ProjectConfigWindow(
            self.root,
            self.project_root,
            status_callback=lambda msg: self.status_bar.configure(text=msg)
        )

    def configure_runtime(self):
        """Open the configure runtime window."""
        ConfigureRuntimeWindow = LazyLoader.get('libs.gui.configure_runtime', 'ConfigureRuntimeWindow')
        ConfigureRuntimeWindow(
            self.root,
            status_callback=lambda msg: self.status_bar.configure(text=msg)
        )

    def show_git_integration(self):
        """Open the Git integration window."""
        GitIntegrationWindow = LazyLoader.get('libs.gui.git_window', 'GitIntegrationWindow')
        GitIntegrationWindow(
            self.root,
            project_root=self.project_root,
            status_callback=lambda msg: self.status_bar.configure(text=msg)
        )

    def show_plugin_manager(self):
        """Open the plugin manager window (loaded + marketplace tabs)."""
        PluginManagerWindow = LazyLoader.get('libs.gui.plugin_ui', 'PluginManagerWindow')
        cfg_data = self._get_cfg_data()
        market_url = cfg_data.get("plugin_marketplace_url", "")

        def _save_url(url: str):
            cfg = self._get_cfg_data()
            cfg["plugin_marketplace_url"] = url
            import libs.cfg_handle as cfg_handle
            cfg_handle.cfg_handle().write_cfg(cfg)

        PluginManagerWindow(
            self.root, self.plugin_manager,
            base_path=base_path,
            marketplace_url=market_url,
            on_save_marketplace_url=_save_url,
        )

    def _show_editor_context_menu(self, event):
        """Show the editor right-click context menu.
        
        Args:
            event: The right-click event
        """
        if not self.textbox_widget or not self.textbox_widget.winfo_exists():
            return
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=self.langs_cfg.status_refresh_editor, command=self._refresh_editor_highlight)
        menu.post(event.x_root, event.y_root)

    def _refresh_editor_highlight(self):
        """Refresh editor syntax highlighting and update status."""
        if self.editor_manager and self.editor_manager.editor:
            self.editor_manager.editor.highlight_all()
            self.status_bar.configure(text=self.langs_cfg.status_ready)


if __name__ == "__main__":
    _boot_start = time.perf_counter()
    # Initialize logging with rotation before anything else
    from libs.log_manager import init_logging
    init_logging()
    _boot_logger = logging.getLogger("thoncode.boot")
    _boot_logger.info("Application starting")

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
    _boot_end = time.perf_counter()
    print(f"[ThonCode] Total boot time: {_boot_end - _boot_start:.3f}s")
    main_window.root.mainloop()