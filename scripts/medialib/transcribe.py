# Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠
# Provenance marker: sk-w3709n
"""Turn speech into timestamped text.

The transcriber is a small interface so the real one (OpenAI whisper-1 over a
standard-library HTTP POST) can be swapped for a fake in tests without a network.
Paid results are banked locally the moment they arrive, so nothing is ever paid
for twice.
"""
from __future__ import annotations

import io
import json
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol

from . import VERSION, classify, system
from .paths import Library

# Verified on the OpenAI pricing page 2026-09-08. whisper-1 is $0.006/min and the only
# transcription model that returns segment timestamps.
MODEL = "whisper-1"
USD_PER_MIN = 0.006
PRICE_VERIFIED = "2026-09-08"
ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"
UPLOAD_CAP = 24 * 1024 * 1024
CHUNK_SECONDS = 3000


@dataclass
class Segment:
    start: float
    end: float
    text: str


class Transcriber(Protocol):
    def transcribe(self, audio: Path, filename: str) -> tuple[list[Segment], float]:
        """Return (segments, duration_seconds) for one audio file under the cap."""


class UserFixable(Exception):
    """Bad key, no credit: the person has to act; the run stops."""


# ---------------------------------------------------------------- HTTP

def multipart(fields: dict[str, str], file_field: str, filename: str, data: bytes,
              content_type: str = "audio/mpeg") -> tuple[bytes, str]:
    boundary = "----media-library-" + uuid.uuid4().hex
    buf = io.BytesIO()
    for k, v in fields.items():
        buf.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    safe = re.sub(r'["\r\n\\]', "_", filename)
    buf.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
              f'filename="{safe}"\r\nContent-Type: {content_type}\r\n\r\n'.encode())
    buf.write(data)
    buf.write(f"\r\n--{boundary}--\r\n".encode())
    return buf.getvalue(), boundary


class _IPv4Only:
    """Some Macs stall ~40 s per HTTPS call trying IPv6 first."""
    def __enter__(self):
        self.real = socket.getaddrinfo
        real = self.real

        def only4(*a, **kw):
            res = [r for r in real(*a, **kw) if r[0] == socket.AF_INET]
            return res or real(*a, **kw)
        socket.getaddrinfo = only4

    def __exit__(self, *exc):
        socket.getaddrinfo = self.real


class OpenAIWhisper:
    def __init__(self, key: str):
        self.key = key

    def transcribe(self, audio: Path, filename: str) -> tuple[list[Segment], float]:
        body, boundary = multipart({"model": MODEL, "response_format": "verbose_json",
                                    "timestamp_granularities[]": "segment"},
                                   "file", filename, audio.read_bytes())
        req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
            "Authorization": f"Bearer {self.key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": f"media-library-setup/{VERSION}"})
        last = ""
        with _IPv4Only():
            for attempt in range(1, 4):
                try:
                    with urllib.request.urlopen(req, timeout=900) as resp:
                        d = json.loads(resp.read().decode("utf-8"))
                    segs = [Segment(float(s.get("start", 0)), float(s.get("end", 0)), s.get("text", ""))
                            for s in d.get("segments") or []]
                    if not segs and d.get("text"):
                        segs = [Segment(0.0, 0.0, d["text"])]
                    return segs, float(d.get("duration") or 0)
                except urllib.error.HTTPError as e:
                    text = e.read().decode("utf-8", "replace")[:600]
                    if e.code == 401:
                        raise UserFixable("OpenAI rejected the key (401). Set a fresh one with:  library.py key")
                    if "insufficient_quota" in text:
                        raise UserFixable("The key works but the OpenAI account has no credit.\n"
                                          "Add some at https://platform.openai.com/settings/organization/billing")
                    if e.code in (408, 409, 429, 500, 502, 503, 504) and attempt < 3:
                        last = f"HTTP {e.code}"
                        time.sleep(5 * attempt)
                        continue
                    raise RuntimeError(f"HTTP {e.code}: {text[:200]}")
                except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as e:
                    last = str(e)
                    if attempt < 3:
                        time.sleep(5 * attempt)
                        continue
                    raise RuntimeError(f"could not reach OpenAI: {last}")
        raise RuntimeError(f"gave up after 3 attempts: {last}")


# ---------------------------------------------------------------- audio prep

def extract_audio(src: Path, out: Path) -> None:
    """16 kHz mono at 32 kbps: about an hour and a half fits under the 25 MB cap."""
    subprocess.run(["ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-i", str(src), "-vn",
                    "-ac", "1", "-ar", "16000", "-b:a", "32k", str(out)],
                   capture_output=True, check=True)


def split_audio(audio: Path, out_dir: Path) -> list[Path]:
    pattern = out_dir / "chunk-%03d.mp3"
    subprocess.run(["ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-i", str(audio),
                    "-f", "segment", "-segment_time", str(CHUNK_SECONDS), "-c", "copy",
                    str(pattern)], capture_output=True, check=True)
    return sorted(out_dir.glob("chunk-*.mp3"))


# ---------------------------------------------------------------- selection + estimate

