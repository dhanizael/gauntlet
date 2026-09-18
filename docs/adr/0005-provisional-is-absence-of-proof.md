# 0005 — `provisional` means the claim failed to be proven; the posture is revert

- Status: Accepted · 2026-09-18

## Context
A ternary verdict (keep/revert/provisional) invites reading "provisional" as a
third outcome that preserves the status quo favorably. That quietly re-imports
faith through the door we removed. Doctrine lineage: a change stays PROVISIONAL
*until it wins* — not "until it doesn't lose".

## Decision
`provisional` = CI cannot clear the margin, insufficient/noncomparable evidence, or
corrupted evidence (>25% exclusions). Operational meaning: **do not ship the change**;
collect more trials or fix the harness. `--require-every-task` sharpens the conservative
variant: a task with *no graded evidence* counts as a no-win, not a pass.

## Consequences
- Absence of proof is treated as absence of warrant, consistently, in code and language.
- Exit code 2 (provisional) is a CI failure for shipping purposes by design.
