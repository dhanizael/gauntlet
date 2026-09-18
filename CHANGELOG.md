# Changelog

## v0.2.0 — 2026-09-18

The trial protocol: `gauntlet run`.

- `run init|prep|exec|close|status|verify|blindpack` — tasks x arms x repeats
  into opaque single-use slots. Fixtures copied (never linked) with per-file
  sha verification; symlink-bearing fixture trees refused.
- Environment drift: python + installed-package fingerprints at prep and close;
  any drift is enumerated on the close record and marked `sealed-drift`.
  (Born from a real incident: a mid-experiment pip install that silently
  invalidated every later trial.)
- Seal + `verify`: outputs manifest (path,size,sha256) recomputable — post-close
  edits, deletions, additions are detected.
- `blindpack`: judge-facing artifacts contain pseudonyms only; arm assignments
  live exclusively in a chmod-600 `unblind.json` on the private side.
- `run` coordinates any agent command (exit + duration captured); it records
  and proves, it does not judge — verdicts are v0.3 `grade`.
- 28 tests, CI matrix unchanged (3.11/3.13). PyPI: `gauntlet-guard` v0.2.0
  pending token refresh (distribution name; import and CLI remain `gauntlet`).

## v0.1.0 — 2026-09-18

First release: the integrity layer that ships today — `guard` + `manifest`.

- `gauntlet manifest add|list|retire` — sealed instance registry (JSONL):
  full-content SHA-256, normalized text, and 8-word shingle fingerprints.
  Manifests are private-side artifacts; instances retire on leak.
- `gauntlet guard scan` — persistence-leak scanner for agent stores
  (LESSONS/notes/journals/transcripts). Findings: exact / near (≥5% shingle
  overlap) / trace (≥2 shingles). CI-friendly exit codes; `--json` output.
- Redaction by design: scanner reports contain hash references, never matched
  text — the report is safe to publish (verified by assertion in tests/CI).
- Operational hardening after first real-world scan: file size caps with
  reported skips, binary sniffing, single-pass shingle computation
  (271 files in 3.1 s, zero runtime dependencies).
- `gauntlet guard selftest` — end-to-end proof: planted paraphrase caught,
  clean file untouched, oversized + binary files skipped-and-reported,
  report verified content-free.
- Python ≥3.11, MIT, 12 tests, CI matrix (3.11/3.13): pytest + ruff + ty + selftest.
- Published to PyPI as **`gauntlet-guard`** (distribution name; `agent-gauntlet` was
  blocked by PyPI's PEP-503 similarity rule against an existing live project;
  import name and CLI remain `gauntlet` / `gauntlet`).

Roadmap: `run` (blind paired arms, isolated workspaces, drift fingerprint),
`grade` (keep/revert verdict engine, ≥N repeats + spread), `holdout` (seed
generation + retirement ledger).
