#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui-libs",
    "Name": "Thon Code Editor Package",
    "Path": ".main.libs.gui_libs.code_editor",
    "Entrance": "main.py"
}

"""
Code editor subpackage for gui_libs.

Provides Canvas-based code editor components with syntax highlighting,
gutter display, and auto-completion support.
"""

from libs.gui_libs.code_editor.canvas_editor import CanvasCodeEditor
from libs.gui_libs.code_editor.editor_gutter import EditorGutter

__all__ = ["CanvasCodeEditor", "EditorGutter"]