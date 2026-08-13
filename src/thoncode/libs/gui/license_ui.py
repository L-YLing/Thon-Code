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
    """License management window for projects"""

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
        """Create the license manager window"""
        self.window = ttkb.Toplevel(self.parent)
        self.window.title(self._get_text("license.title"))
        self.window.geometry("640x360")
        self.window.transient(self.parent)
        self.window.lift()
        self.window.focus_force()

        self._create_widgets()

    def _create_widgets(self):
        """Create all UI widgets"""
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Project info
        project_label = ttk.Label(main_frame, text=self._get_text("license.project") + f" {os.path.basename(self.project_root)}",
                                  font=("Microsoft YaHei", 14, "bold"))
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
            textvariable=self.license_var
        )
        self.license_menu.pack(side="left", padx=(0, 10))
        self.license_menu.bind("<<ComboboxSelected>>", lambda e: self._on_license_selected(self.license_var.get()))

        # Browse button for custom template
        ttk.Button(select_frame, text=self._get_text("license.browse"), command=self._browse_license_file).pack(side="left")

        # Custom license name input
        ttk.Label(main_frame, text=self._get_text("license.custom_name")).pack(anchor="w", pady=(10, 2))
        self.name_entry = ttk.Entry(main_frame)
        self.name_entry.pack(anchor="w", pady=(0, 10))

        # Custom variables frame
        vars_frame = ttk.Frame(main_frame)
        vars_frame.pack(fill="x", pady=(5, 10))

        ttk.Label(vars_frame, text=self._get_text("license.variables"), font=("Microsoft YaHei", 12)).pack(anchor="w")

        var_grid = ttk.Frame(vars_frame)
        var_grid.pack(fill="x", pady=5)

        # Year variable
        ttk.Label(var_grid, text=self._get_text("license.year")).grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.year_entry = ttk.Entry(var_grid)
        self.year_entry.grid(row=0, column=1, padx=(0, 20), sticky="w")

        # Author variable
        ttk.Label(var_grid, text=self._get_text("license.author")).grid(row=0, column=2, padx=(0, 5), sticky="w")
        self.author_entry = ttk.Entry(var_grid)
        self.author_entry.grid(row=0, column=3, sticky="w")

        # License preview
        preview_frame = ttk.Frame(main_frame)
        preview_frame.pack(fill="both", expand=True, pady=(10, 10))

        ttk.Label(preview_frame, text=self._get_text("license.preview"), anchor="w").pack(anchor="w")

        colors = theme.get_colors()
        self.preview_text = tk.Text(
            preview_frame,
            height=150,
            bg=colors["bg"],
            fg=colors["fg"],
            relief="flat",
            borderwidth=0,
            highlightthickness=0
        )
        self.preview_text.pack(fill="both", expand=True, pady=(5, 0))

        # Action buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(btn_frame, text=self._get_text("license.apply"), command=self._apply_license).pack(side="right", padx=5)
        ttk.Button(btn_frame, text=self._get_text("license.remove"), command=self._remove_license).pack(side="right", padx=5)
        ttk.Button(btn_frame, text=self._get_text("license.close"), command=self.window.destroy).pack(side="right", padx=5)

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
        """Check if project already has a LICENSE file.

        Does NOT overwrite the template preview; only notifies via the
        status callback so the user knows an existing LICENSE will be
        replaced when they apply a new one.
        """
        content = self.license_handle.read_project_license(self.project_root)
        if content:
            if self.status_callback:
                self.status_callback(self._get_text("license.existing"))

    def _on_license_selected(self, license_name):
        """Handle license selection from dropdown"""
        content = self.license_handle.get_license_content(license_name)
        if content:
            self.preview_text.delete("1.0", "end")
            # Show preview with variable placeholders
            preview = content
            if self.year_entry.get():
                preview = preview.replace('[year]', self.year_entry.get())
                preview = preview.replace('{{year}}', self.year_entry.get())
            if self.author_entry.get():
                preview = preview.replace('[author]', self.author_entry.get())
                preview = preview.replace('{{author}}', self.author_entry.get())
            self.preview_text.insert("1.0", preview)

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
            self.status_callback(self._get_text("license.loaded") + f" {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror(self._get_text("settings.error_title"), self._get_text("license.browse_failed") + f" {e}")

    def _apply_license(self):
        """Apply selected license to project"""
        license_name = self.license_var.get()
        if not license_name or license_name == self._get_text("license.no_licenses"):
            messagebox.showwarning(self._get_text("git.warning"), self._get_text("license.select_license_first"))
            return

        # Check if custom name is provided
        custom_name = self.name_entry.get().strip()
        if custom_name:
            license_name = custom_name

        # Check if content exists
        content = self.preview_text.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning(self._get_text("git.warning"), self._get_text("license.content_empty"))
            return

        # Save custom license if from file
        if license_name.endswith('.md') or license_name.endswith('.txt'):
            license_name = os.path.splitext(license_name)[0]

        # Build custom variables
        custom_vars = {}
        if self.year_entry.get().strip():
            custom_vars['year'] = self.year_entry.get().strip()
            custom_vars['Year'] = self.year_entry.get().strip()
        if self.author_entry.get().strip():
            custom_vars['author'] = self.author_entry.get().strip()
            custom_vars['Author'] = self.author_entry.get().strip()

        # Apply license
        try:
            # Write LICENSE file
            license_file = os.path.join(self.project_root, "LICENSE")
            with open(license_file, 'w', encoding='utf-8') as f:
                f.write(content)

            self.status_callback(self._get_text("license.license_applied") + f" {license_name}")
            messagebox.showinfo(self._get_text("license.success"), self._get_text("license.applied_success").format(name=license_name))
        except Exception as e:
            messagebox.showerror(self._get_text("settings.error_title"), f"Failed to apply license: {e}")

    def _remove_license(self):
        """Remove LICENSE file from project"""
        license_file = os.path.join(self.project_root, "LICENSE")
        if not os.path.exists(license_file):
            messagebox.showinfo(self._get_text("git.info"), self._get_text("license.no_license"))
            return

        if messagebox.askyesno(self._get_text("git.confirm"), self._get_text("license.remove_confirm")):
            try:
                os.remove(license_file)
                self.preview_text.delete("1.0", "end")
                self.status_callback("LICENSE file removed")
                messagebox.showinfo(self._get_text("license.success"), self._get_text("license.remove_success"))
            except Exception as e:
                messagebox.showerror(self._get_text("settings.error_title"), self._get_text("license.remove_failed") + f" {e}")
