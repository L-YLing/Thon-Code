"""Quick syntax + import sanity check for upgraded plugin modules.

This script is a lightweight alternative to running the full unittest
suite when PowerShell ExecutionPolicy blocks the test runner. It verifies
that the modified modules compile and can be imported (it does not spin
up a Tk window so it works in headless environments).

Run with:
    python quick_import_sanity.py
"""

import os
import sys
import traceback
import types

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)  # src/thoncode/
# Only put the thoncode package root on sys.path so `libs.*` and
# `plugins.*` live under unambiguous paths (libs/plugins no longer
# shadows user-plugins plugins/ folder).
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

# Don't launch Tk during sanity checks
os.environ.setdefault("THONCODE_HEADLESS", "1")


# ---------------------------------------------------------------------------
# Stub Tk modules so headless imports don't fail when sandbox Python lacks
# the tkinter extension.
# ---------------------------------------------------------------------------
def _install_stubs() -> None:
    def _make(name, attrs=None):
        m = types.ModuleType(name)
        if attrs:
            for k, v in attrs.items():
                setattr(m, k, v)
        sys.modules[name] = m
        return m

    if "tkinter" not in sys.modules:
        import abc as _abc

        class _StubMeta(type):
            def __getattr__(cls, item):  # noqa: N805
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

        tk = _make("tkinter", {
            "Text": _Stub,
            "Toplevel": _Stub,
            "Frame": _Stub,
            "Label": _Stub,
            "Button": _Stub,
            "Entry": _Stub,
            "Canvas": _Stub,
            "Menu": _Stub,
            "Scrollbar": _Stub,
            "Listbox": _Stub,
            "StringVar": _Stub,
            "IntVar": _Stub,
            "BooleanVar": _Stub,
            "Misc": _Stub,
            "Widget": _Stub,
            "END": "end",
            "INSERT": "insert",
            "SEL_FIRST": "sel.first",
            "SEL_LAST": "sel.last",
            "W": "w", "E": "e", "N": "n", "S": "s",
            "BOTH": "both", "X": "x", "Y": "y",
            "LEFT": "left", "RIGHT": "right",
            "TOP": "top", "BOTTOM": "bottom",
            "ALL": "all", "NONE": "none",
            "NORMAL": "normal", "DISABLED": "disabled",
        })

        ttk = _make("tkinter.ttk", {
            "Notebook": _Stub,
            "Frame": _Stub,
            "LabelFrame": _Stub,
            "Button": _Stub,
            "Label": _Stub,
            "Entry": _Stub,
            "Combobox": _Stub,
            "Treeview": _Stub,
            "Scrollbar": _Stub,
            "Progressbar": _Stub,
            "Separator": _Stub,
            "Style": _Stub,
        })
        setattr(tk, "ttk", ttk)
        tk_constants = _make("tkinter.constants", {
            "END": "end", "INSERT": "insert",
            "BOTH": "both", "X": "x", "Y": "y",
        })
        setattr(tk, "constants", tk_constants)
        messagebox = _make("tkinter.messagebox", {
            "showinfo": lambda *a, **k: None,
            "showerror": lambda *a, **k: None,
            "showwarning": lambda *a, **k: None,
            "askyesno": lambda *a, **k: True,
            "askyesnocancel": lambda *a, **k: None,
            "askokcancel": lambda *a, **k: True,
        })
        setattr(tk, "messagebox", messagebox)
        filedialog = _make("tkinter.filedialog", {
            "askopenfilename": lambda **k: "",
            "asksaveasfilename": lambda **k: "",
            "askdirectory": lambda **k: "",
        })
        setattr(tk, "filedialog", filedialog)
        font = _make("tkinter.font", {
            "Font": _Stub,
            "nametofont": lambda *a: _Stub(),
        })
        setattr(tk, "font", font)
        # ttkbootstrap stub
        ttkb = _make("ttkbootstrap", {
            "Window": _Stub,
            "Style": _Stub,
            "Frame": _Stub,
            "Button": _Stub,
            "Label": _Stub,
            "Entry": _Stub,
            "Notebook": _Stub,
            "Combobox": _Stub,
            "Treeview": _Stub,
            "Scrollbar": _Stub,
            "LabelFrame": _Stub,
            "Dialog": _Stub,
        })

    # Stub the theme, style_system and lazy_loader modules if they need Tk.
    stub_names = [
        "libs.gui.theme",
        "libs.gui_libs",
        "libs.gui_libs.style_system",
        "libs.gui_libs.lazy_loader",
    ]
    for sn in stub_names:
        if sn not in sys.modules:
            mod = _make(sn)
            if sn.endswith("lazy_loader"):
                class _LL:
                    @staticmethod
                    def get(module, symbol):
                        return None
                mod.LazyLoader = _LL
            if sn.endswith("style_system"):
                class _SS:
                    get = lambda self, *a, **k: {}  # noqa: E731
                mod.StyleSystem = _SS
            if sn.endswith("theme"):
                mod.get_theme = lambda: "default"
                mod.get_accent_color = lambda: "#2D7FF9"


