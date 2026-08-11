#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui-libs",
    "Name": "Thon Code GUI Base Classes",
    "Path": ".main.libs.gui_libs.base",
    "Entrance": "main.py"
}

"""
Abstract base classes and interfaces for gui_libs components.
Provides consistent contracts for code editors, file trees, and widgets.
"""

import abc
from typing import Any, Callable, Dict, List, Optional


class BaseWidget(abc.ABC):
    """Abstract base class for all gui_libs widgets.

    Defines the common interface for widget lifecycle, styling, and event handling.
    """

    def __init__(self, parent: Any) -> None:
        """Initialize the base widget.

        Args:
            parent: Parent Tkinter widget
        """
        self.parent = parent
        self._widget = None
        self._destroyed = False

    @abc.abstractmethod
    def create_widget(self) -> Any:
        """Create and return the underlying Tkinter widget.

        Returns:
            The created Tkinter widget
        """
        pass

    @abc.abstractmethod
    def pack(self, **kwargs) -> None:
        """Pack the widget into its parent.

        Args:
            **kwargs: Pack configuration options
        """
        pass

    @abc.abstractmethod
    def grid(self, **kwargs) -> None:
        """Grid the widget into its parent.

        Args:
            **kwargs: Grid configuration options
        """
        pass

    @abc.abstractmethod
    def destroy(self) -> None:
        """Destroy the widget and free resources."""
        pass

    def get_widget(self) -> Any:
        """Get the underlying Tkinter widget.

        Returns:
            The Tkinter widget instance
        """
        return self._widget

    @property
    def is_destroyed(self) -> bool:
        """Check if the widget has been destroyed.

        Returns:
            bool: True if widget is destroyed
        """
        return self._destroyed

    def configure(self, **kwargs) -> None:
        """Configure widget options.

        Args:
            **kwargs: Widget configuration options
        """
        if self._widget and not self._destroyed:
            self._widget.configure(**kwargs)


class StyleProvider(abc.ABC):
    """Abstract interface for components that support style configuration."""

    @abc.abstractmethod
    def apply_style(self, style_name: str) -> None:
        """Apply a named style configuration.

        Args:
            style_name: Name of the style to apply
        """
        pass

    @abc.abstractmethod
    def get_style_value(self, key: str, default: Any = None) -> Any:
        """Get the current value of a style property.

        Args:
            key: Style property key
            default: Default value if key not found

        Returns:
            The style value
        """
        pass

    @abc.abstractmethod
    def set_style_value(self, key: str, value: Any) -> None:
        """Set a single style property.

        Args:
            key: Style property key
            value: New value
        """
        pass


class EventHandler(abc.ABC):
    """Abstract interface for components that handle keyboard and mouse events."""

    @abc.abstractmethod
    def on_key_press(self, event: Any) -> Optional[str]:
        """Handle key press events.

        Args:
            event: The keyboard event

        Returns:
            Optional[str]: 'break' to prevent propagation, None to allow it
        """
        pass

    @abc.abstractmethod
    def on_mouse_click(self, event: Any) -> None:
        """Handle mouse click events.

        Args:
            event: The mouse event
        """
        pass

    @abc.abstractmethod
    def on_mouse_drag(self, event: Any) -> None:
        """Handle mouse drag events.

        Args:
            event: The mouse event
        """
        pass

    @abc.abstractmethod
    def on_mouse_hover(self, event: Any) -> None:
        """Handle mouse hover/enter events.

        Args:
            event: The mouse event
        """
        pass


class LazyLoadable(abc.ABC):
    """Abstract interface for components that support lazy loading."""

    @abc.abstractmethod
    def load(self) -> None:
        """Load and initialize the component on demand."""
        pass

    @abc.abstractmethod
    def unload(self) -> None:
        """Unload and release component resources."""
        pass

    @property
    def is_loaded(self) -> bool:
        """Check if the component is currently loaded.

        Returns:
            bool: True if loaded
        """
        return False