# Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠
# Provenance marker: sk-w3709n
"""Platform helpers. Everything that talks to the operating system lives here so the
rest of the package can be tested without it."""
from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

IS_MAC = sys.platform == "darwin"
IS_WIN = os.name == "nt"
IS_LINUX = not IS_MAC and not IS_WIN
PLATFORM = "Mac" if IS_MAC else "Windows" if IS_WIN else "Linux"

# macOS Finder tag colours: 1 grey, 2 green, 3 purple, 4 blue, 5 yellow, 6 red, 7 orange.
FINDER_TAGS = {"Videos": ("Purple", 3), "Photos": ("Blue", 4), "Audio": ("Green", 2),
               "Documents": ("Orange", 7), "_Index": ("Grey", 1)}


def has_tool(name: str) -> bool:
    return shutil.which(name) is not None


def open_file(p: Path) -> bool:
    """Open a file in whatever this computer uses. False if it could not."""
    try:
        if IS_MAC:
            subprocess.run(["open", str(p)], check=False)
        elif IS_WIN:
            os.startfile(str(p))  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(p)], check=False)
        return True
    except Exception:
        return False


def set_finder_tag(path: Path, cat: str) -> None:
    """Colour a folder in Finder. Cosmetic; a failure is never fatal."""
    tag = FINDER_TAGS.get(cat)
    if not tag or not IS_MAC:
        return
    try:
        data = plistlib.dumps([f"{tag[0]}\n{tag[1]}"], fmt=plistlib.FMT_BINARY)
        subprocess.run(["/usr/bin/xattr", "-w", "-x", "com.apple.metadata:_kMDItemUserTags",
                        data.hex(), str(path)], capture_output=True, check=False)
    except Exception:
        pass


def force_case(path: Path) -> None:
    """Make the folder on disk use `path`'s casing. macOS and Windows are
    case-insensitive, so mkdir("Videos") silently reuses an existing "videos"."""
    try:
        actual = next((c.name for c in path.parent.iterdir()
                       if c.name.lower() == path.name.lower()), None)
    except OSError:
        return
    if actual is None or actual == path.name:
        return
    tmp = path.parent / f".__case__{path.name}"
    try:
        (path.parent / actual).rename(tmp)
        tmp.rename(path)
    except OSError:
        if tmp.exists():
            tmp.rename(path.parent / actual)


def same_file(a: Path, b: Path) -> bool:
    try:
        return a.exists() and b.exists() and a.samefile(b)
    except OSError:
        return False


def media_seconds(p: Path) -> float:
    """Length of a video or audio file via ffprobe. 0.0 if it cannot be read."""
    if not has_tool("ffprobe"):
        return 0.0
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(p)], capture_output=True, text=True)
    try:
        return max(0.0, float(r.stdout.strip()))
    except ValueError:
        return 0.0


def free_disk(p: Path) -> int:
    return shutil.disk_usage(p).free


def find_drive_folders() -> list[Path]:
    """Where Google Drive for Desktop mounts, across the versions people have."""
    out: list[Path] = []
    cs = Path.home() / "Library" / "CloudStorage"
    if cs.is_dir():
        out += sorted(p for p in cs.iterdir() if p.name.startswith("GoogleDrive-"))
    for legacy in (Path.home() / "Google Drive", Path("/Volumes/GoogleDrive")):
        if legacy.is_dir():
            out.append(legacy)
    for letter in "GHIJKL":
        d = Path(f"{letter}:/My Drive")
        if d.is_dir():
            out.append(d)
    return out


def ffmpeg_install_line() -> str:
    if IS_MAC:
        return "brew install ffmpeg\n    No Homebrew? Install it from https://brew.sh first."
    if IS_WIN:
        return ("winget install --id Gyan.FFmpeg -e\n"
                "    Then close this window and open a new one so it is found.")
    return "sudo apt install ffmpeg      (or your distribution's equivalent)"


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def mmss(seconds: float) -> str:
    s = int(round(seconds))
    if s >= 3600:
        return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    return f"{s // 60:02d}:{s % 60:02d}"
