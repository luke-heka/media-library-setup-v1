# Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠
# Provenance marker: sk-w3709n
"""The two approval visuals, from templates/. Everything untrusted is escaped."""
from __future__ import annotations

import html
from pathlib import Path, PurePosixPath
from string import Template

from .classify import CATEGORIES
from .paths import Library
from .plan import Plan
from .scan import Scan

TEMPLATES = Path(__file__).parent / "templates"
SWATCH = {"Videos": "#6736E2", "Photos": "#00A9A5", "Audio": "#16A34A",
          "Documents": "#F5A524", "_Index": "#64748B"}
LANE_TEXT = {
    "Videos": "Every video, in one flat scrollable folder. What a clip shows lives in the "
              "index, not in a subfolder.",
    "Photos": "Every photo and image together, so you can flick through them.",
    "Audio": "Podcast episodes, voice memos and recordings, together and searchable.",
    "Documents": "PDFs, decks, sheets, contracts and edit project files for that event.",
    "_Index": "The searchable layer: a timestamped transcript for every clip. This is what "
              "lets you ask for a moment instead of a filename.",
}


def _t(name: str) -> Template:
    return Template((TEMPLATES / name).read_text())


def _plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


def render(p: Plan, s: Scan) -> tuple[str, str]:
    css = (TEMPLATES / "base.css").read_text()
    e = html.escape
    root_name = e(p.root_name)
    per_dest = p.per_destination
    events = p.events
    present = [c for c in CATEGORIES if any(PurePosixPath(d).name == c for d in per_dest)]

    files_in = s.files_in()
    deepest = sorted(s.folders, key=lambda f: (-f.depth, f.path))[:12]
    before_rows = "".join(
        f'<li class="deep{" sparse" if files_in.get(f.path, 0) <= 2 else ""}">'
        f'<span class="path">{e(f.path)}</span>'
        f'<span class="muted">{files_in.get(f.path, 0)} file{_plural(files_in.get(f.path, 0), "", "s")}</span></li>'
        for f in deepest) or '<li class="muted">no subfolders</li>'
    if len(s.folders) > len(deepest):
        before_rows += f'<li class="more">+ {len(s.folders) - len(deepest)} more folders</li>'

    def event_block(ev: str) -> str:
        def n_of(cat: str) -> int:
            return per_dest.get(f"{ev}/{cat}" if ev else cat, 0)
        rows = "".join(
            f'<li><span class="dot" style="background:{SWATCH[c]}"></span>{c}'
            f'<span class="count">{n_of(c)} file{_plural(n_of(c), "", "s")}</span></li>'
            for c in CATEGORIES if n_of(c))
        return f'<div class="event"><h4>{e(ev) or root_name}</h4><ul class="cats">{rows}</ul></div>'

    shown = 4
    after_blocks = "".join(event_block(ev) for ev in events[:shown]) or event_block("")
    if len(events) > shown:
        rest = [e(ev) for ev in events[shown:]]
        after_blocks += (f'<div class="rest"><b>+ {len(rest)} more event folder{_plural(len(rest), "", "s")}</b>,'
                         f' each with the same folders<span>{", ".join(rest[:6])}'
                         f'{" &hellip;" if len(rest) > 6 else ""}</span></div>')

    n_ren, n_pkg = len(p.renames), sum(1 for m in p.moves if m.package)
    v1 = _t("structure.html").safe_substitute(
        css=css, root_name=root_name,
        folders_before=len(s.folders), depth_before=s.max_depth,
        folders_after=p.folders_after, depth_after=p.depth_after,
        before_rows=before_rows, after_blocks=after_blocks,
        sparse=s.sparse_folders, sparse_verb=_plural(s.sparse_folders, "is", "are"),
        files_total=len(p.moves), files_moving=p.files_moving, cleared=p.folders_cleared(),
        rename_tile=(f'<div class="stat"><b>{n_ren}</b><span>files get a number added because another '
                     f'file shares their name. Neither is lost.</span></div>' if n_ren else ""),
        package_tile=(f'<div class="stat"><b>{n_pkg}</b><span>Keynote / Pages / Final Cut documents moved '
                      f'whole, never opened up</span></div>' if n_pkg else ""))

    lanes = "".join(
        f'<div class="lane"><div class="lane-head" style="--c:{SWATCH[c]}">'
        f'<span class="dot" style="background:{SWATCH[c]}"></span><b>{c}</b>'
        f'<span class="n">{sum(v for k, v in per_dest.items() if PurePosixPath(k).name == c)} files</span>'
        f'</div><p>{LANE_TEXT[c]}</p></div>' for c in present)
    sample = ", ".join(e(ev) for ev in events[:2]) or "single flat library"
    if len(events) > 2:
        sample += f" and {len(events) - 2} more"
    v2 = _t("storage.html").safe_substitute(
        css=css, root_name=root_name, files_total=len(p.moves),
        event_count=len(events) or 1, event_word=_plural(len(events) or 1, "folder", "folders"),
        event_sample=sample, n_folders=len(present) + (0 if "_Index" in present else 1), lanes=lanes)
    return v1, v2


def write(lib: Library, p: Plan, s: Scan) -> tuple[Path, Path]:
    v1, v2 = render(p, s)
    p1, p2 = lib.visuals
    p1.write_text(v1)
    p2.write_text(v2)
    return p1, p2
