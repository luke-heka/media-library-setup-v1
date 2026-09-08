#!/usr/bin/env python3
# Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠
# Provenance marker: sk-w3709n
"""Behavioural tests for media-library-setup. Standard library only, fully offline.

Run:  python3 -m unittest discover -s tests -t . -v
Every test builds its own fictional library in a temp folder and points the tool's
state at a temp folder too, so nothing on the real machine is read or touched.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import os
import re
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(SKILL / "scripts"))
os.environ["MEDIA_LIBRARY_WORK_DIR"] = tempfile.mkdtemp(prefix="mls-state-")

from medialib import cli, journal, keystore, paths, plan as planmod  # noqa: E402
from medialib import scan as scanmod, system, transcribe  # noqa: E402


def run(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out):
        try:
            cli.main(list(argv))
        except SystemExit as e:
            code = 1 if e.code not in (None, 0) else 0
            if isinstance(e.code, str):
                print(e.code)
    return code, out.getvalue()


def snapshot(root: Path) -> dict[str, str]:
    snap = {}
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        for n in dirnames:
            snap[str((d / n).relative_to(root))] = ""
        for n in filenames:
            p = d / n
            snap[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return snap


def mk(root: Path, rel: str, content: str = "x") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mls-"))
        os.environ["MEDIA_LIBRARY_WORK_DIR"] = str(self.tmp / "state")
        os.environ["XDG_CONFIG_HOME"] = str(self.tmp / "cfg")
        os.environ["APPDATA"] = str(self.tmp / "cfg")
        self._env = os.environ.pop("OPENAI_API_KEY", None)
        self.root = self.tmp / "Footage"
        self.root.mkdir()
        self._patches = []

    def tearDown(self):
        for p in self._patches:
            p.stop()
        if self._env is not None:
            os.environ["OPENAI_API_KEY"] = self._env

    def patch(self, target, value):
        p = mock.patch(target, value)
        p.start()
        self._patches.append(p)

    def messy_library(self) -> Path:
        r = self.root
        mk(r, "Brisbane May/Raw Videos/Stage/clip.mp4", "brisbane stage clip")
        mk(r, "Brisbane May/Raw Videos/Stage/clip.srt", "1\n00:00 --> 00:01\nhi")
        mk(r, "Brisbane May/Raw Videos/Handheld/clip.mp4", "brisbane handheld clip")
        mk(r, "Brisbane May/Raw Videos/Handheld/Deeper/Still/IMG_1.jpg", "img")
        mk(r, "Brisbane May/Deck.key/Index.zip", "keynote-index")
        mk(r, "Brisbane May/Deck.key/Data/preview.jpg", "keynote-preview")
        mk(r, "Brisbane May/videos/old.mov", "already lowercase videos folder")
        mk(r, "Brisbane May/notes.pdf", "pdf")
        mk(r, "Sydney June/pod.mp3", "podcast")
        mk(r, "Sydney June/pod.xmp", "sidecar")
        mk(r, "Sydney June/Photos/x.jpg", "x")
        mk(r, "Sydney June/.DS_Store", "junk")
        mk(r, "loose.png", "loose at top")
        return r

    def organise(self, root: Path, who: str = "Test Person") -> str:
        for cmd in (["scan", str(root)], ["plan"], ["visualise", "--no-open"]):
            code, out = run(*cmd)
            self.assertEqual(code, 0, out)
        code, out = run("apply", "--approved-by", who)
        self.assertEqual(code, 0, out)
        return out

    def lib(self) -> paths.Library:
        return paths.current_library()


class TestGates(Base):
    def test_apply_refuses_without_plan(self):
        run("scan", str(self.messy_library()))
        code, out = run("apply", "--approved-by", "Someone")
        self.assertEqual(code, 1); self.assertIn("No plan", out)

    def test_apply_refuses_without_visuals(self):
        run("scan", str(self.messy_library())); run("plan")
        code, out = run("apply", "--approved-by", "Someone")
        self.assertEqual(code, 1); self.assertIn("visuals have not been generated", out)

    def test_apply_refuses_without_a_name_or_with_whitespace(self):
        run("scan", str(self.messy_library())); run("plan"); run("visualise", "--no-open")
        for who in ("", "   ", "A"):
            code, out = run("apply", "--approved-by", who)
            self.assertEqual(code, 1, who)
            self.assertIn("Refusing to move anything without approval", out)
        self.assertFalse(self.lib().journal_file.exists())
        self.assertTrue((self.root / "Brisbane May" / "Raw Videos").is_dir())

    def test_apply_refuses_a_plan_changed_after_the_visuals(self):
        run("scan", str(self.messy_library())); run("plan"); run("visualise", "--no-open")
        p = planmod.load(self.lib())
        p.moves[0].dst = "Somewhere/Else"
        planmod.save(self.lib(), p)
        code, out = run("apply", "--approved-by", "Someone")
        self.assertEqual(code, 1); self.assertIn("changed since the visuals", out)

    def test_apply_refuses_a_no_op(self):
        mk(self.root, "Videos/a.mp4"); mk(self.root, "Photos/b.jpg")
        run("scan", str(self.root)); run("plan"); run("visualise", "--no-open")
        code, out = run("apply", "--approved-by", "Someone")
        self.assertEqual(code, 1); self.assertIn("nothing to approve", out)

    def test_scan_refuses_empty_and_package_roots(self):
        empty = self.tmp / "Empty"; empty.mkdir()
        code, out = run("scan", str(empty))
        self.assertEqual(code, 1); self.assertIn("nothing to organise", out)
        pkg = self.tmp / "Deck.key"; mk(pkg, "Index.zip")
        code, out = run("scan", str(pkg))
        self.assertEqual(code, 1); self.assertIn("single document", out)

    def test_fresh_scan_invalidates_old_plan(self):
        run("scan", str(self.messy_library())); run("plan"); run("visualise", "--no-open")
        run("scan", str(self.root))
        self.assertFalse(self.lib().plan_file.exists())
        self.assertFalse(self.lib().visuals[0].exists())


class TestRoundTrip(Base):
    def test_apply_then_rollback_is_byte_identical_and_packages_stay_whole(self):
        root = self.messy_library()
        before = snapshot(root)
        out = self.organise(root)
        self.assertIn("0 deleted", out)
        b = root / "Brisbane May"
        self.assertTrue((b / "Documents" / "Deck.key" / "Index.zip").is_file())
        self.assertTrue((b / "Documents" / "Deck.key" / "Data" / "preview.jpg").is_file())
        self.assertFalse((b / "Photos" / "preview.jpg").exists())
        self.assertFalse((b / "Deck.key").exists())
        self.assertTrue((b / "Videos" / "clip.srt").is_file())
        self.assertEqual(sorted(p.name for p in (b / "Videos").iterdir()),
                         ["clip-2.mp4", "clip.mp4", "clip.srt", "old.mov"])
        self.assertIn("Videos", [p.name for p in b.iterdir()])
        self.assertNotIn("videos", [p.name for p in b.iterdir()])
        self.assertTrue((b / "Photos" / "IMG_1.jpg").is_file())
        self.assertFalse((b / "Raw Videos").exists())
        s = root / "Sydney June"
        self.assertTrue((s / "Audio" / "pod.mp3").is_file())
        self.assertTrue((s / "Audio" / "pod.xmp").is_file())
        self.assertTrue((root / "Unsorted" / "Photos" / "loose.png").is_file())
        self.assertTrue((s / ".DS_Store").exists())
        for p in root.rglob("*"):
            if "Deck.key" not in p.parts:
                self.assertLessEqual(len(p.relative_to(root).parts), 3, p)
        code, out = run("rollback")
        self.assertEqual(code, 0); self.assertIn("Nothing has moved", out)
        self.assertNotEqual(snapshot(root), before)
        code, out = run("rollback", "--approved-by", "Test Person")
        self.assertEqual(code, 0, out); self.assertIn("back to how it was", out)
        self.assertEqual(snapshot(root), before)
        j = journal.Journal(self.lib())
        self.assertEqual(j.counts(), (0, 10)); j.close()

    def test_partial_rollback_keeps_failed_rows_retryable(self):
        root = self.messy_library()
        self.organise(root)
        (root / "Sydney June" / "Audio" / "pod.mp3").rename(self.tmp / "taken-away.mp3")
        code, out = run("rollback", "--approved-by", "Test Person")
        self.assertEqual(code, 0); self.assertIn("could not be moved back", out)
        j = journal.Journal(self.lib())
        pending = j.pending(); j.close()
        self.assertEqual([r.final_name for r in pending], ["pod.mp3"])
        code, out = run("status")
        self.assertIn("partly put back", out)
        (root / "Sydney June" / "Audio").mkdir(parents=True, exist_ok=True)
        (self.tmp / "taken-away.mp3").rename(root / "Sydney June" / "Audio" / "pod.mp3")
        code, out = run("rollback", "--approved-by", "Test Person")
        self.assertIn("back to how it was", out)

    def test_wrong_library_cannot_receive_an_approval(self):
        a = self.messy_library()
        b = self.tmp / "Other"; mk(b, "Deep/x/y.mp4")
        run("scan", str(a)); run("plan"); run("visualise", "--no-open")
        run("scan", str(b))
        code, out = run("apply", "--approved-by", "Someone")
        self.assertEqual(code, 1)
        code, out = run("apply", "--library", str(a), "--approved-by", "Someone")
        self.assertEqual(code, 0, out); self.assertIn(str(a), out)
        self.assertTrue((a / "Brisbane May" / "Videos").is_dir())
        self.assertFalse((b / "Videos").exists())

    def test_legacy_rollback_csv_is_imported_and_still_undoes(self):
        root = self.root
        mk(root, "Ev/Videos/a.mp4", "a")
        lib = paths.open_library(root)
        scanmod.save(lib, scanmod.scan(root))
        planmod.save(lib, planmod.build(scanmod.load(lib), "event"))
        (lib.state / "rollback.csv").write_text(
            "original_name,final_name,moved_from,moved_to,at\na.mp4,a.mp4,Ev/old,Ev/Videos,2026-07-30T10:00:00\n")
        code, out = run("rollback", "--approved-by", "Test Person")
        self.assertEqual(code, 0, out)
        self.assertTrue((root / "Ev" / "old" / "a.mp4").is_file())
        self.assertFalse((lib.state / "rollback.csv").exists())


class TestTranscribe(Base):
    def fake_transport(self, seconds: float = 60.0):
        calls: list[str] = []

        class Fake:
            def transcribe(self, audio, filename):
                calls.append(filename)
                return ([transcribe.Segment(0.0, 4.5, " Welcome everyone."),
                         transcribe.Segment(5.2, 9.0, " Let's talk about pricing.")], seconds)
        self.patch("medialib.system.has_tool", lambda name: True)
        self.patch("medialib.system.media_seconds", lambda p: seconds)
        self.patch("medialib.transcribe.extract_audio", lambda src, out: out.write_bytes(b"fake-audio"))
        self.patch("medialib.cli.make_transcriber", lambda key: Fake())
        return calls

    def test_refuses_while_moves_are_pending_and_allows_an_organised_library(self):
        self.fake_transport()
        run("scan", str(self.messy_library())); run("plan")
        code, out = run("transcribe")
        self.assertEqual(code, 1); self.assertIn("not been approved", out)
        tidy = self.tmp / "Tidy"; mk(tidy, "Videos/a.mp4"); mk(tidy, "Photos/b.jpg")
        run("scan", str(tidy)); run("plan")
        code, out = run("transcribe")
        self.assertEqual(code, 0, out); self.assertIn("Nothing has been sent", out)
        self.assertIn("$0.01", out); self.assertIn(transcribe.PRICE_VERIFIED, out)
        self.patch("medialib.system.media_seconds", lambda p: 3600.0)
        code, out = run("transcribe")
        self.assertIn("$0.36", out)

    def test_writes_timestamped_transcripts_and_never_pays_twice(self):
        calls = self.fake_transport()
        root = self.messy_library()
        self.organise(root)
        os.environ["OPENAI_API_KEY"] = "sk-test-" + "x" * 30
        code, out = run("transcribe", "--yes")
        self.assertEqual(code, 0, out)
        t = root / "Brisbane May" / "_Index" / "clip.mp4.transcript.md"
        body = t.read_text()
        self.assertIn("[00:05] Let's talk about pricing.", body)
        self.assertIn("Source: Brisbane May/Videos/clip.mp4", body)
        self.assertTrue((root / "Sydney June" / "_Index" / "pod.mp3.transcript.md").is_file())
        n = len(calls); self.assertEqual(n, 4)
        t.unlink()
        code, out = run("transcribe", "--yes")
        self.assertEqual(code, 0, out); self.assertIn("reusing, no charge", out)
        self.assertEqual(len(calls), n); self.assertTrue(t.is_file())
        code, out = run("transcribe")
        self.assertIn("already has a transcript", out)

    def test_only_restricts_to_named_events(self):
        calls = self.fake_transport()
        root = self.messy_library()
        self.organise(root)
        os.environ["OPENAI_API_KEY"] = "sk-test-" + "x" * 30
        code, out = run("transcribe", "--only", "Nowhere")
        self.assertEqual(code, 1); self.assertIn("No event folder called: Nowhere", out)
        code, out = run("transcribe", "--yes", "--only", "sydney june")
        self.assertEqual(code, 0, out)
        self.assertEqual(calls, ["pod.mp3"])
        self.assertFalse((root / "Brisbane May" / "_Index").exists())

    def test_missing_key_stops_before_sending(self):
        calls = self.fake_transport()
        self.organise(self.messy_library())
        code, out = run("transcribe", "--yes")
        self.assertEqual(code, 1); self.assertIn("No OpenAI key set", out)
        self.assertEqual(calls, [])

    def test_user_fixable_error_stops_the_run_cleanly(self):
        self.fake_transport()

        class Broke:
            def transcribe(self, audio, filename):
                raise transcribe.UserFixable("The key works but the OpenAI account has no credit.")
        self.patch("medialib.cli.make_transcriber", lambda key: Broke())
        self.organise(self.messy_library())
        os.environ["OPENAI_API_KEY"] = "sk-test-" + "x" * 30
        code, out = run("transcribe", "--yes")
        self.assertEqual(code, 1); self.assertIn("no credit", out)
        self.assertFalse((self.root / "Brisbane May" / "_Index").exists())

    def test_multipart_body_shape(self):
        body, boundary = transcribe.multipart({"model": "whisper-1", "response_format": "verbose_json"},
                                              "file", 'na"me\r\n.mp3', b"\x00\x01audio")
        self.assertTrue(body.startswith(f"--{boundary}\r\n".encode()))
        self.assertTrue(body.endswith(f"\r\n--{boundary}--\r\n".encode()))
        self.assertIn(b'name="model"\r\n\r\nwhisper-1\r\n', body)
        self.assertIn(b'name="file"; filename="na_me__.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n\x00\x01audio\r\n', body)

    def test_symlinked_media_is_never_sent(self):
        calls = self.fake_transport()
        tidy = self.tmp / "Tidy"; mk(tidy, "Videos/a.mp4")
        os.symlink(self.tmp / "elsewhere.mp4", tidy / "Videos" / "link.mp4")
        run("scan", str(tidy)); run("plan")
        os.environ["OPENAI_API_KEY"] = "sk-test-" + "x" * 30
        code, out = run("transcribe", "--yes")
        self.assertEqual(code, 0, out); self.assertIn("Skipping 1 shortcut", out)
        self.assertEqual(calls, ["a.mp3"])


class TestKeyStore(Base):
    def test_key_is_stored_owner_only_and_never_printed(self):
        secret = "sk-proj-" + "q" * 40
        code, out = run("key", "--check"); self.assertIn("No key is set", out)
        with mock.patch("sys.stdin", io.StringIO(secret + "\n")):
            code, out = run("key", "--stdin")
        self.assertEqual(code, 0, out)
        self.assertNotIn(secret, out); self.assertNotIn("q" * 10, out)
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(keystore.key_file().stat().st_mode), 0o600)
        self.assertEqual(keystore.load(), (secret, "file"))
        code, out = run("key", "--check")
        self.assertIn("from the file", out); self.assertNotIn(secret, out)
        os.environ["OPENAI_API_KEY"] = "sk-env-" + "e" * 30
        self.assertEqual(keystore.load()[1], "environment")
        run("key", "--forget")
        self.assertFalse(keystore.key_file().exists())

    def test_rejects_something_that_is_not_a_key(self):
        with mock.patch("sys.stdin", io.StringIO("hello world\n")):
            code, out = run("key", "--stdin")
        self.assertEqual(code, 1); self.assertFalse(keystore.key_file().exists())


class TestSearchAndManifest(Base):
    def test_manifest_and_search(self):
        root = self.messy_library()
        self.organise(root)
        idx = root / "Brisbane May" / "_Index"; idx.mkdir()
        (idx / "clip.mp4.transcript.md").write_text(
            "# Transcript — clip.mp4\n\n[00:00] Welcome.\n[12:34] Our pricing starts at five.\n")
        (idx / "old.mov.summary.md").write_text("# Summary\n\nA room filling up before the talk.\n")
        code, out = run("manifest")
        self.assertEqual(code, 0, out)
        m = (idx / "_MANIFEST.md").read_text()
        self.assertIn("| Videos | clip.mp4 |", m); self.assertIn("| yes | Welcome. |", m)
        self.assertIn("| Documents | Deck.key |", m); self.assertIn("A room filling up", m)
        self.assertTrue((root / "Sydney June" / "_Index" / "_MANIFEST.md").is_file())
        code, out = run("search", "pricing")
        self.assertEqual(code, 0); self.assertIn("Brisbane May / clip.mp4  [12:34]", out)
        code, out = run("search", "room", "filling"); self.assertIn("old.mov", out)
        code, out = run("search", "unicorns"); self.assertIn("Nothing in the transcripts", out)
        (idx / "clip.mp4.transcript.md").write_text("# Transcript — clip.mp4\n\n[00:07] Bananas only.\n")
        os.utime(idx / "clip.mp4.transcript.md", (1, 2 ** 31 - 1))
        code, out = run("search", "pricing"); self.assertIn("Nothing", out)
        code, out = run("search", "bananas"); self.assertIn("[00:07]", out)

    def test_search_falls_back_without_fts5(self):
        root = self.messy_library(); self.organise(root)
        idx = root / "Brisbane May" / "_Index"; idx.mkdir()
        (idx / "clip.mp4.transcript.md").write_text("[00:01] Pricing talk.\n")
        self.patch("medialib.index.SearchIndex._has_fts5", lambda self: False)
        code, out = run("search", "pricing")
        self.assertIn("[00:01]", out)


class TestClassification(Base):
    def test_categories(self):
        from medialib.classify import CATEGORIES, category
        P = Path
        self.assertEqual(category(P("a.MP4")), "Videos"); self.assertEqual(category(P("a.mts")), "Videos")
        self.assertEqual(category(P("a.wav")), "Audio"); self.assertEqual(category(P("a.heic")), "Photos")
        self.assertEqual(category(P("a.pdf")), "Documents"); self.assertEqual(category(P("a.prproj")), "Documents")
        self.assertEqual(category(P("a.transcript.md")), "_Index")
        self.assertEqual(category(P("_MANIFEST.md")), "_Index"); self.assertEqual(category(P("_NOTES.md")), "_Index")
        self.assertEqual(category(P("a.srt")), "Documents")
        self.assertEqual(category(P("a.srt"), {"a": "Videos"}), "Videos")
        self.assertEqual(category(P("b.xmp"), {"b": "Photos"}), "Photos")
        self.assertEqual(category(P("mystery.xyz")), "Documents")
        self.assertEqual(set(CATEGORIES), {"Videos", "Photos", "Audio", "Documents", "_Index"})
        self.assertEqual(set(system.FINDER_TAGS), set(CATEGORIES))

    def test_junk(self):
        from medialib.classify import is_junk
        self.assertTrue(is_junk(Path(".DS_Store"))); self.assertTrue(is_junk(Path("Thumbs.db")))
        self.assertFalse(is_junk(Path("clip.mp4")))
        self.assertFalse(is_junk(Path("/nonexistent-dir/._family-archive.mp4")))
        mk(self.root, "x.mp4"); mk(self.root, "._x.mp4")
        self.assertTrue(is_junk(self.root / "._x.mp4"))

    def test_shape_detection(self):
        def s(folders):
            files = [scanmod.Item("f", "f", folders[0] if folders else ".", 1, 1, "Videos")]
            return scanmod.Scan("t", "t", "/r", "r", files, [scanmod.Folder(n, n, 1) for n in folders])
        self.assertEqual(planmod.detect_shape(s(["Videos", "Photos", "_Index"])), "flat")
        self.assertEqual(planmod.detect_shape(s(["Brisbane May", "Sydney June", "Perth July"])), "event")
        self.assertEqual(planmod.detect_shape(s([])), "flat")

    def test_scan_reports_unknown_types_and_packages(self):
        mk(self.root, "Ev/a.mp4"); mk(self.root, "Ev/thing.xyz"); mk(self.root, "Ev/Deck.pages/x")
        code, out = run("scan", str(self.root))
        self.assertIn("Unrecognised types filed under Documents: .xyz (1)", out)
        self.assertIn("1 Keynote/Pages/Final Cut style document", out)
        s = scanmod.load(self.lib())
        self.assertEqual(s.packages, 1); self.assertEqual(len(s.files), 3)


class TestVisuals(Base):
    def test_html_is_escaped_and_counts_are_real(self):
        mk(self.root, "<b>Evil<b> Event/deep/x.mp4"); mk(self.root, "<b>Evil<b> Event/y.jpg")
        run("scan", str(self.root)); run("plan")
        code, out = run("visualise", "--no-open")
        self.assertEqual(code, 0, out)
        v1, v2 = (v.read_text() for v in self.lib().visuals)
        self.assertNotIn("<b>Evil<b>", v1); self.assertNotIn("<b>Evil<b>", v2)
        self.assertIn("&lt;b&gt;Evil&lt;b&gt;", v1)
        self.assertIn("<b>1</b><span>emptied folders cleared away", v1)
        self.assertNotIn("$", v1.split("</style>")[1])
        self.assertNotIn("$", v2.split("</style>")[1])
        p = planmod.load(self.lib())
        self.assertEqual(p.shown_digest, p.digest())


class TestDocsMatchCode(unittest.TestCase):
    skill = (SKILL / "SKILL.md").read_text()
    readme = (SKILL / "README.md").read_text()
    setup = (SKILL / "references" / "setup.md").read_text()
    rules = (SKILL / "references" / "structure-rules.md").read_text()
    prompt = (SKILL / "SETUP-PROMPT.md").read_text()
    src = "".join(p.read_text() for p in (SKILL / "scripts").rglob("*.py"))
    everything = skill + readme + setup + rules + prompt

    def test_every_documented_command_exists(self):
        parser_cmds = set(re.findall(r'add_parser\("([a-z]+)"', self.src)) | {"visualize"}
        for cmd in set(re.findall(r"library\.py (?:--[a-z-]+ )*([a-z]+)", self.everything)):
            self.assertIn(cmd, parser_cmds, f"docs mention library.py {cmd}")

    def test_no_shell_profile_or_pip_instructions_remain(self):
        for banned in (".zshrc", ".bashrc", "pip3 install", "pip install", "setx OPENAI"):
            self.assertNotIn(banned, self.everything, banned); self.assertNotIn(banned, self.src, banned)

    def test_prices_carry_the_verification_date(self):
        self.assertIn(transcribe.PRICE_VERIFIED, self.skill); self.assertIn(transcribe.PRICE_VERIFIED, self.setup)
        self.assertIn("$0.36", self.skill); self.assertAlmostEqual(transcribe.USD_PER_MIN * 60, 0.36)

    def test_promises_are_stated_and_bounded(self):
        for phrase in ("No file is ever deleted", "Never delete a file", "rollback",
                       "Never go deeper than two levels", "--only", "manifest", "search",
                       "library.py key", "Nothing changes until you approve it"):
            self.assertIn(phrase, self.skill, phrase)
        self.assertIn("Nothing is renamed", self.rules); self.assertIn("Audio", self.rules)
        self.assertIn("package", self.rules.lower())
        self.assertRegex(self.readme, r"github\.com/[A-Za-z0-9-]+/media-library-setup")

    def test_publishing_firewall(self):
        for b in ("@gmail.com", "@selrai", "@selrgroup", "+61", "Luke", "ask us",
                  "contact us", "message us", "reach out", "if you get stuck"):
            self.assertNotIn(b, self.everything, b)


if __name__ == "__main__":
    unittest.main()
