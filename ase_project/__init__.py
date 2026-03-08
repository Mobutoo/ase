"""Asé — Human-centric flow engine."""
from pathlib import Path

_version_file = Path(__file__).resolve().parent.parent / "version.txt"
_parts = _version_file.read_text(encoding="utf-8").strip().split("-")
__version__ = _parts[0] + "." + _parts[1] if len(_parts) > 1 else _parts[0]
