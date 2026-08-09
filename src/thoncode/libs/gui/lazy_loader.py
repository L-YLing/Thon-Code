# libs/gui/lazy_loader.py - This is the shared version

import sys
import importlib
from typing import Optional, Any, Dict


class LazyLoader:
    """
    Universal lazy loader for GUI components and heavy libraries.
    Implements singleton pattern to cache imported modules.
    """
    _instances: Dict[str, Any] = {}
    
    @classmethod
    def get(cls, module_path: str, class_name: Optional[str] = None) -> Any:
        """
        Lazy load a module or class.
        
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
    def get_send2trash(cls):
        """Lazy load send2trash library"""
        try:
            return cls.get('send2trash', 'send2trash')
        except ImportError:
            return None
    
    @classmethod
    def get_pil(cls):
        """Lazy load PIL (Pillow) library"""
        try:
            from PIL import Image, ImageTk
            return Image, ImageTk
        except ImportError:
            return None, None
    
    @classmethod
    def clear_cache(cls):
        """Clear all cached imports (useful for testing)"""
        cls._instances.clear()
    
    @classmethod
    def is_cached(cls, module_path: str, class_name: Optional[str] = None) -> bool:
        """Check if a module/class is already cached"""
        cache_key = f"{module_path}:{class_name}" if class_name else module_path
        return cache_key in cls._instances