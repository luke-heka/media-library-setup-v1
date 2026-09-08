---
name: media-library-setup
description: Use when someone says "organise my Google Drive", "sort out my video folders", "I can't find anything in my Drive", "set up my media library", "transcribe all my videos so I can search them", "make my footage searchable", "find the bit where someone says…", or wants a messy folder of photos, videos and audio turned into something they can browse and ask questions about.
---

# Media Library Setup

Turns a messy Google Drive full of photos, videos and audio into a library you can browse with
your eyes and search in plain English, down to the moment in the clip.

**Works on Mac and Windows.** `check` detects which and gives the right instructions. Folder
colours are a Mac-only nicety — everything else behaves identically. Nothing to install for the
organising half: Python 3.9 or newer and this folder are the whole tool.

**You are talking to a business owner, not a developer.** Assume they have never opened a
terminal. Never paste a command at them and ask them to run it — run it yourself, then say in
one sentence what came back. The only things they ever do by hand: click through an installer,
sign into their own Google account, and paste their own OpenAI key at a hidden prompt.
Everything else is yours.

Two promises to state out loud, early, in these words:

1. **Nothing changes until you approve it.** They see two pictures of the exact plan first.
2. **No file is ever deleted, and it can all be undone.** Files move, every move is written
   down, and `library.py rollback` puts the whole thing back. Folders left completely empty are
   tidied away — say that out loud too, so it is never a surprise.

---

## Step 1 — find out what is missing

First command, every time, before anything else:

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py check
```

It lists what is ready and what is not, with the fix for each. Read the result and **do the
fixes for them**:

- **Google Drive for Desktop** — they must install this themselves; it is a normal app.
  Send them to https://www.google.com/drive/download/, tell them to sign in with the Google
  account holding their media, and to choose **"Stream files"** when asked. Then wait — a big
  Drive takes a while to appear the first time.
- **ffmpeg** — only for transcribing. Run the line `check` prints for their computer:
  `brew install ffmpeg` on a Mac (send them to https://brew.sh first if Homebrew is missing),
  `winget install --id Gyan.FFmpeg -e` on Windows, `sudo apt install ffmpeg` on Linux. On
  Windows a new terminal is needed afterwards.
- **The OpenAI key** — only for transcribing. Walk them through it in Step 2.

**It works on any folder on their computer** — an external drive of footage, a local Projects
folder, a Dropbox folder. Google Drive for Desktop is just the usual way to get a Drive onto the
machine as a normal folder. If their media is already local, they need nothing at all installed.

**Only Google Drive for Desktop is required, and only if their media lives in Drive.**
Organising their folders needs nothing else — no key, no account, no cost, no Python packages.
ffmpeg and the key are needed *only* if they want the searchable transcripts in Step 7, and they
can decide that later. Re-run `check` after each install to confirm it took.

Full detail on every install, with a fix for each way it fails:
[references/setup.md](references/setup.md).

---

## Step 2 — the money conversation, before any of it

Have this conversation **before** they spend anything, not when the bill lands.

- **Organising their folders is free.** No key, no account, no cost.
- **Transcribing costs money**, because it uses OpenAI to turn speech into text.
  About **$0.36 per hour of video or audio** (price checked 2026-09-08):

| Their library | Roughly |
|---|---|
| 1 hour | $0.36 |
| 10 hours | $3.60 |
| 40 hours | $14 |

- It is **their own OpenAI account**, billed to their card. Not a subscription, not through
  anyone else. **$5 of credit covers about 14 hours.**
- The tool measures their actual library and prints the exact figure **before sending anything**.
  Nothing is charged until they say go.
- Each file is only ever paid for once. A stopped run costs nothing to resume.

Getting the key, if they want transcribing:

1. https://platform.openai.com/api-keys — sign in or create an account
2. https://platform.openai.com/settings/organization/billing — *Add to credit balance*, $5 is plenty
3. Back to the keys page → **Create new secret key** → copy it (it is shown once)

Storing it — the one moment they touch a terminal, and it is their secret in their hands:

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py key
```

