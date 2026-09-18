# v0.3 DESIGN — `gauntlet grade`: the verdict engine

**Pre-registered 2026-09-18, BEFORE implementation.** Criteria below are frozen;
code that deviates is a bug, not a discovery. This document IS the product.

## What grade decides

One question only: does arm `primary` (e.g. `harness`) **prove** it beats arm
`baseline` (e.g. `raw`) on the same tasks? Verdicts: `keep | revert | provisional`.
`provisional` is not a third place — it is the absence of proof, and it means
"revert next time, collect more evidence". Silence is loss.

## Evidence pipeline (fixed order, fail-fast)

1. **Chain of custody** — grade pins `sha256(ledger)` into its own output; a
   verdict is only valid for that ledger state.
2. **Seal re-verification** — every trial is `run verify`-checked first. Any
   violation ⇒ `exit 3 (integrity failure)`, no verdict produced. A tampered
   trial is worse than a lost trial: it poisons the whole claim.
3. **Drift quarantine** — `sealed-drift` trials are EXCLUDED from scoring but
   always listed in the report. Exclusions > `--max-excluded-pct` (default 25%)
   ⇒ forced `provisional` with reason `evidence corrupted`.
4. **Deterministic grading before judgment** — verifier types:
   - `expect_file {path, equals | regex}` on a sealed-output copy (temp dir,
     never the original workspace — evidence is read-only by construction);
   - `check_cmd {argv, timeout}` run in the copy, exit 0 = pass;
   - `judge` — score supplied externally via `--judge-scores FILE` (blindpack
     `pseud -> score`); grade merges, never invents. Missing score ⇒ task
     quarantined like drift.
5. **Scoring** — per task, every `primary × baseline` trial pair is one
   observation: `+1` primary's verifier score higher, `-1` baseline higher,
   `0` equal (judge scores break pass-vs-pass ties, then stop at ties — a
   tie contributes nothing to the claim).
6. **Statistics** — net win-rate = mean over paired signs; confidence interval =
   **percentile bootstrap**, `B=10_000` draws, fixed `seed=20260918` (byte-
   identical reruns are a feature, not a courtesy), `alpha=0.05`.

## Decision rule (frozen)

Let `lo`, `hi` = 95% CI of net win-rate, `margin` δ (default `0.10`):

| condition | verdict | exit |
|---|---|---|
| `lo > δ` | **keep** | 0 |
| `hi < -δ` | **revert** | 1 |
| otherwise | **provisional** | 2 |
| integrity failure / corrupted evidence | *(no verdict)* | 3 |

`--require-every-task`: keep additionally demands per-task net > 0 for EVERY
task — the conservative gate for doctrine changes (one-task heroics are noise).

## Redaction contract

The verdict JSON has two faces: default (private, human details) and
`--public` (shareable): verifier identities, pass/fail bits, counts, hashes —
expected values, prompts, and stderr tails appear ONLY in the private face.
Same scanner principle as v0.1: a report must never leak what it grades.

## Anti-patterns this design explicitly rejects

- LLM-judge-before-deterministic (judge scores semantic residue only).
- Mean-without-spread (n=1 folklore).
- Silent exclusion (every dropped trial is named in the report).
- Post-hoc margins (δ is in the frozen section above, not tuned after seeing CI).
- Verdicts over unverified seals (exit 3 exists; use it).

## Test commitments (each maps to a mechanism above)

T1 determinism: grade twice ⇒ byte-identical JSON · T2 6-0 keep (CI clear of δ)
· T3 3-3 ⇒ provisional · T4 drift excluded + listed · T5 exclusion >25% ⇒
corrupted · T6 seal violation ⇒ exit 3, no verdict · T7 require-every-task
blocks 5-win-1-loss hero · T8 judge-scores break pass/pass ties · T9 public
face redacts expected values · T10 exit codes exhaustive · T11 CI over fixed
seed is reproducible across runs and versions (run under 3.11 AND 3.13).
