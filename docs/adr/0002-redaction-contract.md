# 0002 — The scanner must not leak

- Status: Accepted · 2026-09-17

## Context
`guard` reads secret holdout content to find it inside agent stores. A report that quotes
matches would itself become a leak channel — the tool would destroy the secrecy it audits.
First real-world scan (271 files) already forced skip-accounting (size caps, binary
sniffing) *and reporting of skips*: a silent skip is a silent lie.

## Decision
All findings are content-free by construction: file, word-position, counts, hash
references. Never matched text — in stdout, `--json`, or verdict faces. This is asserted
by tests (`test_report_contains_no_task_text`) and by the selftest, not by discipline.

## Consequences
- Reports are safe to paste into issues/CI logs; users can share findings without
  exposing tasks. Cost: humans must re-open the source file to *see* a match —
  intentional friction.
- Skipped files are always enumerated; "what wasn't scanned" is a first-class output.