Ask them to open a terminal, run that line, and paste the key at the prompt. Nothing is shown
while they type, and the key lands in a private file only their user account can read
(`~/.config/media-library-setup/openai-key` on Mac and Linux, `%APPDATA%\media-library-setup\`
on Windows). It never goes into a shell profile, a chat window, or anything that syncs.

If they cannot manage a terminal and paste the key into the chat instead, store it for them
with `library.py key --stdin` and tell them plainly that the key has now passed through the
chat transcript, so it is worth keeping the credit on it small and revoking it once the job is
done. Never print the key back, never repeat it, never write it anywhere else.
`library.py key --check` confirms one is set without showing it; `--forget` removes it.

---

## Step 3 — before proposing anything, read the structure rules

[references/structure-rules.md](references/structure-rules.md) is the point of this skill. It
defines the two-level ceiling and explains why sorting clips into folders by shot type is the
mistake that makes a library unusable. Read it before proposing any structure.

```
My Media Library/
├── Brisbane Workshop May/
│   ├── Videos/       ← every video, one flat list
│   ├── Photos/       ← every photo, one flat list
│   ├── Audio/        ← podcasts, voice memos, recordings (only if there are any)
│   ├── Documents/    ← PDFs, decks, sheets, edit project files
│   └── _Index/       ← transcripts and the manifest, so you can search what was said
└── Sydney Shoot June/
    └── ...
```

Two levels. That is the floor. Nobody can flick through forty folders holding one clip each.
Keynote, Pages and Final Cut documents look like folders to a computer; the tool knows they are
one file and moves them whole.

---

## Step 4 — look, without touching

`check` prints where their Drive folder is. Ask which folder inside it holds the media, then:

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py scan "<that folder>"
python3 ~/.claude/skills/media-library-setup/scripts/library.py plan
```

Both are read-only. Tell them the numbers in plain words — how many files, how deep the folders
go, and **how many folders hold two files or fewer**. That last number is usually the moment it
lands for them. If `scan` lists unrecognised file types, say what they are and that they will
be filed under Documents.

`plan` works out whether this is a whole library or a single shoot. If it guesses wrong, re-run
with `--group-by event` or `--group-by flat`. Loose files at the top level of a library go into
an `Unsorted` event folder — say so, and offer to rename it afterwards.

---

## Step 5 — show them, then wait

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py visualise
```

Two pages open in their browser:

- **Folders now versus proposed**, colour-coded, near-empty folders in red
- **Where each kind of file ends up**, and what that buys them

If they do not open automatically, the paths are printed — open them by hand. **Never skip
this**, it is the only thing standing between a plan and their files.

Walk through both out loud. Name the real numbers: files moving, folders disappearing, how deep
it ends up, any files getting a `-2` because two share a name. Say plainly that nothing is deleted.

**Then stop and ask for a yes.** This is the gate. Do not continue on a maybe, and do not
continue on silence.

Want something different? Re-run `plan` and `visualise`. Costs nothing, because nothing has moved.

---

## Step 6 — move the files

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py apply --approved-by "<their name>"
```

Refuses without a real name, and refuses if the plan changed since those pictures were drawn —
so what they approved is what happens. It prints the full path of the library it is about to
change; if two libraries have been scanned, pin the right one with `--library "<path>"`.

Moves every file, colours the folders in Finder, clears away the folders it emptied, and records
every move in a journal as it goes. Nothing is deleted. Anything it could not move is listed at the end
and left exactly where it was.

Tell them Drive will now sync the new layout back up, and on a big library that takes a while.

**If they want it back**, at any point:

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py rollback
```

Shows what it would put back and changes nothing. Add `--approved-by "<their name>"` to do it.
Undo covers the moves. Transcripts and manifests written into `_Index` afterwards are new files
and stay where they are — nothing is ever deleted, including by the undo.
`library.py status` says which library is active and whether an undo is available.

---

## Step 7 — make it searchable

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py transcribe
```

Prints the exact cost and the amount of audio it will read, then stops. Show them the figure.
Only when they agree:

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py transcribe --yes
```

Watch for the disk warning. If their Drive is set to stream, this pulls each file down as it
goes — on a large library that is a lot of disk. Do one event at a time instead:

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py transcribe --yes --only "Brisbane Workshop May"
```

Every transcript carries a timestamp on each line, so an answer can say *where* in the clip,
not just which clip. A library that is already tidy can be transcribed straight after `scan`
and `plan` — there is nothing to approve when nothing moves.

---

## Step 8 — the manifest and the search

Free, instant, and worth running every time transcripts change:

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py manifest
python3 ~/.claude/skills/media-library-setup/scripts/library.py search pricing
```

`manifest` writes one `_Index/_MANIFEST.md` per event: every file, its size and length, whether
it has a transcript, and its first words. That single table answers most questions without
opening anything. It is regenerated each run — their own notes belong in `_Index/_NOTES.md`,
which the tool never touches.

`search` is full-text search over every transcript and summary, ranked by relevance, and prints
the event, the file and the timestamp. The index refreshes itself whenever a transcript changes. Show them at least one, live:

- "find the bit where someone talks about pricing"
- "pull every testimonial from the May workshop"
- "what footage do we have of the room filling up"

Answer with the actual file and the time. For richer questions, read the transcripts in
`_Index/` yourself. Worth adding by hand afterwards: a `<clip>.summary.md` beside each
transcript with two lines on what the clip shows and who is in it — `manifest` picks those up.

---

## Step 9 — hand them the report

This folder ships with `SELR-REPORT.html`: a plain-English, file-by-file account of what the
tool does, what it touches and what it cannot do. Open it for them and walk the verdict. If the
`skill-install-report` skill is available on this machine, regenerate it so the report matches
the copy they actually have; if not, the bundled one is the report. That page is what they keep.

---

## Naming

`apply` never renames anything — files keep the names they already have, so nothing becomes
unrecognisable. The only exception is a collision: two files with the same name arriving from
different folders, where the second gets `-2` appended rather than overwriting the first. That is
decided in the plan and shown in the visuals, never invented after the approval.

If they want a naming convention going forward, this one holds up:

```
2026-05-07_brisbane_testimonial-short_sarah-results_001.mp4
```

Date, event, what it is, a short description. Applying it to existing files is a separate job
and a bigger conversation — offer it, do not fold it into the reorganise.

---

## When things go sideways

Setup problems — missing Drive folder, ffmpeg, API key, no credit — are all in
[references/setup.md](references/setup.md), and `check` names them for you. Beyond those:

| What happens | What it means | What to do |
|---|---|---|
| "could not be read, skipped" | That file is damaged, zero bytes, or still downloading from Drive | Everything else still runs; open that one to check it |
| Some files listed as not moved | Permissions, or Drive dropped out mid-run | They are untouched where they were. Re-run `apply` to retry just those |
| A file lands in the wrong folder | Its type was guessed from the extension | Move that one by hand; the index still finds it |
| The plan looks wrong | Library-versus-one-shoot was guessed wrong | Re-run `plan` with an explicit `--group-by` |
| Drive still shows the old layout | Sync has not caught up | Check the Drive icon in the menu bar; large moves take time |
| "rejected the key" or "no credit" | The key is wrong, or the account has no balance | `library.py key` for a fresh one; add credit on the billing page |
| They want the old structure back | | `library.py rollback` previews it; add `--approved-by` to do it |

Everything here is safe to run again, and it self-heals — re-running never double-charges and
never re-moves. If a step fails twice in a row, run `check` again: it is almost always a
prerequisite that dropped out, not the library.

---

## Boundaries

- Never run `apply` without a spoken yes on the two visuals.
- Never delete a file. Not as cleanup, not for duplicates, not on request without an explicit
  confirmation naming the files. Emptied folders are cleared; files never are.
- Never go deeper than two levels, whatever the folder count.
- Always show the transcription cost and get agreement before spending anything.
- Never print, repeat, or store their API key anywhere but the private key file.
- Let a big first sync finish before scanning, or the scan sees a half-populated folder.

<!-- Provenance marker: sk-18btjs4 --><!-- Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠ -->
