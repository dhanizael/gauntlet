# v0.4 DESIGN — `gauntlet holdout`: fresh-instance generation + retirement ledger

**Pre-registered 2026-09-18, BEFORE implementation.** Criteria below are frozen;
code that deviates is a bug, not a discovery. This document IS the product.
(Precedent: GRADE_DESIGN.md, ADR-0004, ADR-0008.)

## The one question holdout answers

After a holdout leaks, "regenerate" must mean **provably fresh** — not
"hope the new one is different". Every generated instance carries its
provenance; every dead seed stays dead, and the tool can *prove* both.

## Family templates (the only way instances come into existence)

A family is a private-side JSON file (`schema 1`):

```json
{
  "schema": 1,
  "id": "frostgate",
  "prompt": "Task frostgate-{{ tag }}: read task/fixtures/nums.txt and write the SUM OF SQUARES OF THE EVEN numbers in it to result.txt.",
  "slots": {
    "tag":  {"kind": "permutation", "of": ["A", "B", "C", "D"]},
    "nums": {"kind": "int_list", "count": 4, "min": 1, "max": 15}
  },
  "fixtures": {"nums.txt": "{{ nums }}"},
  "answer_cmd": ["python3", "answer.py"],
  "verifier": {"type": "expect_file", "path": "result.txt"}
}
```

- **Slot kinds (frozen for v0.4):** `int {min,max}`, `int_list {count,min,max,sep=" "}`,
  `choice {of}`, `permutation {of}`. Nothing else — YAGNI is a security feature here:
  every kind is auditable for cardinality and determinism.
- **Rendering:** `{{ name }}` substitution only (regex `\{\{\s*(\w+)\s*\}\}`);
  `int_list`/`permutation` render sep-joined. No filters, no logic — templates that
  need logic need a new ADR.
- **`answer_cmd`** (optional): argv; receives the slot values as JSON on stdin; its
  stripped stdout becomes the `equals` of the task's `expect_file` verifier. Requires
  `verifier.type == "expect_file"`. Without it, the verifier must be complete as
  declared (or judged externally, v0.3 style).
- **Templates may be public; seeds may not.** The instance is `f(family, seed)`;
  leaking the shape leaks nothing. A small family is still enumerable — hence
  cardinality accounting (below).

## Seeds and the version-stable PRNG

- Seed string = `"<family_id>:<n>"`, `n` a 0-based counter from the ledger. Every
  `new` consumes the next counter; consumed is consumed forever (the ledger records
  it). `--seed` overrides for exact reproduction (ADR-0008 culture) and refuses a
  seed string the ledger has already consumed.
- **No stdlib `random` anywhere in generation.** `random.Random` is not guaranteed
  stable across Python versions — a byte-drift between 3.11 and 3.13 would silently
  break reproduction (provenance rot). The PRNG is ~15 lines of counter-mode SHA-256:
  `block_i = sha256(key + ":" + i)`, uniform ints via rejection sampling. Stable
  across versions and platforms, forever.

## The freshness gate (dual, because one gate would lie)

Same-family instances share boilerplate BY DESIGN — full-text shingle distance
would fire on every generation. Two gates instead:

1. **Intra-family (slot space):** `slot_sha256 = sha256(canonical slot JSON)`.
   Exact match against any prior `generated` entry ⇒ collision ⇒ the counter is
   consumed and honestly recorded as a `skipped` entry, next counter is tried.
   Partial numeric proximity ("8" vs "9") is explicitly out of scope: the *answer*
   differs, so remembered values don't transfer.
