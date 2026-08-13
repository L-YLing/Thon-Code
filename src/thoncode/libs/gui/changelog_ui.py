#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Changelog",
    "Path": ".main.libs.gui.changelog_ui",
    "Entrance": "main.py"
}

import os
import ttkbootstrap as ttkb
from tkinter import ttk, messagebox, filedialog, simpledialog
import tkinter as tk
from datetime import datetime
from typing import Optional, List, Dict, Any

from libs.gui.lazy_loader import LazyLoader
from libs.gui import theme
from libs.changelog_handle import ChangelogHandle, ChangelogEntry
import libs.cfg_handle as cfg_handle
import libs.langs_loader as langs_loader


class ChangelogWindow:
    """
    Changelog management window for creating and editing changelog entries.
    Supports version tracking, entry editing, and export functionality.
    Part of Git integration tools.
    """

    def __init__(self, parent, project_root: Optional[str] = None, status_callback=None):
        self.parent = parent
        self.project_root = project_root or os.getcwd()
        self.status_callback = status_callback
        self.changelog = ChangelogHandle(self.project_root)
        self.current_entry: Optional[ChangelogEntry] = None
        self.section_items: Dict[str, List[str]] = {}
        self.current_section: Optional[str] = None

        self._load_language()

        self._create_window()
        self._load_changelog()
        self._update_version_list()
        self._select_first_entry()

    def _load_language(self):
        """Load language from config and language files"""
        try:
            self.lang = langs_loader.langs()
        except Exception:
            self.lang = None

    def _get_text(self, key: str) -> str:
        """Get localized text from language files"""
        if self.lang:
            try:
                return getattr(self.lang, key, key)
            except AttributeError:
                pass
        return key

    def _create_window(self):
        """Create the changelog management window"""
        self.window = ttkb.Toplevel(self.parent)
        self.window.title(self._get_text("changelog_git_title"))
        self.window.geometry("960x540")
        self.window.transient(self.parent)
        self.window.lift()
        self.window.focus_force()

        self._create_widgets()

    def _create_widgets(self):
        """Create all UI widgets"""
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._create_top_bar(main_frame)

        paned = ttk.PanedWindow(main_frame, orient='horizontal')
        paned.pack(fill="both", expand=True, pady=5)

        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        self._create_left_panel(left_frame)

        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=3)
        self._create_right_panel(right_frame)

        self._create_status_bar(main_frame)

    def _create_top_bar(self, parent):
        """Create top bar with project info"""
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill="x", pady=(0, 5))

        path_label = ttk.Label(
            top_frame,
            text=f"📁 {os.path.basename(self.project_root)}",
            font=("Microsoft YaHei", 13, "bold")
        )
        path_label.pack(side="left", padx=10)

        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side="right", padx=10)

        ttk.Button(
            btn_frame,
            text=self._get_text("changelog_export"),
            command=self._export_changelog,
        ).pack(side="left", padx=2)

        ttk.Button(
            btn_frame,
            text=self._get_text("changelog_import"),
            command=self._import_changelog,
        ).pack(side="left", padx=2)

        ttk.Button(
            btn_frame,
            text=self._get_text("changelog_preview"),
            command=self._preview_changelog,
        ).pack(side="left", padx=2)

    def _create_left_panel(self, parent):
        """Create left panel with version list"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill="x", pady=(0, 5))

        ttk.Label(header_frame, text=self._get_text("changelog_version"), font=("Microsoft YaHei", 12, "bold")).pack(side="left", padx=10)

        self.version_listbox = theme.themed_listbox(
            parent,
            height=15,
            font=("Consolas", 11),
        )
        self.version_listbox.pack(fill="both", expand=True, padx=10, pady=5)
        self.version_listbox.bind("<<ListboxSelect>>", self._on_version_select)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            btn_frame,
            text=self._get_text("changelog_add_entry"),
            command=self._add_new_entry,
        ).pack(side="left", padx=2)

        ttk.Button(
            btn_frame,
            text=self._get_text("changelog_remove_entry"),
            command=self._remove_entry,
        ).pack(side="left", padx=2)

    def _create_right_panel(self, parent):
        """Create right panel with entry editor"""
        form_frame = ttk.Frame(parent)
        form_frame.pack(fill="both", expand=True, pady=(0, 5))

        # Version field
        version_frame = ttk.Frame(form_frame)
        version_frame.pack(fill="x", pady=5)
        ttk.Label(version_frame, text=self._get_text("changelog_version")).pack(side="left", padx=(10, 5))
        self.version_entry = ttk.Entry(version_frame)
        self.version_entry.pack(side="left", padx=5)

        # Date field
        date_frame = ttk.Frame(form_frame)
        date_frame.pack(fill="x", pady=5)
        ttk.Label(date_frame, text=self._get_text("changelog_date")).pack(side="left", padx=(10, 5))
        self.date_entry = ttk.Entry(date_frame)
        self.date_entry.pack(side="left", padx=5)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))

        # Sections management
        sections_frame = ttk.Frame(form_frame)
        sections_frame.pack(fill="both", expand=True, pady=(5, 5))

        # Section tabs (listbox)
        tab_frame = ttk.Frame(sections_frame)
        tab_frame.pack(fill="x", pady=2)

        ttk.Label(tab_frame, text=self._get_text("changelog_sections"), font=("Microsoft YaHei", 11, "bold")).pack(side="left", padx=5)

        ttk.Button(tab_frame, text=self._get_text("changelog_add_section"), command=self._add_section).pack(side="right", padx=2)
        ttk.Button(tab_frame, text=self._get_text("changelog_remove_section"), command=self._remove_section).pack(side="right", padx=2)

        self.section_tabs = theme.themed_listbox(
            sections_frame,
            height=3,
            font=("Consolas", 10),
        )
        self.section_tabs.pack(fill="x", padx=10, pady=5)
        self.section_tabs.bind("<<ListboxSelect>>", self._on_section_select)

        # Items for selected section
        items_frame = ttk.Frame(sections_frame)
        items_frame.pack(fill="both", expand=True, pady=(5, 0))

        ttk.Label(items_frame, text=self._get_text("changelog_items"), font=("Microsoft YaHei", 11, "bold")).pack(anchor="w", padx=10)

        self.items_listbox = theme.themed_listbox(
            items_frame,
            height=6,
            font=("Consolas", 10),
        )
        self.items_listbox.pack(fill="both", expand=True, padx=10, pady=5)

        # Item input
        item_input_frame = ttk.Frame(items_frame)
        item_input_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.item_entry = ttk.Entry(item_input_frame)
        self.item_entry.pack(side="left", padx=2)
        self.item_entry.bind("<Return>", self._add_item)

        ttk.Button(item_input_frame, text=self._get_text("changelog_add_item"), command=self._add_item).pack(side="left", padx=2)
        ttk.Button(item_input_frame, text=self._get_text("changelog_remove_selected"), command=self._remove_item).pack(side="left", padx=2)

        # Save/Cancel buttons
        save_frame = ttk.Frame(parent)
        save_frame.pack(fill="x", pady=5)

        ttk.Button(save_frame, text=self._get_text("changelog_save"), command=self._save_entry).pack(side="right", padx=10)
        ttk.Button(save_frame, text=self._get_text("changelog_cancel"), command=self._clear_form).pack(side="right", padx=5)

    def _create_status_bar(self, parent):
        """Create status bar"""
        self.status_bar = ttk.Label(
            parent,
            text=self._get_text("git.ready"),
            anchor="w",
            font=("Microsoft YaHei", 10)
        )
        self.status_bar.pack(fill="x", pady=(5, 0))

    def _load_changelog(self):
        """Load changelog from file"""
        self.changelog.load_changelog()
        self._update_status(self._get_text("changelog_loaded_entries").format(n=len(self.changelog.entries)))

    def _update_version_list(self):
        """Update the version list"""
        self.version_listbox.delete(0, tk.END)
        versions = self.changelog.get_versions()
        if not versions:
            self.version_listbox.insert(tk.END, self._get_text("changelog_no_entries"))
            self.version_listbox.config(fg="gray")
            return
        self.version_listbox.config(fg="white")
        for version in versions:
            self.version_listbox.insert(tk.END, version)

    def _select_first_entry(self):
        """Select the first entry in the list"""
        if self.version_listbox.size() > 0 and self.changelog.entries:
            self.version_listbox.selection_set(0)
            self._on_version_select(None)

    def _on_version_select(self, event):
        """Handle version selection"""
        selection = self.version_listbox.curselection()
        if not selection:
            return
        version = self.version_listbox.get(selection[0])
        if version == self._get_text("changelog_no_entries"):
            return
        entry = self.changelog.get_entry(version)
        if entry:
            self.current_entry = entry
            self._display_entry(entry)

    def _display_entry(self, entry: ChangelogEntry):
        """Display an entry in the form"""
        self.version_entry.delete(0, "end")
        self.version_entry.insert(0, entry.version)
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, entry.date)

        # Clear and display sections
        self.section_tabs.delete(0, tk.END)
        self.section_items.clear()

        for section_name, items in entry.sections.items():
            self.section_tabs.insert(tk.END, section_name)
            self.section_items[section_name] = items.copy()

        if self.section_tabs.size() > 0:
            self.section_tabs.selection_set(0)
            self._on_section_select(None)

        self.item_entry.delete(0, "end")

    def _clear_form(self):
        """Clear the form"""
        self.version_entry.delete(0, "end")
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.section_tabs.delete(0, tk.END)
        self.items_listbox.delete(0, tk.END)
        self.item_entry.delete(0, "end")
        self.section_items.clear()
        self.current_section = None
        self.current_entry = None
        self.version_listbox.selection_clear(0, tk.END)

    def _add_section(self):
        """Add a new section"""
        section_name = simpledialog.askstring(self._get_text("changelog_add_section_title"), self._get_text("changelog_enter_section"))
        if not section_name:
            return

        section_name = section_name.strip()
        if section_name in self.section_items:
            messagebox.showinfo(self._get_text("git.info"), self._get_text("changelog_section_exists").format(name=section_name))
            return

        self.section_tabs.insert(tk.END, section_name)
        self.section_items[section_name] = []
        self.section_tabs.selection_set(self.section_tabs.size() - 1)
        self._on_section_select(None)

    def _remove_section(self):
        """Remove selected section"""
        selection = self.section_tabs.curselection()
        if not selection:
            messagebox.showinfo(self._get_text("git.info"), self._get_text("changelog_select_section"))
            return

        section_name = self.section_tabs.get(selection[0])
        if messagebox.askyesno(self._get_text("git.confirm"), self._get_text("changelog_confirm_remove_section").format(name=section_name)):
            self.section_tabs.delete(selection[0])
            if section_name in self.section_items:
                del self.section_items[section_name]
            self.items_listbox.delete(0, tk.END)
            self.current_section = None

    def _on_section_select(self, event):
        """Handle section selection"""
        selection = self.section_tabs.curselection()
        if not selection:
            return

        section_name = self.section_tabs.get(selection[0])
        self.current_section = section_name

        # Display items for this section
        self.items_listbox.delete(0, tk.END)
        for item in self.section_items.get(section_name, []):
            self.items_listbox.insert(tk.END, item)

    def _add_item(self, event=None):
        """Add an item to the current section"""
        if not self.current_section:
            messagebox.showinfo(self._get_text("git.info"), self._get_text("changelog_select_section_first"))
            return

        item = self.item_entry.get().strip()
        if not item:
            return

        if self.current_section not in self.section_items:
            self.section_items[self.current_section] = []

        self.section_items[self.current_section].append(item)
        self.items_listbox.insert(tk.END, item)
        self.item_entry.delete(0, "end")

    def _remove_item(self):
        """Remove selected item"""
        selection = self.items_listbox.curselection()
        if not selection:
            return

        if not self.current_section:
            return

        item = self.items_listbox.get(selection[0])
        if item in self.section_items.get(self.current_section, []):
            self.section_items[self.current_section].remove(item)
        self.items_listbox.delete(selection[0])

    def _add_new_entry(self):
        """Add a new entry"""
        self._clear_form()
        versions = self.changelog.get_versions()
        if versions:
            latest = self.changelog.get_latest_version()
            if latest:
                parts = latest.split('.')
                if len(parts) == 3:
                    try:
                        major, minor, patch = parts
                        self.version_entry.insert(0, f"{major}.{minor}.{int(patch) + 1}")
                    except:
                        self.version_entry.insert(0, "1.0.0")
                else:
                    self.version_entry.insert(0, "1.0.0")
            else:
                self.version_entry.insert(0, "1.0.0")
        else:
            self.version_entry.insert(0, "1.0.0")

        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.version_listbox.selection_clear(0, tk.END)
        self.current_entry = None
        self.item_entry.focus()

    def _save_entry(self):
        """Save the current entry"""
        version = self.version_entry.get().strip()
        date = self.date_entry.get().strip()

        if not version:
            messagebox.showerror(self._get_text("settings.error_title"), self._get_text("changelog_invalid_version"))
            return
        if not date:
            messagebox.showerror(self._get_text("settings.error_title"), self._get_text("changelog_invalid_date"))
            return

        # Collect sections from the UI
        sections = {}
        for section_name in self.section_tabs.get(0, tk.END):
            items = self.section_items.get(section_name, [])
            if items:
                sections[section_name] = items

        if not sections:
            messagebox.showerror(self._get_text("settings.error_title"), self._get_text("changelog_no_changes"))
            return

        existing = self.changelog.get_entry(version)
        if existing and (not self.current_entry or self.current_entry.version != version):
            if not messagebox.askyesno(self._get_text("git.confirm"), self._get_text("changelog_version_exists").format(version=version) + "\n" + self._get_text("changelog_overwrite")):
                return

        if self.changelog.add_entry(version, date, sections):
            self._update_status(self._get_text("changelog_save_success"))
            self._load_changelog()
            self._update_version_list()
            for i, v in enumerate(self.changelog.get_versions()):
                if v == version:
                    self.version_listbox.selection_set(i)
                    self._on_version_select(None)
                    break
        else:
            messagebox.showerror(self._get_text("settings.error_title"), self._get_text("changelog_save_failed"))

    def _remove_entry(self):
        """Remove selected entry"""
        selection = self.version_listbox.curselection()
        if not selection:
            messagebox.showinfo(self._get_text("git.info"), self._get_text("git.select_file_first"))
            return
        version = self.version_listbox.get(selection[0])
        if version == self._get_text("changelog_no_entries"):
            return
        if messagebox.askyesno(self._get_text("git.confirm"), self._get_text("changelog_confirm_delete").format(version=version)):
            if self.changelog.remove_entry(version):
                self._update_status(self._get_text("changelog_delete_success"))
                self._load_changelog()
                self._update_version_list()
                self._clear_form()
                self._select_first_entry()
            else:
                messagebox.showerror(self._get_text("settings.error_title"), self._get_text("changelog_failed_delete"))

    def _export_changelog(self):
        """Export changelog"""
        if not self.changelog.entries:
            messagebox.showinfo(self._get_text("git.info"), self._get_text("changelog_no_entries"))
            return
        file_path = filedialog.asksaveasfilename(
            title=self._get_text("changelog_export_title"),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Markdown files", "*.md"), ("All files", "*.*")]
        )
        if not file_path:
            return
        if file_path.endswith('.json'):
            self.changelog.export_to_json(file_path)
        else:
            content = self.changelog.generate_markdown()
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                messagebox.showerror(self._get_text("settings.error_title"), self._get_text("changelog_export_failed") + f" {e}")
                return
        self._update_status(self._get_text("changelog_export_success").format(path=os.path.basename(file_path)))

    def _import_changelog(self):
        """Import changelog from file"""
        file_path = filedialog.askopenfilename(
            title=self._get_text("changelog_import_title"),
            filetypes=[("JSON files", "*.json"), ("Markdown files", "*.md"), ("All files", "*.*")]
        )
        if not file_path:
            return
        if file_path.endswith('.json'):
            if self.changelog.import_from_json(file_path):
                self._update_status(self._get_text("changelog_import_success"))
                self._load_changelog()
                self._update_version_list()
                self._select_first_entry()
            else:
                messagebox.showerror(self._get_text("settings.error_title"), self._get_text("changelog_import_failed"))
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                entries = self.changelog.parse_changelog(content)
                if entries:
                    self.changelog.entries = entries
                    self.changelog.save_changelog()
                    self._update_status(self._get_text("changelog_import_success"))
                    self._load_changelog()
                    self._update_version_list()
                    self._select_first_entry()
                else:
                    messagebox.showerror(self._get_text("settings.error_title"), self._get_text("changelog_no_valid_entries"))
            except Exception as e:
                messagebox.showerror(self._get_text("settings.error_title"), self._get_text("changelog_import_failed") + f": {e}")

    def _preview_changelog(self):
        """Preview the changelog"""
        if not self.changelog.entries:
            messagebox.showinfo(self._get_text("git.info"), self._get_text("changelog_no_entries"))
            return
        preview_window = ttkb.Toplevel(self.window)
        preview_window.title(self._get_text("changelog_preview"))
        preview_window.geometry("640x360")
        preview_window.transient(self.window)
        preview_window.lift()
        preview_window.focus_force()
        text_frame = ttk.Frame(preview_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        colors = theme.get_colors()
        text_widget = tk.Text(
            text_frame,
            font=("Consolas", 11),
            bg=colors["bg"],
            fg=colors["fg"],
            relief="flat",
            borderwidth=0,
            highlightthickness=0
        )
        text_widget.pack(fill="both", expand=True)
        content = self.changelog.generate_markdown()
        text_widget.insert("1.0", content)
        text_widget.configure(state="disabled")

    def _update_status(self, message: str):
        """Update status bar"""
        self.status_bar.configure(text=message)
        if self.status_callback:
            self.status_callback(message)
