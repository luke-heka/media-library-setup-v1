# Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠
# Provenance marker: sk-w3709n
"""The commands. Every line a person reads is printed from here and nowhere else."""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from . import VERSION, apply, index, keystore, paths, plan as planmod, render, scan as scanmod
from . import system, transcribe
from .journal import Journal
from .paths import Library, NoLibrary


def _lib(args) -> Library:
    try:
        return paths.current_library(getattr(args, "library", None))
    except NoLibrary as e:
        raise SystemExit(str(e))


def _plan(lib: Library) -> planmod.Plan:
    if not lib.plan_file.exists():
        raise SystemExit("No plan yet. Run:  library.py plan")
    return planmod.load(lib)


# ---------------------------------------------------------------- check

def cmd_check(args) -> None:
    ok, todo = [], []
    v = sys.version_info
    if v < (3, 9):
        todo.append((f"Python {v.major}.{v.minor} is too old", "This tool needs Python 3.9 or newer.",
                     "Install the current version from https://www.python.org/downloads/"))
    else:
        ok.append(f"Python {v.major}.{v.minor} is here (nothing else to install for organising)")

    drives = system.find_drive_folders()
    if drives:
        ok.append(f"Google Drive is on this computer ({drives[0]})")
    else:
        todo.append(("Google Drive is not on this computer yet",
                     "Only needed if your media lives in Google Drive — it puts your Drive here as a\n"
                     "    normal folder. If your files are already on this computer, skip this.",
                     "Install it from https://www.google.com/drive/download/ , sign in, and pick\n"
                     '    "Stream files" when it asks. Then wait for the first sync to finish.'))

    if system.has_tool("ffmpeg") and system.has_tool("ffprobe"):
        ok.append("ffmpeg is installed (reads the audio out of your videos, for transcribing)")
    else:
        todo.append(("ffmpeg is missing", "Needed only to transcribe — it reads the audio out of your videos.",
                     system.ffmpeg_install_line()))

    key, where = keystore.load()
    if key:
        ok.append(f"Your OpenAI key is set ({len(key)} characters, from the {where}, not shown)")
    else:
        todo.append(("No OpenAI key set", "Only needed for transcribing. Organising your folders works without it.",
                     "1. Get a key at https://platform.openai.com/api-keys\n"
                     "    2. Add credit at https://platform.openai.com/settings/organization/billing\n"
                     "       — $5 covers about 14 hours of video\n"
                     "    3. Run:  library.py key   and paste it at the hidden prompt"))

    print(f"media-library-setup {VERSION} — checking what is already set up on this {system.PLATFORM}…\n")
    for line in ok:
        print(f"  READY   {line}")
    if not todo:
        print("\nEverything is ready. Nothing else to install.")
        if drives:
            print(f"\nYour Drive folder is at:\n  {drives[0]}")
            print("Point me at the folder inside it that holds your photos and videos.")
        return
    print(f"\n  {len(todo)} thing{'s' if len(todo) != 1 else ''} still to set up:\n")
    for i, (what, why, how) in enumerate(todo, 1):
        print(f"  {i}. {what}\n     {why}\n     " + how.replace("\n    ", "\n     ") + "\n")
    if any("Google Drive" in w for w, _, _ in todo):
        print("If your media is already on this computer, you can start right now — organising")
        print("is free and needs nothing installed. Google Drive above is only for pulling a")
        print("Drive down as a folder. The rest is only for searchable transcripts later.")
    else:
        print("You have everything you need to organise your folders — that part is free.")
        print("The items above are only for the optional searchable-transcripts step.")
    print("Run this check again after each step.")


# ---------------------------------------------------------------- scan / plan / visualise

