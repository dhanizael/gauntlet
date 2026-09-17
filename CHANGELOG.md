# Changelog

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

Roadmap: `run` (blind paired arms, isolated workspaces, drift fingerprint),
`grade` (keep/revert verdict engine, ≥N repeats + spread), `holdout` (seed
generation + retirement ledger).
