#!/usr/bin/env bash
# Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠
# Provenance marker: sk-w3709n
# Offline check for media-library-setup.
# No Drive calls, no network, no writes outside temp folders, no packages needed.
set -euo pipefail

skill_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
py="${PYTHON:-python3}"

# 1. The script parses and needs nothing outside the standard library.
"$py" - "$skill_dir/scripts" <<'PY'
import ast, pathlib, sys
stdlib = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else None
nodes = []
for f in sorted(pathlib.Path(sys.argv[1]).rglob("*.py")):
    nodes += list(ast.walk(ast.parse(f.read_text())))
for node in nodes:
    names = []
    if isinstance(node, ast.Import):
        names = [a.name.split(".")[0] for a in node.names]
    elif isinstance(node, ast.ImportFrom) and node.level == 0:
        names = [node.module.split(".")[0]]
    for n in names:
        if stdlib is not None and n not in stdlib and n != "medialib":
            raise SystemExit(f"non-stdlib import: {n}")
print(f"syntax ok, standard library only ({len(list(pathlib.Path(sys.argv[1]).rglob('*.py')))} files)")
PY

# 2. Behavioural tests: fictional libraries in temp folders, gates, round-trip, transcription
#    with a fake transport, key store, manifest, search, and the docs-match-code checks.
export MEDIA_LIBRARY_WORK_DIR="$(mktemp -d)"
cd "$skill_dir"
out="$("$py" -B -m unittest discover -s tests -t . 2>&1)" || { echo "$out"; exit 1; }
ran="$(echo "$out" | sed -n 's/^Ran \([0-9]*\) tests.*/\1/p')"
test -s "$skill_dir/references/structure-rules.md"
test -s "$skill_dir/SELR-REPORT.html"

echo "ok: media-library-setup — ${ran} tests passed"
