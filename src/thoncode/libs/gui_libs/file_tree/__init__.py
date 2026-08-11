#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui-libs",
    "Name": "Thon Code File Tree Package",
    "Path": ".main.libs.gui_libs.file_tree",
    "Entrance": "main.py"
}

"""
File tree subpackage for gui_libs.

Provides Canvas-based file tree components with customizable styling.
"""

from libs.gui_libs.file_tree.canvas_tree import CanvasFileTree, TreeNode

__all__ = ["CanvasFileTree", "TreeNode"]