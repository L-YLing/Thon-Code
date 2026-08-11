#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui-libs",
    "Name": "Thon Code Style System",
    "Path": ".main.libs.gui_libs.style_system",
    "Entrance": "main.py"
}

"""
Style system module for gui_libs components.
Provides config-driven theming for colors, fonts, borders, and spacing.
"""

import json
import os
import copy
from typing import Any, Dict, List, Optional


# Default style configuration
DEFAULT_STYLE: dict = {
    "editor": {
        "font_family": "Consolas",
        "font_size": 12,
        "line_height": 20,
        "bg": "#282c34",
        "fg": "#abb2bf",
        "fg_dim": "#5c6370",
        "cursor": "#528bff",
        "selection_bg": "#264f78",
        "selection_fg": "#ffffff",
        "line_number_bg": "#282c34",
        "line_number_fg": "#4b5263",
        "line_number_width": 50,
        "fold_gutter_bg": "#282c34",
        "fold_gutter_width": 20,
        "border_width": 0,
        "pad_x": 4,
        "pad_y": 4,
    },
    "highlight": {
        "keyword": "#c678dd",
        "builtin": "#56b6c2",
        "constant": "#56b6c2",
        "function": "#61afef",
        "classname": "#e5c07b",
        "string": "#98c379",
        "number": "#d19a66",
        "comment": "#7f848e",
        "type": "#e06c75",
        "variable": "#e06c75",
        "operator": "#56b6c2",
        "bracket_match_bg": "#3e4451",
    },
    "tree": {
        "font_family": "Microsoft YaHei",
        "font_size": 10,
        "bg": "#282c34",
        "fg": "#abb2bf",
        "fg_dim": "#5c6370",
        "selection_bg": "#264f78",
        "selection_fg": "#ffffff",
        "hover_bg": "#3e4451",
        "icon_size": 16,
        "indent_width": 16,
        "row_height": 22,
        "border_width": 0,
        "pad_x": 4,
        "pad_y": 2,
        "folder_icon": "📁",
        "file_icon": "📄",
        "folder_open_icon": "📂",
        "expand_indicator": "▾",
        "collapse_indicator": "▸",
    },
}


class StyleSystem:
    """Centralized style configuration manager for gui_libs components.

    Supports loading styles from JSON config files or setting programmatically.
    Provides singleton-style access to current style configuration.
    """

    _instance: Optional["StyleSystem"] = None
    _styles: dict = {}
    _current_style: str = "default"
    _listeners: List = []

    def __new__(cls) -> "StyleSystem":
        """Create or return singleton instance.

        Returns:
            StyleSystem: Singleton instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize style system with default styles."""
        if self._initialized:
            return
        self._initialized = True
        self._styles = {"default": copy.deepcopy(DEFAULT_STYLE)}
        self._current_style = "default"
        self._listeners = []

    def get_style(self, component: str = "") -> dict:
        """Get current style configuration for a component.

        Args:
            component: Component name (e.g., 'editor', 'tree', 'highlight')

        Returns:
            dict: Style configuration for the specified component or full config
        """
        style = self._styles.get(self._current_style, {})
        if component:
            return style.get(component, {})
        return style

    def get_value(self, component: str, key: str, default: Any = None) -> Any:
        """Get a specific style value.

        Args:
            component: Component name
            key: Style property key
            default: Default value if key not found

        Returns:
            The style value or default
        """
        style = self.get_style(component)
        return style.get(key, default)

    def set_style(self, component: str, key: str, value: Any) -> None:
        """Set a single style value for a component.

        Args:
            component: Component name
            key: Style property key
            value: New value to set
        """
        style = self._styles.get(self._current_style, {})
        if component not in style:
            style[component] = {}
        style[component][key] = value
        self._notify_listeners()

    def set_component_style(self, component: str, style_dict: dict) -> None:
        """Set multiple style values for a component.

        Args:
            component: Component name
            style_dict: Dictionary of style properties to set
        """
        style = self._styles.get(self._current_style, {})
        if component not in style:
            style[component] = {}
        style[component].update(style_dict)
        self._notify_listeners()

    def register_style(self, name: str, style_config: dict) -> None:
        """Register a named style configuration.

        Args:
            name: Style name identifier
            style_config: Full style configuration dictionary
        """
        self._styles[name] = copy.deepcopy(style_config)

    def apply_style(self, name: str) -> bool:
        """Apply a registered style by name.

        Args:
            name: Style name to apply

        Returns:
            bool: True if style was found and applied
        """
        if name in self._styles:
            self._current_style = name
            self._notify_listeners()
            return True
        return False

    def get_current_style_name(self) -> str:
        """Get the name of the currently applied style.

        Returns:
            str: Current style name
        """
        return self._current_style

    def load_from_file(self, file_path: str) -> bool:
        """Load a style configuration from a JSON file.

        Args:
            file_path: Path to JSON style file

        Returns:
            bool: True if file was loaded successfully
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            style_name = os.path.splitext(os.path.basename(file_path))[0]
            self.register_style(style_name, config)
            self.apply_style(style_name)
            return True
        except (json.JSONDecodeError, IOError):
            return False

    def save_to_file(self, file_path: str, name: str = "") -> bool:
        """Save a style configuration to a JSON file.

        Args:
            file_path: Path to save the JSON file
            name: Style name to save (empty for current style)

        Returns:
            bool: True if saved successfully
        """
        style_name = name or self._current_style
        config = self._styles.get(style_name, {})
        try:
            os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except IOError:
            return False

    def add_listener(self, callback) -> None:
        """Register a callback for style change notifications.

        Args:
            callback: Callable to invoke when style changes
        """
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback) -> None:
        """Remove a style change listener.

        Args:
            callback: Callback to remove
        """
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        """Notify all registered listeners of style changes."""
        for callback in self._listeners:
            try:
                callback()
            except Exception:
                pass

    def reset(self) -> None:
        """Reset to default style and clear all registrations."""
        self._styles = {"default": copy.deepcopy(DEFAULT_STYLE)}
        self._current_style = "default"
        self._notify_listeners()