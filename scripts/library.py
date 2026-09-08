#!/usr/bin/env python3
# Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠
# Provenance marker: sk-w3709n
"""media-library-setup — organise a folder of photos, videos and audio, then make it searchable.

This file is the entry point. The tool itself is the `medialib` package beside it:

    library.py check                          what is installed, what is missing
    library.py scan <folder>                  read-only survey
    library.py plan                           read-only proposed structure
    library.py visualise                      read-only, writes the two approval visuals
    library.py apply --approved-by "<who>"    moves files. Nothing is deleted
    library.py rollback [--approved-by ...]   puts every moved file back
    library.py status                         which library is active, what state it is in
    library.py key                            store the OpenAI key (hidden prompt, or --stdin)
    library.py transcribe [--yes] [--only X]  makes it searchable (costs a few dollars)
    library.py manifest                       free: one table per event of every file
    library.py search <words>                 find the moment, with a timestamp

Python 3.9 or newer, standard library only. ffmpeg is needed only for transcribing.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from medialib.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
