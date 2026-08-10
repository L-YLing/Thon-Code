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
        """Create all welcome page UI components including recent projects."""
        style = ttk.Style()
        style.configure("Recent.TButton", borderwidth=0, relief="flat", padding=2)

        card = ttk.Frame(self.welcome_frame)
        card.place(relx=0.5, rely=0.4, anchor="center")

        title = ttk.Label(card, text=self._get_text("welcome.app_title"), font=("Microsoft YaHei", 28, "bold"))
        title.pack(pady=(30, 10))

        subtitle = ttk.Label(card, text=self._get_text("welcome.subtitle"), font=("Microsoft YaHei", 14))
        subtitle.pack(pady=(0, 20))

        btn_frame = ttk.Frame(card)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text=self._get_text("welcome.new_file"), command=self.new_file_callback).pack(side="left", padx=10)
        ttk.Button(btn_frame, text=self._get_text("welcome.open_file"), command=self.open_file_callback).pack(side="left", padx=10)
        ttk.Button(btn_frame, text=self._get_text("welcome.open_folder"), command=self.open_folder_callback).pack(side="left", padx=10)

        recent_label = ttk.Label(card, text=self._get_text("welcome.recent"), font=("Microsoft YaHei", 12), anchor="w")
        recent_label.pack(pady=(20, 5), padx=20, anchor="w")

        recent_projects = cfg_handle.cfg_handle().get_recent_projects()
        if recent_projects:
            for proj in recent_projects[:5]:
                btn = ttk.Button(card, text=os.path.basename(proj),
                                 command=lambda path=proj: self.open_recent_callback(path),
                                 style="Recent.TButton")
                btn.pack(pady=2, padx=20, anchor="w")
        else:
            no_recent = ttk.Label(card, text=self._get_text("welcome.no_recent"), font=("Microsoft YaHei", 10))
            no_recent.pack(pady=5, padx=20, anchor="w")

        config_frame = ttk.Frame(card)
        config_frame.pack(pady=(20, 30))

        self.welcome_show_check = ttk.Checkbutton(config_frame, text=self._get_text("welcome.show_on_start"),
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