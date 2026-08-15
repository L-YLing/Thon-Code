#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Editor Tab Manager",
    "Path": ".main.libs.gui.editor_tab_manager",
    "Entrance": "main.py"
}

"""Tabbed multi-editor container backed by ``ttk.Notebook``.

Responsibilities
----------------

* Keeps the welcome page as the first, non-closable tab. When the user
  clicks the welcome tab the welcome frame (passed in at construction)
  stays visible.
* Every ``open_file(...)`` / ``new_file()`` call adds a new tab, or
  re-activates an existing tab if the requested file is already open.
* Each editor tab owns an :class:`libs.gui.editor_manager.EditorManager`
  instance so all editor state (language, dirty flag, undo stack, cursor
  position) stays independent per file.
* Provides close buttons via an ``X`` glyph on the tab label. Dirty files
  prepend a ``*`` to their label.
* Syncs active-tab state back to the host ``MainWindow`` so legacy single-
  editor code paths continue to read ``self.current_file`` / ``self.editor``
  / ``self.textbox_widget`` without big changes.

Lazy loading note: imports from files other than the currently-being-
edited file happen on demand (via :class:`libs.gui.symbol_loader`) so
holding many open tabs does not cost much extra memory beyond what the
``CodeEditor`` text widgets themselves consume.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Callable, Dict, List, Optional, Tuple

from libs.gui_libs.style_system import StyleSystem
from libs.gui.lazy_loader import LazyLoader


class EditorTabManager:
    """Notebook-backed multi-tab editor container."""

    WELCOME_TAB_ID = "__welcome__"

    def __init__(self, parent: tk.Misc, main_window: Any, *,
                 status_callback: Callable[[str], None],
                 update_title_callback: Callable[[], None],
                 get_welcome_frame: Callable[[], tk.Widget],
                 hide_welcome_callback: Optional[Callable[[], None]] = None,
                 plugin_hook_callback: Optional[Callable[[str, str], None]] = None):
        """
        Args:
            parent: Parent widget (the centre pane frame).
            main_window: Reference to host :class:`MainWindow`.
            status_callback: ``(message) -> None`` for the status bar.
            update_title_callback: ``() -> None`` called after state changes
                that should refresh the window title (dirty flag, tab change).
            get_welcome_frame: Called lazily to get the welcome-page frame
                that is placed inside the welcome tab.
            hide_welcome_callback: Optional ``() -> None`` invoked whenever a
                non-welcome tab is opened (used to hide any overlays).
            plugin_hook_callback: Optional ``(hook_name, arg) -> None`` used
                to fire ``file_open`` / ``file_save`` plugin hooks.
        """
        self.parent = parent
        self.main_window = main_window
        self.status_callback = status_callback
        self.update_title_callback = update_title_callback
        self._get_welcome_frame = get_welcome_frame
        self._hide_welcome_callback = hide_welcome_callback
        self._plugin_hook = plugin_hook_callback

        self._style_system = StyleSystem()
        self._style_system.sync_from_theme()

        # notebook: the main tab container
        self.notebook = ttk.Notebook(self.parent)
        self.notebook.pack(fill="both", expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        # Bind left-click to detect close-button clicks on tab labels.
        # We use a global click handler because ttk.Notebook does not
        # support embedding arbitrary widgets (like a close-button Frame)
        # directly in tab labels on all platforms.
        self.notebook.bind("<Button-1>", self._on_notebook_click)
        # Approximate width (in pixels) of the close-button hit area at
        # the right edge of each tab label. Tuned for typical font sizes.
        self._close_btn_hit_width = 22

        # state: tab_id -> tab_meta
        # tab_meta is {"file": str|None, "manager": EditorManager|None,
        #              "welcome": bool, "frame": ttk.Frame}
        self._tabs: Dict[str, Dict[str, Any]] = {}

        # Create the welcome tab (always index 0, not closable).
        self._add_welcome_tab()

        # Internal counter for synthetic "Untitled N" tab IDs.
        self._untitled_counter = 0

    # ------------------------------------------------------------------
    # Tab creation helpers
    # ------------------------------------------------------------------

    def _tab_id_for_file(self, file_path: str) -> str:
        return f"file::{os.path.abspath(file_path)}"

    def _tab_title(self, title: str, is_dirty: bool) -> str:
        return ("* " if is_dirty else "") + title

    def _make_closable_label(self, tab_id: str, title: str, is_dirty: bool) -> ttk.Frame:
        """Return a small frame containing the title + a clickable [×]."""
        label_frame = ttk.Frame(self.notebook)
        txt = self._tab_title(title, is_dirty)
        lbl = ttk.Label(label_frame, text="  " + txt + "  ", padding=(2, 0))
        lbl.pack(side="left")
        btn = ttk.Label(label_frame, text="×", padding=(4, 0),
                        foreground="#888888", cursor="hand2")
        btn.pack(side="right")

        def _on_close_click(_evt):
            # Defer actual tab closing one tick so click events on the
            # notebook label don't race.
            self.notebook.after(0, lambda: self.close_tab(tab_id))

        btn.bind("<Button-1>", _on_close_click)
        return label_frame

    def _add_welcome_tab(self) -> None:
        welcome_container = ttk.Frame(self.notebook)
        welcome_container.pack(fill="both", expand=True)
        welcome_lbl = ttk.Label(welcome_container)
        welcome_lbl.pack(fill="both", expand=True)
        # Store; the real welcome frame gets slotted in on first activation
        self._tabs[self.WELCOME_TAB_ID] = {
            "file": None,
            "manager": None,
            "welcome": True,
            "frame": welcome_container,
            "title": "Welcome",
        }
        # Simple text label for the welcome tab (no close button).
        self.notebook.add(welcome_container, text="  Welcome  ")
        # We re-dock the welcome frame into welcome_container when the
        # user navigates to the welcome tab (see _dock_welcome_into_tab).

    def _dock_welcome_into_tab(self) -> None:
        """Move the host's welcome_frame into the welcome tab container."""
        meta = self._tabs[self.WELCOME_TAB_ID]
        container: ttk.Frame = meta["frame"]
        # Clear container
        for w in container.winfo_children():
            w.pack_forget()
        try:
            welcome_frame = self._get_welcome_frame()
            if welcome_frame is None:
                return
            welcome_frame.pack(in_=container, fill="both", expand=True)
        except Exception:
            # If welcome page creation fails (very early boot) we still
            # want the tab container to stay functional.
            pass

    def _add_editor_tab(self, tab_id: str, title: str) -> Tuple[str, Any]:
        """Create a new tab with an empty ``EditorManager`` inside.

        Returns:
            (tab_id, editor_manager)
        """
        frame = ttk.Frame(self.notebook)
        frame.pack(fill="both", expand=True)

        EditorManager = LazyLoader.get('libs.gui.editor_manager', 'EditorManager')
        manager = EditorManager(
            frame,
            main_window=self.main_window,
            status_callback=self.status_callback,
            update_title_callback=self.update_title_callback,
        )
        manager.get_widget().pack(fill="both", expand=True)

        # Track metadata
        self._tabs[tab_id] = {
            "file": None,
            "manager": manager,
            "welcome": False,
            "frame": frame,
            "title": title,
        }

        # Add tab with a text label that includes a "✕" close glyph.
        # We use plain text (not custom widgets) because ttk.Notebook
        # does not reliably support embedded widgets in tab labels across
        # all platforms/themes. Close-button clicks are detected via the
        # _on_notebook_click hit-test handler bound at __init__ time.
        self.notebook.add(frame)
        tab_idx = self.notebook.index("end") - 1
        self.notebook.tab(tab_idx, text=" " + self._tab_title(title, False) + "  ✕")
        return tab_id, manager

    # ------------------------------------------------------------------
    # Public API: multi-file operations
    # ------------------------------------------------------------------

    def new_file(self) -> Any:
        """Add a new "Untitled" editor tab and return its ``EditorManager``."""
        self._untitled_counter += 1
        title = f"Untitled {self._untitled_counter}"
        tab_id = f"untitled::{self._untitled_counter}"
        _tid, manager = self._add_editor_tab(tab_id, title)
        # manager.clear() — freshly created editors are already empty
        self._activate_tab(tab_id)
        if self._hide_welcome_callback:
            try:
                self._hide_welcome_callback()
            except Exception:
                pass
        self._sync_host_state()
        self.update_title_callback()
        return manager

    def open_file(self, file_path: str, jump_to_line: Optional[int] = None) -> bool:
        """Open ``file_path`` in a tab, re-activating existing tab if present.

        Args:
            file_path: Absolute path to the file to open.
            jump_to_line: Optional 1-based line number to scroll to after
                opening. Used by go-to-definition navigation.

        Returns:
            True on success.
        """
        if not file_path or not os.path.isfile(file_path):
            self.status_callback(f"Cannot open: {file_path}")
            return False
        abs_path = os.path.abspath(file_path)
        tab_id = self._tab_id_for_file(abs_path)
        if tab_id in self._tabs:
            self._activate_tab(tab_id)
            manager = self._tabs[tab_id]["manager"]
            self._jump_to_line(manager, jump_to_line)
            if self._hide_welcome_callback:
                try:
                    self._hide_welcome_callback()
                except Exception:
                    pass
            self._sync_host_state()
            return True

        title = os.path.basename(abs_path)
        _tid, manager = self._add_editor_tab(tab_id, title)
        ok = manager.open_file(abs_path)
        if not ok:
            self.close_tab(tab_id, _force=True, _sync=False)
            self.status_callback(f"Failed to open: {abs_path}")
            return False
        self._tabs[tab_id]["file"] = abs_path
        # Re-label with the real file name in case of case differences
        self._refresh_tab_label(tab_id)
        self._activate_tab(tab_id)
        self._jump_to_line(manager, jump_to_line)

        if self._hide_welcome_callback:
            try:
                self._hide_welcome_callback()
            except Exception:
                pass
        self._sync_host_state()
        self.update_title_callback()
        if self._plugin_hook:
            try:
                self._plugin_hook("file_open", abs_path)
            except Exception:
                pass
        return True

    def close_tab(self, tab_id: str, _force: bool = False, _sync: bool = True) -> bool:
        """Close a tab by its id. Asks to save if the tab is dirty."""
        if tab_id == self.WELCOME_TAB_ID:
            # The welcome tab is permanent.
            return False
        meta = self._tabs.get(tab_id)
        if meta is None:
            return False
        manager: Any = meta.get("manager")
        if not _force and manager is not None:
            if hasattr(manager, "is_dirty") and callable(getattr(manager, "is_dirty", None)):
                dirty = bool(manager.is_dirty())
            else:
                dirty = bool(getattr(manager, "_is_dirty", False))
            if dirty:
                name = meta.get("title") or (os.path.basename(meta["file"])
                                              if meta.get("file") else "Untitled")
                from libs.i18n import I18N
                i18n = I18N.get_instance()
                title = i18n.get("tabs.save_before_close_title", "Save changes?")
                msg = i18n.get(
                    "tabs.save_before_close",
                    "'{name}' has unsaved changes. Save before closing?"
                ).format(name=name)
                yes = i18n.get("common.yes", "Yes")
                no = i18n.get("common.no", "No")
                cancel = i18n.get("common.cancel", "Cancel")
                from tkinter import messagebox as mb
                res = mb.askyesnocancel(title, msg,
                                         parent=self.notebook.winfo_toplevel())
                if res is None:  # Cancel
                    return False
                if res:  # Yes: save
                    saved = self._save_tab(tab_id, meta)
                    if not saved:
                        return False
        # Fire file_close hook before destroying state so plugins can
        # still read the file path / content if desired.
        file_path = meta.get("file")
        if file_path and self._plugin_hook:
            try:
                self._plugin_hook("file_close", file_path)
            except Exception:
                pass

        # Remove notebook tab and clean up internal state
        try:
            frame = meta["frame"]
            idx = self.notebook.index(frame)
            if idx is not None:
                self.notebook.forget(idx)
        except Exception:
            pass
        try:
            meta["frame"].destroy()
        except Exception:
            pass
        self._tabs.pop(tab_id, None)
        # If we just closed the active tab, fall back to welcome.
        if _sync:
            try:
                if not self.notebook.select():
                    self._activate_tab(self.WELCOME_TAB_ID)
            except Exception:
                self._activate_tab(self.WELCOME_TAB_ID)
            self._sync_host_state()
            self.update_title_callback()
        return True

    def save_current(self) -> bool:
        """Save the active editor tab. Returns True on success."""
        tab_id, meta = self._get_active_tab_meta()
        if meta is None or meta.get("welcome"):
            return False
        return self._save_tab(tab_id, meta)

    def save_as_current(self, new_path: str) -> bool:
        """Save-as for active tab (used by MainWindow.save_as dialogs)."""
        tab_id, meta = self._get_active_tab_meta()
        if meta is None or meta.get("welcome"):
            return False
        manager: Any = meta.get("manager")
        content = manager.get_content()
        try:
            with open(new_path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as e:
            self.status_callback(f"Save failed: {e}")
            return False
        # Re-bind the tab under its new file path.
        new_tab_id = self._tab_id_for_file(new_path)
        old_title = meta["title"]
        new_title = os.path.basename(new_path)
        # Update manager state
        manager.current_file = new_path
        manager.last_saved_content = content
        manager._is_dirty = False
        # Update tab metadata + label
        if tab_id != new_tab_id:
            # Move entry under new key if it isn't occupied.
            if new_tab_id in self._tabs:
                # Collision (file already open): switch to that tab.
                self.status_callback("File already open in another tab.")
                self.close_tab(tab_id, _force=True, _sync=False)
                self._activate_tab(new_tab_id)
                self._sync_host_state()
                return True
            self._tabs[new_tab_id] = self._tabs.pop(tab_id)
            tab_id = new_tab_id
        self._tabs[tab_id]["file"] = new_path
        self._tabs[tab_id]["title"] = new_title
        self._refresh_tab_label(tab_id)
        if self._plugin_hook:
            try:
                self._plugin_hook("file_save", new_path)
            except Exception:
                pass
        self._sync_host_state()
        self.update_title_callback()
        return True

    def refresh_all_labels(self) -> None:
        """Re-draw every tab's label to pick up dirty flag changes."""
        for tab_id, meta in self._tabs.items():
            if meta.get("welcome"):
                continue
            self._refresh_tab_label(tab_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _save_tab(self, tab_id: str, meta: Dict[str, Any]) -> bool:
        manager: Any = meta.get("manager")
        if manager is None:
            return False
        file_path = getattr(manager, "current_file", None)
        if not file_path:
            # No path yet: needs save-as. Delegate to host's save_as dialog.
            mw = self.main_window
            if hasattr(mw, "save_as") and callable(getattr(mw, "save_as")):
                return bool(mw.save_as())
            return False
        result = manager.save_file()
        if result:
            self._refresh_tab_label(tab_id)
            self._sync_host_state()
            self.update_title_callback()
            if self._plugin_hook:
                try:
                    self._plugin_hook("file_save", file_path)
                except Exception:
                    pass
        return bool(result)

    def _refresh_tab_label(self, tab_id: str) -> None:
        meta = self._tabs.get(tab_id)
        if not meta or meta.get("welcome"):
            return
        manager: Any = meta.get("manager")
        dirty = False
        if manager is not None:
            if hasattr(manager, "is_dirty") and callable(getattr(manager, "is_dirty", None)):
                dirty = bool(manager.is_dirty())
            else:
                dirty = bool(getattr(manager, "_is_dirty", False))
        title = os.path.basename(meta["file"]) if meta.get("file") else meta.get("title", "Untitled")
        meta["title"] = title
        try:
            frame = meta["frame"]
            idx = self.notebook.index(frame)
            if idx is None:
                return
            self.notebook.tab(idx, text=" " + self._tab_title(title, dirty) + "  ✕")
        except Exception:
            pass

    def _jump_to_line(self, manager: Any, line: Optional[int]) -> None:
        if line is None or manager is None:
            return
        editor = getattr(manager, "editor", None)
        if editor is None:
            return
        text = getattr(editor, "_textbox", None) or getattr(editor, "text", None)
        if text is None:
            return
        try:
            text.see(f"{line}.0")
            text.mark_set("insert", f"{line}.0")
            text.focus_set()
            tag = "nav_highlight"
            if tag not in text.tag_names():
                text.tag_configure(tag, background="#4A90E2", foreground="white")
            text.tag_remove(tag, "1.0", "end")
            text.tag_add(tag, f"{line}.0", f"{line}.end")
            text.after(800, lambda: text.tag_remove(tag, "1.0", "end"))
        except tk.TclError:
            pass

    def _activate_tab(self, tab_id: str) -> None:
        meta = self._tabs.get(tab_id)
        if meta is None:
            return
        try:
            idx = self.notebook.index(meta["frame"])
            self.notebook.select(idx)
        except Exception:
            pass

    def _on_notebook_click(self, evt) -> None:
        """Handle left-clicks on the notebook widget.

        Detects clicks on the close-button area of a tab label and
        closes the corresponding tab. This works around the fact that
        ttk.Notebook does not support arbitrary custom widgets in tab
        labels on all platforms – the close glyph is just text at the
        end of the label, so we hit-test the right edge of each tab.
        """
        try:
            # Identify which tab (if any) was clicked.
            # ttk.Notebook.identify(x, y) returns the element name
            # (e.g. "label", "close") or "" on miss. We also check
            # the tab index via @x,y as a fallback.
            elem = ""
            try:
                elem = self.notebook.identify(evt.x, evt.y)
            except Exception:
                pass
            # If the theme already provides a working close button,
            # let the built-in handler deal with it.
            if elem and "close" in elem.lower():
                return

            # Fallback: find the tab index under the cursor and check
            # whether the click landed in the rightmost N pixels of
            # that tab's label (our "virtual close button" area).
            try:
                tab_idx = self.notebook.index(f"@{evt.x},{evt.y}")
            except Exception:
                return
            if tab_idx is None or tab_idx < 0:
                return

            # Get the bounding box of the tab label.
            try:
                bbox = self.notebook.bbox(tab_idx)
            except Exception:
                return
            if not bbox:
                return
            x0, y0, w, h = bbox
            # Click must be within the label's vertical range and
            # inside the right-edge hit zone.
            if evt.y < y0 or evt.y > y0 + h:
                return
            close_x_start = x0 + w - self._close_btn_hit_width
            if evt.x < close_x_start:
                return

            # Find the tab_id for this index and close it.
            tab_id = self._tab_id_at_index(tab_idx)
            if tab_id is None:
                return
            # Defer so the normal tab-select behaviour can settle first.
            self.notebook.after(0, lambda tid=tab_id: self.close_tab(tid))
        except Exception:
            # Never let a click-handler bug crash the editor.
            pass

    def _tab_id_at_index(self, idx: int) -> Optional[str]:
        """Return the tab_id of the tab at notebook index ``idx``."""
        try:
            frame_path = self.notebook.tabs()[idx]
            frame_widget = self.notebook.nametowidget(frame_path)
            for tab_id, meta in self._tabs.items():
                if str(meta["frame"]) == str(frame_widget):
                    return tab_id
        except Exception:
            pass
        return None

    def _on_tab_changed(self, _evt=None) -> None:
        selected = self.notebook.select()
        if not selected:
            return
        # Find tab metadata matching the selected frame identity
        sel_frame = self.notebook.nametowidget(selected)
        for tab_id, meta in self._tabs.items():
            if str(meta["frame"]) == str(sel_frame):
                if meta.get("welcome"):
                    self._dock_welcome_into_tab()
                break
        self._sync_host_state()
        self.update_title_callback()

    def _get_active_tab_meta(self) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        try:
            selected = self.notebook.select()
            if not selected:
                return None, None
            sel_frame = self.notebook.nametowidget(selected)
            for tab_id, meta in self._tabs.items():
                if str(meta["frame"]) == str(sel_frame):
                    return tab_id, meta
        except Exception:
            return None, None
        return None, None

    def get_active_manager(self) -> Any:
        """Return the active ``EditorManager`` (or ``None`` on welcome tab)."""
        _tid, meta = self._get_active_tab_meta()
        if meta and not meta.get("welcome"):
            return meta.get("manager")
        return None

    def _sync_host_state(self) -> None:
        """Push active-tab derived state to the host MainWindow.

        This keeps legacy single-editor accessors (``main_window.editor``,
        ``main_window.textbox_widget``, ``main_window.current_file``,
        ``main_window.is_dirty`` etc) working even though the canonical
        source of truth now lives inside the tab manager.
        """
        _tid, meta = self._get_active_tab_meta()
        mw = self.main_window
        if meta is None:
            return
        if meta.get("welcome"):
            mw.current_file = None
            mw.is_dirty = False
            mw.last_saved_content = ""
            mw.editor_manager = None
            mw.editor_widget = None
            mw.textbox_widget = None
            mw.editor = None
            return
        manager: Any = meta.get("manager")
        if manager is None:
            return
        mw.editor_manager = manager
        mw.editor_widget = manager.get_widget()
        try:
            mw.textbox_widget = manager.get_textbox()
        except Exception:
            mw.textbox_widget = None
        mw.editor = manager.get_editor_instance()
        # Also set project_root on the editor so completion/navigation
        # can resolve imports against the top-level folder.
        if mw.editor is not None:
            try:
                setattr(mw.editor, "project_root",
                        getattr(mw, "current_project", "") or getattr(mw, "project_root", ""))
            except Exception:
                pass
        # current_file / dirty / last-saved content
        mw.current_file = getattr(manager, "current_file", None)
        if hasattr(manager, "is_dirty") and callable(getattr(manager, "is_dirty", None)):
            mw.is_dirty = bool(manager.is_dirty())
        else:
            mw.is_dirty = bool(getattr(manager, "_is_dirty", False))
        mw.last_saved_content = getattr(manager, "last_saved_content", "")

    # ------------------------------------------------------------------
    # Compatibility shims
    # ------------------------------------------------------------------

    def get_widget(self) -> ttk.Notebook:
        """Return the notebook widget for embedding in the centre pane."""
        return self.notebook

    def clear(self) -> None:
        """Compatibility: alias for :meth:`new_file`."""
        self.new_file()

    def apply_editor_style(self, component: str = "", key: str = "", value=None) -> None:
        """Forward a style change to every open editor tab."""
        for tab_id, meta in self._tabs.items():
            if meta.get("welcome"):
                continue
            manager: Any = meta.get("manager")
            if manager is None:
                continue
            try:
                manager.apply_editor_style(component, key, value)
            except Exception:
                pass
