#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-plugin-sample",
    "Name": "Sample Plugin",
    "Path": ".main.plugins.sample_plugin",
    "Entrance": "main.py"
}

"""Sample plugin demonstrating the Thon Code plugin system.

Logs file open events to the application logger and shows a status
message. Safe to delete or use as a template for new plugins.
"""

from libs.plugins import PluginBase


class SamplePlugin(PluginBase):
    """Logs file-open events and demonstrates plugin lifecycle."""

    name = "sample_plugin"
    version = "1.0.0"
    description = "Logs file open events (demo plugin)"
    author = "Thon Code"

    def on_load(self) -> None:
        """Called when the plugin is loaded; log initialization."""
        logger = self.api.get_logger(self.name)
        logger.info("Sample plugin loaded v%s", self.version)

    def on_file_open(self, file_path: str) -> None:
        """Called when a file is opened in the editor.

        Args:
            file_path: Absolute path of the opened file
        """
        logger = self.api.get_logger(self.name)
        logger.debug("File opened: %s", file_path)
        self.api.show_status(f"[{self.name}] {file_path}")

    def on_unload(self) -> None:
        """Called when the plugin is unloaded; log cleanup."""
        logger = self.api.get_logger(self.name)
        logger.info("Sample plugin unloaded")
