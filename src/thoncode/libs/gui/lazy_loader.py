# libs/gui/lazy_loader.py - Shared lazy loader for GUI components

import sys
import importlib
from typing import Optional, Any, Dict


class LazyLoader:
    """Universal lazy loader for GUI components and heavy libraries.

    Implements singleton pattern to cache imported modules.
    Supports unloading modules to free memory when components are closed.
    """
    _instances: Dict[str, Any] = {}

    @classmethod
    def get(cls, module_path: str, class_name: Optional[str] = None) -> Any:
        """Lazy load a module or class.

        Args:
            module_path: Full module path (e.g., 'libs.gui.settings_win')
            class_name: Optional class name to extract from module

        Returns:
            The loaded module or class
        """
        cache_key = f"{module_path}:{class_name}" if class_name else module_path

        if cache_key in cls._instances:
            return cls._instances[cache_key]

        try:
            module = importlib.import_module(module_path)

            if class_name:
                result = getattr(module, class_name)
            else:
                result = module

            cls._instances[cache_key] = result
            return result

        except ImportError as e:
            raise ImportError(f"Failed to lazy load {module_path}: {e}")
        except AttributeError as e:
            raise AttributeError(f"Class '{class_name}' not found in {module_path}: {e}")

    @classmethod
    def unload(cls, module_path: str) -> bool:
        """Unload a module and all its cached classes to free memory.

        Args:
            module_path: Module path to unload (e.g., 'libs.gui.editor_manager')

        Returns:
            True if module was found and unloaded, False otherwise
        """
        removed = False
        keys_to_remove = [k for k in cls._instances if k.startswith(module_path)]
        for key in keys_to_remove:
            del cls._instances[key]
            removed = True

        if module_path in sys.modules:
            del sys.modules[module_path]
            removed = True

        return removed

    @classmethod
    def get_send2trash(cls):
        """Lazy load send2trash library."""
        try:
            return cls.get('send2trash', 'send2trash')
        except ImportError:
            return None

    @classmethod
    def get_pil(cls):
        """Lazy load PIL (Pillow) library."""
        try:
            from PIL import Image, ImageTk
            return Image, ImageTk
        except ImportError:
            return None, None

    @classmethod
    def clear_cache(cls):
        """Clear all cached imports (useful for testing)."""
        cls._instances.clear()

    @classmethod
    def is_cached(cls, module_path: str, class_name: Optional[str] = None) -> bool:
        """Check if a module/class is already cached.

        Args:
            module_path: Module path
            class_name: Optional class name

        Returns:
            True if the module/class is cached
        """
        cache_key = f"{module_path}:{class_name}" if class_name else module_path
        return cache_key in cls._instances