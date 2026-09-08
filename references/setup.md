# Setup — one time, about ten minutes

Works on **Mac and Windows**. Linux works too, but Google has no Drive for Desktop for it — see the note in step 1.

Three things, and only the first is needed to organise. Claude does the work; the person just signs in and pastes one key.

Walk them through it in this order. Do not move on until each one checks out.

---

## 1. Google Drive for Desktop — puts their Drive on their computer

This is the whole trick. With this installed, Google Drive is just a folder on the machine.
No API, no Google Cloud project, no developer account. Anything reorganised locally syncs
straight back up to Drive on its own.

Download: **https://www.google.com/drive/download/**

- Install it, open it, sign in with the Google account that holds the media.
- When it asks how to sync, choose **"Stream files"** (the default). Files download on demand
  instead of filling the hard drive.
- Wait for the first sync to settle. A big Drive can take a while the first time.

**One thing to know about streaming.** Organising the folders never downloads anything — moving
a streamed file is just a rename. But **transcribing does**: reading a video pulls the whole
file down. On a large library that can be hundreds of gigabytes passing through the disk.

The `transcribe` step prints how much it is about to read and how much free space there is,
and warns if it is tight. If it is, do one event at a time with
`library.py transcribe --yes --only "<event folder>"`. Drive normally clears its cache as it
goes, but on a nearly full disk do not rely on it.

**Check it worked.** `check` finds it for you and prints the path. If you want to look yourself:

- **Mac** — `~/Library/CloudStorage/GoogleDrive-<their-email>`, or `~/Google Drive` on older installs
- **Windows** — a drive letter, usually `G:\My Drive`
- **Linux** — Drive for Desktop is not available; use a third-party sync client, or work on a
  local folder and upload afterwards

Nothing there → the app is not signed in, or the first sync has not finished. Open the Drive
app from the menu bar and check.

**Skip this entirely** if the media is already on the computer, an external drive, or a
Dropbox folder. The tool works on any folder.

---

## 2. Python — already there on almost every machine

The tool is a single Python file with no packages to install. It needs Python 3.9 or newer.

- **Mac** — `python3 --version`. If it says the command line developer tools are missing,
  click *Install* on the box that appears (or run `xcode-select --install`), wait, and try again.
- **Windows** — `python3 --version` or `python --version`. Missing? Install it from
  https://www.python.org/downloads/ and tick **"Add python.exe to PATH"** in the installer.
- **Linux** — already installed on every mainstream distribution.

**Check it worked:** `check` prints the version on its first line.

---

## 3. ffmpeg — reads the audio out of video files (transcription only)

```bash
brew install ffmpeg                        # Mac
winget install --id Gyan.FFmpeg -e         # Windows
sudo apt install ffmpeg                    # Linux
```

No Homebrew on a Mac → install it from **https://brew.sh** first, then run the line above.
On Windows, close the terminal and open a new one afterwards or it will not be found.

**Check it worked:** `ffmpeg -version` prints a version. `check` reports it too.

---

## 4. An OpenAI key — for the transcription only

Only needed for the `transcribe` step. Organising the folders needs nothing.

1. Go to **https://platform.openai.com/api-keys** and sign in (or create an account).
2. Add credit first: **https://platform.openai.com/settings/organization/billing** →
   *Add to credit balance*. **$5 goes a long way** — see the costs below.
3. Back on the API keys page, click **Create new secret key**, name it something like
   `media-library`, and copy it. It is shown once.
4. Have them open a terminal and run:

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py key
```

They paste the key at the prompt. Nothing is shown while they type. It is written to a file
only their user account can read — `~/.config/media-library-setup/openai-key` on Mac and
Linux, `%APPDATA%\media-library-setup\openai-key` on Windows — and nowhere else. No shell
profile, no chat, nothing that syncs.

If they set `OPENAI_API_KEY` in their environment some other way, that is used first.

**Check it worked** without printing the secret:

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py key --check
```

Never paste the key itself into a chat window or a shared terminal. If they have already done
that, keep the credit on that key small and revoke it when the job is finished.
`library.py key --forget` removes the stored copy.

### What it costs

Transcription runs on OpenAI's `whisper-1` at **$0.006 per minute of audio** — the only
OpenAI transcription model that returns timestamps, which is what makes "the bit where…"
answerable with a time. Price checked on the OpenAI pricing page 2026-09-08; the tool prints
that date with every estimate so a stale figure is visible.

| Their library | Cost |
|---|---|
| 1 hour of video or audio | about $0.36 |
| 10 hours | about $3.60 |
| 40 hours | about $14 |

The `transcribe` command measures every file and prints the exact estimate **before** sending
anything. Nothing is charged until it is confirmed with `--yes`.

It only ever transcribes each file once. The paid result is banked locally the moment it
arrives, so an interrupted run, a full disk or a permissions hiccup never means paying twice.

---

## Then what

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py scan "~/Library/CloudStorage/GoogleDrive-them@example.com/My Drive/Footage"
```

The first three steps of the main flow change nothing on disk. Files move only after they see the two
visuals and say yes.

---

## When something is not right

| What they see | What it means | Fix |
|---|---|---|
| No `CloudStorage` folder | Drive for Desktop is not signed in | Open it from the menu bar, sign in, wait for sync |
| Folder is there but empty | First sync still running | Wait; the Drive icon shows sync progress |
| `ffmpeg: command not found` | Not installed, or a new terminal is needed | Re-run the install, then open a fresh terminal |
| `python3: command not found` | Mac developer tools missing, or Windows PATH not set | Mac: `xcode-select --install`. Windows: reinstall Python with the PATH box ticked |
| `Python 3.x is too old` | An old system Python | Install the current one from python.org |
| "No OpenAI key set" | The key was never stored, or was stored for a different user account | `library.py key` again |
| "OpenAI rejected the key" | The key was pasted wrongly or has been revoked | Make a new one, `library.py key` |
| "the OpenAI account has no credit" | Key works, balance is zero | Add credit on the billing page above |
| Folders have no colours | Colour tags are a Mac feature | Nothing is wrong — the folders are organised identically, just without colours |
| The two pictures did not open | No default browser set | The paths are printed on screen; open them by hand. **Do not skip this step** |
| "could not be read, skipped" | Damaged file, or Drive has not finished downloading it | Open it once in Drive so it downloads, then re-run |
| Transcribing feels slow | Normal — roughly real-time per file, faster on short clips | Leave it running; re-running resumes where it stopped |

All of it retries safely. Ask Claude to run the step again.