def cmd_scan(args) -> None:
    root = Path(args.folder).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Not a folder: {root}")
    try:
        s = scanmod.scan(root)
    except scanmod.EmptyLibrary as e:
        raise SystemExit(str(e))
    lib = paths.open_library(root)
    scanmod.save(lib, s)
    print(f"Scanned '{root.name}' — read only, nothing changed.")
    print(f"  {len(s.files)} files ({system.human(s.total_bytes)}) in {len(s.folders)} folders, "
          f"{s.max_depth} levels deep")
    print(f"  {s.sparse_folders} folders hold 2 files or fewer")
    for cat, n in sorted(s.by_category.items(), key=lambda kv: -kv[1]):
        print(f"  {cat:<12} {n}")
    if s.packages:
        print(f"  {s.packages} Keynote/Pages/Final Cut style document{'s' if s.packages != 1 else ''}"
              f" (folders that are really one file) — kept whole")
    if s.unknown_extensions:
        top = sorted(s.unknown_extensions.items(), key=lambda kv: -kv[1])[:8]
        print("  Unrecognised types filed under Documents: " + ", ".join(f"{e} ({n})" for e, n in top)
              + (" …" if len(s.unknown_extensions) > 8 else ""))
    print(f"\nWrote {lib.scan_file}")


def cmd_plan(args) -> None:
    lib = _lib(args)
    s = scanmod.load(lib)
    group_by = args.group_by or planmod.detect_shape(s)
    if not args.group_by:
        print(f"Treating this as {'one shoot' if group_by == 'flat' else 'a library of events'}"
              f" — {planmod.why_shape(s, group_by)}. Override with --group-by.")
    p = planmod.build(s, group_by)
    planmod.save(lib, p)
    print("Planned — still read only, nothing has moved.")
    print(f"  {len(s.folders)} folders ({s.max_depth} deep)  ->  {p.folders_after} folders ({p.depth_after} deep)")
    print(f"  {p.files_moving} files will move, {len(p.moves) - p.files_moving} already correct")
    loose = sum(1 for m in p.moves if m.event == "Unsorted")
    if loose:
        print(f"  {loose} loose file{'s' if loose != 1 else ''} at the top level go into an "
              f"'Unsorted' event folder — rename it afterwards if they belong to one event.")
    if p.renames:
        print(f"  {len(p.renames)} share a name with another file and get a number added so neither is lost:")
        for m in p.renames[:5]:
            print(f"    {m.name}  ->  {m.final_name}")
        if len(p.renames) > 5:
            print(f"    …and {len(p.renames) - 5} more")
    print("  Nothing is deleted. Every move is logged and reversible.")
    print(f"\nWrote {lib.plan_file}")


def cmd_visualise(args) -> None:
    lib = _lib(args)
    p, s = _plan(lib), scanmod.load(lib)
    p1, p2 = render.write(lib, p, s)
    p.shown_digest = p.digest()          # what was shown is what apply will accept
    planmod.save(lib, p)
    print(f"Wrote:\n  {p1}\n  {p2}")
    if not args.no_open:
        if all(system.open_file(x) for x in (p1, p2)):
            print("\nBoth visuals opened in the browser.")
        else:
            print("\nCould not open them automatically. Open these two files in a browser —"
                  "\nthey must be looked at before anything moves:")
            for x in (p1, p2):
                print(f"  {x}")
    if not system.IS_MAC:
        print("\nNote: folder colours are a Mac feature. On this computer the folders are"
              "\nnamed and organised the same way, just without the colour tags.")


# ---------------------------------------------------------------- apply / rollback / status

def cmd_apply(args) -> None:
    lib = _lib(args)
    if not lib.plan_file.exists():
        raise SystemExit("No plan.json. Run scan, plan and visualise first.")
    p = planmod.load(lib)
    try:
        todo = apply.check_gate(lib, p, args.approved_by or "")
    except apply.Refused as e:
        raise SystemExit(str(e))
    print(f"About to change:  {lib.root}")
    print(f"Applying: {len(todo)} files to move. Nothing will be deleted.")
    try:
        r = apply.run(lib, p, args.approved_by, log=lambda d: print(f"  {d}"))
    except apply.Refused as e:
        raise SystemExit(str(e))
    print(f"\nDone. {r.moved} files moved, 0 deleted.")
    if r.skipped:
        print(f"  {r.skipped} files were not where the plan expected — moved or removed by "
              f"someone since the scan, or already moved by an earlier run. Left alone.")
    print(f"  {r.cleared} emptied folders cleared away.")
    if r.failures:
        print(f"\n  {len(r.failures)} files could NOT be moved and are untouched where they were:")
        for name, why in r.failures[:10]:
            print(f"    {name} — {why}")
        if len(r.failures) > 10:
            print(f"    …and {len(r.failures) - 10} more")
        print("  Re-run apply to retry just those.")
    print(f"Move journal: {lib.journal_file}")


