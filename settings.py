"""
Persistent user settings — stored as JSON in the user's home directory.
All I/O is best-effort: exceptions are silenced so a bad settings file
never prevents the app from starting.
"""

import json
from pathlib import Path

_FILE = Path.home() / ".markitdown_converter.json"
_MAX_RECENT = 10

_DEFAULTS: dict = {
    "theme": "System",
    "ocr_language": "English",
    "last_output_folder": "",
    "recent_files": [],
}


def load() -> dict:
    """Return settings dict, falling back to defaults on any read/parse error."""
    try:
        data = json.loads(_FILE.read_text(encoding="utf-8"))
        merged = {**_DEFAULTS, **data}
        merged["recent_files"] = [
            p for p in merged.get("recent_files", [])
            if isinstance(p, str)
        ][:_MAX_RECENT]
        return merged
    except Exception:
        return dict(_DEFAULTS)


def save(settings: dict) -> None:
    """Write settings to disk; silently ignore any I/O error."""
    try:
        _FILE.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def add_recent(settings: dict, path: str) -> None:
    """Prepend *path* to recent_files, deduplicating and capping at _MAX_RECENT."""
    recent = [p for p in settings.get("recent_files", []) if p != path]
    recent.insert(0, path)
    settings["recent_files"] = recent[:_MAX_RECENT]
