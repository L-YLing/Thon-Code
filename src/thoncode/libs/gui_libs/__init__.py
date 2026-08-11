#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui-libs",
    "Name": "Thon Code GUI Libraries",
    "Path": ".main.libs.gui_libs",
    "Entrance": "main.py"
}

"""
GUI Libraries subpackage for ThonCode.

Provides reusable GUI components:
- style_system: Centralized theming and style management
- base: Abstract base classes for widget interfaces
- code_editor: Canvas-based code editor with syntax highlighting
- file_tree: Canvas-based file tree with expand/collapse
"""

__all__ = ["style_system", "base", "code_editor", "file_tree"]