try:
    from .settings_win import SettingsWindow  # noqa: F401
except Exception:
    SettingsWindow = None  # type: ignore[assignment,misc]

try:
    from .code_editor import CodeEditor  # noqa: F401
except Exception:
    CodeEditor = None  # type: ignore[assignment,misc]