def index_dir_for(p: Path) -> Path:
    return p.parent.parent / "_Index" if p.parent.name in classify.CATEGORIES else p.parent / "_Index"


def transcript_path(p: Path) -> Path:
    return index_dir_for(p) / f"{p.name}.transcript.md"


def spoken_files(root: Path, only: list[str] | None = None) -> tuple[list[Path], list[Path]]:
    """(files, symlinks) of every video/audio file, optionally limited to event folders."""
    files, links = [], []
    wanted = {o.strip().lower() for o in (only or []) if o.strip()}
    for here, _dirs, items in classify.walk(root):
        rel = here.relative_to(root)
        if wanted and (rel.parts[0].lower() if rel.parts else "") not in wanted:
            continue
        for p in items:
            if classify.is_package(p) or classify.is_junk(p) or not classify.is_spoken(p):
                continue
            (links if p.is_symlink() else files).append(p)
    return sorted(files), links


@dataclass
class Estimate:
    todo: list[tuple[Path, float]]      # (file, seconds)
    unreadable: list[Path]
    total_bytes: int
    free_bytes: int

    @property
    def minutes(self) -> float:
        return sum(s for _, s in self.todo) / 60

    @property
    def cost(self) -> float:
        return self.minutes * USD_PER_MIN

    @property
    def readable(self) -> list[tuple[Path, float]]:
        return [(f, s) for f, s in self.todo if s > 0]

    @property
    def disk_tight(self) -> bool:
        return self.total_bytes > self.free_bytes * 0.8


def estimate(root: Path, files: list[Path]) -> Estimate:
    todo = [(f, system.media_seconds(f)) for f in files if not transcript_path(f).exists()]
    return Estimate(todo, [f for f, s in todo if s <= 0],
                    sum(f.stat().st_size for f, _ in todo if f.exists()),
                    system.free_disk(root))


# ---------------------------------------------------------------- run

def transcript_markdown(name: str, rel: str, seconds: float, segments: list[Segment]) -> str:
    lines = [f"# Transcript — {name}", "", f"Source: {rel}",
             f"Duration: {system.mmss(seconds)}" if seconds else "Duration: unknown",
             f"Transcribed: {datetime.now():%Y-%m-%d} (OpenAI {MODEL})", ""]
    for s in segments:
        text = s.text.strip()
        if text:
            lines.append(f"[{system.mmss(s.start)}] {text}")
    if not segments:
        lines.append("(no speech detected)")
    return "\n".join(lines) + "\n"


def _banked(lib: Library, v: Path) -> list[Segment] | None:
    j = lib.bank / f"{v.name}.json"
    if j.exists():
        return [Segment(**s) for s in json.loads(j.read_text())["segments"]]
    legacy = lib.bank / f"{v.name}.txt"        # 0.x bank: text without timestamps
    if legacy.exists():
        return [Segment(0.0, 0.0, legacy.read_text())]
    return None


def run(lib: Library, est: Estimate, transcriber: Transcriber,
        log: Callable[[str], None] = lambda s: None) -> tuple[int, int]:
    """Transcribe every readable file in the estimate. Returns (done, failed)."""
    lib.bank.mkdir(parents=True, exist_ok=True)
    lib.tmp.mkdir(exist_ok=True)
    done = failed = 0
    todo = est.readable
    for i, (v, seconds) in enumerate(todo, 1):
        log(f"  [{i}/{len(todo)}] {v.name}")
        chunks: list[Path] = []
        try:
            segments = _banked(lib, v)
            if segments is not None:
                log("      already paid for on an earlier run — reusing, no charge")
            else:
                audio = lib.tmp / "audio.mp3"
                extract_audio(v, audio)
                chunks = split_audio(audio, lib.tmp) if audio.stat().st_size > UPLOAD_CAP else [audio]
                if len(chunks) > 1:
                    log(f"      long recording — sent in {len(chunks)} parts")
                segments, offset = [], 0.0
                for c in chunks:
                    segs, dur = transcriber.transcribe(c, f"{v.stem}.mp3")
                    segments += [Segment(s.start + offset, s.end + offset, s.text) for s in segs]
                    offset += system.media_seconds(c) or dur
                (lib.bank / f"{v.name}.json").write_text(json.dumps(
                    {"file": v.name, "model": MODEL, "seconds": seconds,
                     "segments": [s.__dict__ for s in segments]}))
            out = transcript_path(v)
            out.parent.mkdir(parents=True, exist_ok=True)
            system.set_finder_tag(out.parent, "_Index")
            out.write_text(transcript_markdown(v.name, v.relative_to(lib.root).as_posix(),
                                               seconds, segments))
            done += 1
        except subprocess.CalledProcessError:
            log("      could not read that file, skipping")
            failed += 1
        except UserFixable:
            raise
        except Exception as e:
            log(f"      failed: {e}. Re-run to retry just this one.")
            failed += 1
        finally:
            for c in [lib.tmp / "audio.mp3"] + chunks:
                c.unlink(missing_ok=True)
    return done, failed
