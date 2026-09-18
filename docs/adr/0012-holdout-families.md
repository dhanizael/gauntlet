# 0012 — Holdout families and the retirement ledger

- Status: Accepted
- Date: 2026-09-18
- Deciders: author

## Context
The protocol's answer to a leaked holdout is "retire and regenerate from an
unused seed" (ADR-0005 era doctrine; demo ACT 3b does it by hand). Until v0.4,
regeneration was manual: the operator invented a new instance, hand-registered
it, and *hoped* it was fresh. Nothing recorded which seeds existed, which
produced instances, or which were dead — so nothing could prove that a
"fresh" instance wasn't a memory of a leaked one. Separately, hand-made
instances share boilerplate with their dead siblings by design, which makes
naive text-distance the wrong freshness measure.

## Decision
`gauntlet holdout`: instances come into existence only through **family
templates** (private-side JSON: typed slots — `int`, `int_list`, `choice`,
`permutation` — filled by a **purpose-built counter-mode SHA-256 PRNG**,
never stdlib `random`, whose cross-version instability would silently rot
provenance). Seed strings are `family:counter`, consumed strictly in order
and recorded forever in a per-family, append-only, hash-chained **retirement
ledger** (0600, private side). Freshness is a **dual gate**: exact slot-space
collision within a family (boilerplate makes text distance meaningless there),
shingle overlap against other families in the manifest. Retirement writes the
manifest first, the ledger second; `verify` reconciles both directions and
`--deep` re-derives every instance from template + seed to prove
`content_sha256` still matches. Full frozen criteria:
[docs/HOLDOUT_DESIGN.md](../HOLDOUT_DESIGN.md).

## Consequences
- Positive: "regenerate from an unused seed" becomes a provable property —
  chain integrity, seed death, and even byte-identical reproduction are
  machine-checkable, closing the loop the demo could only narrate.
- Positive: templates may be public (shape leaks nothing); cardinality
  accounting exposes the real remaining risk (small families are enumerable).
- Negative: a fourth private-key class now exists (family file + ledger) —
  losing either orphans remaining counters; documented as a backup duty.
- Negative: partial numeric proximity between fresh and dead instances is
  out of scope by design (answers differ); accepted because the threat is
  remembered *answers*, not remembered task numbers.
- Negative: template edits are visible but not forbidden; they invalidate
  deep provenance for prior instances (detected by `--deep`, named in
  `status`), which is the honest trade: evolution over false immutability.
