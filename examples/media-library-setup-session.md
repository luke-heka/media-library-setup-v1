# media-library-setup — worked session

A fictional run, condensed. Shows the approval gate doing its job and the search paying off.

---

**Them:** My Drive is a disaster. I can never find the video I want.

**Claude:** Your Drive is already on this machine via Drive for Desktop, so I can
work on it as a normal folder. Scanning — read only, nothing will change.

```
Scanned 'Footage' — read only, nothing changed.
  6847 files (412GB) in 109 folders, 4 levels deep
  48 folders hold 2 files or fewer
  Videos       1596
  Photos       1539
  Audio          31
  Documents     277
  3 Keynote/Pages/Final Cut style documents (folders that are really one file) — kept whole
```

48 of your 109 folders hold two files or fewer. That is the thing making this hard to use —
not the number of files. Three of the "folders" are Keynote decks; they stay whole.

Working out a structure. Still not changing anything.

```
Treating this as a library of events — its subfolders look like separate events.
  109 folders (4 deep)  ->  82 folders (2 deep)
  6712 files will move, 135 already correct
  4 share a name with another file and get a number added so neither is lost:
    IMG_0412.jpg  ->  IMG_0412-2.jpg
    ...
```

Two pictures opened in your browser:

1. **Folder structure** — your folders now versus proposed. Red rows are the near-empty ones.
2. **Where everything is stored** — what lands where, and what it buys you.

The short version: one folder per event, and inside each, up to five folders — Videos, Photos,
Audio, Documents, and `_Index` for the searchable text. Nothing goes deeper than that.

6,712 files move. 27 near-empty folders disappear. Four photos get a `-2` because another
photo from a different folder has the same name. **Nothing is deleted** — every move is written
to a rollback file first, so this is fully reversible.

Have a look at both, and tell me to go ahead when you are happy.

---

**Them:** Why not sort the videos by type? Interviews, b-roll, that sort of thing.

**Claude:** Tried that, and it is the trap. Your footage classifies into 37 shot types — sorting
by type would turn 1,596 videos into roughly 37 folders per event, most holding one or two
clips. That is what you already have, and it is why you cannot find anything.

The type is not lost. Once transcribed, `search interview` finds every interview and the minute
it starts, whichever folder it sits in. You get to scroll one folder of thumbnails instead of
opening forty. If you still want the split after seeing that, say so and I will build it.

---

**Them:** No, makes sense. Go ahead.

**Claude:**

```
About to change:  /Users/them/Library/CloudStorage/GoogleDrive-them@example.com/My Drive/Footage
Applying: 6712 files to move. Nothing will be deleted.
  Brisbane 1 — 2026-05-07/Videos
  Brisbane 1 — 2026-05-07/Photos
  ...
Done. 6712 files moved, 0 deleted.
  27 emptied folders cleared away.
Move journal: ~/active/media-library-setup/footage-3f2a91c0/journal.sqlite
```

Done. On a Mac the folders are colour-tagged in Finder — Videos purple, Photos blue, Audio
green, Documents orange, `_Index` grey. On Windows they are organised identically, without
colours. Drive for Desktop is syncing the new layout back up now.

Next: transcribing, so you can ask for a moment instead of a filename. I measure it first:

```
  1627 files, 4210 minutes of audio
  Estimated cost: $25.26 USD (OpenAI whisper-1, $0.006/min, price checked 2026-09-08)
  This is billed to your own OpenAI account.

  Reads 388GB of media. On a streaming Drive that downloads each file as it goes.
  Free disk right now: 96GB.

  WARNING: that is close to or more than the free space available.
  Do it in batches — transcribe one event folder at a time with
  library.py transcribe --only "<event folder>" — or free up space first.

Nothing has been sent and nothing has been charged.
```

Your disk is too small to pull the whole library down at once, so I will do it one event at a
time, starting with Brisbane — about $3.10 for that one. Your call.

---

**Them:** Do Brisbane.

**Claude:** Brisbane done, 214 files, $3.08. Now the bit you actually wanted:

```
library.py search pricing

9 matches for pricing:

  Brisbane 1 — 2026-05-07 / C0042.MP4  [12:34]
      So when people ask me about pricing, the honest answer is it depends on...
  Brisbane 1 — 2026-05-07 / C0042.MP4  [14:02]
      ...and that is why we never lead with pricing on the first call.
  Brisbane 1 — 2026-05-07 / testimonial-sarah.mov  [00:41]
      The pricing was the thing I was most nervous about and it turned out...
```

The clip you were thinking of is `C0042.MP4`, 12 minutes 34 seconds in.

---

## What to notice

- Three read-only steps before anything moved.
- The visuals came before the ask, not after.
- The pushback on shot-type folders was answered with the actual count, then handed back to them.
- Nothing was deleted, and the rollback path was named up front.
- The transcription cost was quoted in dollars before a single request went out, and the disk
  warning turned a whole-library job into a per-event one.
- The search answered with a file **and** a timestamp.
