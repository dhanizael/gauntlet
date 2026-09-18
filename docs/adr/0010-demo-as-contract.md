# 0010 — `gauntlet demo` is a public API surface with a self-asserting narrative

- Status: Accepted · 2026-09-18

## Context
External feedback (GitHub DM, 2026-09-18): the bottleneck is not features but
comprehension — people do not yet feel why they need an integrity layer. A
3-minute, $0, deterministic story ("did your agent improve, or did it remember
the test?") makes the failure mode *seen*, not explained.

## Decision
`demo` runs the three-act contamination story through the real public APIs
(run/grade/guard) with scripted agents. The demo asserts its own narrative
(provisional → KEEP → EXACT hit → collapse to provisional) and exits non-zero
if any act deviates. CI runs it. It is therefore simultaneously the README's
first line, an acceptance test for the whole stack, and a regression detector
for the story we promise.

## Consequences
- Anyone can verify the thesis in one command before trusting a single claim
  in this repo (including ours).
- Cost: the demo's scenario is now part of the API contract — refactors must
  keep the three acts true. Intended: the story is the product.
