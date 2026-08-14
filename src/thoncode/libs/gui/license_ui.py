#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code License Manager",
    "Path": ".main.libs.gui.license_ui",
    "Entrance": "main.py"
}

import os
import ttkbootstrap as ttkb
from tkinter import ttk, filedialog, messagebox
import tkinter as tk

import libs.langs_loader as langs_loader
from libs.gui import theme
from libs.license_handle import LicenseHandle
from libs.gui.lazy_loader import LazyLoader


class LicenseManagerWindow:
    """License management window for projects.

    Behaviour notes (formerly the two biggest defects of this window):

    * *Window clipping on 16:9 / small-DPI screens* – the dialog now
      wraps its body in a ScrollableFrame, enforces a minimum size, and
      the preview Text widget uses a reasonable row height instead of
      ``height=150`` which previously pushed the Apply / Remove / Close
      buttons cleanly outside the window.
    * *Z-order / grab interaction with the Git parent* – when the
      License Manager is opened from a modal Git integration window the
      git window's grab is released before this dialog is shown. This
      dialog then applies its own transient + lift + focus_force +
      grab_set so it can receive input without the user having to
      close the Git window first. When the dialog is destroyed it
      tries to restore the grab on its parent so the git modal
      experience is preserved.
    """

    def __init__(self, parent, project_root=None, status_callback=None):
        self.parent = parent
        self.project_root = project_root or os.getcwd()
        self.status_callback = status_callback
        self.license_handle = LicenseHandle()
        self.custom_vars = {}
        self.lang = langs_loader.langs()

        self._create_window()
        self._load_licenses()
        self._check_existing_license()

    def _get_text(self, key):
        return getattr(self.lang, key.replace('.', '_'), key)

    def _create_window(self):
        """Create the license manager window with safe geometry & z-order.
        """
        # The ``parent`` argument may be either a raw Tk widget (Tk/Toplevel)
        # *or* a window-wrapper object that exposes a ``.window`` attribute
        # (e.g. GitIntegrationWindow). Extracting the real widget here keeps
        # callers flexible and still lets ``_on_close`` reach back to the
        # wrapper for grab-restoration hooks.
        parent_widget = getattr(self.parent, "window", self.parent)

        self.window = ttkb.Toplevel(parent_widget)
        self.window.title(self._get_text("license.title"))
        self.window.geometry("760x520")
        # Resizeable so the user can read long licenses comfortably.
        try:
            self.window.resizable(True, True)
        except Exception:
            pass

        from libs.gui.window_helper import (
            set_window_minimum_size,
            apply_modal_window_order,
        )
        set_window_minimum_size(self.window, min_width=640, min_height=440)
        apply_modal_window_order(self.window, parent_widget, modal=True)

        self._create_widgets()

        # Ensure closing the dialog (X-button / close-button) restores
        # the grab on any modal parent window.
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self):
        """Create all UI widgets inside a scrollable frame."""
        from libs.gui.window_helper import ScrollableFrame

        outer = ttk.Frame(self.window)
        outer.pack(fill="both", expand=True, padx=14, pady=14)

        scroll = ScrollableFrame(outer)
        scroll.pack(fill="both", expand=True)
        main_frame = scroll.interior
        main_frame.configure(padding=(6, 4))

        # Project info
        project_label = ttk.Label(
            main_frame,
            text=self._get_text("license.project") + f" {os.path.basename(self.project_root)}",
            font=("Microsoft YaHei", 14, "bold"),
        )
        project_label.pack(anchor="w", pady=(0, 15))

        # License selection frame
        select_frame = ttk.Frame(main_frame)
        select_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(select_frame, text=self._get_text("license.select")).pack(anchor="w")

        # Dropdown for available licenses
        self.license_var = tk.StringVar(value="")
        self.license_menu = ttk.Combobox(
            select_frame,
            values=[],
            textvariable=self.license_var,
        )
        self.license_menu.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.license_menu.bind(
            "<<ComboboxSelected>>",
            lambda e: self._on_license_selected(self.license_var.get()),
        )

        # Browse button for custom template
        ttk.Button(
            select_frame, text=self._get_text("license.browse"),
            command=self._browse_license_file,
        ).pack(side="left")

        # Custom license name input
        ttk.Label(
            main_frame, text=self._get_text("license.custom_name"),
        ).pack(anchor="w", pady=(10, 2))
        self.name_entry = ttk.Entry(main_frame)
        self.name_entry.pack(fill="x", pady=(0, 10))

        # Custom variables frame
        vars_frame = ttk.Frame(main_frame)
        vars_frame.pack(fill="x", pady=(5, 10))

        ttk.Label(
            vars_frame, text=self._get_text("license.variables"),
            font=("Microsoft YaHei", 12),
        ).pack(anchor="w")

        var_grid = ttk.Frame(vars_frame)
        var_grid.pack(fill="x", pady=5)

        ttk.Label(var_grid, text=self._get_text("license.year"))\
            .grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.year_entry = ttk.Entry(var_grid, width=12)
        self.year_entry.grid(row=0, column=1, padx=(0, 20), sticky="w")

        ttk.Label(var_grid, text=self._get_text("license.author"))\
            .grid(row=0, column=2, padx=(0, 5), sticky="w")
        self.author_entry = ttk.Entry(var_grid)
        self.author_entry.grid(row=0, column=3, sticky="ew")
        var_grid.columnconfigure(3, weight=1)

        # Re-render preview on year/author change so users have live feedback.
        self.year_entry.bind("<KeyRelease>", lambda e: self._refresh_preview())
        self.author_entry.bind("<KeyRelease>", lambda e: self._refresh_preview())

        # License preview (uses a sensible row height + fills the remaining
        # area via fill+expand, so the layout no longer overflows).
        preview_frame = ttk.Frame(main_frame)
        preview_frame.pack(fill="both", expand=True, pady=(10, 10))

        ttk.Label(
            preview_frame, text=self._get_text("license.preview"), anchor="w",
        ).pack(anchor="w")

        colors = theme.get_colors()
        self.preview_text = tk.Text(
            preview_frame,
            height=10,
            wrap="word",
            bg=colors["bg"],
            fg=colors["fg"],
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=colors.get("border", "#444444"),
            highlightcolor=colors.get("border", "#444444"),
        )
        self.preview_text.pack(fill="both", expand=True, pady=(5, 0))

        # Action buttons – pinned to the bottom so they are always clickable.
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(
            btn_frame, text=self._get_text("license.close"),
            command=self._on_close,
        ).pack(side="right", padx=5)
        ttk.Button(
            btn_frame, text=self._get_text("license.remove"),
            command=self._remove_license,
        ).pack(side="right", padx=5)
        ttk.Button(
            btn_frame, text=self._get_text("license.apply"),
            command=self._apply_license,
            style="Accent.TButton",
        ).pack(side="right", padx=5)

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------
    def _load_licenses(self):
        """Load available licenses into dropdown"""
        licenses = self.license_handle.get_available_licenses()
        if licenses:
            self.license_menu.configure(values=licenses)
            if not self.license_var.get():
                self.license_var.set(licenses[0])
                self._on_license_selected(licenses[0])
        else:
            self.license_menu.configure(values=[self._get_text("license.no_licenses")])
            self.license_var.set(self._get_text("license.no_licenses"))

    def _check_existing_license(self):
        """Check if project already has a LICENSE file."""
        content = self.license_handle.read_project_license(self.project_root)
        if content and self.status_callback:
            self.status_callback(self._get_text("license.existing"))

    def _on_license_selected(self, license_name):
        """Handle license selection from dropdown"""
        content = self.license_handle.get_license_content(license_name)
        if not content:
            return
        self.preview_text.delete("1.0", "end")
        preview = content
        if self.year_entry.get():
            preview = preview.replace('[year]', self.year_entry.get())
            preview = preview.replace('{{year}}', self.year_entry.get())
        if self.author_entry.get():
            preview = preview.replace('[author]', self.author_entry.get())
            preview = preview.replace('{{author}}', self.author_entry.get())
        self.preview_text.insert("1.0", preview)

    def _refresh_preview(self):
        """Re-apply variable substitution for the currently selected template."""
        current = self.license_var.get()
        if current and current != self._get_text("license.no_licenses"):
            self._on_license_selected(current)

    def _browse_license_file(self):
        """Browse for custom license file"""
        file_path = filedialog.askopenfilename(
            title=self._get_text("license.browse_title"),
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", content)
            self.license_var.set(os.path.basename(file_path))
            if self.status_callback:
                self.status_callback(self._get_text("license.loaded") + f" {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror(
                self._get_text("settings.error_title"),
                self._get_text("license.browse_failed") + f" {e}",
            )

    def _apply_license(self):
        """Apply selected license to project"""
        license_name = self.license_var.get()
        if not license_name or license_name == self._get_text("license.no_licenses"):
            messagebox.showwarning(
                self._get_text("git.warning"),
                self._get_text("license.select_license_first"),
            )
            return

        custom_name = self.name_entry.get().strip()
        if custom_name:
            license_name = custom_name

        content = self.preview_text.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning(
                self._get_text("git.warning"),
                self._get_text("license.content_empty"),
            )
            return

        if license_name.endswith('.md') or license_name.endswith('.txt'):
            license_name = os.path.splitext(license_name)[0]

        custom_vars = {}
        if self.year_entry.get().strip():
            custom_vars['year'] = self.year_entry.get().strip()
            custom_vars['Year'] = self.year_entry.get().strip()
        if self.author_entry.get().strip():
            custom_vars['author'] = self.author_entry.get().strip()
            custom_vars['Author'] = self.author_entry.get().strip()

        try:
            license_file = os.path.join(self.project_root, "LICENSE")
            with open(license_file, 'w', encoding='utf-8') as f:
                f.write(content)

            if self.status_callback:
                self.status_callback(self._get_text("license.license_applied") + f" {license_name}")
            messagebox.showinfo(
                self._get_text("license.success"),
                self._get_text("license.applied_success").format(name=license_name),
            )
        except Exception as e:
            messagebox.showerror(
                self._get_text("settings.error_title"),
                f"Failed to apply license: {e}",
            )

    def _remove_license(self):
        """Remove LICENSE file from project"""
        license_file = os.path.join(self.project_root, "LICENSE")
        if not os.path.exists(license_file):
            messagebox.showinfo(
                self._get_text("git.info"),
                self._get_text("license.no_license"),
            )
            return

        if messagebox.askyesno(
            self._get_text("git.confirm"),
            self._get_text("license.remove_confirm"),
        ):
            try:
                os.remove(license_file)
                self.preview_text.delete("1.0", "end")
                if self.status_callback:
                    self.status_callback("LICENSE file removed")
                messagebox.showinfo(
                    self._get_text("license.success"),
                    self._get_text("license.remove_success"),
                )
            except Exception as e:
                messagebox.showerror(
                    self._get_text("settings.error_title"),
                    self._get_text("license.remove_failed") + f" {e}",
                )

    def _on_close(self):
        """Release our own grab then try to hand focus/grab back to the parent.

        This coordination is what fixes the "I had to close the Git
        window before I could use it" symptom – before, the license
        dialog would not steal grab and the git window's grab was
        re-applied synchronously after open, so all license clicks were
        rejected by Tk's grab ownership rules.
        """
        try:
            self.window.grab_release()
        except Exception:
            pass
        try:
            # Restore parent grab if the parent has a restore hook (e.g.
            # GitIntegrationWindow._make_modal). We deliberately avoid
            # reaching into private attributes of the caller and only
            # use a protocol method that any modal parent can implement.
            if self.parent is not None:
                parent_window = getattr(self.parent, "window", self.parent)
                restore = getattr(self.parent, "_make_modal", None)
                if callable(restore):
                    try:
                        restore()
                    except Exception:
                        pass
                else:
                    try:
                        parent_window.lift()
                        parent_window.focus_force()
                    except Exception:
                        pass
        finally:
            try:
                self.window.destroy()
            except Exception:
                pass
