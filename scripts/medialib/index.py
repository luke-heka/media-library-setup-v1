# Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠
# Provenance marker: sk-w3709n
"""The searchable layer: a manifest per event, and full-text search over transcripts.

Transcripts stay as Markdown in each event's _Index folder for people. The search
index is a SQLite FTS5 table in the library's state folder, rebuilt from any
transcript whose modification time changed, so it is never stale and never
needs a separate command.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import classify, system
from .paths import Library
from .transcribe import index_dir_for

STAMP = re.compile(r"^\[([0-9:]+)\]\s*(.*)$")


# ---------------------------------------------------------------- manifest

def manifest_for(root: Path, event_dir: Path) -> str:
    rows = []
    for here, _dirs, items in classify.walk(event_dir):
        if here.name == "_Index":
            continue
        for p in items:
            if classify.is_junk(p):
                continue
            package = classify.is_package(p)
            if not package and not p.is_file():
                continue
            cat = here.name if here.name in classify.CATEGORIES else classify.category(p)
            size = classify.dir_size(p) if package else p.stat().st_size
            length = ""
            if cat in classify.SPOKEN and classify.is_spoken(p):
                secs = system.media_seconds(p)
                length = system.mmss(secs) if secs else ""
            idx = index_dir_for(p) if here.name in classify.CATEGORIES else here / "_Index"
            t, s = idx / f"{p.name}.transcript.md", idx / f"{p.name}.summary.md"
            snippet = ""
            if t.exists():
                first = next((m.group(2) for ln in t.read_text(errors="replace").splitlines()
                              if (m := STAMP.match(ln))), "")
                snippet = first[:90]
            if s.exists():
                first = next((ln for ln in s.read_text(errors="replace").splitlines()
                              if ln.strip() and not ln.startswith("#")), "")
                snippet = first[:90] or snippet
            rows.append((cat, p.name, system.human(size), length,
                         "yes" if t.exists() else "", snippet.replace("|", "/")))
    order = {c: i for i, c in enumerate(classify.CATEGORIES)}
    rows.sort(key=lambda r: (order.get(r[0], 9), r[1].lower()))
    label = event_dir.name if event_dir != root else root.name
    out = [f"# {label} — manifest", "",
           f"Generated {datetime.now():%Y-%m-%d %H:%M} by media-library-setup. Regenerated on every "
           "`manifest` run — keep your own notes in `_NOTES.md` beside this file.", "",
           "| Folder | File | Size | Length | Transcript | First words / summary |",
           "|---|---|---|---|---|---|"]
    out += [f"| {r[0]} | {r[1].replace('|', '/')} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |" for r in rows]
    out += ["", f"{len(rows)} files, {sum(1 for r in rows if r[4])} with transcripts."]
    return "\n".join(out) + "\n"


def write_manifests(lib: Library, group_by: str) -> list[Path]:
    root = lib.root
    targets = [root] if group_by == "flat" else sorted(
        d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".") and not classify.is_package(d))
    written = []
    for ev in targets:
        idx = ev / "_Index"
        idx.mkdir(exist_ok=True)
        system.set_finder_tag(idx, "_Index")
        (idx / "_MANIFEST.md").write_text(manifest_for(root, ev))
        written.append(idx / "_MANIFEST.md")
    return written


# ---------------------------------------------------------------- search

@dataclass
class Hit:
    event: str
    media: str
    stamp: str
    text: str


class SearchIndex:
    def __init__(self, lib: Library):
        self.lib = lib
        self.db = sqlite3.connect(lib.search_db)
        self.fts = self._has_fts5()
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS docs (path TEXT PRIMARY KEY, mtime REAL NOT NULL,
                                             event TEXT NOT NULL, media TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS lines (path TEXT NOT NULL, stamp TEXT NOT NULL, text TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS lines_path ON lines(path);
        """)
        if self.fts:
            self.db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS lines_fts USING fts5("
                            "text, content='lines', content_rowid='rowid')")

    def _has_fts5(self) -> bool:
        try:
            self.db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _probe USING fts5(x)")
            self.db.execute("DROP TABLE _probe")
            return True
        except sqlite3.OperationalError:
            return False

    def refresh(self) -> int:
        """Index every transcript or summary whose mtime changed. Returns files (re)indexed."""
        root = self.lib.root
        seen: set[str] = set()
        changed = 0
        known = dict(self.db.execute("SELECT path, mtime FROM docs").fetchall())
        for here, _dirs, items in classify.walk(root):
            if here.name != "_Index":
                continue
            event = here.parent.relative_to(root).as_posix() if here.parent != root else ""
            for t in items:
                if not t.name.endswith((".transcript.md", ".summary.md")):
                    continue
                rel = t.relative_to(root).as_posix()
                seen.add(rel)
                mtime = t.stat().st_mtime
                if known.get(rel) == mtime:
                    continue
                media = re.sub(r"\.(transcript|summary)\.md$", "", t.name)
                with self.db:
                    self._drop(rel)
                    self.db.execute("INSERT INTO docs VALUES (?,?,?,?)", (rel, mtime, event, media))
                    rows = []
                    for ln in t.read_text(errors="replace").splitlines():
                        if not ln.strip() or ln.startswith("#"):
                            continue
                        m = STAMP.match(ln)
                        rows.append((rel, m.group(1) if m else "", m.group(2) if m else ln.strip()))
                    self.db.executemany("INSERT INTO lines VALUES (?,?,?)", rows)
                    if self.fts:
                        self.db.execute("INSERT INTO lines_fts(lines_fts) VALUES ('rebuild')")
                changed += 1
        gone = set(known) - seen
        if gone:
            with self.db:
                for rel in gone:
                    self._drop(rel)
                if self.fts:
                    self.db.execute("INSERT INTO lines_fts(lines_fts) VALUES ('rebuild')")
        return changed

    def _drop(self, rel: str) -> None:
        self.db.execute("DELETE FROM lines WHERE path=?", (rel,))
        self.db.execute("DELETE FROM docs WHERE path=?", (rel,))

    def search(self, words: list[str], limit: int = 25) -> list[Hit]:
        terms = [w.strip() for w in words if w.strip()]
        if not terms:
            return []
        if self.fts:
            q = " ".join('"' + t.replace('"', '""') + '"' for t in terms)
            sql = ("SELECT d.event, d.media, l.stamp, l.text FROM lines_fts f "
                   "JOIN lines l ON l.rowid = f.rowid JOIN docs d ON d.path = l.path "
                   "WHERE lines_fts MATCH ? ORDER BY bm25(lines_fts), d.event, d.media, l.rowid LIMIT ?")
            rows = self.db.execute(sql, (q, limit)).fetchall()
        else:
            cond = " AND ".join("lower(l.text) LIKE ?" for _ in terms)
            sql = (f"SELECT d.event, d.media, l.stamp, l.text FROM lines l JOIN docs d ON d.path = l.path "
                   f"WHERE {cond} ORDER BY d.event, d.media, l.rowid LIMIT ?")
            rows = self.db.execute(sql, [f"%{t.lower()}%" for t in terms] + [limit]).fetchall()
        return [Hit(*r) for r in rows]

    def count(self, words: list[str]) -> int:
        terms = [w.strip() for w in words if w.strip()]
        if self.fts:
            q = " ".join('"' + t.replace('"', '""') + '"' for t in terms)
            return self.db.execute("SELECT COUNT(*) FROM lines_fts WHERE lines_fts MATCH ?", (q,)).fetchone()[0]
        cond = " AND ".join("lower(text) LIKE ?" for _ in terms)
        return self.db.execute(f"SELECT COUNT(*) FROM lines WHERE {cond}",
                               [f"%{t.lower()}%" for t in terms]).fetchone()[0]

    def close(self) -> None:
        self.db.close()
