# Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠
# Provenance marker: sk-w3709n
"""What kind of thing a path is, and how to walk a library without breaking anything.

Three facts this module owns:
  * a file's category (Videos, Photos, Audio, Documents, _Index)
  * that some "folders" are really one document (Keynote, Final Cut...) and must
    never be opened up
  * that camera sidecars belong beside their media file
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".mpg", ".mpeg", ".wmv",
              ".mts", ".m2ts", ".3gp", ".mxf", ".flv", ".ts", ".insv", ".360"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".oga", ".opus",
              ".aiff", ".aif", ".wma", ".caf", ".amr"}
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".gif", ".webp", ".tif", ".tiff",
              ".bmp", ".dng", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".rw2",
              ".svg", ".avif", ".psd"}
DOC_EXTS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".key",
            ".numbers", ".pages", ".txt", ".rtf", ".csv", ".md", ".odt", ".ods", ".odp",
            ".prproj", ".aep", ".drp", ".fcpxml", ".xml", ".zip", ".ai", ".indd"}
SIDECAR_EXTS = {".xmp", ".aae", ".thm", ".lrf", ".lrv", ".srt", ".vtt", ".sbv"}
INDEX_SUFFIXES = (".transcript.md", ".summary.md", ".tags.json")
INDEX_NAMES = ("_MANIFEST", "_NOTES")

# macOS packages: folders Finder shows as one file. Walking into them and filing
# their insides separately destroys the document.
PACKAGE_EXTS = {".key", ".pages", ".numbers", ".rtfd", ".fcpbundle", ".imovielibrary",
                ".photoslibrary", ".band", ".logicx", ".scriv", ".sparsebundle", ".app",
                ".bundle", ".framework", ".xcodeproj", ".fcpcache", ".lrdata", ".lrlibrary",
                ".theater", ".pkg", ".mpkg", ".dvdproj", ".idlib", ".abbu",
                ".migratedphotolibrary"}

CATEGORIES = ("Videos", "Photos", "Audio", "Documents", "_Index")
SPOKEN = ("Videos", "Audio")
JUNK = {".DS_Store", "Icon\r", "desktop.ini", ".localized", "Thumbs.db", "ehthumbs.db"}


def media_category(p: Path) -> str | None:
    ext = p.suffix.lower()
    if ext in VIDEO_EXTS:
        return "Videos"
    if ext in AUDIO_EXTS:
        return "Audio"
    if ext in PHOTO_EXTS:
        return "Photos"
    return None


def category(p: Path, siblings: dict[str, str] | None = None) -> str:
    """Folder a file belongs in. `siblings` maps lower-cased stems of media files in
    the same folder to their category, so clip.srt follows clip.mp4."""
    name = p.name
    if any(name.endswith(s) for s in INDEX_SUFFIXES) or name.startswith(INDEX_NAMES):
        return "_Index"
    cat = media_category(p)
    if cat:
        return cat
    if p.suffix.lower() in SIDECAR_EXTS and siblings:
        partner = siblings.get(p.stem.lower())
        if partner:
            return partner
    return "Documents"


def is_known(p: Path) -> bool:
    ext = p.suffix.lower()
    return (ext in VIDEO_EXTS or ext in AUDIO_EXTS or ext in PHOTO_EXTS or ext in DOC_EXTS
            or ext in SIDECAR_EXTS or ext in PACKAGE_EXTS
            or any(p.name.endswith(s) for s in INDEX_SUFFIXES))


def is_package(p: Path) -> bool:
    return p.is_dir() and p.suffix.lower() in PACKAGE_EXTS


def is_junk(p: Path) -> bool:
    """OS litter only. `._name` is treated as litter only when the file it shadows is
    actually there — a person can legitimately name a file that."""
    if p.name in JUNK:
        return True
    if p.name.startswith("._"):
        return (p.parent / p.name[2:]).exists()
    return False


def is_spoken(p: Path) -> bool:
    return p.suffix.lower() in VIDEO_EXTS or p.suffix.lower() in AUDIO_EXTS


def dir_size(d: Path) -> int:
    total = 0
    for dirpath, _, filenames in os.walk(d):
        for fn in filenames:
            try:
                total += (Path(dirpath) / fn).stat().st_size
            except OSError:
                pass
    return total


def walk(root: Path) -> Iterator[tuple[Path, list[str], list[Path]]]:
    """Like os.walk but never descends into hidden folders or packages. Packages are
    returned as items of their parent, alongside its files."""
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        packages = [d for d in dirnames if is_package(here / d)]
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d not in packages)
        items = [here / fn for fn in sorted(filenames)] + [here / d for d in sorted(packages)]
        yield here, dirnames, items


def items_in(folder: Path) -> list[Path]:
    """Files and packages directly inside one folder, junk removed."""
    out = []
    for p in sorted(folder.iterdir(), key=lambda x: x.name.lower()):
        if is_junk(p) or p.name.startswith("."):
            continue
        if p.is_file() or is_package(p):
            out.append(p)
    return out
