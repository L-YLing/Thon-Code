# Thon Code Plugin Development Guide

## Overview

Thon Code provides a lightweight plugin system that allows extending the editor's functionality without modifying core source code. Plugins are Python files placed in the `src/thoncode/plugins/` directory and are automatically discovered and loaded on startup.

## Quick Start

Create a `.py` file in the `plugins/` directory:

```python
from libs.plugins import PluginBase

class MyPlugin(PluginBase):
    name = "my_plugin"
    version = "1.0.0"
    description = "My first Thon Code plugin"

    def on_load(self):
        self.api.show_status("MyPlugin loaded!")

    def on_file_open(self, file_path):
        self.api.get_logger("my_plugin").info("Opened: %s", file_path)

    def on_unload(self):
        self.api.show_status("MyPlugin unloaded")
```

Restart Thon Code (or click Refresh in Plugin Manager) and the plugin will be active.

## PluginBase

All plugins must inherit from `PluginBase` and set the following class attributes:

| Attribute     | Type   | Description                        |
|---------------|--------|------------------------------------|
| `name`        | str    | Unique plugin identifier           |
| `version`     | str    | Semantic version string            |
| `description` | str    | Human-readable description         |

The `__init__(self, api)` method receives a `PluginAPI` instance; call `super().__init__(api)` to store it as `self.api`.

## Hooks

Hooks are optional methods. Implement any subset; the host calls them at the appropriate lifecycle point.

| Hook                       | Trigger                                  | Parameters          |
|----------------------------|------------------------------------------|---------------------|
| `on_load()`                | Plugin loaded, before first use          | —                   |
| `on_unload()`              | Plugin about to be unloaded              | —                   |
| `on_file_open(path)`       | A file was opened in the editor          | `path`: file path   |
| `on_file_save(path)`       | A file was saved                         | `path`: file path   |
| `on_file_close(path)`      | A file was closed                        | `path`: file path   |
| `on_editor_change(text)`   | Editor content modified                  | `text`: full text   |
| `on_tree_refresh()`        | File tree was refreshed                  | —                   |
| `on_theme_change(name)`    | Theme was switched                       | `name`: theme name  |
| `on_project_open(path)`    | A project folder was opened              | `path`: folder path |

## PluginAPI Reference

The `PluginAPI` object (`self.api`) provides controlled access to host services.

### Logging

```python
logger = self.api.get_logger("my_plugin")
logger.info("Information message")
logger.error("Error message")
```

### Configuration

```python
cfg = self.api.get_config()          # Read full config dict
self.api.set_config("my_key", 42)    # Write and persist a key
```

### Status Bar

```python
self.api.show_status("Processing...")
```

### Editor Access

```python
text = self.api.get_editor_text()           # Get all editor content
self.api.set_editor_text("new content")     # Replace editor content
sel = self.api.get_editor_selection()       # Get selected text
self.api.insert_editor_text("snippet")      # Insert at cursor
```

### Project Info

```python
root = self.api.get_project_root()          # Current project root
current = self.api.get_current_file()       # Currently open file path
recent = self.api.get_recent_projects()     # List of recent projects
```

### Theme

```python
theme = self.api.get_current_theme()        # e.g., "darkly"
accent = self.api.get_accent_color()        # e.g., "#0078D7" or None
```

### File Tree

```python
self.api.refresh_file_tree()                # Trigger tree refresh
```

### i18n

```python
text = self.api.get_text("status.ready")    # Localized string
```

### Plugin Management

```python
names = self.api.get_plugin_names()         # List of loaded plugin names
```

## Error Handling

Plugin errors are isolated: if one plugin raises an exception in a hook, other plugins are unaffected. Errors are logged to the host logger and the test log directory.

## File Convention

- Plugin files must end with `.py` and NOT start with `_` (underscore-prefixed files are ignored).
- One plugin class per file is recommended.
- The plugin class must be the only `PluginBase` subclass in the file.

## Discovery & Reload

Plugins are discovered from the `plugins/` directory on startup. Use the Plugin Manager (Tools menu > Plugin Manager) to refresh the list at runtime without restarting.
