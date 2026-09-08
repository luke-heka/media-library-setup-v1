# Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠
# Provenance marker: sk-w3709n
"""The proposed structure, and the fingerprint that ties an approval to it."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import PurePosixPath

from . import VERSION
from .classify import CATEGORIES
from .paths import Library
from .scan import Scan

CATEGORY_ISH = {c.lower() for c in CATEGORIES} | {
    "images", "docs", "index", "raw videos", "raw photos", "edits", "video", "photo",
    "testimonials", "text", "metadata", "transcripts", "summaries", "music", "sound",
    "footage", "stills", "clips", "pictures", "pics", "recordings", "exports", "raw"}


@dataclass
class Move:
    path: str           # current relative path
    name: str           # current name
    src: str            # current folder ("." = root)
    dst: str            # destination folder, e.g. "Brisbane May/Videos"
    final_name: str     # name at the destination (differs only on a collision)
    category: str
    event: str
    package: bool = False

    @property
    def moving(self) -> bool:
        return self.src != self.dst


@dataclass
class Plan:
    version: str
    planned_at: str
    root: str
    root_name: str
    group_by: str
    moves: list[Move]
    approved: bool = False
    approved_by: str = ""
    applied_at: str = ""
    rolled_back_at: str = ""
    partial_rollback_at: str = ""
    shown_digest: str = ""
    notes: dict = field(default_factory=dict)

    # ---- derived
    @property
    def destinations(self) -> list[str]:
        return sorted({m.dst for m in self.moves})

    @property
    def events(self) -> list[str]:
        return sorted({m.event for m in self.moves if m.event})

    @property
    def per_destination(self) -> dict[str, int]:
        return dict(Counter(m.dst for m in self.moves))

    @property
    def files_moving(self) -> int:
        return sum(1 for m in self.moves if m.moving)

    @property
    def renames(self) -> list[Move]:
        return [m for m in self.moves if m.final_name != m.name]

    @property
    def folders_after(self) -> int:
        return len(self.destinations) + len(self.events)

    @property
    def depth_after(self) -> int:
        return 2 if self.group_by != "flat" else 1

    def digest(self) -> str:
        payload = json.dumps({
            "root": self.root, "group_by": self.group_by,
            "moves": [[m.path, m.src, m.name, m.dst, m.final_name] for m in self.moves],
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def folders_cleared(self) -> int:
        """Folders this plan genuinely empties: every file leaves and no destination
        is created inside them."""
        from_dirs = Counter(m.src for m in self.moves)
        leaving = Counter(m.src for m in self.moves if m.moving)
        dest_parents = {PurePosixPath(d).parts[0] for d in self.destinations if "/" in d}
        return sum(1 for d, n in from_dirs.items()
                   if d != "." and leaving.get(d, 0) == n and d not in dest_parents)


def detect_shape(s: Scan) -> str:
    """'flat' for one shoot whose subfolders are categories, 'event' for a library."""
    level1 = [f.name.strip().lower() for f in s.folders if f.depth == 1]
    if not level1:
        return "flat"
    if sum(1 for n in level1 if n in CATEGORY_ISH) >= max(1, len(level1) // 2):
        return "flat"
    loose = sum(1 for f in s.files if f.parent == ".")
    if loose > len(s.files) // 2:
        return "flat"
    return "event"


def why_shape(s: Scan, group_by: str) -> str:
    if not any(f.depth == 1 for f in s.folders):
        return "everything sits in one folder already"
    if group_by == "flat":
        return "its subfolders are already categories, so this is one shoot"
    return "its subfolders look like separate events"


def build(s: Scan, group_by: str) -> Plan:
    moves: list[Move] = []
    for f in s.files:
        if group_by == "flat":
            event = ""
        else:
            event = PurePosixPath(f.parent).parts[0] if f.parent != "." else "Unsorted"
        dst = f"{event}/{f.category}" if event else f.category
        moves.append(Move(f.path, f.name, f.parent, dst, f.name, f.category, event, f.package))

    # Same name landing in the same folder gets -2. Decided here, before approval,
    # so the visuals and the fingerprint cover it.
    taken: dict[str, set[str]] = {}
    for m in moves:
        here = taken.setdefault(m.dst, set())
        name = m.name
        if name.lower() in here:
            stem, _, ext = name.rpartition(".")
            ext = f".{ext}" if stem else ""
            stem = stem or name
            n = 2
            while f"{stem}-{n}{ext}".lower() in here:
                n += 1
            name = f"{stem}-{n}{ext}"
        here.add(name.lower())
        m.final_name = name
    return Plan(VERSION, datetime.now().isoformat(timespec="seconds"), s.root, s.root_name,
                group_by, moves)


def save(lib: Library, p: Plan) -> None:
    lib.plan_file.write_text(json.dumps(asdict(p), indent=1))


def load(lib: Library) -> Plan:
    d = json.loads(lib.plan_file.read_text())
    moves = [Move(**m) for m in d.pop("moves")]
    return Plan(moves=moves, **d)
