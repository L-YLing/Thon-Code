# libs/gui/git_window.py

import os
import sys
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import tkinter as tk
from typing import Optional, List, Dict, Any

from libs.gui.lazy_loader import LazyLoader
from libs.git_functions import GitFunctions
from libs.license_handle import LicenseHandle


class GitIntegrationWindow:
    """
    Git integration window providing version control operations.
    Supports init, commit, push, pull, branch management, and license management.
    """
    
    def __init__(self, parent, project_root: Optional[str] = None, status_callback=None):
        self.parent = parent
        self.project_root = project_root or os.getcwd()
        self.status_callback = status_callback
        
        if not os.path.exists(self.project_root):
            self.project_root = os.getcwd()
        
        self.git = GitFunctions(self.project_root, self._log_output)
        
        self.license_handle = LicenseHandle()
        
        self.selected_branch = None
        self.selected_file = None
        self.repo_initialized = False
        
        self._create_window()  # This creates self.window
        self.git.parent = self.window  # Now self.window exists
        
        self._check_repo_status()
        self._load_branches()
        self._load_status()
    
    def _create_window(self):
        """Create the Git integration window"""
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("Git Integration")
        self.window.geometry("900x700")
        self.window.transient(self.parent)
        self.window.lift()
        self.window.focus_force()
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create all UI widgets"""
        # Main container
        main_frame = ctk.CTkFrame(self.window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Top info bar
        self._create_info_bar(main_frame)
        
        # Main content area with paned window
        paned = ttk.PanedWindow(main_frame, orient='horizontal')
        paned.pack(fill="both", expand=True, pady=5)
        
        # Left panel - Git operations
        left_frame = ctk.CTkFrame(paned, fg_color="transparent")
        paned.add(left_frame, weight=1)
        self._create_left_panel(left_frame)
        
        # Right panel - Status and output
        right_frame = ctk.CTkFrame(paned, fg_color="transparent")
        paned.add(right_frame, weight=2)
        self._create_right_panel(right_frame)
        
        # Bottom status bar
        self._create_status_bar(main_frame)
    
    def _create_info_bar(self, parent):
        """Create info bar with project path and repo status"""
        info_frame = ctk.CTkFrame(parent)
        info_frame.pack(fill="x", pady=(0, 5))
        
        # Project path with ellipsis if too long
        display_path = self.project_root
        if len(display_path) > 60:
            display_path = "..." + display_path[-57:]
        
        path_label = ctk.CTkLabel(
            info_frame, 
            text=f"Project: {display_path}",
            font=("Microsoft YaHei", 12, "bold")
        )
        path_label.pack(side="left", padx=10)
        
        self.repo_status_label = ctk.CTkLabel(
            info_frame,
            text="🔴 Not a git repository",
            font=("Microsoft YaHei", 12)
        )
        self.repo_status_label.pack(side="right", padx=10)
    
    def _create_left_panel(self, parent):
        """Create left panel with operation buttons and branch management"""
        # Branch management
        branch_frame = ctk.CTkFrame(parent)
        branch_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(branch_frame, text="Branches", font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=10)
        
        self.branch_listbox = tk.Listbox(
            branch_frame,
            height=6,
            bg="#2b2b2b",
            fg="#ffffff",
            selectbackground="#0078D7",
            selectforeground="#ffffff",
            font=("Consolas", 10),
            relief="flat",
            highlightthickness=0
        )
        self.branch_listbox.pack(fill="x", padx=10, pady=5)
        self.branch_listbox.bind("<<ListboxSelect>>", self._on_branch_select)
        
        branch_btn_frame = ctk.CTkFrame(branch_frame, fg_color="transparent")
        branch_btn_frame.pack(fill="x", padx=10)
        
        ctk.CTkButton(branch_btn_frame, text="New Branch", command=self._create_branch, width=80).pack(side="left", padx=2)
        ctk.CTkButton(branch_btn_frame, text="Delete", command=self._delete_branch, width=80).pack(side="left", padx=2)
        ctk.CTkButton(branch_btn_frame, text="Switch", command=self._switch_branch, width=80).pack(side="left", padx=2)
        
        # Git operations
        ops_frame = ctk.CTkFrame(parent)
        ops_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(ops_frame, text="Operations", font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=10)
        
        # Operation buttons grid
        btn_grid = ctk.CTkFrame(ops_frame, fg_color="transparent")
        btn_grid.pack(fill="x", padx=10, pady=5)
        
        operations = [
            ("Init", self._git_init, "#2d7d2d"),
            ("Add All", self._git_add_all, "#2d6b8a"),
            ("Commit", self._git_commit, "#8a6d2d"),
            ("Push", self._git_push, "#2d5a8a"),
            ("Pull", self._git_pull, "#5a2d8a"),
            ("Status", self._load_status, "#2d8a7a"),
            ("Changelog", self._git_changelog, "#6a2d8a"),
        ]
        
        for i, (label, command, color) in enumerate(operations):
            row = i // 3
            col = i % 3
            ctk.CTkButton(
                btn_grid, 
                text=label, 
                command=command,
                width=100,
                fg_color=color,
                hover_color=color
            ).grid(row=row, column=col, padx=2, pady=2, sticky="ew")
        
        btn_grid.grid_columnconfigure(0, weight=1)
        btn_grid.grid_columnconfigure(1, weight=1)
        btn_grid.grid_columnconfigure(2, weight=1)
        
        # License management
        license_frame = ctk.CTkFrame(parent)
        license_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(license_frame, text="License", font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=10)
        
        license_btn_frame = ctk.CTkFrame(license_frame, fg_color="transparent")
        license_btn_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(
            license_btn_frame,
            text="Manage License",
            command=self._manage_license,
            width=150,
            fg_color="#6a2d8a"
        ).pack(side="left", padx=2)
        
        ctk.CTkLabel(
            license_btn_frame,
            text="Apply open-source license to project",
            font=("Microsoft YaHei", 10),
            text_color="gray"
        ).pack(side="left", padx=10)
        
        # Project selector
        project_frame = ctk.CTkFrame(parent)
        project_frame.pack(fill="x", pady=(10, 0))
        
        ctk.CTkLabel(project_frame, text="Project", font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=10)
        
        project_btn_frame = ctk.CTkFrame(project_frame, fg_color="transparent")
        project_btn_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(
            project_btn_frame,
            text="Select Project",
            command=self._select_project,
            width=120,
            fg_color="#2d5a8a"
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            project_btn_frame,
            text="Refresh",
            command=self._refresh_project,
            width=80,
            fg_color="#2d6b8a"
        ).pack(side="left", padx=2)
    
    def _create_right_panel(self, parent):
        """Create right panel with file status and output"""
        # File status
        status_frame = ctk.CTkFrame(parent)
        status_frame.pack(fill="both", expand=True, pady=(0, 5))
        
        ctk.CTkLabel(status_frame, text="File Status", font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=10)
        
        self.file_listbox = tk.Listbox(
            status_frame,
            height=8,
            bg="#2b2b2b",
            fg="#d4d4d4",
            selectbackground="#0078D7",
            selectforeground="#ffffff",
            font=("Consolas", 9),
            relief="flat",
            highlightthickness=0
        )
        self.file_listbox.pack(fill="both", expand=True, padx=10, pady=5)
        self.file_listbox.bind("<<ListboxSelect>>", self._on_file_select)
        
        file_btn_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        file_btn_frame.pack(fill="x", padx=10)
        
        ctk.CTkButton(file_btn_frame, text="Add Selected", command=self._add_selected, width=100).pack(side="left", padx=2)
        ctk.CTkButton(file_btn_frame, text="Discard", command=self._discard_selected, width=100).pack(side="left", padx=2)
        
        # Output log
        log_frame = ctk.CTkFrame(parent)
        log_frame.pack(fill="both", expand=True)
        
        ctk.CTkLabel(log_frame, text="Output", font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=10)
        
        self.output_text = ctk.CTkTextbox(log_frame, height=100)
        self.output_text.pack(fill="both", expand=True, padx=10, pady=5)
    
    def _create_status_bar(self, parent):
        """Create status bar"""
        self.status_bar = ctk.CTkLabel(
            parent,
            text="Ready",
            anchor="w",
            height=25,
            font=("Microsoft YaHei", 10)
        )
        self.status_bar.pack(fill="x", pady=(5, 0))
    
    def _select_project(self):
        """Select a different project directory"""
        path = filedialog.askdirectory(
            title="Select Project Directory",
            initialdir=self.project_root
        )
        if path and os.path.exists(path):
            self.project_root = path
            self.git.project_root = path
            self._refresh_project()
            self._log_output(f"Switched to project: {path}")
    
    def _refresh_project(self):
        """Refresh the current project status"""
        self._check_repo_status()
        self._load_branches()
        self._load_status()
        self._log_output("Project refreshed")
    
    def _check_repo_status(self):
        """Check if current directory is a git repository"""
        self.repo_initialized = self.git.is_repo()
        if self.repo_initialized:
            self.repo_status_label.configure(text="🟢 Git repository detected")
        else:
            self.repo_status_label.configure(text="🔴 Not a git repository")
    
    def _load_branches(self):
        """Load and display branches"""
        self.branch_listbox.delete(0, tk.END)
        
        if not self.repo_initialized:
            self.branch_listbox.insert(tk.END, "Initialize git first")
            return
        
        branches = self.git.get_branches()
        current = self.git.get_current_branch()
        
        if not branches:
            self.branch_listbox.insert(tk.END, "No branches found")
            return
        
        for branch in branches:
            if branch == current:
                self.branch_listbox.insert(tk.END, f"* {branch}")
            else:
                self.branch_listbox.insert(tk.END, f"  {branch}")
    
    def _load_status(self):
        """Load and display git status"""
        self.file_listbox.delete(0, tk.END)
        
        if not self.repo_initialized:
            self.file_listbox.insert(tk.END, "Initialize git first")
            return
        
        status = self.git.get_status()
        if not status:
            self.file_listbox.insert(tk.END, "Working tree clean")
            return
        
        for line in status.splitlines():
            if line.strip():
                self.file_listbox.insert(tk.END, line)
    
    def _on_branch_select(self, event):
        """Handle branch selection"""
        selection = self.branch_listbox.curselection()
        if selection:
            branch_text = self.branch_listbox.get(selection[0])
            self.selected_branch = branch_text.lstrip('* ')
    
    def _on_file_select(self, event):
        """Handle file selection"""
        selection = self.file_listbox.curselection()
        if selection:
            self.selected_file = self.file_listbox.get(selection[0])
    
    def _git_init(self):
        """Initialize git repository"""
        if self.repo_initialized:
            messagebox.showinfo("Info", "Repository already initialized")
            return
        
        if self.git.init():
            self.repo_initialized = True
            self.repo_status_label.configure(text="🟢 Git repository detected")
            self._log_output("Git initialized successfully")
            self._load_branches()
            self._load_status()
        else:
            self._log_output("Failed to initialize git")
            messagebox.showerror("Error", "Failed to initialize git repository")
    
    def _git_add_all(self):
        """Add all files to git"""
        if not self.repo_initialized:
            messagebox.showwarning("Warning", "Initialize git first")
            return
        
        if self.git.add_all():
            self._log_output("All files added to staging")
            self._load_status()
        else:
            self._log_output("Failed to add files")
            messagebox.showerror("Error", "Failed to add files")
    
    def _add_selected(self):
        """Add selected file to git"""
        if not self.selected_file:
            messagebox.showinfo("Info", "Select a file first")
            return
        
        if not self.repo_initialized:
            messagebox.showwarning("Warning", "Initialize git first")
            return
        
        if self.git.add_file(self.selected_file):
            self._log_output(f"Added: {self.selected_file}")
            self._load_status()
        else:
            self._log_output(f"Failed to add: {self.selected_file}")
    
    def _git_commit(self):
        """Commit changes"""
        if not self.repo_initialized:
            messagebox.showwarning("Warning", "Initialize git first")
            return
        
        dialog = ctk.CTkInputDialog(text="Enter commit message:", title="Commit")
        message = dialog.get_input()
        if not message:
            return
        
        if self.git.commit(message):
            self._log_output(f"Committed: {message}")
            self._load_status()
        else:
            self._log_output("Commit failed")
            messagebox.showerror("Error", "Commit failed")
    
    def _git_push(self):
        """Push to remote"""
        if not self.repo_initialized:
            messagebox.showwarning("Warning", "Initialize git first")
            return
        
        if self.git.push():
            self._log_output("Push successful")
        else:
            self._log_output("Push failed")
            messagebox.showerror("Error", "Push failed")
    
    def _git_pull(self):
        """Pull from remote"""
        if not self.repo_initialized:
            messagebox.showwarning("Warning", "Initialize git first")
            return
        
        if self.git.pull():
            self._log_output("Pull successful")
            self._load_status()
        else:
            self._log_output("Pull failed")
            messagebox.showerror("Error", "Pull failed")
    
    def _create_branch(self):
        """Create a new branch"""
        if not self.repo_initialized:
            messagebox.showwarning("Warning", "Initialize git first")
            return
        
        dialog = ctk.CTkInputDialog(text="Enter new branch name:", title="New Branch")
        branch_name = dialog.get_input()
        if not branch_name:
            return
        
        if self.git.create_branch(branch_name):
            self._log_output(f"Branch created: {branch_name}")
            self._load_branches()
        else:
            self._log_output(f"Failed to create branch: {branch_name}")
            messagebox.showerror("Error", f"Failed to create branch: {branch_name}")
    
    def _delete_branch(self):
        """Delete selected branch"""
        if not self.selected_branch:
            messagebox.showinfo("Info", "Select a branch first")
            return
        
        if not messagebox.askyesno("Confirm", f"Delete branch '{self.selected_branch}'?"):
            return
        
        if self.git.delete_branch(self.selected_branch):
            self._log_output(f"Branch deleted: {self.selected_branch}")
            self._load_branches()
        else:
            self._log_output(f"Failed to delete branch: {self.selected_branch}")
    
    def _switch_branch(self):
        """Switch to selected branch"""
        if not self.selected_branch:
            messagebox.showinfo("Info", "Select a branch first")
            return
        
        if self.git.switch_branch(self.selected_branch):
            self._log_output(f"Switched to: {self.selected_branch}")
            self._load_branches()
            self._load_status()
        else:
            self._log_output(f"Failed to switch to: {self.selected_branch}")
    
    def _discard_selected(self):
        """Discard changes to selected file"""
        if not self.selected_file:
            messagebox.showinfo("Info", "Select a file first")
            return
        
        if not messagebox.askyesno("Confirm", f"Discard changes to '{self.selected_file}'?"):
            return
        
        if self.git.discard_file(self.selected_file):
            self._log_output(f"Discarded: {self.selected_file}")
            self._load_status()
        else:
            self._log_output(f"Failed to discard: {self.selected_file}")
    
    def _manage_license(self):
        """Open license manager window"""
        LicenseManagerWindow = LazyLoader.get('libs.gui.license_ui', 'LicenseManagerWindow')
        LicenseManagerWindow(
            self.window,
            project_root=self.project_root,
            status_callback=self._log_output
        )
    
    def _git_changelog(self):
        """Open changelog manager"""
        self.git.manage_changelog()
    
    def _log_output(self, message: str):
        """Log output to the output text widget"""
        self.output_text.insert("end", f"{message}\n")
        self.output_text.see("end")
        if self.status_callback:
            self.status_callback(message)