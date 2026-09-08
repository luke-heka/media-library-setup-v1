# media-library-setup — Setup Prompt

Paste this into Claude Code to install and verify the skill.

```
Install the media-library-setup skill for me.

1. Confirm SKILL.md exists at ~/.claude/skills/media-library-setup/SKILL.md
2. Run the offline check: bash ~/.claude/skills/media-library-setup/scripts/smoke.sh
   The last line should start with "ok:".
3. Run: python3 ~/.claude/skills/media-library-setup/scripts/library.py check
   It tells you what is already on my computer and what is missing. Walk me through
   installing anything it lists, one at a time, checking each before the next.
4. Then tell me in three lines what folder structure you are going to propose and why
   it stays flat.

Do not scan, plan, or move anything yet.
```

## What it does

Turns a messy Google Drive of photos, videos and audio into a library you can browse and
search in plain English, down to the moment in the clip.

It scans, plans, and shows you two pictures of the proposed structure **before** it touches
anything. Files move only after you say yes, nothing is ever deleted, and every move is written
to a rollback file first.

Works on **Mac and Windows**.

## What you need

- **Google Drive for Desktop** — https://www.google.com/drive/download/
  Makes your Drive a normal folder on your computer. No API, no developer account.
  Only if your media lives in Drive; a folder already on your computer needs nothing.
- **ffmpeg** — `brew install ffmpeg` (Mac), `winget install --id Gyan.FFmpeg -e` (Windows).
  Only for transcription.
- **An OpenAI key** — https://platform.openai.com/api-keys
  Only for transcription. About **$0.36 per hour of video** (price checked 2026-09-08),
  billed to your own account. You are shown the exact cost before anything is sent. $5 goes a
  long way. You paste it once at a hidden prompt: `library.py key`.

Full walkthrough with checks and fixes: `references/setup.md`.

## First run

```
Organise my Google Drive media folder for me.
```

Claude finds the folder, scans it, shows you two visuals, and waits for your approval before
moving a thing.
