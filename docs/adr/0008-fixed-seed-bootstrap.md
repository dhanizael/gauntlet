# 0008 — Fixed-seed percentile bootstrap: byte-reproducible verdicts over sampling purity

- Status: Accepted · 2026-09-18

## Context
Verdicts must be re-runnable bit-for-bit by anyone (audits, CI, disputes). A bootstrap
with entropy-sourced seeds changes CI bounds across runs and invites accusations that
"keep" was a lucky draw; the doctrine already fixed seeds for exactly this reason.

## Decision
`bootstrap_ci(signs, B=10000, seed=20260918)` uses a constant default seed echoed into
every verdict's `config` block; alternative seeds are caller-visible parameters, not hidden
state. Percentile method; no BCa (small n ⇒ BCa instability outweighs its bias correction,
and the frozen rule's margin dominates interpretation anyway).

## Consequences
- Determinism test (T1) is meaningful: same ledger ⇒ same JSON bytes.
- Known cost, stated plainly: a fixed resample stream is one draw from the bootstrap
  distribution; with B=10_000 its Monte-Carlo error (~0.01 scale) cannot cross the 0.10
  margin in practice, and `pairs_graded` lets any reader recompute independently.
