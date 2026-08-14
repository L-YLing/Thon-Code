# Thon Code Plugin Development Guide v1.0

> For Thon Code >= 0.4.0. This document explains how to write, package, and debug a Thon Code plugin from scratch.

---

## Table of Contents

1. [Plugin System Overview](#1-plugin-system-overview)
2. [Quick Start: Hello World](#2-quick-start-hello-world)
3. [Plugin Metadata & Permission Declarations](#3-plugin-metadata--permission-declarations)
4. [Lifecycle Hooks](#4-lifecycle-hooks)
5. [Event Hooks](#5-event-hooks)
6. [PluginAPI Reference](#6-pluginapi-reference)
7. [Menu Registration & Hotkey Binding](#7-menu-registration--hotkey-binding)
8. [Syntax Highlighting Extensions](#8-syntax-highlighting-extensions)
9. [Plugin Dependencies & Version Constraints](#9-plugin-dependencies--version-constraints)
10. [Single-File vs. Multi-File Package Plugins](#10-single-file-vs-multi-file-package-plugins)
11. [Hot Reload & Debugging](#11-hot-reload--debugging)
12. [PyInstaller / Nuitka Packaging Compatibility](#12-pyinstaller--nuitka-packaging-compatibility)

---

## 1. Plugin System Overview

The Thon Code plugin system lives under `src/thoncode/libs/plugins/` and consists of the following core modules:

| Module | Responsibility |
| --- | --- |
| `plugin_base.py` | Defines the `PluginBase` base class, permission constants, and dependency-declaration syntax |
| `plugin_api.py`   | The stable API surface (`PluginAPI`) exposed to plugins — every host interaction goes through it |
| `plugin_manager.py` | Loading / unloading / hot-reload, permission grant dialog, dependency topo-sort |
| `plugin_marketplace.py` | Marketplace client (download, checksum, extract & install) |

Plugins are **loosely coupled** with the host: a plugin only talks to the host through `PluginAPI`, and every high-impact operation is gated by a permission check at the API layer.

---

## 2. Quick Start: Hello World

### 2.1 Minimal Single-File Plugin

Create `hello_world.py` inside `src/thoncode/plugins/` (or `plugins/` next to the packaged executable):

```python
#! /usr/bin/env python3
from libs.plugins import PluginBase

class HelloWorldPlugin(PluginBase):
    name        = "hello_world"
    version     = "1.0.0"
    description = "Shows Hello World on the status bar (demo plugin)"
    author      = "Your Name"

    def on_load(self):
        self.api.show_status("Hello, Thon Code!")

    def on_unload(self):
        self.api.show_status("Bye!")
```

Then:

1. Start Thon Code → menu **Tools** → **Plugin Manager**.
2. Click **Refresh** — you should see `hello_world 1.0.0` with status **Loaded**.
3. The status bar briefly shows `Hello, Thon Code!`.
4. Click **Unload** → status bar shows `Bye!`. Click **Hot Reload** → the latest file on disk is re-imported.

### 2.2 Listen to File-Open Events

```python
class HelloWorldPlugin(PluginBase):
    # ... metadata same as above ...

    def on_file_open(self, file_path: str):
        logger = self.api.get_logger(self.name)
        logger.info("User opened file: %s", file_path)
        self.api.show_status(f"Opened: {file_path}")
```

---

## 3. Plugin Metadata & Permission Declarations

### 3.1 Required Metadata

Every plugin class **must** override these 4 fields:

| Field | Type | Description |
| --- | --- | --- |
| `name` | `str` | Unique plugin ID, matching `[a-z0-9_]+`. Duplicate names overwrite each other. |
| `version` | `str` | [Semantic version](https://semver.org/), e.g. `1.2.3` |
| `description` | `str` | Short description displayed in the Plugin Manager panel |
| `author` | `str` | Author name or team name |

### 3.2 Permission Declarations (`permissions`)

A plugin **requests only the permissions it needs**; on first load the host shows a grant dialog and the user checks each flag:

```python
from libs.plugins import PluginBase, PERMISSION_MENU_REGISTER, PERMISSION_HOTKEY_BIND

class MyPlugin(PluginBase):
    permissions = [
        PERMISSION_MENU_REGISTER,   # Register menu items
        PERMISSION_HOTKEY_BIND,     # Bind global hotkeys
    ]
```

Full permission list (defined in `plugin_base.py`):

| Constant | Value | Description |
| --- | --- | --- |
| `PERMISSION_FILESYSTEM_READ`  | `filesystem:read`   | Read files outside the project tree |
| `PERMISSION_FILESYSTEM_WRITE` | `filesystem:write`  | Write files outside the project tree |
| `PERMISSION_NETWORK`          | `network`           | Open network connections (HTTP / sockets) |
| `PERMISSION_EXECUTE`          | `execute`           | Spawn external child processes |
| `PERMISSION_CONFIG`           | `config`            | Read & write host-level configuration |
| `PERMISSION_EDITOR_MODIFY`    | `editor:modify`     | Mutate editor content / selection |
| `PERMISSION_MENU_REGISTER`    | `ui:menu_register`  | Register new menu items |
| `PERMISSION_HOTKEY_BIND`      | `ui:hotkey_bind`    | Register global keyboard shortcuts |
| `PERMISSION_HIGHLIGHT_EXTEND` | `editor:highlight_extend` | Extend syntax-highlight rules |
| `PERMISSION_PLUGIN_MANAGE`    | `plugins:manage`    | Load / unload / reload other plugins |

> Low-risk APIs such as `get_project_root`, `get_current_theme`, `show_status`, and `get_logger` require **no permission**.

### 3.3 Host-Version Requirement (`host_version`)

```python
class MyPlugin(PluginBase):
    host_version = ">=0.4.0,<2.0.0"   # Same constraint syntax as `requires`
```

### 3.4 Dependency Declarations (`requires`)

```python
class LintPlugin(PluginBase):
    requires = [
        {"name": "core_utils", "version": ">=1.0.0,<2.0.0"},
        {"name": "sdk_base",   "version": "==3.2.1"},
    ]
```

Supported constraint operators: `==`, `>=`, `>`, `<=`, `<`. Multiple constraints are comma-separated, e.g. `>=1.0,<2.0`. If a dependency is missing or its version is incompatible, the host skips loading this plugin and emits a log message (i18n keys `plugins.dep_missing` / `plugins.dep_version_mismatch`).

---

## 4. Lifecycle Hooks

### `on_load()`

Called **once, after the plugin loads successfully and permissions are granted**. Perform initialization here: register menus, bind hotkeys, open resources.

```python
def on_load(self):
    self.api.add_menu_item(
        menu_path="tools.my_plugin",
        label="Do My Action",
        command=self._do_work,
    )
```

### `on_unload()`

Called immediately before the plugin is **unloaded or hot-reloaded**. Must be **idempotent** — it must be safe to run even if `on_load` failed halfway. Typical cleanup:

- close file handles / network sockets;
- persist plugin-private data (under `get_project_root()/.thoncode/` or via `set_config`).

> Menu items / hotkeys / syntax-highlight extensions are **auto-cleaned** by `PluginAPI` — plugins should NOT manually undo those registrations.

---

## 5. Event Hooks

Besides `on_load` / `on_unload`, plugins may define any `on_<event_name>` method; the host dispatches them as events occur.

Currently supported events (also listed in the `plugin_api.py` header comment):

| Hook signature | Fired when… |
| --- | --- |
| `on_file_open(path: str)`   | A file is opened in the editor |
| `on_file_save(path: str)`   | A file is successfully saved |
| `on_file_close(path: str)`  | An editor tab is closed |
| `on_editor_change(text: str)` | Editor content changes (throttled) |
| `on_tree_refresh()`         | The left-hand file tree finishes refreshing |
| `on_theme_change(name: str)`| User switches the UI theme |
| `on_project_open(path: str)`| User opens a project folder |
| `on_syntax_highlight_ext()` | Highlight groups are rebuilt |

Example:

```python
def on_project_open(self, path: str):
    logger = self.api.get_logger(self.name)
    logger.info("New project root: %s", path)
```

---

## 6. PluginAPI Reference

`PluginAPI` is the **single entry point** for plugins to reach the host, accessed as `self.api`.

### 6.1 Logging

```python
logger = self.api.get_logger(self.name)
logger.debug("Debug info")
logger.info("General info")
logger.warning("Warning")
logger.error("Error detail", exc_info=True)
```

Logs go through the standard logging pipeline and are also captured by the test harness into `src/thoncode/test/log/`.

### 6.2 Status Bar

```python
self.api.show_status("Processed 123 files")
```

### 6.3 Project / File Info

| API | Description | Permission needed |
| --- | --- | --- |
| `get_project_root() -> str` | Absolute path of the current project root; `""` if none open | None |
| `get_current_file() -> Optional[str]` | Absolute path of the active editor tab | None |
| `get_recent_projects() -> List[str]` | List of recently opened project folders | None |

### 6.4 Editor (Read-Only)

| API | Description | Permission |
| --- | --- | --- |
| `get_editor_text() -> str` | Full editor text (from `"1.0"` to end) | None |
| `get_editor_selection() -> str` | Currently selected text | None |

### 6.5 Editor (Writes, needs `PERMISSION_EDITOR_MODIFY`)

| API | Description |
| --- | --- |
| `set_editor_text(text: str)` | Replace the entire editor buffer |
| `insert_editor_text(text, position="insert")` | Insert at the Tk caret position (or a supplied position) |

### 6.6 Config (writes need `PERMISSION_CONFIG`)

| API | Description |
| --- | --- |
| `get_config() -> dict` | Read a snapshot of host config (read-only; don't mutate the returned dict in place) |
| `set_config(key, value) -> bool` | Persist one config key to disk |

### 6.7 Filesystem (cross-project access needs the corresponding permission)

For files **inside the project**, just `os.path.join(self.api.get_project_root(), "...")` — no permission required.

Use these only when you need paths outside the project tree:

| API | Required permission |
| --- | --- |
| `read_file_external(path) -> Optional[str]` | `PERMISSION_FILESYSTEM_READ` |
| `write_file_external(path, content) -> bool` | `PERMISSION_FILESYSTEM_WRITE` |

### 6.8 Theme & Appearance

| API | Description | Permission |
| --- | --- | --- |
| `get_current_theme() -> str` | E.g. `"darkly"` / `"litera"` | None |
| `get_accent_color() -> Optional[str]` | Current custom accent color as `#RRGGBB` | None |

### 6.9 Network & Subprocess (need corresponding permissions)

| API | Permission |
| --- | --- |
| `http_get(url, timeout=10.0) -> Optional[bytes]` | `PERMISSION_NETWORK` |
| `run_process(args, cwd=None, timeout=30) -> (code, stdout, stderr)` | `PERMISSION_EXECUTE` |

### 6.10 Plugin Management (needs `PERMISSION_PLUGIN_MANAGE`)

| API | Description |
| --- | --- |
| `get_plugin_names() -> List[str]` | List names of all currently loaded plugins |
| `reload_plugin(name: str) -> bool` | Trigger a hot-reload of another plugin |

### 6.11 i18n

```python
label = self.api.get_text("plugins.refresh")   # Looked up against current UI language
```

If the key is missing, the key string itself is returned verbatim.

---

## 7. Menu Registration & Hotkey Binding

### 7.1 Register Menu Items (needs `PERMISSION_MENU_REGISTER`)

```python
def on_load(self):
    self.api.add_menu_item(
        menu_path="tools.my_plugin",     # Dot-separated path; submenus are auto-created
        label="Format Current File",
        command=self._format,
        accelerator="Ctrl+Shift+F",      # Label only — does NOT bind the key
        separator_before=False,
        separator_after=False,
    )

def _format(self):
    text = self.api.get_editor_text()
    # ... process ...
    self.api.set_editor_text(text)
```

### 7.2 Bind Hotkeys (needs `PERMISSION_HOTKEY_BIND`)

```python
def on_load(self):
    self.api.bind_hotkey("<Control-Shift-F>", self._on_hotkey, scope="editor")
    self.api.bind_hotkey("<F8>",             self._on_global,  scope="global")

def _on_hotkey(self, event):
    self.api.show_status("You pressed Ctrl+Shift+F")

def _on_global(self, event):
    self.api.show_status("Global hotkey F8 fired")
```

`scope` values:

| Value | Bind target |
| --- | --- |
| `"global"` | Root window — always active |
| `"editor"` | Editor text widget — only when editor has focus |
| `"menu"`   | Same as `"global"` (reserved for future menu integration) |

> ⚠️ The `accelerator` string shown on a menu item and a `scope="global"` `bind_hotkey` call are **two separate things**. The former only paints text; the latter actually wires the key. For UI consistency, call both together.

---

## 8. Syntax-Highlight Extensions (needs `PERMISSION_HIGHLIGHT_EXTEND`)

Plugins can add highlight groups to existing languages or register rules for new file types.

```python
from libs.plugins import PluginBase, PERMISSION_HIGHLIGHT_EXTEND

class RustHighlightPlugin(PluginBase):
    permissions = [PERMISSION_HIGHLIGHT_EXTEND]

    def on_load(self):
        self.api.add_syntax_groups(
            language_patterns=[".rs", "rust"],    # Matches file extension or internal language name
            groups=[
                {
                    "name": "rust.keyword.ext",
                    "color": "#569CD6",
                    "words": ["match", "impl", "trait", "async", "await"],
                },
                {
                    "name": "rust.macro",
                    "color": "#C586C0",
                    "regex": [r"\b\w+!\b"],
                },
            ],
        )
```

Fields inside each highlight-group dict:

| Field | Type | Description |
| --- | --- | --- |
| `name`  | `str` | Unique identifier. If a name collides with a built-in group, the plugin's version **replaces** it. |
| `color` | `str` | Hex color `#RRGGBB`. |
| `words` | `List[str]` | Whole-word match list (automatically wrapped with word boundaries). |
| `regex` | `List[str]` | Raw Python `re` patterns. |

---

## 9. Plugin Dependencies & Version Constraints

### 9.1 Topo-Sort & Cycle Detection

Before loading, `PluginManager` runs a topological sort so that **dependencies load first**. If a cycle is detected (A → B → A), the host:

- logs it (i18n key `plugins.dep_cycle`);
- falls back to loading in **alphabetical order by plugin name**;
- any plugin that still fails is simply marked as skipped in the UI.

### 9.2 Failures Are Isolated

If a single plugin fails to load (missing dep / syntax error / denied permission), the host **skips that one plugin only** and continues — the IDE itself keeps running.

---

## 10. Single-File vs. Multi-File Package Plugins

Entries under the plugins directory can follow either layout.

### 10.1 Single File (Recommended for Newcomers)

```
plugins/
└── hello_world.py           # Contains one PluginBase subclass
```

Load rule: `import hello_world`, then scan the module for **all** classes that inherit from `PluginBase` and instantiate each one. You *may* put multiple plugin classes inside one `.py`, but one-file-one-plugin is the social convention.

### 10.2 Multi-File Package (For Complex Plugins)

```
plugins/
└── my_linter/
    ├── __init__.py          # Re-exports the plugin class(es) from submodules
    ├── checks.py            # Business logic
    ├── rules.py
    └── README.md            # Human-only readme; does not participate in import
```

Sample `__init__.py`:

```python
# plugins/my_linter/__init__.py
from .checks import LinterPlugin

__all__ = ["LinterPlugin"]
```

> When you zip this up for marketplace distribution, the extraction result **must** correspond to one of the two layouts above — either a single `.py` at the zip root, or a directory containing `__init__.py`.

---

## 11. Hot Reload & Debugging

### 11.1 Hot-Reload Flow

1. User clicks **Hot Reload** in the Plugin Manager (or another plugin that holds `PERMISSION_PLUGIN_MANAGE` calls `api.reload_plugin(name)`).
2. `PluginManager` performs:
   - call `on_unload()`;
   - `PluginAPI._unregister_all_for_plugin` cleans menus / hotkeys / highlight extensions;
   - removes the module from `sys.modules`;
   - re-`importlib.import_module` + instantiates a fresh object;
   - runs permission grant → `on_load()` again.
3. This yields the classic "save plugin file → click reload → changes appear immediately" loop.

### 11.2 Debugging Tips

- Use `self.api.get_logger(...)` instead of `print` to keep stdout clean;
- Intentionally throw during `on_load` to verify the failure is isolated and the rest of the IDE keeps working;
- When debugging menu / hotkey registrations, click **Hot Reload** repeatedly and confirm there's no duplication after unload;
- Permission weirdness? First re-check whether the flags you need are actually checked in the grant dialog.

---

## 12. PyInstaller / Nuitka Packaging Compatibility

### 12.1 Plugin-Directory Resolution

The packaged host resolves the plugins directory with the following priority:

1. `sys.frozen == True` → `<exe_directory>/plugins/` (user-writable; the marketplace installer defaults here);
2. Otherwise → `<thoncode_package>/plugins/` (source layout).

Therefore, **user plugins should never be baked into the frozen binary**.

### 12.2 Built-in Licence Templates / Asset Files

Similarly, resources such as `assets/license/`, `assets/langs/`, and `assets/fonts/`:

- **PyInstaller**: In your `.spec`, add the whole `src/thoncode/assets` tree under `datas`;
- **Nuitka**: Pass `--include-data-dir=src/thoncode/assets=thoncode/assets`.

`license_handle.py` auto-resolves paths against three scenarios (source / frozen / `_MEIPASS`) and materializes a set of built-in licence templates on first run when none exist, so the licence dropdown never stays empty due to a missing path.

### 12.3 Hook-Richness Compatibility

- **Menu registration**: `PluginAPI._install_menu_entry` has built-in fallbacks looking for `host.menubar`, `host._menubar`, and `host.root.cget("menu")` — it works as long as the main window exposes any of the three references;
- **Highlight extension**: Iterates every `CodeEditor` instance inside the editor manager and updates them all;
- **Hot reload**: Implemented via `importlib.reload` + module re-import, works in both PyInstaller one-file and one-dir modes.

---

**Further reading**: [Plugin Marketplace Setup Guide](./plugin_marketplace.md), [User Manual](./user_manual.md).
