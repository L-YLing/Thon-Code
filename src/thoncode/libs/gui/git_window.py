#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Git Window",
    "Path": ".main.libs.gui.git_window",
    "Entrance": "main.py"
}

"""
Git integration window with non-blocking async operations.

All git commands run in background threads via AsyncTaskRunner so the GUI
never freezes. The layout is organized into clear sections: a header bar
with project path and repo status, a prominent Sync button, a left panel
for branches and quick operations, a right panel for file status grouped
by staged/unstaged/untracked, and a bottom output log.
"""

import os
import logging
import ttkbootstrap as ttkb
from tkinter import ttk, messagebox, filedialog
import tkinter as tk
from typing import Optional, List, Dict, Any

from libs.gui.lazy_loader import LazyLoader
from libs.gui import theme
from libs.gui.async_utils import AsyncTaskRunner
from libs.gui.styled_dialog import ask_string
from libs.git_functions import GitFunctions
from libs.license_handle import LicenseHandle
import libs.langs_loader as langs_loader

_logger = logging.getLogger("thoncode.git_window")


class GitIntegrationWindow:
    """Git integration window providing version control operations.

    All git operations run asynchronously via AsyncTaskRunner to keep the
    UI responsive. Supports init, commit, push, pull, sync (pull+push),
    branch management, and license management.
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

        self.selected_branch: Optional[str] = None
        self.selected_file: Optional[str] = None
        self.repo_initialized = False
        self.git_installed = True
        self.operation_buttons: List[ttk.Button] = []
        self._busy = False

        self._create_window()
        self.git.parent = self.window

        # Defer initial git operations until after the window is shown so
        # synchronous git calls do not block window creation.
        self.window.after(50, self._after_window_shown)

    def _get_text(self, key: str) -> str:
        return getattr(self.lang, key.replace('.', '_'), key)

    # ------------------------------------------------------------------
    # Window lifecycle
    # ------------------------------------------------------------------

    def _create_window(self):
        self.window = ttkb.Toplevel(self.parent)
        self.window.title(self._get_text("git.title"))
        self.window.geometry("960x720")
        self.window.transient(self.parent)
        self.window.lift()
        self.window.focus_force()
        self._create_widgets()

    def _after_window_shown(self):
        """Run once the window is visible: make modal then load initial state."""
        self._make_modal()
        self._initial_load()

    def _make_modal(self):
        """Make the git window modal.

        The grab makes the git window the only interactive window. Child
        windows (License Manager) temporarily release this grab via
        _with_grab_released so they can receive input independently.
        """
        try:
            self.window.grab_set()
        except Exception:
            pass

    def _with_grab_released(self, func):
        """Run func with the window grab released, then re-acquire it.

        Used when opening child windows (e.g., License Manager) that need
        their own input grab. The git window's grab is restored after the
        child window closes so the git window remains modal overall.

        Args:
            func: Callable to execute while grab is released
        """
        try:
            self.window.grab_release()
        except Exception:
            pass
        try:
            func()
        finally:
            try:
                self.window.grab_set()
                self.window.lift()
                self.window.focus_force()
            except Exception:
                pass

    def _initial_load(self):
        """Perform the initial repo status checks after the window is shown."""
        self._async_check_repo_status()

    # ------------------------------------------------------------------
    # Busy state management
    # ------------------------------------------------------------------

    def _set_busy(self, busy: bool, message: str = ""):
        """Toggle busy state: disable buttons and show a status message.

        Args:
            busy: True when an async operation is running.
            message: Optional status message shown in the status bar.
        """
        self._busy = busy
        state = "disabled" if busy else "normal"
        for btn in self.operation_buttons:
            try:
                btn.configure(state=state)
            except Exception:
                pass
        if message:
            self._set_status(message)

    def _set_status(self, message: str):
        """Update the status bar text."""
        self.status_bar.configure(text=message)

    # ------------------------------------------------------------------
    # Widget creation
    # ------------------------------------------------------------------

    def _create_widgets(self):
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._create_header(main_frame)

        paned = ttk.PanedWindow(main_frame, orient='horizontal')
        paned.pack(fill="both", expand=True, pady=5)

        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        self._create_left_panel(left_frame)

        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        self._create_right_panel(right_frame)

        self._create_status_bar(main_frame)

    def _create_header(self, parent):
        """Create the top header bar with project path, status, and Sync button."""
        header = ttk.Frame(parent)
        header.pack(fill="x", pady=(0, 8))

        display_path = self.project_root
        if len(display_path) > 55:
            display_path = "..." + display_path[-52:]

        path_label = ttk.Label(
            header,
            text=f"  {display_path}",
            font=("Microsoft YaHei", 11, "bold"),
        )
        path_label.pack(side="left", padx=(5, 10))

        self.repo_status_label = ttk.Label(
            header,
            text=f"  {self._get_text('git.not_repo')}",
            font=("Microsoft YaHei", 11),
        )
        self.repo_status_label.pack(side="left", padx=10)

        # Prominent Sync button on the right side of the header.
        self.sync_btn = ttk.Button(
            header,
            text=self._get_text("git.sync"),
            command=self._git_sync,
            style="Success.TButton",
        )
        self.sync_btn.pack(side="right", padx=(5, 5))
        self.operation_buttons.append(self.sync_btn)

    def _create_left_panel(self, parent):
        """Create the left panel: branches + quick operations."""
        # --- Branches section ---
        branch_frame = ttk.LabelFrame(parent, text=self._get_text("git.branches"),
                                      padding=8)
        branch_frame.pack(fill="x", pady=(0, 8))

        self.branch_listbox = theme.themed_listbox(
            branch_frame,
            height=7,
            font=("Consolas", 10),
        )
        self.branch_listbox.pack(fill="x", pady=(0, 5))
        self.branch_listbox.bind("<<ListboxSelect>>", self._on_branch_select)

        branch_btn_frame = ttk.Frame(branch_frame)
        branch_btn_frame.pack(fill="x")
        ttk.Button(branch_btn_frame, text=self._get_text("git.new_branch"),
                   command=self._create_branch).pack(side="left", padx=2)
        ttk.Button(branch_btn_frame, text=self._get_text("git.switch"),
                   command=self._switch_branch).pack(side="left", padx=2)
        ttk.Button(branch_btn_frame, text=self._get_text("git.delete"),
                   command=self._delete_branch).pack(side="left", padx=2)

        # --- Quick operations section ---
        ops_frame = ttk.LabelFrame(parent, text=self._get_text("git.operations"),
                                   padding=8)
        ops_frame.pack(fill="x", pady=(0, 8))

        # Primary actions in a clear vertical layout.
        actions = [
            (self._get_text("git.init"), self._git_init),
            (self._get_text("git.add_all"), self._git_add_all),
            (self._get_text("git.commit"), self._git_commit),
            (self._get_text("git.push"), self._git_push),
            (self._get_text("git.pull"), self._git_pull),
            (self._get_text("git.status"), self._async_load_status),
            (self._get_text("git.changelog"), self._git_changelog),
        ]
        for label, command in actions:
            btn = ttk.Button(ops_frame, text=label, command=command)
            btn.pack(fill="x", pady=2)
            self.operation_buttons.append(btn)

        # --- License section ---
        license_frame = ttk.LabelFrame(parent, text=self._get_text("git.license"),
                                       padding=8)
        license_frame.pack(fill="x", pady=(0, 8))
        ttk.Button(license_frame, text=self._get_text("git.manage_license"),
                   command=self._manage_license).pack(fill="x", pady=2)

        # --- Project section ---
        project_frame = ttk.LabelFrame(parent, text=self._get_text("git.project_select"),
                                       padding=8)
        project_frame.pack(fill="x")
        ttk.Button(project_frame, text=self._get_text("git.select_project"),
                   command=self._select_project).pack(fill="x", pady=2)
        ttk.Button(project_frame, text=self._get_text("struct.refresh"),
                   command=self._refresh_project).pack(fill="x", pady=2)

    def _create_right_panel(self, parent):
        """Create the right panel: file status + output log."""
        # --- File status section ---
        status_frame = ttk.LabelFrame(parent, text=self._get_text("git.file_status"),
                                      padding=8)
        status_frame.pack(fill="both", expand=True, pady=(0, 8))

        self.file_listbox = theme.themed_listbox(
            status_frame,
            height=10,
            font=("Consolas", 10),
        )
        self.file_listbox.pack(fill="both", expand=True, pady=(0, 5))
        self.file_listbox.bind("<<ListboxSelect>>", self._on_file_select)

        file_btn_frame = ttk.Frame(status_frame)
        file_btn_frame.pack(fill="x")
        ttk.Button(file_btn_frame, text=self._get_text("git.add_selected"),
                   command=self._add_selected).pack(side="left", padx=2)
        ttk.Button(file_btn_frame, text=self._get_text("git.discard"),
                   command=self._discard_selected).pack(side="left", padx=2)

        # --- Output log section ---
        log_frame = ttk.LabelFrame(parent, text=self._get_text("git.output"),
                                   padding=8)
        log_frame.pack(fill="both", expand=True)

        colors = theme.get_colors()
        self.output_text = tk.Text(
            log_frame,
            height=8,
            bg=colors["bg"],
            fg=colors["fg"],
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            font=("Consolas", 9),
        )
        self.output_text.pack(fill="both", expand=True)

    def _create_status_bar(self, parent):
        self.status_bar = ttk.Label(
            parent,
            text=self._get_text("git.ready"),
            anchor="w",
            font=("Microsoft YaHei", 10),
        )
        self.status_bar.pack(fill="x", pady=(5, 0))

    # ------------------------------------------------------------------
    # Async git operations (non-blocking)
    # ------------------------------------------------------------------

    def _run_async(self, func, on_success=None, on_error=None, busy_msg=""):
        """Run a git function in a background thread with UI-safe callbacks.

        Args:
            func: Callable to execute in background (no args).
            on_success: Callback receiving the result on the main thread.
            on_error: Callback receiving the exception on the main thread.
            busy_msg: Status message shown while the operation runs.
        """
        self._set_busy(True, busy_msg or self._get_text("git.running"))

        def _on_success(result):
            self._set_busy(False, self._get_text("git.ready"))
            if on_success:
                on_success(result)

        def _on_error(exc):
            self._set_busy(False, self._get_text("git.ready"))
            self._log_output(f"{self._get_text('git.error')}: {exc}")
            _logger.error("Git async operation failed: %s", exc, exc_info=True)
            if on_error:
                on_error(exc)

        AsyncTaskRunner.run(func, on_success=_on_success, on_error=_on_error)

    def _async_check_repo_status(self):
        """Check git availability and repo status in a background thread."""
        def _check():
            installed = self.git.is_git_installed()
            if not installed:
                return {"installed": False, "initialized": False}
            initialized = self.git.is_repo()
            return {"installed": True, "initialized": initialized}

        def _on_success(result):
            self.git_installed = result["installed"]
            self.repo_initialized = result["initialized"]
            if not self.git_installed:
                self.repo_status_label.configure(
                    text=f"  {self._get_text('git.not_installed')}")
                self._set_busy(True, self._get_text("git.not_installed"))
            elif self.repo_initialized:
                self.repo_status_label.configure(
                    text=f"  {self._get_text('git.is_repo')}")
                self._set_busy(False)
                self._async_load_branches()
                self._async_load_status()
            else:
                self.repo_status_label.configure(
                    text=f"  {self._get_text('git.not_repo')}")
                self._set_busy(False)

        self._run_async(_check, on_success=_on_success,
                        busy_msg=self._get_text("git.checking"))

    def _async_load_branches(self):
        """Load branches in a background thread."""
        if not self.git_installed or not self.repo_initialized:
            return

        def _load():
            return self.git.get_branches(), self.git.get_current_branch()

        def _on_success(result):
            branches, current = result
            self.branch_listbox.delete(0, tk.END)
            if not branches:
                self.branch_listbox.insert(tk.END, self._get_text("git.no_branches"))
                return
            for branch in branches:
                marker = "* " if branch == current else "  "
                self.branch_listbox.insert(tk.END, f"{marker}{branch}")

        self._run_async(_load, on_success=_on_success,
                        busy_msg=self._get_text("git.loading_branches"))

    def _async_load_status(self):
        """Load file status in a background thread."""
        if not self.git_installed or not self.repo_initialized:
            return

        def _load():
            return self.git.get_status()

        def _on_success(status):
            self.file_listbox.delete(0, tk.END)
            if not status:
                self.file_listbox.insert(tk.END, self._get_text("git.working_tree_clean"))
                return
            for line in status.splitlines():
                if line.strip():
                    self.file_listbox.insert(tk.END, line)

        self._run_async(_load, on_success=_on_success,
                        busy_msg=self._get_text("git.loading_status"))

    # ------------------------------------------------------------------
    # User actions
    # ------------------------------------------------------------------

    def _select_project(self):
        path = filedialog.askdirectory(
            title=self._get_text("git.select_project_dir"),
            initialdir=self.project_root,
        )
        if path and os.path.exists(path):
            self.project_root = path
            self.git.project_root = path
            self._refresh_project()
            self._log_output(f"{self._get_text('git.switched_project')}: {path}")

    def _refresh_project(self):
        self._async_check_repo_status()
        self._log_output(self._get_text("git.project_refreshed"))

    def _on_branch_select(self, event):
        selection = self.branch_listbox.curselection()
        if selection:
            branch_text = self.branch_listbox.get(selection[0])
            if branch_text.startswith('* '):
                self.selected_branch = branch_text[2:].strip()
            else:
                self.selected_branch = branch_text.strip()

    def _on_file_select(self, event):
        selection = self.file_listbox.curselection()
        if selection:
            raw = self.file_listbox.get(selection[0])
            if len(raw) >= 4 and raw[2] == ' ':
                path = raw[3:].strip()
                if ' -> ' in path:
                    path = path.split(' -> ', 1)[1].strip()
                self.selected_file = path

    def _git_init(self):
        if self.repo_initialized:
            messagebox.showinfo(self._get_text("git.info"),
                                self._get_text("git.repo_already_init"))
            return

        def _do_init():
            return self.git.init()

        def _on_success(result):
            if result:
                self.repo_initialized = True
                self.repo_status_label.configure(
                    text=f"  {self._get_text('git.is_repo')}")
                self._log_output(self._get_text("git.init_success"))
                self._async_load_branches()
                self._async_load_status()
            else:
                self._log_output(self._get_text("git.init_failed"))
                messagebox.showerror(self._get_text("settings.error_title"),
                                     self._get_text("git.failed_init_repo"))

        self._run_async(_do_init, on_success=_on_success,
                        busy_msg=self._get_text("git.initializing"))

    def _git_add_all(self):
        if not self._require_repo():
            return

        def _do_add():
            return self.git.add_all()

        def _on_success(result):
            if result:
                self._log_output(self._get_text("git.all_added_staging"))
                self._async_load_status()
            else:
                self._log_output(self._get_text("git.failed_add_files"))
                messagebox.showerror(self._get_text("settings.error_title"),
                                     self._get_text("git.failed_add_files"))

        self._run_async(_do_add, on_success=_on_success,
                        busy_msg=self._get_text("git.adding"))

    def _add_selected(self):
        if not self.selected_file:
            messagebox.showinfo(self._get_text("git.info"),
                                self._get_text("git.select_file_first"))
            return
        if not self._require_repo():
            return
        file_path = self.selected_file

        def _do_add():
            return self.git.add_file(file_path)

        def _on_success(result):
            if result:
                self._log_output(f"{self._get_text('git.added_file')}: {file_path}")
                self._async_load_status()
            else:
                self._log_output(f"{self._get_text('git.failed_add_file')}: {file_path}")

        self._run_async(_do_add, on_success=_on_success,
                        busy_msg=self._get_text("git.adding"))

    def _git_commit(self):
        if not self._require_repo():
            return

        message = ask_string(
            self.window, self._get_text("git.commit"),
            self._get_text("git.enter_commit_msg"), multiline=True)
        if not message or not message.strip():
            return

        def _do_commit():
            return self.git.commit(message)

        def _on_success(result):
            if result:
                self._log_output(f"{self._get_text('git.committed')}: {message}")
                self._async_load_status()
            else:
                self._log_output(self._get_text("git.failed_commit"))
                messagebox.showerror(self._get_text("settings.error_title"),
                                     self._get_text("git.failed_commit"))

        self._run_async(_do_commit, on_success=_on_success,
                        busy_msg=self._get_text("git.committing"))

    def _git_push(self):
        if not self._require_repo():
            return
        branch = self.selected_branch

        def _do_push():
            return self.git.push(branch=branch)

        def _on_success(result):
            if result:
                self._log_output(self._get_text("git.push_success"))
            else:
                self._log_output(self._get_text("git.failed_push"))
                messagebox.showerror(self._get_text("settings.error_title"),
                                     self._get_text("git.failed_push"))

        self._run_async(_do_push, on_success=_on_success,
                        busy_msg=self._get_text("git.pushing"))

    def _git_pull(self):
        if not self._require_repo():
            return
        branch = self.selected_branch

        def _do_pull():
            return self.git.pull(branch=branch)

        def _on_success(result):
            if result:
                self._log_output(self._get_text("git.pull_success"))
                self._async_load_status()
            else:
                self._log_output(self._get_text("git.failed_pull"))
                messagebox.showerror(self._get_text("settings.error_title"),
                                     self._get_text("git.failed_pull"))

        self._run_async(_do_pull, on_success=_on_success,
                        busy_msg=self._get_text("git.pulling"))

    def _git_sync(self):
        """VSCode-style sync: pull then push in one async operation."""
        if not self._require_repo():
            return
        branch = self.selected_branch

        def _do_sync():
            return self.git.sync(branch=branch)

        def _on_success(result):
            pull_ok, push_ok, message = result
            self._log_output(message)
            if not pull_ok:
                messagebox.showerror(self._get_text("settings.error_title"),
                                     self._get_text("git.failed_pull"))
            elif not push_ok:
                messagebox.showwarning(self._get_text("git.warning"),
                                       self._get_text("git.failed_push"))
            self._async_load_status()

        self._run_async(_do_sync, on_success=_on_success,
                        busy_msg=self._get_text("git.syncing"))

    def _create_branch(self):
        if not self._require_repo():
            return
        branch_name = ask_string(
            self.window, self._get_text("git.new_branch"),
            self._get_text("git.enter_branch_name"))
        if not branch_name or not branch_name.strip():
            return

        def _do_create():
            return self.git.create_branch(branch_name)

        def _on_success(result):
            if result:
                self._log_output(f"{self._get_text('git.branch_created')}: {branch_name}")
                self._async_load_branches()
            else:
                self._log_output(f"{self._get_text('git.failed_create_branch')}: {branch_name}")
                messagebox.showerror(self._get_text("settings.error_title"),
                                     f"{self._get_text('git.failed_create_branch')}: {branch_name}")

        self._run_async(_do_create, on_success=_on_success,
                        busy_msg=self._get_text("git.creating_branch"))

    def _delete_branch(self):
        if not self.selected_branch:
            messagebox.showinfo(self._get_text("git.info"),
                                self._get_text("git.select_branch_first"))
            return
        if not messagebox.askyesno(
                self._get_text("git.confirm"),
                self._get_text("git.delete_branch_confirm").format(branch=self.selected_branch)):
            return
        branch = self.selected_branch

        def _do_delete():
            return self.git.delete_branch(branch)

        def _on_success(result):
            if result:
                self._log_output(f"{self._get_text('git.branch_deleted')}: {branch}")
                self._async_load_branches()
            else:
                self._log_output(f"{self._get_text('git.failed_delete_branch')}: {branch}")

        self._run_async(_do_delete, on_success=_on_success,
                        busy_msg=self._get_text("git.deleting_branch"))

    def _switch_branch(self):
        if not self.selected_branch:
            messagebox.showinfo(self._get_text("git.info"),
                                self._get_text("git.select_branch_first"))
            return
        branch = self.selected_branch

        def _do_switch():
            return self.git.switch_branch(branch)

        def _on_success(result):
            if result:
                self._log_output(f"{self._get_text('git.switched_to')}: {branch}")
                self._async_load_branches()
                self._async_load_status()
            else:
                self._log_output(f"{self._get_text('git.failed_switch')}: {branch}")

        self._run_async(_do_switch, on_success=_on_success,
                        busy_msg=self._get_text("git.switching_branch"))

    def _discard_selected(self):
        if not self.selected_file:
            messagebox.showinfo(self._get_text("git.info"),
                                self._get_text("git.select_file_first"))
            return
        if not messagebox.askyesno(
                self._get_text("git.confirm"),
                self._get_text("git.discard_confirm").format(file=self.selected_file)):
            return
        file_path = self.selected_file

        def _do_discard():
            return self.git.discard_file(file_path)

        def _on_success(result):
            if result:
                self._log_output(f"{self._get_text('git.discarded')}: {file_path}")
                self._async_load_status()
            else:
                self._log_output(f"{self._get_text('git.failed_discard')}: {file_path}")

        self._run_async(_do_discard, on_success=_on_success,
                        busy_msg=self._get_text("git.discarding"))

    def _manage_license(self):
        """Open the License Manager, releasing the git window grab so the
        license window can receive input independently."""
        def _open():
            LicenseManagerWindow = LazyLoader.get('libs.gui.license_ui', 'LicenseManagerWindow')
            LicenseManagerWindow(
                self.window,
                project_root=self.project_root,
                status_callback=self._log_output,
            )
        self._with_grab_released(_open)

    def _git_changelog(self):
        self.git.manage_changelog()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _require_repo(self) -> bool:
        """Check repo is initialized; show a warning and return False if not."""
        if not self.git_installed:
            messagebox.showwarning(self._get_text("git.warning"),
                                   self._get_text("git.not_installed"))
            return False
        if not self.repo_initialized:
            messagebox.showwarning(self._get_text("git.warning"),
                                   self._get_text("git.init_first"))
            return False
        return True

    def _log_output(self, message: str):
        """Append a timestamped message to the output log with visual separation.

        Each log entry is prefixed with a compact HH:MM:SS timestamp so
        consecutive operations are easy to distinguish. Multi-line git
        output (e.g., push errors) is indented under the timestamp for
        readability. The status callback receives the raw message.

        Args:
            message: The log message text
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        lines = message.splitlines() or [message]
        # First line gets the timestamp prefix; continuation lines are indented.
        formatted = f"[{timestamp}] {lines[0]}"
        for line in lines[1:]:
            formatted += f"\n          {line}"
        self.output_text.insert("end", f"{formatted}\n")
        self.output_text.see("end")
        if self.status_callback:
            self.status_callback(message)
