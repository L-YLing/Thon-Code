#! /usr/bin/env python3
"""Quick test to verify plugin loading and hook dispatch work correctly."""

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

# Headless mode
os.environ.setdefault("THONCODE_HEADLESS", "1")

# Stub Tk
import types
def _install_stubs():
    def _make(name, attrs=None):
        m = types.ModuleType(name)
        if attrs:
            for k, v in attrs.items():
                setattr(m, k, v)
        sys.modules[name] = m
        return m
    if "tkinter" not in sys.modules:
        class _StubMeta(type):
            def __getattr__(cls, item):
                return _StubMeta(f"{cls.__name__}.{item}", (), {})
        class _Stub(metaclass=_StubMeta):
            def __init__(self, *args, **kwargs):
                pass
            def __getattr__(self, item):
                def _call(*args, **kwargs):
                    return None
                return _call
            def __call__(self, *args, **kwargs):
                return None
        _make("tkinter", {"Misc": _Stub, "Widget": _Stub, "Text": _Stub, "Frame": _Stub, "Label": _Stub, "Menu": _Stub, "END": "end", "INSERT": "insert"})
        _make("tkinter.ttk", {"Notebook": _Stub, "Frame": _Stub, "Label": _Stub, "Style": _Stub})
        _make("tkinter.messagebox", {"askyesnocancel": lambda *a, **kw: True})
_install_stubs()

from libs.plugins import PluginBase, PluginManager

def test_plugin_loading_and_hooks():
    """Test that plugins load and hooks are dispatched correctly."""
    print("=" * 60)
    print("Testing plugin loading and hook dispatch")
    print("=" * 60)
    
    # Create temp plugin directory
    tmp_dir = tempfile.mkdtemp(prefix="thoncode_hook_test_")
    plugin_dir = os.path.join(tmp_dir, "plugins")
    os.makedirs(plugin_dir)
    
    # Create a test plugin
    test_plugin_code = '''
from libs.plugins import PluginBase

class HookTestPlugin(PluginBase):
    name = "hook_test"
    version = "1.0.0"
    description = "Test plugin for hook dispatch"
    
    def __init__(self, api):
        super().__init__(api)
        self.load_called = False
        self.file_open_called = False
        self.last_file_path = None
    
    def on_load(self):
        self.load_called = True
        print("  [plugin] on_load called")
    
    def on_file_open(self, file_path):
        self.file_open_called = True
        self.last_file_path = file_path
        print(f"  [plugin] on_file_open called with: {file_path}")
        return "hook_result"
    
    def on_unload(self):
        print("  [plugin] on_unload called")
'''
    
    plugin_file = os.path.join(plugin_dir, "hook_test.py")
    with open(plugin_file, "w", encoding="utf-8") as f:
        f.write(test_plugin_code)
    
    # Create PluginManager
    mgr = PluginManager()
    
    # Discover and load plugins
    print("\n1. Discovering and loading plugins...")
    count = mgr.discover_and_load(plugin_dir)
    print(f"   Loaded {count} plugin(s)")
    print(f"   Plugin names: {mgr.get_plugin_names()}")
    
    if count != 1:
        print("   FAIL: Expected 1 plugin to load")
        return False
    
    if "hook_test" not in mgr.get_plugin_names():
        print("   FAIL: Plugin 'hook_test' not found")
        return False
    
    # Check on_load was called
    print("\n2. Checking on_load...")
    plugins = mgr.get_plugins()
    plugin = plugins["hook_test"]
    if not plugin.load_called:
        print("   FAIL: on_load was not called")
        return False
    print("   OK: on_load was called")
    
    # Test hook dispatch
    print("\n3. Testing hook dispatch (file_open)...")
    results = mgr.call_hook("file_open", "/test/path.py")
    print(f"   Hook results: {results}")
    
    if not plugin.file_open_called:
        print("   FAIL: on_file_open was not called")
        return False
    
    if plugin.last_file_path != "/test/path.py":
        print(f"   FAIL: Expected file_path '/test/path.py', got '{plugin.last_file_path}'")
        return False
    
    if len(results) != 1 or results[0] != "hook_result":
        print(f"   FAIL: Expected ['hook_result'], got {results}")
        return False
    
    print("   OK: Hook dispatch works correctly")
    
    # Test nonexistent hook
    print("\n4. Testing nonexistent hook...")
    results2 = mgr.call_hook("nonexistent_hook")
    if results2 != []:
        print(f"   FAIL: Expected [], got {results2}")
        return False
    print("   OK: Nonexistent hook returns empty list")
    
    # Test unload
    print("\n5. Testing plugin unload...")
    ok = mgr.unload_plugin("hook_test")
    if not ok:
        print("   FAIL: unload_plugin returned False")
        return False
    if "hook_test" in mgr.get_plugin_names():
        print("   FAIL: Plugin still loaded after unload")
        return False
    print("   OK: Plugin unloaded correctly")
    
    print("\n" + "=" * 60)
    print("All tests PASSED!")
    print("=" * 60)
    
    # Cleanup
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)
    
    return True

if __name__ == "__main__":
    success = test_plugin_loading_and_hooks()
    sys.exit(0 if success else 1)
