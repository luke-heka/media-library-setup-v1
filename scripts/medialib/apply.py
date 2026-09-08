# Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠
# Provenance marker: sk-w3709n
"""Move files under an approved plan, and put them back. No file is ever deleted."""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath

from . import plan as planmod
from . import system
from .journal import Journal
from .paths import Library
from .plan import Plan


class Refused(Exception):
    """The gate said no. The message is for the person."""


@dataclass
class ApplyResult:
    moved: int = 0
    skipped: int = 0
    cleared: int = 0
    created: list[str] = field(default_factory=list)
    failures: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class RollbackResult:
    restored: int = 0
    cleared: int = 0
    renamed: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.problems


def check_gate(lib: Library, p: Plan, approver: str) -> list[planmod.Move]:
    """Every reason apply may refuse, in the order a person would hit them."""
    if not all(v.exists() for v in lib.visuals):
        raise Refused("The visuals have not been generated, so nobody has seen this plan.\n"
                      "Run: library.py visualise")
    if len(approver.strip()) < 2:
        raise Refused("Refusing to move anything without approval.\n"
                      "Show the two visuals to the owner, get a clear yes, then re-run with:\n"
                      '  library.py apply --approved-by "<their name>"')
    if p.shown_digest != p.digest():
        raise Refused("This plan has changed since the visuals were made, so what was approved\n"
                      "is not what would happen. Re-run:  library.py visualise\n"
                      "then show them again before applying.")
    if not lib.root.is_dir():
        raise Refused(f"The library folder is not there any more:  {lib.root}\n"
                      "If it is on Google Drive, check Drive for Desktop is running and signed in.")
    todo = [m for m in p.moves if m.moving]
    if not todo:
        raise Refused("Every file is already where it should be. There is nothing to move,\n"
                      "so there is nothing to approve. This library is already organised.")
    return todo


def _unique(dest: Path) -> Path:
    stem, ext, n = dest.stem, dest.suffix, 2
    while dest.exists() or dest.is_symlink():
        dest = dest.with_name(f"{stem}-{n}{ext}")
        n += 1
    return dest


def _clear_empty(root: Path, candidates: set[Path]) -> int:
    """Remove only truly empty folders, walking up but never past the root."""
    removed = 0
    while candidates:
        nxt: set[Path] = set()
        for d in candidates:
            if not d.is_dir() or d == root or root not in d.parents:
                continue
            if any(True for _ in d.iterdir()):
                continue
            parent = d.parent
            try:
                d.rmdir()
                removed += 1
                if parent != root:
                    nxt.add(parent)
            except OSError:
                pass
        candidates = nxt
    return removed


def run(lib: Library, p: Plan, approver: str, log=lambda s: None) -> ApplyResult:
    todo = check_gate(lib, p, approver)
    root = lib.root
    res = ApplyResult()
    journal = Journal(lib)
    emptied: set[Path] = set()
    made: set[str] = set()
    try:
        for m in todo:
            src = root / m.path
            if not src.exists() and not src.is_symlink():
                res.skipped += 1
                continue
            dest_dir = root / m.dst
            if m.dst not in made:
                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    system.force_case(dest_dir)
                    system.set_finder_tag(dest_dir, m.category)
                except OSError as e:
                    res.failures.append((m.name, f"could not create {m.dst}: {e.strerror}"))
                    continue
                made.add(m.dst)
                res.created.append(m.dst)
                log(m.dst)
            dest = dest_dir / m.final_name
            if (dest.exists() or dest.is_symlink()) and dest != src and not system.same_file(dest, src):
                dest = _unique(dest)      # only external changes since the scan reach here
            try:
                shutil.move(str(src), str(dest))
            except Exception as e:
                res.failures.append((m.name, f"{type(e).__name__}: {e}"))
                continue
            journal.record(m.name, dest.name, m.src, m.dst)   # after the move, never before
            emptied.add(root / m.src if m.src != "." else root)
            res.moved += 1
    finally:
        journal.close()
    res.cleared = _clear_empty(root, {d for d in emptied if d != root})

    p.approved = True
    p.approved_by = approver.strip()
    p.applied_at = datetime.now().isoformat(timespec="seconds")
    p.rolled_back_at = ""
    p.partial_rollback_at = ""
    planmod.save(lib, p)
    return res


def rollback(lib: Library, p: Plan) -> RollbackResult:
    root = lib.root
    res = RollbackResult()
    journal = Journal(lib)
    try:
        rows = journal.pending()          # newest first: a file moved twice lands at its origin
        for r in rows:
            src = root / r.moved_to / r.final_name
            dest_dir = root / r.moved_from if r.moved_from != "." else root
            dest = dest_dir / r.original_name
            if not src.exists() and not src.is_symlink():
                res.problems.append(f"{r.final_name} is not where the journal says it is")
                continue
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                if (dest.exists() or dest.is_symlink()) and not system.same_file(dest, src):
                    dest = _unique(dest)
                    res.renamed.append(f"{r.original_name} came back as {dest.name} — "
                                       f"something else now uses its old name")
                shutil.move(str(src), str(dest))
                journal.mark_restored(r.id, dest.name)
                res.restored += 1
            except Exception as e:
                res.problems.append(f"{r.final_name}: {type(e).__name__}")
        # Restore original folder casing, every component, outermost first.
        for original in sorted({r.moved_from for r in rows if r.moved_from != "."}):
            parts = PurePosixPath(original).parts
            for i in range(1, len(parts) + 1):
                d = root.joinpath(*parts[:i])
                if d.is_dir():
                    system.force_case(d)
        res.cleared = _clear_empty(root, {root / r.moved_to for r in rows})
    finally:
        journal.close()

    stamp = datetime.now().isoformat(timespec="seconds")
    if res.complete:
        p.approved = False
        p.rolled_back_at = stamp
        p.partial_rollback_at = ""
        p.shown_digest = ""
    else:
        p.approved = True
        p.partial_rollback_at = stamp
    planmod.save(lib, p)
    return res
