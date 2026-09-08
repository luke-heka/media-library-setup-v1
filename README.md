# Media Library Setup

**Turns a messy Google Drive of photos, videos and audio into something you can actually browse —
and search by what was said in the clip, down to the moment, not just the filename.**

Made by Selr AI.

---

## Who this is for

Anyone whose Drive fills up faster than it gets filed. Event footage, client shoots, workshops,
podcast episodes, social content. If finding an old clip currently means twenty minutes of
clicking through folders, this is for you.

You do not need to be technical. Claude runs every command. You install one app, sign into your
own Google account, and paste one key at a hidden prompt if you want the search feature.

---

## What it actually does

**1. It looks, and changes nothing.** Counts what you have, how deep your folders go, and how
many folders are holding one or two files.

**2. It shows you two pictures.** Your folders now, versus what it proposes. Near-empty folders
marked in red. Where every kind of file would end up.

**3. It waits.** Nothing moves until you say yes. If you want it different, it redraws for free.

**4. Then it tidies.** Everything lands in a simple shape, two levels deep, never more:

```
Your Library/
├── Brisbane Workshop May/
│   ├── Videos/       every video, one scrollable list
│   ├── Photos/       every photo together
│   ├── Audio/        podcasts and recordings, if you have any
│   ├── Documents/    decks, PDFs, contracts, edit projects
│   └── _Index/       transcripts and a manifest, so you can search what was said
└── Sydney Shoot June/
```

Keynote, Pages and Final Cut documents are folders in disguise. They are moved whole, never
opened up.

**5. Optionally, it makes it searchable.** Transcribes your videos and audio with a timestamp
on every line, so you can ask:

> find the bit where someone talks about pricing

and get the file **and** the minute.

**Changed your mind at any point?** "Put my library back the way it was" — it restores every
file to its original folder under its original name.

---

## The two promises

- **Nothing changes until you approve it.** You see the exact plan first, as pictures.
- **No file is ever deleted, and it can all be undone.** Files move, every move is written down,
  and one command puts the whole thing back exactly as it was:

  ```
  Put my library back the way it was
  ```

  Folders left completely empty afterwards are tidied away; anything still holding a file is
  left alone.

---

## What it costs

**Organising your folders is free.** No account, no key, no cost, nothing to install beyond
Python, which Macs and most Windows machines already have.

**Transcribing costs money** — it uses OpenAI to turn speech into text, billed to your own
OpenAI account at about **$0.36 per hour of video** (price checked 2026-09-08). $5 of credit
covers roughly 14 hours.

You are shown the exact figure for your library before anything is sent, and nothing is charged
until you confirm. Each file is only ever paid for once.

---

## Install

Get the folder onto your computer, either way:

```bash
git clone https://github.com/luke-heka/media-library-setup-v1.git ~/.claude/skills/media-library-setup
```

Not using git? Use the green **Code** button at the top of this page to download the folder,
then move `media-library-setup` into `~/.claude/skills/`.

Then paste this into Claude Code:

```
Install the media-library-setup skill for me.

1. Confirm SKILL.md exists at ~/.claude/skills/media-library-setup/SKILL.md
2. Run: bash ~/.claude/skills/media-library-setup/scripts/smoke.sh
   The last line should start with "ok:".
3. Run: python3 ~/.claude/skills/media-library-setup/scripts/library.py check
   Then walk me through installing anything it says is missing.

Do not scan or move anything yet.
```

Works on **Mac and Windows**. Linux works too, though Google does not make Drive for Desktop
for it.

## Then

```
Organise my Google Drive media folder.
```

---

## What is in here

| File | What it is |
|---|---|
| `SKILL.md` | The step-by-step Claude follows, from install to finished library |
| `references/setup.md` | Every install, with links and a fix for each way it fails |
| `references/structure-rules.md` | Why the folders stay flat, and the rule that stops them nesting |
| `scripts/library.py` | The entry point. Runs the `medialib` package beside it |
| `scripts/medialib/` | The tool, one module per job: classify, scan, plan, render, journal, apply, keystore, transcribe, index, cli. Standard library only |
| `scripts/medialib/templates/` | The two approval visuals as HTML templates |
| `scripts/smoke.sh` | Runs the offline test suite that proves the safety gates still work |
| `tests/test_library.py` | The tests themselves: fictional libraries in temp folders, nothing real touched |
| `SELR-REPORT.html` | A full security and plain-English report on this skill. Open it in a browser |
| `examples/` | A worked example of a fictional run |
| `CHANGELOG.md` | What changed in each version and why |
