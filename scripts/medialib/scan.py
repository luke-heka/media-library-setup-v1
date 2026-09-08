# Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠
# Provenance marker: sk-w3709n
"""Read-only survey of a folder. Writes nothing inside the library."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from . import VERSION, classify
from .paths import Library


@dataclass
class Item:
    name: str
    path: str          # relative to root, forward slashes
    parent: str        # relative folder, "." for the root
    depth: int
    size: int
    category: str
    package: bool = False


@dataclass
class Folder:
    name: str
    path: str
    depth: int


@dataclass
class Scan:
    version: str
    scanned_at: str
    root: str
    root_name: str
    files: list[Item]
    folders: list[Folder]
    unknown_extensions: dict[str, int] = field(default_factory=dict)

    @property
    def max_depth(self) -> int:
        return max((f.depth for f in self.folders), default=0)

    @property
    def sparse_folders(self) -> int:
        per = Counter(f.parent for f in self.files)
        return sum(1 for f in self.folders if per.get(f.path, 0) <= 2)

    @property
    def total_bytes(self) -> int:
        return sum(f.size for f in self.files)

    @property
    def by_category(self) -> dict[str, int]:
        return dict(Counter(f.category for f in self.files))

    @property
    def packages(self) -> int:
        return sum(1 for f in self.files if f.package)

    def files_in(self) -> Counter:
        return Counter(f.parent for f in self.files)


class EmptyLibrary(Exception):
    pass


def rel(p: Path, root: Path) -> str:
    return p.relative_to(root).as_posix()


def scan(root: Path) -> Scan:
    if classify.is_package(root):
        raise EmptyLibrary(f"'{root.name}' is a single document (a package), not a folder of media.")
    files: list[Item] = []
    folders: list[Folder] = []
    unknown: Counter = Counter()
    for here, _dirs, items in classify.walk(root):
        rel_dir = "." if here == root else rel(here, root)
        depth = 0 if here == root else len(here.relative_to(root).parts)
        if here != root:
            folders.append(Folder(here.name, rel_dir, depth))
        siblings = {p.stem.lower(): classify.media_category(p)
                    for p in items if classify.media_category(p) and not classify.is_junk(p)}
        for p in items:
            if classify.is_junk(p):
                continue
            package = classify.is_package(p)
            if not package and not p.is_file():
                continue
            try:
                size = classify.dir_size(p) if package else p.stat().st_size
            except OSError:
                continue
            if not classify.is_known(p):
                unknown[p.suffix.lower() or "(no extension)"] += 1
            files.append(Item(p.name, rel(p, root), rel_dir, depth, size,
                              classify.category(p, siblings), package))
    if not files:
        raise EmptyLibrary(
            f"'{root.name}' has no photos, videos, audio or documents in it.\n"
            "There is nothing to organise. Check you pointed at the right folder —\n"
            "if your Drive is still syncing, the files may not be here yet.")
    return Scan(VERSION, datetime.now().isoformat(timespec="seconds"), str(root), root.name,
                files, folders, dict(unknown))


def save(lib: Library, s: Scan) -> None:
    lib.scan_file.write_text(json.dumps(asdict(s), indent=1))
    # A fresh scan invalidates any plan built from the previous one.
    lib.plan_file.unlink(missing_ok=True)
    for v in lib.visuals:
        v.unlink(missing_ok=True)


def load(lib: Library) -> Scan:
    d = json.loads(lib.scan_file.read_text())
    return Scan(d["version"], d["scanned_at"], d["root"], d["root_name"],
                [Item(**f) for f in d["files"]], [Folder(**f) for f in d["folders"]],
                d.get("unknown_extensions", {}))
