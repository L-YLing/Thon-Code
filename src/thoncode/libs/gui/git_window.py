#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Git Window",
    "Path": ".main.libs.gui.git_window",
    "Entrance": "main.py"
}

import os
import sys
import ttkbootstrap as ttkb
from tkinter import ttk, messagebox, filedialog, simpledialog
import tkinter as tk
from typing import Optional, List, Dict, Any

from libs.gui.lazy_loader import LazyLoader
from libs.gui import theme
from libs.git_functions import GitFunctions
from libs.license_handle import LicenseHandle
import libs.langs_loader as langs_loader


class GitIntegrationWindow:
    """
    Git integration window providing version control operations.
    Supports init, commit, push, pull, branch management, and license management.
    """

    def __init__(self, parent, project_root: Optional[str] = None, status_callback=None):
        self.parent = parent
        self.project_root = project_root or os.getcwd()
        self.status_callback = status_callback

        self.lang = langs_loader.langs()

        if not os.path.exists(self.project_root):
            self.project_root = os.getcwd()

        self.git = GitFunctions(self.project_root, self._log_output)

        self.license_handle = LicenseHandle()

        self.selected_branch = None
        self.selected_file = None
        self.repo_initialized = False

        self._create_window()
        self.git.parent = self.window

        self._check_repo_status()
        self._load_branches()
        self._load_status()

    def _get_text(self, key):
        return getattr(self.lang, key.replace('.', '_'), key)

    def _create_window(self):
        self.window = ttkb.Toplevel(self.parent)
        self.window.title(self._get_text("git.title"))
        self.window.geometry("900x700")
        self.window.transient(self.parent)
        self.window.lift()
        self.window.focus_force()

        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._create_info_bar(main_frame)

        paned = ttk.PanedWindow(main_frame, orient='horizontal')
        paned.pack(fill="both", expand=True, pady=5)

        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        self._create_left_panel(left_frame)

        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        self._create_right_panel(right_frame)

        self._create_status_bar(main_frame)

    def _create_info_bar(self, parent):
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill="x", pady=(0, 5))

        display_path = self.project_root
        if len(display_path) > 60:
            display_path = "..." + display_path[-57:]

        path_label = ttk.Label(
            info_frame,
            text=self._get_text("git.project") + f" {display_path}",
            font=("Microsoft YaHei", 12, "bold")
        )
        path_label.pack(side="left", padx=10)

        self.repo_status_label = ttk.Label(
            info_frame,
            text=f"🔴 {self._get_text('git.not_repo')}",
            font=("Microsoft YaHei", 12)
        )
        self.repo_status_label.pack(side="right", padx=10)

    def _create_left_panel(self, parent):
        branch_frame = ttk.Frame(parent)
        branch_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(branch_frame, text=self._get_text("git.branches"), font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=10)

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

        branch_btn_frame = ttk.Frame(branch_frame)
        branch_btn_frame.pack(fill="x", padx=10)

        ttk.Button(branch_btn_frame, text=self._get_text("git.new_branch"), command=self._create_branch).pack(side="left", padx=2)
        ttk.Button(branch_btn_frame, text=self._get_text("git.delete"), command=self._delete_branch).pack(side="left", padx=2)
        ttk.Button(branch_btn_frame, text=self._get_text("git.switch"), command=self._switch_branch).pack(side="left", padx=2)

        ops_frame = ttk.Frame(parent)
        ops_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(ops_frame, text=self._get_text("git.operations"), font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=10)

        btn_grid = ttk.Frame(ops_frame)
        btn_grid.pack(fill="x", padx=10, pady=5)

        operations = [
            (self._get_text("git.init"), self._git_init),
            (self._get_text("git.add_all"), self._git_add_all),
            (self._get_text("git.commit"), self._git_commit),
            (self._get_text("git.push"), self._git_push),
            (self._get_text("git.pull"), self._git_pull),
            (self._get_text("git.status"), self._load_status),
            (self._get_text("git.changelog"), self._git_changelog),
        ]

        for i, (label, command) in enumerate(operations):
            row = i // 3
            col = i % 3
            ttk.Button(
                btn_grid,
                text=label,
                command=command,
            ).grid(row=row, column=col, padx=2, pady=2, sticky="ew")

        btn_grid.grid_columnconfigure(0, weight=1)
        btn_grid.grid_columnconfigure(1, weight=1)
        btn_grid.grid_columnconfigure(2, weight=1)

        license_frame = ttk.Frame(parent)
        license_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(license_frame, text=self._get_text("git.license"), font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=10)

        license_btn_frame = ttk.Frame(license_frame)
        license_btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            license_btn_frame,
            text=self._get_text("git.manage_license"),
            command=self._manage_license,
        ).pack(side="left", padx=2)

        ttk.Label(
            license_btn_frame,
            text=self._get_text("git.apply_license"),
            font=("Microsoft YaHei", 10),
        ).pack(side="left", padx=10)

        project_frame = ttk.Frame(parent)
        project_frame.pack(fill="x", pady=(10, 0))

        ttk.Label(project_frame, text=self._get_text("git.project_select"), font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=10)

        project_btn_frame = ttk.Frame(project_frame)
        project_btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            project_btn_frame,
            text=self._get_text("git.select_project"),
            command=self._select_project,
        ).pack(side="left", padx=2)

        ttk.Button(
            project_btn_frame,
            text=self._get_text("struct.refresh"),
            command=self._refresh_project,
        ).pack(side="left", padx=2)

    def _create_right_panel(self, parent):
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill="both", expand=True, pady=(0, 5))

        ttk.Label(status_frame, text=self._get_text("git.file_status"), font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=10)

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

        file_btn_frame = ttk.Frame(status_frame)
        file_btn_frame.pack(fill="x", padx=10)

        ttk.Button(file_btn_frame, text=self._get_text("git.add_selected"), command=self._add_selected).pack(side="left", padx=2)
        ttk.Button(file_btn_frame, text=self._get_text("git.discard"), command=self._discard_selected).pack(side="left", padx=2)

        log_frame = ttk.Frame(parent)
        log_frame.pack(fill="both", expand=True)

        ttk.Label(log_frame, text=self._get_text("git.output"), font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=10)

        colors = theme.get_colors()
        self.output_text = tk.Text(
            log_frame,
            height=100,
            bg=colors["bg"],
            fg=colors["fg"],
            relief="flat",
            borderwidth=0,
            highlightthickness=0
        )
        self.output_text.pack(fill="both", expand=True, padx=10, pady=5)

    def _create_status_bar(self, parent):
        self.status_bar = ttk.Label(
            parent,
            text=self._get_text("git.ready"),
            anchor="w",
            font=("Microsoft YaHei", 10)
        )
        self.status_bar.pack(fill="x", pady=(5, 0))

    def _select_project(self):
        path = filedialog.askdirectory(
            title=self._get_text("git.select_project_dir"),
            initialdir=self.project_root
        )
        if path and os.path.exists(path):
            self.project_root = path
            self.git.project_root = path
            self._refresh_project()
            self._log_output(self._get_text("git.switched_project") + f": {path}")

    def _refresh_project(self):
        self._check_repo_status()
        self._load_branches()
        self._load_status()
        self._log_output(self._get_text("git.project_refreshed"))

    def _check_repo_status(self):
        self.repo_initialized = self.git.is_repo()
        if self.repo_initialized:
            self.repo_status_label.configure(text=f"🟢 {self._get_text('git.is_repo')}")
        else:
            self.repo_status_label.configure(text=f"🔴 {self._get_text('git.not_repo')}")

    def _load_branches(self):
        self.branch_listbox.delete(0, tk.END)

        if not self.repo_initialized:
            self.branch_listbox.insert(tk.END, self._get_text("git.init_first"))
            return

        branches = self.git.get_branches()
        current = self.git.get_current_branch()

        if not branches:
            self.branch_listbox.insert(tk.END, self._get_text("git.no_branches"))
            return

        for branch in branches:
            if branch == current:
                self.branch_listbox.insert(tk.END, f"* {branch}")
            else:
                self.branch_listbox.insert(tk.END, f"  {branch}")

    def _load_status(self):
        self.file_listbox.delete(0, tk.END)

        if not self.repo_initialized:
            self.file_listbox.insert(tk.END, self._get_text("git.init_first"))
            return

        status = self.git.get_status()
        if not status:
            self.file_listbox.insert(tk.END, self._get_text("git.working_tree_clean"))
            return

        for line in status.splitlines():
            if line.strip():
                self.file_listbox.insert(tk.END, line)

    def _on_branch_select(self, event):
        selection = self.branch_listbox.curselection()
        if selection:
            branch_text = self.branch_listbox.get(selection[0])
            self.selected_branch = branch_text.lstrip('* ')

    def _on_file_select(self, event):
        selection = self.file_listbox.curselection()
        if selection:
            self.selected_file = self.file_listbox.get(selection[0])

    def _git_init(self):
        if self.repo_initialized:
            messagebox.showinfo(self._get_text("git.info"), self._get_text("git.repo_already_init"))
            return

        if self.git.init():
            self.repo_initialized = True
            self.repo_status_label.configure(text=f"🟢 {self._get_text('git.is_repo')}")
            self._log_output(self._get_text("git.init_success"))
            self._load_branches()
            self._load_status()
        else:
            self._log_output(self._get_text("git.failed_init"))
            messagebox.showerror(self._get_text("settings.error_title"), self._get_text("git.failed_init_repo"))

    def _git_add_all(self):
        if not self.repo_initialized:
            messagebox.showwarning(self._get_text("git.warning"), self._get_text("git.init_first"))
            return

        if self.git.add_all():
            self._log_output(self._get_text("git.all_added_staging"))
            self._load_status()
        else:
            self._log_output(self._get_text("git.failed_add_files"))
            messagebox.showerror(self._get_text("settings.error_title"), self._get_text("git.failed_add_files"))

    def _add_selected(self):
        if not self.selected_file:
            messagebox.showinfo(self._get_text("git.info"), self._get_text("git.select_file_first"))
            return

        if not self.repo_initialized:
            messagebox.showwarning(self._get_text("git.warning"), self._get_text("git.init_first"))
            return

        if self.git.add_file(self.selected_file):
            self._log_output(self._get_text("git.added_file") + f": {self.selected_file}")
            self._load_status()
        else:
            self._log_output(self._get_text("git.failed_add_file") + f": {self.selected_file}")

    def _git_commit(self):
        if not self.repo_initialized:
            messagebox.showwarning(self._get_text("git.warning"), self._get_text("git.init_first"))
            return

        message = simpledialog.askstring(self._get_text("git.commit"), self._get_text("git.enter_commit_msg"))
        if not message:
            return

        if self.git.commit(message):
            self._log_output(self._get_text("git.committed") + f": {message}")
            self._load_status()
        else:
            self._log_output(self._get_text("git.failed_commit"))
            messagebox.showerror(self._get_text("settings.error_title"), self._get_text("git.failed_commit"))

    def _git_push(self):
        if not self.repo_initialized:
            messagebox.showwarning(self._get_text("git.warning"), self._get_text("git.init_first"))
            return

        if self.git.push():
            self._log_output(self._get_text("git.push_success"))
        else:
            self._log_output(self._get_text("git.failed_push"))
            messagebox.showerror(self._get_text("settings.error_title"), self._get_text("git.failed_push"))

    def _git_pull(self):
        if not self.repo_initialized:
            messagebox.showwarning(self._get_text("git.warning"), self._get_text("git.init_first"))
            return

        if self.git.pull():
            self._log_output(self._get_text("git.pull_success"))
            self._load_status()
        else:
            self._log_output(self._get_text("git.failed_pull"))
            messagebox.showerror(self._get_text("settings.error_title"), self._get_text("git.failed_pull"))

    def _create_branch(self):
        if not self.repo_initialized:
            messagebox.showwarning(self._get_text("git.warning"), self._get_text("git.init_first"))
            return

        branch_name = simpledialog.askstring(self._get_text("git.new_branch"), self._get_text("git.enter_branch_name"))
        if not branch_name:
            return

        if self.git.create_branch(branch_name):
            self._log_output(self._get_text("git.branch_created") + f": {branch_name}")
            self._load_branches()
        else:
            self._log_output(self._get_text("git.failed_create_branch") + f": {branch_name}")
            messagebox.showerror(self._get_text("settings.error_title"), self._get_text("git.failed_create_branch") + f": {branch_name}")

    def _delete_branch(self):
        if not self.selected_branch:
            messagebox.showinfo(self._get_text("git.info"), self._get_text("git.select_branch_first"))
            return

        if not messagebox.askyesno(self._get_text("git.confirm"), self._get_text("git.delete_branch_confirm").format(branch=self.selected_branch)):
            return

        if self.git.delete_branch(self.selected_branch):
            self._log_output(self._get_text("git.branch_deleted") + f": {self.selected_branch}")
            self._load_branches()
        else:
            self._log_output(self._get_text("git.failed_delete_branch") + f": {self.selected_branch}")

    def _switch_branch(self):
        if not self.selected_branch:
            messagebox.showinfo(self._get_text("git.info"), self._get_text("git.select_branch_first"))
            return

        if self.git.switch_branch(self.selected_branch):
            self._log_output(self._get_text("git.switched_to") + f": {self.selected_branch}")
            self._load_branches()
            self._load_status()
        else:
            self._log_output(self._get_text("git.failed_switch") + f": {self.selected_branch}")

    def _discard_selected(self):
        if not self.selected_file:
            messagebox.showinfo(self._get_text("git.info"), self._get_text("git.select_file_first"))
            return

        if not messagebox.askyesno(self._get_text("git.confirm"), self._get_text("git.discard_confirm").format(file=self.selected_file)):
            return

        if self.git.discard_file(self.selected_file):
            self._log_output(self._get_text("git.discarded") + f": {self.selected_file}")
            self._load_status()
        else:
            self._log_output(self._get_text("git.failed_discard") + f": {self.selected_file}")

    def _manage_license(self):
        LicenseManagerWindow = LazyLoader.get('libs.gui.license_ui', 'LicenseManagerWindow')
        LicenseManagerWindow(
            self.window,
            project_root=self.project_root,
            status_callback=self._log_output
        )

    def _git_changelog(self):
        self.git.manage_changelog()

    def _log_output(self, message: str):
        self.output_text.insert("end", f"{message}\n")
        self.output_text.see("end")
        if self.status_callback:
            self.status_callback(message)