def cmd_rollback(args) -> None:
    lib = _lib(args)
    p = _plan(lib)
    j = Journal(lib)
    rows = j.pending()
    j.close()
    if not rows:
        raise SystemExit("Nothing to undo — this library has never been changed, or it is already back.")
    print(f"Undo would put {len(rows)} files back where they were, in '{lib.root.name}':")
    print(f"  {lib.root}")
    for r in rows[:8]:
        back = r.moved_from if r.moved_from != "." else "the top level"
        print(f"  {r.final_name}  ->  {back}/{r.original_name}")
    if len(rows) > 8:
        print(f"  …and {len(rows) - 8} more")
    print("\nNothing is deleted by this either — files move back, that is all.")
    if len((args.approved_by or "").strip()) < 2:
        print("\nNothing has moved. To go ahead, re-run with:")
        print('  library.py rollback --approved-by "<their name>"')
        return
    r = apply.rollback(lib, p)
    print(f"\nDone. {r.restored} files put back, 0 deleted.")
    if r.cleared:
        print(f"  {r.cleared} folders that ended up empty were cleared.")
    for line in r.renamed[:10]:
        print(f"  {line}")
    if r.problems:
        print(f"\n  {len(r.problems)} could not be moved back — they are still where they are, nothing was lost:")
        for x in r.problems[:10]:
            print(f"    {x}")
        if len(r.problems) > 10:
            print(f"    …and {len(r.problems) - 10} more")
        print("\n  Everything else is back where it started. The ones above were moved or"
              "\n  renamed after the organise, so the undo could not find them — look for"
              "\n  them by name and put them back by hand. Running rollback again retries them.")
    else:
        print("The library is back to how it was. You can scan it again any time.")


def cmd_status(args) -> None:
    pin = getattr(args, "library", None)
    if not pin and not (paths.work_base() / "current.json").exists():
        print("No library scanned yet. Run:  library.py scan \"<your folder>\"")
        return
    lib = _lib(args)
    print(f"Current library: {lib.root}")
    if lib.plan_file.exists():
        p = planmod.load(lib)
        if p.partial_rollback_at:
            state = "partly put back — some files could not be found. Run rollback again to retry them"
        elif p.approved:
            state = "organised — undo is available"
        elif p.rolled_back_at:
            state = f"put back the way it was on {p.rolled_back_at[:10]} — nothing pending"
        elif p.files_moving == 0:
            state = "already organised — nothing to move"
        elif p.shown_digest:
            state = "planned and shown, waiting for approval"
        else:
            state = "planned, visuals not shown yet"
        print(f"  Status: {state}")
        print(f"  {len(p.moves)} files -> {p.folders_after} folders")
    else:
        print("  Status: scanned, no plan yet")
    if lib.journal_file.exists() or (lib.state / "rollback.csv").exists():
        j = Journal(lib)
        pending, total = j.counts()
        j.close()
        if pending:
            print(f"  {pending} moves can be undone with:  library.py rollback")
        elif total:
            print(f"  {total} moves in the journal, all undone")
    n_tx = len(list(lib.bank.glob("*.json"))) if lib.bank.is_dir() else 0
    if n_tx:
        print(f"  {n_tx} transcripts paid for and banked")
    others = paths.other_libraries(lib)
    if others:
        print(f"\n  {len(others)} other librar{'y' if len(others) == 1 else 'ies'} also have saved state."
              " Scanning one makes it current; pin one with --library.")


# ---------------------------------------------------------------- key

def cmd_key(args) -> None:
    if args.forget:
        print(f"Removed the stored key ({keystore.key_file()})." if keystore.forget()
              else "No stored key to remove.")
        return
    if args.check:
        key, where = keystore.load()
        print(f"A key is set ({len(key)} characters, from the {where}). Not shown." if key
              else "No key is set. Run:  library.py key")
        return
    if args.stdin:
        key = sys.stdin.read()
    elif sys.stdin.isatty():
        print("Paste your OpenAI key and press Enter. Nothing is shown while you type,")
        print("and the key is stored only in a private file on this computer.")
        key = getpass.getpass("OpenAI key: ")
    else:
        raise SystemExit("No terminal to prompt on. Pipe the key in with:  library.py key --stdin")
    try:
        path = keystore.save(key)
    except keystore.BadKey as e:
        raise SystemExit(str(e))
    print(f"Stored ({len(key.strip())} characters, not shown) in {path}")
    print("It is readable only by your user account. Remove it any time with:  library.py key --forget")


