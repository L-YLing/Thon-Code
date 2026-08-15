# Thon Code User Manual v1.0

> For the everyday developer: how to get productive with Thon Code — editing, project management, Git integration, plugin management, and appearance customisation.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [The Editor & Keyboard Shortcuts](#2-the-editor--keyboard-shortcuts)
3. [Projects & the File Tree](#3-projects--the-file-tree)
4. [Plugin Management & Online Installation](#4-plugin-management--online-installation)
5. [Git Integration & Licence Management](#5-git-integration--licence-management)
6. [Running Code](#6-running-code)
7. [Settings: Language, Theme, Marketplace URL](#7-settings-language-theme-marketplace-url)
8. [Frequently Asked Questions (FAQ)](#8-frequently-asked-questions-faq)

---

## 1. Getting Started

### 1.1 Launch

- **Source run**: From the project root, execute `python -m src.thoncode.main`;
- **Packaged run**: On Windows, double-click `ThonCode.exe`.

On first launch you land on the **Welcome Page**:

- **New File** — start a blank document;
- **Open File…** — open an existing source file;
- **Open Folder** — pick a project directory (recommended for the full experience);
- **Recent Projects** — resume from history;
- Bottom-right checkbox **Show welcome page on startup** — untick to skip next time.

### 1.2 Main Window Overview

```
┌────────────────────────────────────────────────────────────┐
│ Menu bar: File  Edit  Project  Run  Tools  Help            │
├──────────────┬─────────────────────────────────────────────┤
│              │ Tab bar  [main.py ●]  [utils.py]  +         │
│              ├─────────────────────────────────────────────┤
│  File tree   │                                             │
│  (left)      │              Code editor                    │
│              │                                             │
│              │                                             │
├──────────────┴─────────────────────────────────────────────┤
│  Status bar: Ready | Opened project: D:\code\my-app       │
└────────────────────────────────────────────────────────────┘
```

---

## 2. The Editor & Keyboard Shortcuts

### 2.1 Common Shortcuts

| Shortcut | Action | Welcome-page caption |
| --- | --- | --- |
| `Ctrl+N` | New file | New File |
| `Ctrl+O` | Open file | Open File |
| `Ctrl+S` | Save file | Save File |
| `Ctrl+Shift+S` | Save as | Save As |
| `Ctrl+Shift+G` | Open Git Integration window | Git Integration |
| `F5` (plugin-extensible) | Run current file | Run |
| `Ctrl+Q` | Exit | Exit |

> Plugins holding `PERMISSION_HOTKEY_BIND` can add more shortcuts; see *Plugin Development Guide* Chapter 7.

### 2.2 Editing Experience

- Tab width: adjust under **Settings → Tab Indent Spaces** (default 4);
- Font ligatures: enable **Settings → Enable Ligatures** — requires Fira Code to be installed system-wide. The font ships inside `assets/fonts/FiraCode-Regular.ttf` and you can double-click it to install;
- Syntax highlighting: built-in Python / Markdown / JavaScript / HTML / Plain Text. Plugins with `PERMISSION_HIGHLIGHT_EXTEND` can add Rust, Go, and so on.

### 2.3 Multi-Tab

- Opening several files accumulates tabs at the top of the editor;
- Double-clicking a file in the tree **replaces** the current tab (VSCode-style); a plugin can change the behaviour;
- Modified tabs carry a `●` marker to the right of the filename.

---

## 3. Projects & the File Tree

### 3.1 Open a Project

Menu **File → Open Folder** → choose the project root → the left-hand tree populates.

> Without a project folder open, Git integration, run-time configuration, and recent-project shortcuts are partially disabled; the status bar tells you "No folder selected".

### 3.2 File-Tree Context Menu

| Item | Effect |
| --- | --- |
| Refresh | Re-scan from disk (also: button at tree top) |
| New File | Create a file under the selected directory; enter the **full name with extension** |
| New Folder | Create a subdirectory under the selected directory |
| Rename | Rename a file or folder |
| Move to Trash | Safe delete (requires `send2trash`; if missing the app asks whether to permanently delete instead) |
| Delete | Irrecoverable permanent delete — confirmation dialog first |

### 3.3 Directory Structure Viewer

Menu **Project → Directory Structure Viewer**:

- Pick a path and a max depth, then click **Refresh**;
- Export as human-readable **Tree** text or machine-readable **JSON**;
- Useful for producing project-structure docs or attaching a directory snapshot to an issue.

---

## 4. Plugin Management & Online Installation

### 4.1 Open Plugin Manager

Menu **Tools → Plugin Manager**. The window carries two tabs:

- **Installed**: lists plugins discovered under the local `plugins/` directory (Name / Version / Author / Description / Status);
- **Marketplace**: lists plugins available online at the configured marketplace URL.

### 4.2 Installed Tab

Buttons:

| Button | Effect |
| --- | --- |
| Refresh | Re-scan `plugins/` and re-run permission grant + dependency loading |
| Unload | Call the plugin's `on_unload()`, auto-clean menus / hotkeys / highlight extensions. Does **not** delete the file on disk. |
| Hot Reload | Unload, then re-`import` the latest source from disk — no IDE restart required. |

Status column shows **Loaded** or the reason it was skipped (missing dep / host-version mismatch / permissions rejected).

### 4.3 Marketplace Tab

On first use fill the marketplace URL in **Settings → Plugin Marketplace URL** (or just type it at the top of the tab and click **Save URL**).

Flow:

1. Click **Refresh List** → client fetches `{URL}/index.json`;
2. Pick a plugin from the list;
3. Click **Install / Update** → download zip → (optional) SHA-256 check → extract into `plugins/`;
4. Return to **Installed** tab → click **Refresh** to actually load the new plugin.

> For running your own marketplace, see *Plugin Marketplace Setup Guide*.

### 4.4 Permission Grant

On first load of a plugin that declares risky permissions (network, subprocess execution, writing outside the project, …) the **Plugin Permission Grant** dialog pops up:

- Top lists every permission the plugin requested;
- User can check flags individually or all / none;
- Click **Allow** — for the remainder of its lifecycle the plugin only gets the **checked subset**;
- Calls to API methods for unchecked permissions are silently denied and logged (no modal dialog, to avoid disrupting the user).

To re-do permissions later: **Unload** the plugin and load it again — the dialog reappears.

---

## 5. Git Integration & Licence Management

### 5.1 Open Git Integration

Menu **Project → Git Integration** (shortcut `Ctrl+Shift+G`).

The window is split into five areas:

1. **Project selector**: Choose which project to work on. If the folder is not a git repo, it tells you and offers an **Init** button;
2. **Branches**: New / switch / delete branches;
3. **Operations**: Init / Add all / Commit / Push / Pull / Status; **Changelog** management; **Licence** management (see 5.2);
4. **File status**: Per-file view. Stage the selected file or discard its changes;
5. **Output panel**: Real-time stdout/stderr from git commands.

> If Git isn't installed the top banner says **Git not installed** and all buttons are disabled.

### 5.2 Licence Manager

Inside the Git Integration window → **Licence → Manage Licence**.

**Window-hierarchy fix (v0.4+)**: In older versions you had to close the Git window before you could interact with the Licence Manager. The fix:

- Content is wrapped in a `ScrollableFrame`, so small screens / low 16:9 resolutions no longer suffer from "150-row preview shoves the Close button off-screen";
- Preview Text widget height is reduced from a huge number to 10 rows, but scrolls normally;
- On open the Licence Manager explicitly releases its parent Git window's grab; on close the grab is restored — neither window can lock the other up;
- Licence-template directory resolves with a three-tier absolute-path fallback (frozen / `_MEIPASS` / source), so packaged builds never show an empty dropdown.

Usage:

1. From the **Select Licence** dropdown pick a built-in template (MIT / Apache-2.0 / GPL-3.0 … — a set is materialised on first run if none exist);
2. (Optional) **Browse File** to load a completely custom licence text;
3. Fill **Year**, **Author**, and any other substitution variables;
4. Live **Preview**;
5. **Apply Licence** → writes `LICENSE` at the project root;
6. **Remove Licence** → deletes the project `LICENSE` (double confirmation).

### 5.3 Changelog Management

Git Integration window → **Changelog**. Visual editor in Keep a Changelog style:

- Supports sections (Added / Changed / Fixed / Deprecated / Removed / Security … — custom names allowed);
- Add individual entries under each section;
- One-click **Export / Import** against `CHANGELOG.md`, or **Save** to overwrite the project's `CHANGELOG.md` in place.

---

## 6. Running Code

### 6.1 Configure Runtime

Menu **Run → Configure Runtime…**:

- **Python Interpreter Path**: Pick a concrete `python.exe` / `python3`;
- **Run Arguments**: Space-separated, appended to the end of the command line.

### 6.2 Run Current File

Menu **Run → Run Current File** (default `F5`, requires the shortcut binding to be enabled by plugin or config):

1. If the file has unsaved edits, a dialog asks whether to save first;
2. Invokes `python <current file> <args>` using the chosen interpreter;
3. stdout / stderr are routed to the **Run output** panel (typically docked at the bottom — plugins can extend the behaviour).

### 6.3 Project Config

Menu **Project → Project Settings**:

- Override the Python interpreter on a **per-project** basis;
- Reads `requirements.txt` at the project root and lists dependencies for inspection.

---

## 7. Settings: Language, Theme, Marketplace URL

Menu **File → Settings**.

### 7.1 Interface Language

Currently bundled:

| Option | Resource file |
| --- | --- |
| 简体中文 | `assets/langs/zh_cn.json` |
| English (US) | `assets/langs/en_us.json` |
| English (UK) | `assets/langs/en_uk.json` |

After switching, the i18n catalog is reloaded and **any newly opened window** uses the new language. If you see raw dotted keys appearing, that means the translation is missing — please send a PR adding those entries.

### 7.2 Theme

- **Built-in themes**: Provided by ttkbootstrap; selection **takes effect immediately** — includes the VSCode-style dark-blue theme, light office-like themes, and more;
- **Accent Color** (Monet picker): choose from the preset swatches or **Custom…** for any colour;
- **Auto Reload Config**: When on, saving settings applies them without restart (recommended on).

### 7.3 Plugin Marketplace URL

- Root URL — do **not** append `/index.json` yourself;
- E.g. `https://my-org.example.com/thoncode-market`;
- Leave blank to disable online install completely — the Marketplace tab simply reports "not configured".

### 7.4 Editor Advanced

- **Tab Indent Spaces**: 2 / 4 / 8 — affects all open editors in real time;
- **Enable Ligatures**: Turns on Fira Code ligatures such as `->`, `>=`, `===`.

---

## 8. Frequently Asked Questions (FAQ)

### Q1: Launch says "Git not installed". What do I do?

A: The Git integration module expects Git to be installed and available on `PATH`. Grab it from <https://git-scm.com/downloads>, install with "Add Git to PATH" ticked, restart Thon Code, and the warning goes away.

### Q2: The Licence Manager dropdown is empty.

A: Two common causes:

1. On first run the host lacked write permission and couldn't materialise the built-in templates into `assets/license/` → manually copy `src/thoncode/assets/license/` alongside the executable;
2. The PyInstaller / Nuitka build script forgot to ship `assets/license` as data files → adjust the packaging script as described in *Plugin Development Guide*, §12.2.

### Q3: After opening Licence Manager from the Git window, both windows freeze.

A: Fixed in v0.4.0. If it still happens double-check you're running a freshly-built binary. Immediate workaround: **don't manually close the Git window** — close the Licence Manager first and input returns. Please attach the build version when reporting.

### Q4: After a hot-reload the same menu item appears twice.

A: Make sure the plugin does NOT override `on_unload` to manually undo menu / hotkey registrations. Everything registered via `self.api.add_menu_item(...)` is auto-cleaned by `PluginAPI._unregister_all_for_plugin`. If you wrote custom cleanup code in `on_unload`, remove it and retry.

### Q5: Marketplace install says "Operation failed: Marketplace URL is not configured."

A: First fill **Settings → Plugin Marketplace URL** and click **Save**. If it's already filled, check there are no trailing spaces / line-breaks in the URL field.

### Q6: On my 16:9 screen some windows' bottom buttons fall below the display.

A: From v0.4.0 onward every built-in window uses `libs.gui.window_helper.ScrollableFrame`. Please upgrade to the latest release. If a third-party plugin's window still has this problem, ask the plugin author to wrap content in `ScrollableFrame` and enforce a sensible minimum window size.

### Q7: After upgrading Thon Code, are my settings / recent projects / authorisation records lost?

A: No. They live in user-level config (typically under `%APPDATA%\ThonCode\` or `.thoncode\` inside the project, depending on `cfg_handle` policy). An upgrade only replaces the binary and built-in assets — never touches user data.

### Q8: How do I completely reset Thon Code?

A: Close the IDE → delete the user-configuration directory (its path is printed on the very first line of startup logs, or run `test/quick_import_sanity.py` to dump it). After deletion, the next launch returns to factory defaults.

---

## 5. Multi-Tab Editor Management

As of v0.5.0, the main editor area is backed by a `ttk.Notebook` **tab container**:

| Tab | Remarks |
| --- | --- |
| Welcome (pinned, permanent) | New file / Open file / Open project / Recent projects list; cannot be closed |
| File tabs (0..N) | One tab per open file. Tab labels are `filename  ✕`; when dirty a leading `*` is prepended: `* filename ✕` |

### 5.1 Operations

- **New file**: Menu **File → New** (Ctrl+N) or Welcome **New File** button → creates a new `Untitled N` tab;
- **Open file**: Menu **File → Open** (Ctrl+O) or double-click in the project tree → already-open files activate their existing tab instead of spawning duplicates;
- **Switch tabs**: Click tab headers, or use Ctrl+Tab (OS/tk default);
- **Close tab**: Click the trailing `✕`. If the buffer is dirty a confirmation dialog **Save / Don't Save / Cancel** appears;
- **Open-at-line**: Go-to-definition opens the target file in a new tab and scrolls straight to the definition line.

### 5.2 Backward-compatible references

To keep older plugins (which reference `main_window.editor` / `main_window.textbox_widget`) working, `EditorTabManager` keeps these attributes on `MainWindow` in sync on every tab switch:

- `current_file`
- `is_dirty`
- `editor` / `editor_manager` / `editor_widget` / `textbox_widget`

No changes are needed on the plugin side.

---

## 6. Smart Auto-Completion (multi-language, lazy imports)

Since v0.5.0 the completion engine is no longer Python-only and no longer limited to static keyword groups.

### 6.1 Trigger

In supported files (`.py / .java / .rs / .js / .ts / .c / .cpp / .h / .go …`) type at least 1 identifier character; the popup appears within 60 ms.

### 6.2 What appears in the list (descending priority)

1. **Highlight-group keywords**: Static words declared in the language JSON or via plugin `add_syntax_groups`;
2. **Standard-library seed symbols**: e.g. `String` / `ArrayList` / `HashMap` injected by the Java plugin;
3. **Local symbols** from the unsaved buffer: function signatures, class names, variable names, parsed by `SymbolLoader` on each keystroke;
4. **Imported symbols**: `import foo` → completes under `foo.xxx`; `from foo import Bar` → completes bare `Bar`.
   - Import resolution is **lazy** — the target file is only parsed when the user actually types a matching prefix, so opening a huge project does not immediately scan tens of MB of source.

### 6.3 Shortcuts

| Key | Action |
| --- | --- |
| ↑ / ↓ | Navigate candidates |
| **Enter / Tab** | Apply the selected candidate |
| Esc | Close popup |

Display format in the list: `name    <signature>` — e.g. `func    def func(a, b)`. The grey signature is a hint only; only `name` is inserted into the buffer.

---

## 7. Ctrl + Right-Click → Go-to-Definition

### 7.1 How to use

Hover the mouse over any identifier (local function, imported class, method, variable), **hold Ctrl and right-click**.

### 7.2 Supported scenarios

| Scenario | Resolution |
| --- | --- |
| Function/class/variable in the current file | Live in-memory index (no disk read) |
| Public symbol in a same-project import | Absolute path resolved via `SymbolLoaderRegistry.resolve_import` → lazy parse → jump |
| JDK standard-library class (Java) | Since `src.zip` is typically absent, shows an informational tooltip instead — attach a plugin that registers a custom `register_import_resolver` to wire up local sources |

### 7.3 Visual feedback

- Cross-file: Opens a new editor tab and switches to it;
- Same-file: Scrolls to the definition line and highlights it with a transient blue stripe that fades after ~0.8 s;
- Not found: A small dialog pops up with `Definition of "xxx" not found`.

---

## 8. FAQ (continued)

### Q9: Why does the completion popup sometimes not appear?

A: It is intentionally suppressed in the following cases:

- The cursor is inside a string / comment / empty file;
- The file extension is not in the supported list (extend `CodeEditor._should_enable_completion` if needed);
- The token under cursor is a lone `.` without a left-hand-side class/module qualifier.

### Q10: Go-to-definition doesn't work for languages other than Python/Java/Rust?

A: First confirm that a plugin has registered `register_symbol_extractor` and `register_import_resolver` for that language. C/C++, Kotlin, Go, etc. currently use only a rough C-like fallback. For richer navigation / completion, write a custom extractor modelled after `plugins/java_support/import_parser.py` and mount it via `PluginAPI`.

### Q11: Will 50+ open tabs slow things down?

A: Each tab keeps a `CodeEditor` instance (Text widget + syntax tags) in memory; cost scales linearly with file size. Import resolution is on-demand, so having 50 tabs open but editing only 2 of them does **not** cause any background crawling of transitive imports. Extremely large files (>100 kLOC) are still best handled in smaller batches.

---

**Further reading**: Sections 13–15 of the [Plugin Development Guide](./plugin_development.md) (completion pipeline, navigation, new Java/Rust examples).

