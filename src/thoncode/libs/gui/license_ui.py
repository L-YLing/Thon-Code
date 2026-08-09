# libs/gui/license_ui.py

import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk

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
        
        self._create_window()
        self._load_licenses()
        self._check_existing_license()
    
    def _create_window(self):
        """Create the license manager window"""
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("License Manager")
        self.window.geometry("600x500")
        self.window.transient(self.parent)
        self.window.lift()
        self.window.focus_force()
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create all UI widgets"""
        main_frame = ctk.CTkFrame(self.window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Project info
        project_label = ctk.CTkLabel(main_frame, text=f"Project: {os.path.basename(self.project_root)}", 
                                     font=("Microsoft YaHei", 14, "bold"))
        project_label.pack(anchor="w", pady=(0, 15))
        
        # License selection frame
        select_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        select_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(select_frame, text="Select License:").pack(anchor="w")
        
        # Dropdown for available licenses
        self.license_var = ctk.StringVar(value="")
        self.license_menu = ctk.CTkOptionMenu(
            select_frame,
            values=[],
            variable=self.license_var,
            command=self._on_license_selected,
            width=300
        )
        self.license_menu.pack(side="left", padx=(0, 10))
        
        # Browse button for custom template
        ctk.CTkButton(select_frame, text="Browse File", command=self._browse_license_file, width=100).pack(side="left")
        
        # Custom license name input
        ctk.CTkLabel(main_frame, text="Or enter custom license name:").pack(anchor="w", pady=(10, 2))
        self.name_entry = ctk.CTkEntry(main_frame, width=300, placeholder_text="e.g., custom-license")
        self.name_entry.pack(anchor="w", pady=(0, 10))
        
        # Custom variables frame
        vars_frame = ctk.CTkFrame(main_frame)
        vars_frame.pack(fill="x", pady=(5, 10))
        
        ctk.CTkLabel(vars_frame, text="Custom Variables (optional):", font=("Microsoft YaHei", 12)).pack(anchor="w")
        
        var_grid = ctk.CTkFrame(vars_frame, fg_color="transparent")
        var_grid.pack(fill="x", pady=5)
        
        # Year variable
        ctk.CTkLabel(var_grid, text="Year:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.year_entry = ctk.CTkEntry(var_grid, width=100, placeholder_text="2024")
        self.year_entry.grid(row=0, column=1, padx=(0, 20), sticky="w")
        
        # Author variable
        ctk.CTkLabel(var_grid, text="Author:").grid(row=0, column=2, padx=(0, 5), sticky="w")
        self.author_entry = ctk.CTkEntry(var_grid, width=200, placeholder_text="Your Name")
        self.author_entry.grid(row=0, column=3, sticky="w")
        
        # License preview
        preview_frame = ctk.CTkFrame(main_frame)
        preview_frame.pack(fill="both", expand=True, pady=(10, 10))
        
        ctk.CTkLabel(preview_frame, text="Preview:", anchor="w").pack(anchor="w")
        
        self.preview_text = ctk.CTkTextbox(preview_frame, height=150)
        self.preview_text.pack(fill="both", expand=True, pady=(5, 0))
        
        # Action buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))
        
        ctk.CTkButton(btn_frame, text="Apply License", command=self._apply_license, width=120).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Remove License", command=self._remove_license, width=120).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Close", command=self.window.destroy, width=100).pack(side="right", padx=5)
    
    def _load_licenses(self):
        """Load available licenses into dropdown"""
        licenses = self.license_handle.get_available_licenses()
        if licenses:
            self.license_menu.configure(values=licenses)
            if not self.license_var.get():
                self.license_var.set(licenses[0])
                self._on_license_selected(licenses[0])
        else:
            self.license_menu.configure(values=["No licenses found"])
            self.license_var.set("No licenses found")
    
    def _check_existing_license(self):
        """Check if project already has a LICENSE file"""
        content = self.license_handle.read_project_license(self.project_root)
        if content:
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", f"[Existing LICENSE file]\n\n{content[:500]}{'...' if len(content) > 500 else ''}")
            self.status_callback("Existing LICENSE file found")
    
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
            title="Select License File",
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
            self.status_callback(f"Loaded: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read file: {e}")
    
    def _apply_license(self):
        """Apply selected license to project"""
        license_name = self.license_var.get()
        if not license_name or license_name == "No licenses found":
            messagebox.showwarning("Warning", "Please select a license")
            return
        
        # Check if custom name is provided
        custom_name = self.name_entry.get().strip()
        if custom_name:
            license_name = custom_name
        
        # Check if content exists
        content = self.preview_text.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("Warning", "License content is empty")
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
            
            self.status_callback(f"License applied: {license_name}")
            messagebox.showinfo("Success", f"License '{license_name}' has been applied to the project")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply license: {e}")
    
    def _remove_license(self):
        """Remove LICENSE file from project"""
        license_file = os.path.join(self.project_root, "LICENSE")
        if not os.path.exists(license_file):
            messagebox.showinfo("Info", "No LICENSE file found")
            return
        
        if messagebox.askyesno("Confirm", "Remove LICENSE file from project?"):
            try:
                os.remove(license_file)
                self.preview_text.delete("1.0", "end")
                self.status_callback("LICENSE file removed")
                messagebox.showinfo("Success", "LICENSE file has been removed")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove license: {e}")