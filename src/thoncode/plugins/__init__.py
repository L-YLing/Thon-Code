#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-plugins-user",
    "Name": "Thon Code User Plugins",
    "Path": ".main.plugins",
    "Entrance": "main.py"
}

"""Thon Code user plugins directory.

Place plugin .py files here. Each file should define a class inheriting
from PluginBase (from libs.plugins). The PluginManager automatically
discovers and loads all .py files in this directory at startup.

Example plugin structure:

    from libs.plugins import PluginBase

    class MyPlugin(PluginBase):
        name = "my_plugin"
        version = "1.0.0"
        description = "Does something useful"

        def on_load(self):
            self.api.get_logger(self.name).info("Loaded!")

        def on_file_open(self, file_path):
            self.api.show_status(f"Opened: {file_path}")
"""
