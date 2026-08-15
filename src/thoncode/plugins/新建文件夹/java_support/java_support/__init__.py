#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-plugin-java-support",
    "Name": "Java Language Support Plugin",
    "Path": ".main.plugins.java_support",
    "Entrance": "main.py"
}

"""Multi-file example plugin providing Java syntax highlighting,
auto-completion seed symbols and a custom Java symbol extractor.

Files:
    __init__.py            - PluginBase entry point (loads subs below)
    highlight_groups.py    - Java keyword groups for EditorHighlight
    completion_symbols.py  - Representative java.lang/java.util builtins
    import_parser.py       - Java symbol extractor + import path resolver

The plugin demonstrates the PERMISSION_HIGHLIGHT_EXTEND permission, and
uses the PluginAPI completion/navigation registries (which do not require
extra permissions because they extend rather than modify host state).
"""

import os

from libs.plugins import (
    PluginBase,
    PERMISSION_HIGHLIGHT_EXTEND,
    PERMISSION_MENU_REGISTER,
)


class JavaSupportPlugin(PluginBase):
    """Complex (multi-file) Java plugin."""

    name = "java_support"
    version = "1.0.0"
    description = (
        "Java language support: syntax highlighting, auto-completion "
        "builtins, custom symbol extractor for go-to-definition."
    )
    author = "Thon Code"
    permissions = [
        PERMISSION_HIGHLIGHT_EXTEND,
        PERMISSION_MENU_REGISTER,
    ]
    # Dependencies: none. A real plugin might depend on e.g. a jdk_tools plugin.
    dependencies = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_load(self) -> None:
        api = self.api
        logger = api.get_logger(self.name)
        logger.info("Java support plugin v%s loading...", self.version)

        # 1. Syntax highlighting groups (needs PERMISSION_HIGHLIGHT_EXTEND)
        from . import highlight_groups as _hg
        for lang_or_ext, groups in _hg.HIGHLIGHT_BINDINGS:
            ok = api.add_syntax_groups(lang_or_ext, groups)
            logger.debug("add_syntax_groups(%s) -> %s", lang_or_ext, ok)

        # 2. Seed completion with java.lang / java.util built-in classes.
        from . import completion_symbols as _cs
        ok = api.register_builtin_symbols(_cs.LANG_PATTERNS, _cs.BUILTIN_SYMBOLS)
        logger.debug("register_builtin_symbols(java) -> %s", ok)

        # 3. Custom Java extractor + import resolver (for go-to-def).
        from . import import_parser as _ip
        ok = api.register_symbol_extractor("java", _ip.extract_java_symbols)
        logger.debug("register_symbol_extractor(java) -> %s", ok)
        ok = api.register_symbol_extractor(".java", _ip.extract_java_symbols)
        ok = api.register_import_resolver("java", _ip.resolve_java_import)
        logger.debug("register_import_resolver(java) -> %s", ok)
        ok = api.register_import_resolver(".java", _ip.resolve_java_import)

        # 4. Add a menu entry demonstrating the plugin menu hook (optional).
        #    We register under "Help > About Java Support".
        try:
            api.add_menu_entry(
                menu_path=["Help"],
                label=self.api.get_i18n().get(
                    "plugins.java.about",
                    "About Java Support",
                ),
                callback=self._show_about,
                accelerator=None,
            )
        except Exception as exc:  # pragma: no cover - menu API non-fatal
            logger.debug("add_menu_entry skipped: %s", exc)

        logger.info("Java support plugin loaded.")

    def on_unload(self) -> None:
        logger = self.api.get_logger(self.name)
        logger.info("Java support plugin unloaded.")

    # ------------------------------------------------------------------
    # Hooks (optional examples of the plugin event system)
    # ------------------------------------------------------------------

    def on_file_open(self, file_path: str) -> None:
        if not file_path:
            return
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".java":
            logger = self.api.get_logger(self.name)
            logger.debug("Java file opened: %s", file_path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _show_about(self) -> None:
        i18n = self.api.get_i18n()
        from tkinter import messagebox
        mw = self.api.get_main_window()
        parent = mw if mw is not None else None
        messagebox.showinfo(
            i18n.get("plugins.java.about_title", "Java Language Support"),
            (
                "Java Language Support plugin v{ver}\n\n"
                "- {gr} highlight keyword groups\n"
                "- {bs} builtin completion symbols\n"
                "- Custom Java symbol extractor & import resolver\n"
                "Loaded via: {path}"
            ).format(
                ver=self.version,
                gr=len([g for g in _groups_flat()]),
                bs=len(_builtin_count()),
                path=os.path.dirname(os.path.abspath(__file__)),
            ),
            parent=parent,
        )


def _groups_flat():
    from . import highlight_groups as _hg
    for _, groups in _hg.HIGHLIGHT_BINDINGS:
        for g in groups:
            yield g


def _builtin_count():
    from . import completion_symbols as _cs
    return _cs.BUILTIN_SYMBOLS


# Re-export PluginClass alias so the PluginManager loader works for both
# `class Foo(PluginBase):` and `PluginClass` naming conventions.
PluginClass = JavaSupportPlugin
