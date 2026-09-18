# 0003 — Drift = interpreter/packages; the workspace tree is forensics, not drift

- Status: Accepted · 2026-09-18 (caught by design review during v0.2, pre-test)

## Context
First implementation treated a workspace file-tree change between prep and close as
drift. Consequence: **every real trial "drifted"**, because writing outputs *is the point*.
Drift exists to catch a documented incident: a mid-experiment pip install that silently
invalidated all later comparisons. The tree hash still has forensic value (what existed
at prep vs close).

## Decision
`diff(env_start, env_end)` flags only interpreter and installed-package changes. Tree
hashes are recorded on both records for forensics and are never drift. Output integrity
is instead guaranteed by the seal+verify mechanism (separate concern, separate tool).

## Consequences
- Meaningful `sealed-drift` status: if present, something real and environment-wide
  happened during the trial.
- Two-layer honesty: *environment* drift (quarantine) vs *file* mutation post-seal
  (integrity failure, exit 3). Never conflated again.