_install_stubs()


MODULES = [
    "libs.plugins.plugin_base",
    "libs.plugins.plugin_manager",
    "libs.plugins.plugin_api",
    "libs.plugins.plugin_marketplace",
    "libs.i18n",
    "libs.gui.symbol_loader",
    "libs.gui.editor_completion",
    "libs.gui.editor_navigation",
    "libs.gui.editor_tab_manager",
    "plugins.java_support.highlight_groups",
    "plugins.java_support.completion_symbols",
    "plugins.java_support.import_parser",
    "plugins.java_support",
    "plugins.rust_support",
]


def main() -> int:
    print("=" * 60)
    print("Quick import sanity check")
    print("=" * 60)
    failed = 0
    for mod in MODULES:
        try:
            __import__(mod)
            print("OK   ", mod)
        except Exception:
            failed += 1
            print("FAIL ", mod)
            traceback.print_exc()
    # Version constraint smoke test (no Tk required)
    try:
        from libs.plugins.plugin_manager import (
            _check_version_constraint,
            resolve_plugin_dirs,
        )
        assert _check_version_constraint("1.5.0", ">=1.0,<2.0")
        assert not _check_version_constraint("2.0.0", ">=1.0,<2.0")
        print("OK    plugin_manager version constraints")
    except Exception:
        failed += 1
        print("FAIL  plugin_manager version constraints")
        traceback.print_exc()
    # Marketplace helper smoke test
    try:
        from libs.plugins.plugin_marketplace import PluginMarketplace
        tmp_dir = os.path.join(os.path.dirname(HERE), "test", "_market_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        d = PluginMarketplace.user_writable_plugin_dir(tmp_dir)
        assert os.path.isdir(d)
        # Install -> uninstall cycle for single-file & package
        single = os.path.join(d, "x.py")
        with open(single, "w", encoding="utf-8") as f:
            f.write("#\n")
        assert PluginMarketplace.uninstall_plugin("x", d)
        assert not os.path.exists(single)
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print("OK    plugin_marketplace install/uninstall helpers")
    except Exception:
        failed += 1
        print("FAIL  plugin_marketplace install/uninstall helpers")
        traceback.print_exc()
    # SymbolLoader basic smoke (no tk required)
    try:
        from libs.gui.symbol_loader import SymbolLoaderRegistry
        reg = SymbolLoaderRegistry.instance()
        test_src = """
class Foo:
    def bar(self, x):
        y = x + 1
        return y
"""
        symbols, imports = reg.index_text(test_src, "python")
        class_names = {s["name"] for s in symbols if s["kind"] == "class"}
        func_names = {s["name"] for s in symbols if s["kind"] == "method"}
        assert "Foo" in class_names, class_names
        assert "bar" in func_names, func_names
        print("OK    SymbolLoaderRegistry basic Python indexing")
    except Exception:
        failed += 1
        print("FAIL  SymbolLoaderRegistry basic Python indexing")
        traceback.print_exc()
    print("=" * 60)
    print(f"Result: {'PASS' if failed == 0 else 'FAIL'}  failures={failed}")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
