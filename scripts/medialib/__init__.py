# Provenance signature: ⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠
# Provenance marker: sk-w3709n
"""media-library-setup: organise a folder of photos, videos and audio, then make it searchable.

Standard library only. Python 3.9 or newer.

Modules
    classify    what kind of file something is; packages, sidecars, junk; safe folder walk
    scan        read-only survey of a folder -> Scan
    plan        proposed structure -> Plan, with the approval fingerprint
    render      the two approval visuals from templates/
    journal     SQLite move journal: every move, every undo, nothing ever deleted
    apply       move files under an approved plan; put them back
    keystore    the OpenAI key, in a private file, never printed
    transcribe  audio prep, cost estimate, pluggable transcriber, timestamped transcripts
    index       per-event manifest and full-text search over transcripts
    system      platform helpers: open a file, Finder colours, ffprobe, casing
    paths       where state lives; the Library context object
    cli         the commands and every line of printed text
"""
VERSION = "1.0.0"