2. **Cross-family (shingles):** the generated prompt's shingles vs every manifest
   instance of another family (attribution by seed prefix). ≥ 2 matched shingles
   (guard's `trace` threshold) ⇒ collision ⇒ skipped, same accounting.

Attempt budget: `10 * count + 10` skipped counters, then exit 1 — exhaustion is
reported, never papered over with silence.

## The retirement ledger (append-only, hash-chained, private)

JSONL per family (default `<private_dir>/<family_id>.ledger.jsonl`, chmod 0600),
one entry type per line, each carrying `"prev": sha256(previous line)` (genesis:
64 zeros):

- `generated {seq, seed, instance, template_sha256, content_sha256, slot_sha256, at, prev}`
- `skipped  {seq, seed, reason, at, prev}` — a consumed counter that produced nothing
- `retired   {seq, instance, reason, at, prev}`

`content_sha256` = sha256 over the sorted file list (`rel:file_sha` lines) of the
instance directory (prompt + fixtures — fixtures leak too, so they are registered
in the manifest as well). The manifest stays the leak-detection key (v0.1 design);
the ledger is the *provenance and death record*.

**Retire order is frozen:** manifest first (guard reads the manifest — stop the
bleed immediately), ledger second. A crash between the two writes is a real state,
not a bug: `verify` names it from either side.

## `holdout verify` — the trust anchor

1. Re-walk the hash chain; a broken link names the offending `seq`, exit 1.
2. Cross-check manifest ↔ ledger: retired-in-ledger ⇒ retired-in-manifest;
   retired-in-manifest (this family's seed prefix) ⇒ retired-in-ledger. Either
   divergence, exit 1, both sides listed.
3. `--deep`: re-derive every `generated` entry from the on-disk template + seed:
   `template_sha256` must match (else "template changed") and `content_sha256`
   must match (else "instance drifted"). Deterministic-first makes full
   reproduction a property, not a hope (ADR-0006, ADR-0008).

`holdout new` runs the cheap verify (chain + cross-check) before generating:
nothing is ever built on top of a tampered or diverged ledger.

## Cardinality accounting

Cardinality = product of slot spaces (`int`: range size; `int_list`: range^count;
`choice`: len; `permutation`: n!). Shown in `status` (capped display "≥ 10^12").
Below 10,000 ⇒ warning: **an agent can enumerate this family** — the freshness
gate is not a substitute for entropy.

## CLI surface and exit codes

```
gauntlet holdout new    <family.json> --manifest M --private-dir D [--count N] [--seed S] [--ledger L]
gauntlet holdout retire <family.json> --instance ID
gauntlet holdout status <family.json>
gauntlet holdout verify <family.json> [--deep]
```

Exit codes: `0` ok · `1` gate exhausted / verify failure · `2` usage/validation
(any validation failure happens before anything is written).

## Redaction contract

The ledger contains hashes and ids, never slot values or prompt text — a leaked
ledger leaks nothing. Manifest entries already carry normalized text by v0.1
design and stay private-side (ADR-0007). The family file is a private key:
losing it makes remaining counters ungeneratable (backup warning in `new`).

## Anti-patterns this design explicitly rejects

- LLM-generated holdouts (nondeterminism in the secret side; ADR-0006).
- `random.Random` (version drift = provenance rot).
- Seed reuse after retirement (fake freshness — the failure mode, as a feature).
- Full-text shingle gate *within* a family (boilerplate false positives).
- Silent skips (every consumed counter is a ledger line).
- Unversioned template edits (template hash is provenance; changes are visible).
- Rewriting the ledger (append-only; correction happens by new entries).

## Test commitments (each maps to a mechanism above)

T1 determinism: same family+seed twice ⇒ byte-identical artifacts · T2 golden
hash pinned in the test, proven byte-identical under BOTH CI Pythons (3.11/3.13)
· T3 every slot kind renders in-range · T4 PRNG `below` is unbiased-enough (full
coverage of small ranges, no modulo-bias outliers) · T5 seed consumption: two
`new` ⇒ counters 0,1, chained entries · T6 slot collision ⇒ `skipped` entries,
honest accounting, exhaustion ⇒ exit 1 · T7 retired seed refused on `--seed`;
retired slot values can never be regenerated · T8 chain tamper ⇒ verify exit 1
naming seq · T9 manifest↔ledger divergence both directions ⇒ exit 1 · T10
`--deep`: template change detected; restore ⇒ hash matches again · T11
cross-family overlap ⇒ skipped · T12 ledger contains no prompt substring ·
T13 cardinality warning + cap · T14 validation failures write nothing · T15
exit codes exhaustive through `main()`.