# ---------------------------------------------------------------- transcribe

def make_transcriber(key: str) -> transcribe.Transcriber:
    """Tests replace this to avoid the network."""
    return transcribe.OpenAIWhisper(key)


def cmd_transcribe(args) -> None:
    lib = _lib(args)
    p = _plan(lib)
    if p.files_moving > 0 and not p.approved:
        raise SystemExit("The structure has not been approved yet, so there is nothing settled to\n"
                         "index. Run visualise and apply first — transcribing before the files have\n"
                         "moved would write the index into folders that are about to change.")
    if not lib.root.is_dir():
        raise SystemExit(f"The library folder is not there any more:  {lib.root}")
    if not (system.has_tool("ffmpeg") and system.has_tool("ffprobe")):
        raise SystemExit("ffmpeg is needed to pull audio out of video.\n  "
                         + system.ffmpeg_install_line().replace("\n    ", "\n  "))
    only = args.only or []
    if only:
        known = {f.name.lower() for f in lib.root.iterdir() if f.is_dir()}
        missing = [o for o in only if o.strip().lower() not in known]
        if missing:
            raise SystemExit("No event folder called: " + ", ".join(missing)
                             + "\nEvent folders here: " + ", ".join(sorted(known)))
    files, links = transcribe.spoken_files(lib.root, only)
    if links:
        print(f"Skipping {len(links)} shortcut(s) — they point outside this folder and will not be sent anywhere.")
    if not files:
        raise SystemExit("There are no videos or audio files here, so there is nothing to transcribe "
                         "and nothing to pay for.\nPhotos and documents are already organised — you are done.")
    est = transcribe.estimate(lib.root, files)
    if not est.todo:
        print("Every video and audio file already has a transcript. Nothing to do.")
        return
    print(f"Measuring {len(est.todo)} files…")
    mins = f"{est.minutes:.0f}" if est.minutes >= 10 else f"{est.minutes:.1f}"
    print(f"\n  {len(est.readable)} files, {mins} minutes of audio")
    if est.unreadable:
        print(f"  {len(est.unreadable)} file{'s' if len(est.unreadable) != 1 else ''} could not be read, "
              f"so they are skipped — they may be damaged or still downloading:")
        for v in est.unreadable[:5]:
            print(f"    {v.name}")
        if len(est.unreadable) > 5:
            print(f"    …and {len(est.unreadable) - 5} more")
    print(f"  Estimated cost: ${est.cost:.2f} USD (OpenAI {transcribe.MODEL}, "
          f"${transcribe.USD_PER_MIN}/min, price checked {transcribe.PRICE_VERIFIED})")
    print("  This is billed to your own OpenAI account.")
    if est.minutes <= 0:
        print("\n  Nothing readable to transcribe, so there is nothing to pay for.")
        return
    print(f"\n  Reads {system.human(est.total_bytes)} of media. On a streaming Drive that downloads each file as it goes.")
    print(f"  Free disk right now: {system.human(est.free_bytes)}.")
    if est.disk_tight:
        print("\n  WARNING: that is close to or more than the free space available.")
        print("  Do it in batches — transcribe one event folder at a time with")
        print('  library.py transcribe --only "<event folder>" — or free up space first.')
    print()
    if not args.yes:
        print("Nothing has been sent and nothing has been charged.")
        print("To go ahead:  library.py transcribe --yes" + "".join(f' --only "{o}"' for o in only))
        return
    key, _ = keystore.load()
    if not key:
        raise SystemExit("No OpenAI key set. Run:  library.py key   and paste it at the prompt.\n"
                         "  Get a key at https://platform.openai.com/api-keys")
    try:
        done, failed = transcribe.run(lib, est, make_transcriber(key), log=print)
    except transcribe.UserFixable as e:
        raise SystemExit(str(e))
    print(f"\nTranscribed {done} files" + (f", {failed} failed" if failed else "") + ".")
    print("Re-run this command any time — finished ones are skipped.")
    if done:
        print('Next, free and instant:  library.py manifest   then   library.py search "<words>"')


