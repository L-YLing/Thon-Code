# libs/gui/struct_ui.py

import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from libs.struct_handle import get_dir_structure

class StructViewerWindow:
    def __init__(self, parent, root_path=None, status_callback=None):
        self.parent = parent
        self.root_path = root_path or os.getcwd()
        self.status_callback = status_callback
        self.current_data = None
        
        self._create_window()
        self._load_structure()
    
    def _create_window(self):
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("Directory Structure Viewer")
        self.window.geometry("1040x585")
        self.window.transient(self.parent)
        self.window.lift()
        self.window.focus_force()
        
        self._create_widgets()
    
    def _create_widgets(self):
        # Top control frame
        control_frame = ctk.CTkFrame(self.window)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Path entry
        ctk.CTkLabel(control_frame, text="Path:").pack(side="left", padx=(0, 5))
        self.path_entry = ctk.CTkEntry(control_frame, width=400)
        self.path_entry.insert(0, self.root_path)
        self.path_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(control_frame, text="Browse", command=self._browse_path, width=80).pack(side="left", padx=5)
        ctk.CTkButton(control_frame, text="Refresh", command=self._load_structure, width=80).pack(side="left", padx=5)
        
        # Depth control
        ctk.CTkLabel(control_frame, text="Max Depth:").pack(side="left", padx=(10, 5))
        self.depth_var = ctk.StringVar(value="-1")
        depth_entry = ctk.CTkEntry(control_frame, width=50, textvariable=self.depth_var)
        depth_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(control_frame, text="Export JSON", command=self._export_json, width=100).pack(side="right", padx=5)
        ctk.CTkButton(control_frame, text="Export Tree", command=self._export_tree, width=100).pack(side="right", padx=5)
        
        # Format toggle
        self.view_mode = ctk.StringVar(value="tree")
        format_frame = ctk.CTkFrame(self.window)
        format_frame.pack(fill="x", padx=10, pady=2)
        
        ctk.CTkLabel(format_frame, text="View Mode:").pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(format_frame, text="Tree", variable=self.view_mode, value="tree", 
                          command=self._update_display).pack(side="left", padx=5)
        ctk.CTkRadioButton(format_frame, text="JSON", variable=self.view_mode, value="json",
                          command=self._update_display).pack(side="left", padx=5)
        
        # Main display area
        self.display_frame = ctk.CTkFrame(self.window)
        self.display_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self._create_tree_view()
        self._create_json_view()
        
        # Status bar
        self.status_bar = ctk.CTkLabel(self.window, text="Ready", anchor="w", height=25)
        self.status_bar.pack(fill="x", padx=10, pady=5)
    
    def _create_tree_view(self):
        self.tree_frame = ctk.CTkFrame(self.display_frame)
        self.tree_frame.pack(fill="both", expand=True)
        
        # Text widget for tree display
        self.tree_text = tk.Text(self.tree_frame, wrap="none", font=("Consolas", 10), 
                                 bg="#1e1e1e", fg="#d4d4d4", relief="flat")
        self.tree_text.pack(side="left", fill="both", expand=True)
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree_text.yview)
        v_scroll.pack(side="right", fill="y")
        h_scroll = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree_text.xview)
        h_scroll.pack(side="bottom", fill="x")
        self.tree_text.config(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
    
    def _create_json_view(self):
        self.json_frame = ctk.CTkFrame(self.display_frame)
        
        self.json_text = tk.Text(self.json_frame, wrap="none", font=("Consolas", 10),
                                 bg="#1e1e1e", fg="#d4d4d4", relief="flat")
        self.json_text.pack(side="left", fill="both", expand=True)
        
        v_scroll = ttk.Scrollbar(self.json_frame, orient="vertical", command=self.json_text.yview)
        v_scroll.pack(side="right", fill="y")
        h_scroll = ttk.Scrollbar(self.json_frame, orient="horizontal", command=self.json_text.xview)
        h_scroll.pack(side="bottom", fill="x")
        self.json_text.config(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        self.json_frame.pack_forget()
    
    def _load_structure(self):
        """Load directory structure and update display"""
        path = self.path_entry.get().strip()
        if not os.path.exists(path):
            messagebox.showerror("Error", f"Path does not exist: {path}")
            return
        
        try:
            depth = int(self.depth_var.get())
        except ValueError:
            depth = -1
        
        self.root_path = path
        
        try:
            self.current_data = get_dir_structure(
                root_path=path,
                output_format="json",
                max_depth=depth,
                include_file_content=False
            )
            self._update_display()
            self.status_bar.configure(text=f"Loaded: {path} ({self._count_items(self.current_data)} items)")
            if self.status_callback:
                self.status_callback(f"Structure loaded: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load structure: {e}")
            self.status_bar.configure(text=f"Error: {e}")
    
    def _update_display(self):
        """Update display based on current view mode"""
        if not self.current_data:
            return
        
        if self.view_mode.get() == "tree":
            self.tree_frame.pack(fill="both", expand=True)
            self.json_frame.pack_forget()
            
            # Generate tree string
            tree_str = self._dict_to_tree(self.current_data)
            self.tree_text.delete("1.0", "end")
            self.tree_text.insert("1.0", tree_str)
        else:
            self.json_frame.pack(fill="both", expand=True)
            self.tree_frame.pack_forget()
            
            # Display JSON
            json_str = json.dumps(self.current_data, indent=2, ensure_ascii=False)
            self.json_text.delete("1.0", "end")
            self.json_text.insert("1.0", json_str)
    
    def _dict_to_tree(self, data, prefix="", is_last=True):
        """Convert dict to tree string"""
        lines = []
        name = data.get("name", "")
        
        if data.get("type") == "dir":
            connector = "└── " if is_last else "├── "
            lines.append(prefix + connector + name + "/")
            children = data.get("children", [])
            if children:
                child_prefix = prefix + ("    " if is_last else "│   ")
                for i, child in enumerate(children):
                    is_last_child = (i == len(children) - 1)
                    lines.append(self._dict_to_tree(child, child_prefix, is_last_child))
        else:
            connector = "└── " if is_last else "├── "
            lines.append(prefix + connector + name)
        
        return "\n".join(lines)
    
    def _count_items(self, data):
        """Count total items in structure"""
        count = 1
        if data.get("type") == "dir":
            for child in data.get("children", []):
                count += self._count_items(child)
        return count
    
    def _browse_path(self):
        """Browse for directory"""
        path = filedialog.askdirectory(title="Select Directory", initialdir=self.root_path)
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)
            self._load_structure()
    
    def _export_json(self):
        """Export current structure as JSON"""
        if not self.current_data:
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.current_data, f, indent=2, ensure_ascii=False)
                self.status_bar.configure(text=f"Exported to: {file_path}")
                if self.status_callback:
                    self.status_callback(f"Exported JSON: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {e}")
    
    def _export_tree(self):
        """Export current structure as tree text"""
        if not self.current_data:
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            try:
                tree_str = self._dict_to_tree(self.current_data)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(tree_str)
                self.status_bar.configure(text=f"Exported to: {file_path}")
                if self.status_callback:
                    self.status_callback(f"Exported tree: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {e}")