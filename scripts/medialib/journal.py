# Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠
# Provenance marker: sk-w3709n
"""The move journal: every move ever made to a library, in SQLite, never deleted.

One row per move. `restored_at` is set when the undo puts that file back, so a
partial undo leaves exactly the unfinished rows pending and a second run retries
just those. Older state folders carrying a rollback.csv from version 0.x are
imported on first open so their undo still works.
"""
from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .paths import Library

SCHEMA = """
CREATE TABLE IF NOT EXISTS moves (
    id            INTEGER PRIMARY KEY,
    original_name TEXT NOT NULL,
    final_name    TEXT NOT NULL,
    moved_from    TEXT NOT NULL,
    moved_to      TEXT NOT NULL,
    at            TEXT NOT NULL,
    restored_at   TEXT,
    restored_as   TEXT
);
CREATE INDEX IF NOT EXISTS moves_pending ON moves(restored_at) WHERE restored_at IS NULL;
"""


@dataclass(frozen=True)
class Entry:
    id: int
    original_name: str
    final_name: str
    moved_from: str
    moved_to: str
    at: str


class Journal:
    def __init__(self, lib: Library):
        self.path = lib.journal_file
        self.db = sqlite3.connect(self.path)
        self.db.executescript(SCHEMA)
        self._import_legacy(lib.state / "rollback.csv")

    def _import_legacy(self, csv_path: Path) -> None:
        if not csv_path.exists():
            return
        with csv_path.open(newline="") as fh:
            rows = list(csv.DictReader(fh))
        with self.db:
            for r in rows:
                self.db.execute(
                    "INSERT INTO moves(original_name, final_name, moved_from, moved_to, at)"
                    " VALUES (?,?,?,?,?)",
                    (r.get("original_name") or r.get("final_name") or "", r["final_name"],
                     r["moved_from"], r["moved_to"], r.get("at") or ""))
        csv_path.rename(csv_path.with_name(f"rollback-imported-{datetime.now():%Y%m%d-%H%M%S}.csv"))

    def record(self, original_name: str, final_name: str, moved_from: str, moved_to: str) -> None:
        """Called after a move succeeded. Committed and fsynced before returning."""
        with self.db:
            self.db.execute(
                "INSERT INTO moves(original_name, final_name, moved_from, moved_to, at)"
                " VALUES (?,?,?,?,?)",
                (original_name, final_name, moved_from, moved_to,
                 datetime.now().isoformat(timespec="seconds")))

    def pending(self) -> list[Entry]:
        """Moves not yet undone, newest first."""
        cur = self.db.execute(
            "SELECT id, original_name, final_name, moved_from, moved_to, at FROM moves"
            " WHERE restored_at IS NULL ORDER BY id DESC")
        return [Entry(*row) for row in cur.fetchall()]

    def mark_restored(self, entry_id: int, restored_as: str) -> None:
        with self.db:
            self.db.execute("UPDATE moves SET restored_at=?, restored_as=? WHERE id=?",
                            (datetime.now().isoformat(timespec="seconds"), restored_as, entry_id))

    def counts(self) -> tuple[int, int]:
        """(pending, total)."""
        pend = self.db.execute("SELECT COUNT(*) FROM moves WHERE restored_at IS NULL").fetchone()[0]
        total = self.db.execute("SELECT COUNT(*) FROM moves").fetchone()[0]
        return pend, total

    def close(self) -> None:
        self.db.close()
