#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Welcome",
    "Path": ".main.libs.gui.welcome_page",
    "Entrance": "main.py"
}

import os
import tkinter as tk
from tkinter import ttk
import libs.cfg_handle as cfg_handle
import libs.langs_loader as langs_loader


class WelcomePage:
    """Welcome page displayed when the application starts.
    
    Provides quick access to create/open files, open folders,
    and display recently opened projects.
    """

    def __init__(self, parent, new_file_callback, open_file_callback, open_folder_callback, 
                 open_recent_callback, toggle_welcome_callback):
        """Initialize the welcome page.
        
        Args:
            parent: Parent widget
            new_file_callback: Callback for new file action
            open_file_callback: Callback for open file action
            open_folder_callback: Callback for open folder action
            open_recent_callback: Callback for opening recent project
            toggle_welcome_callback: Callback for toggling welcome display
        """
        self.parent = parent
        self.new_file_callback = new_file_callback
        self.open_file_callback = open_file_callback
        self.open_folder_callback = open_folder_callback
        self.open_recent_callback = open_recent_callback
        self.toggle_welcome_callback = toggle_welcome_callback
        self.lang = langs_loader.langs()
        self.welcome_frame = None
        self.welcome_show_check = None
        self._check_var = tk.BooleanVar(value=True)
        self._initialized = False

    def _get_text(self, key: str) -> str:
        """Get localized text by dot-separated key.
        
        Args:
            key: Dot-separated i18n key (e.g., 'welcome.app_title')
            
        Returns:
            Localized string or the key itself if not found
        """
        return getattr(self.lang, key.replace('.', '_'), key)
    
    def _ensure_initialized(self):
        """Lazy initialize welcome page components only when needed."""
        if self._initialized:
            return
        
        self.welcome_frame = ttk.Frame(self.parent)
        self._create_welcome_page()
        self._initialized = True
    
    def _create_welcome_page(self):
        """Create all welcome page UI components including recent projects and shortcuts."""
        style = ttk.Style()
        style.configure("Recent.TButton", borderwidth=0, relief="flat", padding=2)
        style.configure("Shortcut.TLabel", font=("Microsoft YaHei", 10))
        style.configure("ShortcutKey.TLabel", font=("Consolas", 10, "bold"))

        card = ttk.Frame(self.welcome_frame)
        card.place(relx=0.5, rely=0.5, anchor="center")

        # --- Title section ---
        title = ttk.Label(card, text=self._get_text("welcome.app_title"),
                          font=("Microsoft YaHei", 28, "bold"))
        title.pack(pady=(30, 5))

        subtitle = ttk.Label(card, text=self._get_text("welcome.subtitle"),
                             font=("Microsoft YaHei", 14))
        subtitle.pack(pady=(0, 20))

        # --- Action buttons ---
        btn_frame = ttk.Frame(card)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text=self._get_text("welcome.new_file"),
                   command=self.new_file_callback,
                   style="primary.TButton").pack(side="left", padx=10)
        ttk.Button(btn_frame, text=self._get_text("welcome.open_file"),
                   command=self.open_file_callback).pack(side="left", padx=10)
        ttk.Button(btn_frame, text=self._get_text("welcome.open_folder"),
                   command=self.open_folder_callback).pack(side="left", padx=10)

        # --- Two-column layout: recent projects | shortcuts ---
        content_frame = ttk.Frame(card)
        content_frame.pack(fill="x", pady=(20, 10), padx=20)

        # Left column: Recent projects
        left_col = ttk.Frame(content_frame)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ttk.Label(left_col, text=self._get_text("welcome.recent"),
                  font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", pady=(0, 5))

        recent_projects = cfg_handle.cfg_handle().get_recent_projects()
        if recent_projects:
            for proj in recent_projects[:5]:
                btn = ttk.Button(left_col, text=os.path.basename(proj),
                                 command=lambda path=proj: self.open_recent_callback(path),
                                 style="Recent.TButton")
                btn.pack(pady=2, anchor="w")
        else:
            ttk.Label(left_col, text=self._get_text("welcome.no_recent"),
                      font=("Microsoft YaHei", 10)).pack(anchor="w", pady=5)

        # Right column: Keyboard shortcuts
        right_col = ttk.Frame(content_frame)
        right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))

        ttk.Label(right_col, text=self._get_text("welcome.shortcuts"),
                  font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", pady=(0, 5))

        shortcuts = [
            ("Ctrl+N", "welcome.shortcut_new"),
            ("Ctrl+O", "welcome.shortcut_open"),
            ("Ctrl+S", "welcome.shortcut_save"),
            ("Ctrl+Shift+S", "welcome.shortcut_save_as"),
            ("F5", "welcome.shortcut_run"),
            ("F3", "welcome.shortcut_git"),
            ("Ctrl+Q", "welcome.shortcut_exit"),
        ]
        for key, desc_key in shortcuts:
            row = ttk.Frame(right_col)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=key, style="ShortcutKey.TLabel",
                      width=14).pack(side="left")
            ttk.Label(row, text=self._get_text(desc_key),
                      style="Shortcut.TLabel").pack(side="left")

        # --- Footer: show on start checkbox ---
        config_frame = ttk.Frame(card)
        config_frame.pack(pady=(10, 25))

        self.welcome_show_check = ttk.Checkbutton(
            config_frame, text=self._get_text("welcome.show_on_start"),
            variable=self._check_var,
            command=self.toggle_welcome_callback)
        self.welcome_show_check.pack()
    
    def get_frame(self):
        """Get the welcome page frame, initializing if needed.
        
        Returns:
            ttk.Frame: The welcome page container frame
        """
        self._ensure_initialized()
        return self.welcome_frame
    
    def get_check_state(self):
        """Get the current state of the show-on-start checkbox.
        
        Returns:
            bool: True if welcome page should be shown on startup
        """
        self._ensure_initialized()
        return self._check_var.get()
    
    def set_check_state(self, state):
        """Set the state of the show-on-start checkbox.
        
        Args:
            state: Boolean state to set
        """
        self._ensure_initialized()
        self._check_var.set(state)
    
    def place(self, **kwargs):
        """Place the welcome page using geometry manager options.
        
        Args:
            **kwargs: Geometry manager arguments (relx, rely, relwidth, relheight)
        """
        self._ensure_initialized()
        self.welcome_frame.place(**kwargs)
    
    def place_forget(self):
        """Remove the welcome page from the display if initialized."""
        if self._initialized and self.welcome_frame:
            self.welcome_frame.place_forget()