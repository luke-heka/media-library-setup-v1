# Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠
# Provenance marker: sk-w3709n
"""Where state lives, and the Library context every command works on.

Each library gets its own state folder keyed to its path, so scanning a second
library never touches the first one's plan or journal. MEDIA_LIBRARY_WORK_DIR
overrides the base so tests never touch real state.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path


def work_base() -> Path:
    return Path(os.environ.get("MEDIA_LIBRARY_WORK_DIR",
                               Path.home() / "active" / "media-library-setup"))


def config_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", Path.home())) / "media-library-setup"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "media-library-setup"


def slug_for(root: Path) -> str:
    tag = hashlib.sha256(str(root).encode()).hexdigest()[:8]
    name = re.sub(r"[^A-Za-z0-9]+", "-", root.name).strip("-").lower() or "library"
    return f"{name}-{tag}"


@dataclass(frozen=True)
class Library:
    """One library being organised: its root folder and its private state folder."""
    root: Path
    state: Path

    @property
    def scan_file(self) -> Path:
        return self.state / "scan.json"

    @property
    def plan_file(self) -> Path:
        return self.state / "plan.json"

    @property
    def visuals(self) -> tuple[Path, Path]:
        return (self.state / "1-folder-structure.html",
                self.state / "2-where-things-are-stored.html")

    @property
    def journal_file(self) -> Path:
        return self.state / "journal.sqlite"

    @property
    def bank(self) -> Path:
        return self.state / "transcribed"

    @property
    def tmp(self) -> Path:
        return self.state / "tmp"

    @property
    def search_db(self) -> Path:
        return self.state / "search.sqlite"


class NoLibrary(Exception):
    """Raised with a plain-English message when no library can be resumed."""


def open_library(root: Path) -> Library:
    """Point state at this library and remember it as the current one."""
    root = root.expanduser().resolve()
    lib = Library(root, work_base() / slug_for(root))
    lib.state.mkdir(parents=True, exist_ok=True)
    (work_base() / "current.json").write_text(json.dumps(
        {"root": str(root), "slug": slug_for(root)}, indent=2))
    return lib


def current_library(pin: str | None = None) -> Library:
    """Resume a library. `pin` selects one explicitly instead of the last scanned."""
    if pin:
        root = Path(pin).expanduser().resolve()
        lib = Library(root, work_base() / slug_for(root))
        if not lib.scan_file.exists():
            raise NoLibrary(f"'{root}' has not been scanned. Run:  library.py scan \"{root}\"")
        return lib
    ptr = work_base() / "current.json"
    if not ptr.exists():
        raise NoLibrary("No library scanned yet. Run:  library.py scan \"<your folder>\"")
    cur = json.loads(ptr.read_text())
    lib = Library(Path(cur["root"]), work_base() / cur["slug"])
    if not lib.scan_file.exists():
        raise NoLibrary("That library's scan is missing. Run scan again.")
    return lib


def other_libraries(lib: Library) -> list[Path]:
    base = work_base()
    if not base.is_dir():
        return []
    return [d for d in base.iterdir() if d.is_dir() and d != lib.state]