# ---------------------------------------------------------------- manifest / search

def cmd_manifest(args) -> None:
    lib = _lib(args)
    p = _plan(lib)
    if not lib.root.is_dir():
        raise SystemExit(f"The library folder is not there any more:  {lib.root}")
    written = index.write_manifests(lib, p.group_by)
    print(f"Wrote {len(written)} manifest{'s' if len(written) != 1 else ''}:")
    for w in written[:12]:
        print(f"  {w.relative_to(lib.root).as_posix()}")
    if len(written) > 12:
        print(f"  …and {len(written) - 12} more")


def cmd_search(args) -> None:
    lib = _lib(args)
    _plan(lib)
    terms = [t for t in args.words if t.strip()]
    if not terms:
        raise SystemExit("Give me a word or two to look for.")
    ix = index.SearchIndex(lib)
    try:
        ix.refresh()
        total = ix.count(terms)
        hits = ix.search(terms, args.limit)
    finally:
        ix.close()
    label = " + ".join(terms)
    if not hits:
        print(f"Nothing in the transcripts mentions {label}.")
        print("If the clip has not been transcribed yet, run:  library.py transcribe")
        return
    print(f"{total} match{'es' if total != 1 else ''} for {label}:\n")
    for h in hits:
        where = f"{h.event} / " if h.event else ""
        stamp = f"[{h.stamp}]" if h.stamp else ""
        print(f"  {where}{h.media}  {stamp}")
        print(f"      {h.text[:160]}")
    if total > len(hits):
        print(f"\n  …and {total - len(hits)} more. Narrow the words, or raise --limit.")


# ---------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="library.py",
        description="Organise a folder of photos, videos and audio, then make it searchable.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"media-library-setup {VERSION}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def pin(sp):
        sp.add_argument("--library", default=None, help="pin the library by path instead of the last one scanned")

    sub.add_parser("check", help="what is installed, what is still needed").set_defaults(func=cmd_check)
    s = sub.add_parser("scan", help="read-only survey of a folder"); s.add_argument("folder"); s.set_defaults(func=cmd_scan)
    p = sub.add_parser("plan", help="build the proposed structure (no writes)")
    p.add_argument("--group-by", choices=["event", "flat"], default=None, help="auto-detected when omitted")
    pin(p); p.set_defaults(func=cmd_plan)
    v = sub.add_parser("visualise", aliases=["visualize"], help="render the two approval visuals")
    v.add_argument("--no-open", action="store_true"); pin(v); v.set_defaults(func=cmd_visualise)
    a = sub.add_parser("apply", help="move the files — needs approval")
    a.add_argument("--approved-by", default=""); pin(a); a.set_defaults(func=cmd_apply)
    rb = sub.add_parser("rollback", help="put every moved file back where it was")
    rb.add_argument("--approved-by", default=""); pin(rb); rb.set_defaults(func=cmd_rollback)
    st = sub.add_parser("status", help="which library is active and what state it is in"); pin(st); st.set_defaults(func=cmd_status)
    k = sub.add_parser("key", help="store the OpenAI key privately (hidden prompt)")
    k.add_argument("--stdin", action="store_true", help="read the key from standard input")
    k.add_argument("--check", action="store_true", help="say whether a key is set, never show it")
    k.add_argument("--forget", action="store_true", help="remove the stored key")
    k.set_defaults(func=cmd_key)
    t = sub.add_parser("transcribe", help="make it searchable (costs a few dollars)")
    t.add_argument("--yes", action="store_true", help="confirm the cost and go ahead")
    t.add_argument("--only", action="append", default=[], metavar="EVENT",
                   help="only this event folder (repeatable) — batches a big library")
    pin(t); t.set_defaults(func=cmd_transcribe)
    m = sub.add_parser("manifest", help="write _Index/_MANIFEST.md for every event (free)"); pin(m); m.set_defaults(func=cmd_manifest)
    se = sub.add_parser("search", help="find a moment in the transcripts")
    se.add_argument("words", nargs="+"); se.add_argument("--limit", type=int, default=25)
    pin(se); se.set_defaults(func=cmd_search)
    return ap


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)
