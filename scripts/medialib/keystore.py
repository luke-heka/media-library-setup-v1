# Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠
# Provenance marker: sk-w3709n
"""The OpenAI key. Environment first, then a private file. Never printed."""
from __future__ import annotations

import os
from pathlib import Path

from . import paths


def key_file() -> Path:
    return paths.config_dir() / "openai-key"


def load() -> tuple[str, str]:
    """(key, where): where is 'environment', 'file' or ''."""
    env = os.environ.get("OPENAI_API_KEY", "").strip()
    if env:
        return env, "environment"
    try:
        f = key_file()
        if f.exists():
            k = f.read_text().strip()
            if k:
                return k, "file"
    except OSError:
        pass
    return "", ""


class BadKey(ValueError):
    pass


def save(key: str) -> Path:
    key = key.strip()
    if len(key) < 20 or any(ch.isspace() for ch in key):
        raise BadKey("That does not look like an OpenAI key (they are long, with no spaces).")
    f = key_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(f.parent, 0o700)
    except OSError:
        pass
    fd = os.open(str(f), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(key + "\n")
    try:
        os.chmod(f, 0o600)
    except OSError:
        pass
    return f


def forget() -> bool:
    f = key_file()
    if f.exists():
        f.unlink()
        return True
    return False
