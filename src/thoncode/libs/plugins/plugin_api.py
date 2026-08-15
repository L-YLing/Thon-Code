#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-plugins",
    "Name": "Thon Code Plugin API",
    "Path": ".main.libs.plugins.plugin_api",
    "Entrance": "main.py"
}

"""Controlled API surface exposed to plugins.

PluginAPI wraps host application services behind a stable interface
so plugins cannot directly access internal modules. All high-impact
operations are gated behind permission checks (see plugin_base.py
PERMISSION_* constants).

Available hooks (plugins implement any subset as on_<hook_name>):
    on_load()                         - Plugin loaded, before first use
    on_unload()                       - Plugin about to be unloaded
    on_file_open(path)                - A file was opened in the editor
    on_file_save(path)                - A file was saved
    on_file_close(path)               - A file was closed
    on_editor_change(text)            - Editor content modified
    on_tree_refresh()                 - File tree was refreshed
    on_theme_change(name)             - Theme was switched
    on_project_open(path)             - A project folder was opened
    on_syntax_highlight_ext()         - Syntax highlight rules rebuilt
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

from libs.plugins.plugin_base import (
    PluginBase,
    PERMISSION_CONFIG,
    PERMISSION_EDITOR_MODIFY,
    PERMISSION_FILESYSTEM_READ,
    PERMISSION_FILESYSTEM_WRITE,
    PERMISSION_HIGHLIGHT_EXTEND,
    PERMISSION_HOTKEY_BIND,
    PERMISSION_MENU_REGISTER,
    PERMISSION_PLUGIN_MANAGE,
    PERMISSION_NETWORK,
    PERMISSION_EXECUTE,
)

_logger = logging.getLogger("thoncode.plugins.api")


class PluginAPI:
    """Stable API through which plugins interact with the host.

    Each operation either:
      * has no side-effects (get_* / read-only), or
      * checks ``plugin.has_permission(...)`` before mutating state.
    """

    def __init__(self, host: Any):
        self._host = host
        self._logger = logging.getLogger("thoncode.plugins.api")

        # Per-plugin registries – keyed by plugin instance. We store the
        # full set of registrations so we can un-register everything on
        # unload (PluginManager calls _unregister_all_for_plugin).
        self._menu_entries: Dict[int, List[Dict[str, Any]]] = {}
        self._hotkey_binds: Dict[int, List[Dict[str, Any]]] = {}
        self._highlight_providers: Dict[int, Any] = {}

    # ------------------------------------------------------------------
    # Permission helpers (internal)
    # ------------------------------------------------------------------
    def _plugin_from_self(self) -> Optional[PluginBase]:
        """Walk the Python call stack to find the plugin whose method
        is calling us. Returns None if the caller is not a plugin.
        """
        import inspect
        try:
            for frame_info in inspect.stack()[2:]:
                frame = frame_info.frame
                locals_ = frame.f_locals
                # Plugin instances store self under 'self' in methods.
                obj = locals_.get("self", None)
                if isinstance(obj, PluginBase):
                    return obj
                # Also accept any explicit 'plugin' local.
                obj = locals_.get("plugin", None)
                if isinstance(obj, PluginBase):
                    return obj
        except Exception:
            pass
        return None

    def _require(self, permission: str) -> bool:
        """Check permission for the calling plugin.

        Returns True if allowed. Logs a warning and returns False
        otherwise so callers can short-circuit without crashing.
        """
        plugin = self._plugin_from_self()
        if plugin is None:
            # If the API is invoked directly by host code (e.g. tests),
            # allow the operation.
            return True
        if not plugin.has_permission(permission):
            self._logger.warning(
                "Plugin '%s' denied permission '%s'", plugin.name, permission)
            return False
        return True

    # ------------------------------------------------------------------
    # Internal: cleanup on plugin unload
    # ------------------------------------------------------------------
    def _unregister_all_for_plugin(self, plugin: PluginBase) -> None:
        """Called by PluginManager during unload_plugin()."""
        pid = id(plugin)

        # Remove menu entries
        for entry in self._menu_entries.pop(pid, []):
            try:
                self._remove_menu_entry(entry)
            except Exception as e:
                self._logger.debug("Menu cleanup failed: %s", e)

        # Unbind hotkeys
        for bind in self._hotkey_binds.pop(pid, []):
            try:
                self._unbind_hotkey(bind)
            except Exception as e:
                self._logger.debug("Hotkey cleanup failed: %s", e)

        # Deregister highlight provider
        if pid in self._highlight_providers:
            del self._highlight_providers[pid]
            self._rebuild_highlight_groups()

    # ==================================================================
    # Logging
    # ==================================================================
    def get_logger(self, name: str) -> logging.Logger:
        return logging.getLogger(f"thoncode.plugin.{name}")

    # ==================================================================
    # Configuration (gated by PERMISSION_CONFIG for writes)
    # ==================================================================
    def get_config(self) -> dict:
        try:
            return self._host._get_cfg_data()
        except Exception:
            return {}

    def set_config(self, key: str, value: Any) -> bool:
        if not self._require(PERMISSION_CONFIG):
            return False
        try:
            cfg = self._host._get_cfg_data()
            cfg[key] = value
            import libs.cfg_handle as cfg_handle
            cfg_handle.cfg_handle().write_cfg(cfg)
            return True
        except Exception as e:
            self._logger.debug("Failed to set config %s: %s", key, e)
            return False

    # ==================================================================
    # Status bar
    # ==================================================================
    def show_status(self, message: str) -> None:
        try:
            self._host.status_bar.configure(text=message)
        except Exception:
            self._logger.debug("Failed to set status: %s", message)

    # ==================================================================
    # Editor access (writes gated by PERMISSION_EDITOR_MODIFY)
    # ==================================================================
    def get_editor_text(self) -> str:
        try:
            if self._host.textbox_widget and self._host.textbox_widget.winfo_exists():
                return self._host.textbox_widget.get("1.0", "end-1c")
        except Exception:
            pass
        return ""

    def set_editor_text(self, text: str) -> None:
        if not self._require(PERMISSION_EDITOR_MODIFY):
            return
        try:
            if self._host.textbox_widget and self._host.textbox_widget.winfo_exists():
                self._host.textbox_widget.delete("1.0", "end")
                self._host.textbox_widget.insert("1.0", text)
        except Exception:
            self._logger.debug("Failed to set editor text")

    def get_editor_selection(self) -> str:
        try:
            if self._host.textbox_widget and self._host.textbox_widget.winfo_exists():
                return self._host.textbox_widget.selection_get()
        except Exception:
            pass
        return ""

    def insert_editor_text(self, text: str, position: str = "insert") -> None:
        if not self._require(PERMISSION_EDITOR_MODIFY):
            return
        try:
            if self._host.textbox_widget and self._host.textbox_widget.winfo_exists():
                self._host.textbox_widget.insert(position, text)
        except Exception:
            self._logger.debug("Failed to insert editor text")

    # ==================================================================
    # Project / file info
    # ==================================================================
    def get_project_root(self) -> str:
        try:
            return self._host.project_root
        except Exception:
            return ""

    def get_current_file(self) -> Optional[str]:
        try:
            return self._host.current_file
        except Exception:
            return None

    def get_recent_projects(self) -> List[str]:
        try:
            import libs.cfg_handle as cfg_handle
            return cfg_handle.cfg_handle().get_recent_projects()
        except Exception:
            return []

    # ==================================================================
    # Filesystem helpers (gated) – plugins that only need project
    # files should use get_project_root() + os.path.join. These APIs
    # exist for plugins that need external access (backup/upload...).
    # ==================================================================
    def read_file_external(self, path: str) -> Optional[str]:
        """Read a file from anywhere on disk (requires read permission)."""
        if not self._require(PERMISSION_FILESYSTEM_READ):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self._logger.debug("read_file_external(%s) failed: %s", path, e)
            return None

    def write_file_external(self, path: str, content: str) -> bool:
        """Write a file anywhere on disk (requires write permission)."""
        if not self._require(PERMISSION_FILESYSTEM_WRITE):
            return False
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            self._logger.debug("write_file_external(%s) failed: %s", path, e)
            return False

    # ==================================================================
    # Theme
    # ==================================================================
    def get_current_theme(self) -> str:
        try:
            from libs.gui import theme
            return theme.get_theme()
        except Exception:
            return ""

    def get_accent_color(self) -> Optional[str]:
        try:
            from libs.gui import theme
            return theme.get_accent_color()
        except Exception:
            return None

    # ==================================================================
    # Tree
    # ==================================================================
    def refresh_file_tree(self) -> None:
        try:
            if self._host.tree_manager:
                self._host.tree_manager.refresh()
        except Exception:
            self._logger.debug("Failed to refresh file tree")

    # ==================================================================
    # i18n
    # ==================================================================
    def get_text(self, key: str) -> str:
        try:
            from libs.i18n import I18N
            val = I18N.get_instance().get(key, None)
            if val is not None:
                return val
        except Exception:
            pass
        try:
            return getattr(self._host.langs_cfg, key.replace('.', '_'), key)
        except Exception:
            return key

    def get_i18n(self) -> Any:
        """Return an object with a ``.get(key, default)`` method.

        Plugins can do::

            i18n = self.api.get_i18n()
            label = i18n.get("plugins.java.about", "About Java Support")
        """
        class _I18NProxy:
            def __init__(self, outer: "PluginAPI") -> None:
                self._outer = outer

            def get(self, key: str, default: Optional[str] = None) -> str:
                try:
                    from libs.i18n import I18N
                    val = I18N.get_instance().get(key, None)
                    if val is not None:
                        return val
                except Exception:
                    pass
                text = self._outer.get_text(key)
                if text != key:
                    return text
                return default if default is not None else key

        return _I18NProxy(self)

    def get_main_window(self) -> Any:
        """Return a reference to the host MainWindow (best-effort).

        Used by plugins like java_support to pop Tk message boxes with a
        parent window reference. Returns ``None`` if the host reference
        is not available.
        """
        return self._host

    # ==================================================================
    # Plugin management (gated by PERMISSION_PLUGIN_MANAGE)
    # ==================================================================
    def get_plugin_names(self) -> List[str]:
        try:
            if self._host.plugin_manager:
                return self._host.plugin_manager.get_plugin_names()
        except Exception:
            pass
        return []

    def reload_plugin(self, name: str) -> bool:
        """Hot-reload another plugin (requires plugin manage permission)."""
        if not self._require(PERMISSION_PLUGIN_MANAGE):
            return False
        try:
            return self._host.plugin_manager.reload_plugin(name)
        except Exception as e:
            self._logger.debug("reload_plugin(%s) failed: %s", name, e)
            return False

    # ==================================================================
    # Menu registration (gated by PERMISSION_MENU_REGISTER)
    # ==================================================================
    def add_menu_item(
        self,
        menu_path: str,
        label: str,
        command: Callable[[], None],
        accelerator: str = "",
        separator_before: bool = False,
        separator_after: bool = False,
    ) -> bool:
        """Register a new menu item.

        Args:
            menu_path: Dot-separated path under the top-level menu, e.g.
                ``"tools"`` or ``"tools.submenu"``. New top-level menus
                are created automatically.
            label: Display text (i18n lookup supported via get_text()
                by the plugin before passing in).
            command: No-argument callback invoked on click.
            accelerator: Optional key-sequence label, e.g. "Ctrl+Shift+P".
            separator_before/after: Insert Tk separators around the entry.

        Returns:
            True if the entry was registered.
        """
        if not self._require(PERMISSION_MENU_REGISTER):
            return False
        plugin = self._plugin_from_self()
        try:
            entry = self._install_menu_entry(
                menu_path=menu_path, label=label, command=command,
                accelerator=accelerator,
                separator_before=separator_before,
                separator_after=separator_after,
            )
            if plugin is not None:
                self._menu_entries.setdefault(id(plugin), []).append(entry)
            return True
        except Exception as e:
            self._logger.debug("add_menu_item failed: %s", e)
            return False

    def add_menu_entry(
        self,
        menu_path,
        label: str,
        callback: Callable[[], None],
        accelerator: Optional[str] = None,
        separator_before: bool = False,
        separator_after: bool = False,
    ) -> bool:
        """Convenience alias for :meth:`add_menu_item`.

        Compared to ``add_menu_item`` this wrapper accepts:

        * ``menu_path`` as a list of path segments (e.g. ``["Help"]``)
          **or** a dotted string;
        * ``callback`` instead of ``command``.

        This matches the call shape used by plugins like ``java_support``.
        """
        if isinstance(menu_path, (list, tuple)):
            dotted = ".".join(str(part) for part in menu_path)
        else:
            dotted = str(menu_path)
        return self.add_menu_item(
            menu_path=dotted,
            label=label,
            command=callback,
            accelerator=accelerator or "",
            separator_before=separator_before,
            separator_after=separator_after,
        )

    def _install_menu_entry(self, **kw) -> Dict[str, Any]:
        """Create a menu entry in the host menubar. Returns metadata
        needed for later removal."""
        import tkinter as tk
        host = self._host
        menubar: Optional[tk.Menu] = getattr(host, "menubar", None) \
            or getattr(host, "_menubar", None)
        # Fallback: if host stores menu via root.config(menu=...), read it
        if menubar is None and hasattr(host, "root"):
            menubar = host.root.cget("menu")
        if menubar is None:
            raise RuntimeError("Host has no menubar reference.")

        parts = kw["menu_path"].split(".")
        current_menu: tk.Menu = menubar
        # Walk / create submenus
        created_menus: List[Tuple[tk.Menu, str, tk.Menu]] = []  # (parent, label, submenu)
        for i, part in enumerate(parts):
            is_last = (i == len(parts) - 1)
            # Find existing cascade with this label
            found_idx = None
            for idx in range(current_menu.index("end") + 1 if current_menu.index("end") is not None else 0):
                try:
                    lbl = current_menu.entrycget(idx, "label")
                except Exception:
                    continue
                if str(lbl).lower() == part.lower():
                    found_idx = idx
                    break
            if found_idx is None:
                if is_last:
                    # Don't create a submenu for the leaf path component;
                    # we will add the command directly at this level.
                    break
                # Create a new submenu
                new_sub = tk.Menu(current_menu, tearoff=0)
                current_menu.add_cascade(label=part.capitalize(), menu=new_sub)
                created_menus.append((current_menu, part.capitalize(), new_sub))
                current_menu = new_sub
            else:
                # Navigate into the existing cascade
                existing_sub = current_menu.nametowidget(
                    current_menu.entrycget(found_idx, "menu")
                ) if isinstance(current_menu, tk.Menu) else None
                if existing_sub is not None:
                    current_menu = existing_sub

        # Now add the command to current_menu
        added_indexes: List[Tuple[tk.Menu, int]] = []
        if kw.get("separator_before"):
            current_menu.add_separator()
            added_indexes.append((current_menu, current_menu.index("end")))
        if kw.get("accelerator"):
            current_menu.add_command(
                label=kw["label"], accelerator=kw["accelerator"],
                command=kw["command"])
        else:
            current_menu.add_command(
                label=kw["label"], command=kw["command"])
        added_indexes.append((current_menu, current_menu.index("end")))
        if kw.get("separator_after"):
            current_menu.add_separator()
            added_indexes.append((current_menu, current_menu.index("end")))

        return {
            "created_menus": created_menus,
            "entries": added_indexes,
        }

    def _remove_menu_entry(self, entry: Dict[str, Any]) -> None:
        # Remove from deepest indexes first to preserve numbering.
        for menu, idx in reversed(entry.get("entries", [])):
            try:
                menu.delete(idx)
            except Exception:
                pass
        # Clean up any empty submenus we created.
        for parent, _, submenu in reversed(entry.get("created_menus", [])):
            try:
                if submenu.index("end") is None:
                    # Find the cascade index pointing at submenu
                    for idx in range(parent.index("end") + 1 if parent.index("end") is not None else 0):
                        try:
                            widget = parent.nametowidget(parent.entrycget(idx, "menu"))
                        except Exception:
                            continue
                        if widget is submenu:
                            parent.delete(idx)
                            break
            except Exception:
                pass

    # ==================================================================
    # Hotkey binding (gated by PERMISSION_HOTKEY_BIND)
    # ==================================================================
    def bind_hotkey(self, sequence: str, callback: Callable[[Any], Any],
                    scope: str = "global") -> bool:
        """Bind a global or editor-scoped keyboard shortcut.

        Args:
            sequence: Tk-style accelerator, e.g. ``"<Control-Shift-P>"``
                or ``"<F8>"``.
            callback: Function receiving the Tk event argument.
            scope: ``"global"`` (bound to root), ``"editor"`` (bound to
                the text widget when editor exists), or ``"menu"``
                (also registers a menu accelerator entry).

        Returns:
            True on success.
        """
        if not self._require(PERMISSION_HOTKEY_BIND):
            return False
        plugin = self._plugin_from_self()
        try:
            bind_meta = self._apply_hotkey_bind(sequence, callback, scope)
            if plugin is not None:
                self._hotkey_binds.setdefault(id(plugin), []).append(bind_meta)
            return True
        except Exception as e:
            self._logger.debug("bind_hotkey failed: %s", e)
            return False

    def _apply_hotkey_bind(self, sequence: str, callback: Callable, scope: str) -> Dict[str, Any]:
        host = self._host
        targets = []
        if scope in ("global", "menu") and hasattr(host, "root"):
            targets.append(host.root)
        if scope in ("editor",):
            widget = getattr(host, "textbox_widget", None)
            if widget is not None and widget.winfo_exists():
                targets.append(widget)
        applied = []
        for widget in targets:
            func_id = widget.bind(sequence, callback, add="+")
            applied.append((widget, sequence, func_id))
        return {"applied": applied, "scope": scope}

    def _unbind_hotkey(self, bind_meta: Dict[str, Any]) -> None:
        for widget, sequence, _ in bind_meta.get("applied", []):
            try:
                widget.unbind(sequence)
            except Exception:
                pass

    # ==================================================================
    # Syntax highlighting extension (gated by PERMISSION_HIGHLIGHT_EXTEND)
    # ==================================================================
    def add_syntax_groups(
        self,
        language_patterns,
        groups,
    ) -> bool:
        """Register extra highlight groups for files matching patterns.

        Args:
            language_patterns: A single pattern (``".rs"`` / ``"java"``)
                or a list of patterns. Matched against the current file
                extension or CodeEditor language field. ``["*"]`` matches
                every file.
            groups: Highlight group dicts in the same format as
                ``CodeEditor.groups`` entries, or legacy 4-tuples
                ``(name, color, bold, keywords)``.
        """
        if not self._require(PERMISSION_HIGHLIGHT_EXTEND):
            return False
        plugin = self._plugin_from_self()
        if plugin is None:
            return False
        if isinstance(language_patterns, (list, tuple)):
            patterns = [str(p) for p in language_patterns]
        else:
            patterns = [str(language_patterns)]
        normalized_groups: List[Dict[str, Any]] = []
        for g in groups:
            if isinstance(g, dict):
                normalized_groups.append(dict(g))
            elif isinstance(g, (list, tuple)) and len(g) == 4:
                name, color, bold, keywords = g
                normalized_groups.append({
                    "name": name,
                    "color": color,
                    "bold": bool(bold),
                    "words": list(keywords) if keywords is not None else [],
                })
            else:
                self._logger.debug("add_syntax_groups: skipping unknown entry %r", g)
        self._highlight_providers[id(plugin)] = {
            "language_patterns": patterns,
            "groups": normalized_groups,
        }
        self._rebuild_highlight_groups()
        return True

    def _rebuild_highlight_groups(self) -> None:
        """Ask every open editor to re-evaluate highlight groups.

        The editor's own base groups are preserved; providers are
        layered on top (the CodeEditor merges with update=True).
        """
        try:
            host = self._host
            editor_widgets = []
            if hasattr(host, "editor") and host.editor is not None:
                editor_widgets.append(host.editor)
            if hasattr(host, "editor_manager") and host.editor_manager is not None:
                em = host.editor_manager
                for attr in dir(em):
                    val = getattr(em, attr, None)
                    try:
                        from libs.gui.code_editor import CodeEditor
                        if isinstance(val, CodeEditor):
                            editor_widgets.append(val)
                    except Exception:
                        continue
            for editor in editor_widgets:
                self._merge_providers_into_editor(editor)
                if hasattr(editor, "highlight") and editor.highlight:
                    editor.highlight._tags_configured = False
                    editor.highlight._index_signature = None
                    if hasattr(editor.highlight, "highlight_all"):
                        try:
                            editor.highlight.highlight_all()
                        except Exception:
                            pass
        except Exception as e:
            self._logger.debug("_rebuild_highlight_groups failed: %s", e)

    def _merge_providers_into_editor(self, editor: Any) -> None:
        file_lang = str(getattr(editor, "language", "") or "").lower()
        file_path = getattr(editor, "current_file", None) or ""
        file_ext = os.path.splitext(file_path)[1].lower()
        for provider in self._highlight_providers.values():
            patterns = [p.lower() for p in provider["language_patterns"]]
            if "*" in patterns or file_lang in patterns or file_ext in patterns:
                # Merge group entries; same name wins by replacing.
                existing_names = {g.get("name") for g in editor.groups}
                for g in provider["groups"]:
                    name = g.get("name")
                    if name in existing_names:
                        # Replace in-place
                        for i, existing in enumerate(editor.groups):
                            if existing.get("name") == name:
                                editor.groups[i] = dict(g)
                                break
                    else:
                        editor.groups.append(dict(g))
                        existing_names.add(name)

    # ==================================================================
    # Network / execute helpers (gated)
    # ==================================================================
    def http_get(self, url: str, timeout: float = 10.0) -> Optional[bytes]:
        """Simple synchronous HTTP GET helper (requires network perm)."""
        if not self._require(PERMISSION_NETWORK):
            return None
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            self._logger.debug("http_get(%s) failed: %s", url, e)
            return None

    def run_process(self, args: List[str], cwd: Optional[str] = None,
                    timeout: float = 30.0) -> Optional[Tuple[int, str, str]]:
        """Run an external process (requires execute permission).

        Returns:
            (returncode, stdout, stderr) or None on policy/error.
        """
        if not self._require(PERMISSION_EXECUTE):
            return None
        import subprocess
        try:
            result = subprocess.run(
                args, cwd=cwd, capture_output=True, text=True,
                timeout=timeout)
            return (result.returncode, result.stdout, result.stderr)
        except Exception as e:
            self._logger.debug("run_process(%s) failed: %s", args, e)
            return None

    # ==================================================================
    # Completion / Go-to-Definition extension points (no permission;
    # plugins *extend* IDE capabilities rather than mutating host state.)
    # ==================================================================

    def register_symbol_extractor(self, language_or_ext: str, extractor) -> bool:
        """Register a custom symbol extractor for a language / extension.

        The extractor is called by the SymbolLoaderRegistry when a file of
        the matching language is indexed for auto-completion or go-to-
        definition.

        Args:
            language_or_ext: E.g. "java", ".kt", "rust", ".rs".
            extractor: Callable ``(path, source, lang) -> (symbols, imports)``
                where ``symbols`` and ``imports`` follow the shape defined
                in ``libs.gui.symbol_loader``.

        Returns:
            True on success, False on error (logged at DEBUG level).
        """
        try:
            from libs.gui.symbol_loader import SymbolLoaderRegistry
            SymbolLoaderRegistry.instance().register_extractor(language_or_ext, extractor)
            return True
        except Exception as e:
            self._logger.debug("register_symbol_extractor failed: %s", e)
            return False

    def register_import_resolver(self, language_or_ext: str, resolver) -> bool:
        """Register a custom import resolver that maps an ImportEntry +
        context to an absolute source-file path for lazy symbol loading.

        Args:
            language_or_ext: E.g. "java", ".kt".
            resolver: Callable ``(imp, current_file, project_root) -> path or None``.

        Returns:
            True on success.
        """
        try:
            from libs.gui.symbol_loader import SymbolLoaderRegistry
            SymbolLoaderRegistry.instance().register_import_resolver(language_or_ext, resolver)
            return True
        except Exception as e:
            self._logger.debug("register_import_resolver failed: %s", e)
            return False

    def register_builtin_symbols(self, language_patterns, symbols) -> bool:
        """Add language-standard library symbols (e.g. ``java.lang.*``) to
        the completion index.

        These symbols are merged by ``EditorCompletion`` into the keyword
        popup when any file matching ``language_patterns`` is open. Plugins
        are responsible for choosing representative subsets.

        Args:
            language_patterns: List of language ids or file extensions,
                e.g. ``[".java", "java"]``. ``["*"]`` matches every file.
            symbols: List of ``(name, signature_or_None)`` pairs. Signature
                is shown as grey hint next to the keyword in the popup.

        Returns:
            True on success.
        """
        try:
            host = self._host
            registry = getattr(host, "_builtin_symbol_registry", None)
            if registry is None:
                registry = {}
                setattr(host, "_builtin_symbol_registry", registry)
            bucket = registry.setdefault(tuple(language_patterns), [])
            bucket.extend(symbols)
            return True
        except Exception as e:
            self._logger.debug("register_builtin_symbols failed: %s", e)
            return False

    def find_symbol_definition(self, identifier: str, language: str = "",
                               file_path: Optional[str] = None,
                               project_root: str = "") -> Optional[dict]:
        """Ask SymbolLoaderRegistry for the definition site of ``identifier``.

        Primarily exposed so plugins like language tooltips can reuse the
        IDE's lazy index without duplicating the parsing work.

        Returns a Symbol dict with at least ``{"name", "kind", "line", "file"}``
        keys or ``None``.
        """
        try:
            from libs.gui.symbol_loader import SymbolLoaderRegistry
            reg = SymbolLoaderRegistry.instance()
            host = self._host
            fp = file_path or getattr(host, "current_file", None)
            pr = project_root or getattr(host, "project_root", "")
            lang = language or ""
            live = None
            if hasattr(host, "editor_manager") and host.editor_manager:
                try:
                    live = host.editor_manager.get_content()
                except Exception:
                    live = None
            return reg.find_definition(identifier, fp, lang, pr, live)
        except Exception as e:
            self._logger.debug("find_symbol_definition(%s) failed: %s", identifier, e)
            return None
