# Changelog

## v0.4.0 — 2026-09-18

`gauntlet holdout` — regeneration becomes a proof, not a hope.

- **Family templates** (private-side JSON): typed slots (`int`, `int_list`,
  `choice`, `permutation`), `{{ name }}` rendering, optional `answer_cmd`
  that derives the verifier's expected value from the slot values (runs with
  cwd = the family dir; relative scripts are validated to exist). Instance
  dirs carry `prompt.txt`, `fixtures/`, and a ready-to-feed `task.json`.
- **Version-stable PRNG**: counter-mode SHA-256 with rejection sampling.
  stdlib `random` is NOT stable across Python versions — byte-drift would
  silently rot provenance. A golden-hash test pins one family+seed digest;
  the CI matrix (3.11 + 3.13) proves it byte-identical.
- **Dual freshness gate**: exact slot-digest collision intra-family
  (same-family instances share boilerplate by design — text distance would
  lie there), ≥2-shingle overlap cross-family against the manifest. Skipped
  counters are recorded honestly; exhaustion exits 1 with the budget named.
- **Retirement ledger**: append-only, hash-chained JSONL, 0600, private
  side. `retire` writes the manifest first (guard reads the manifest — stop
  the bleed), ledger second; a crash between the two writes is a named
  divergence, not a silent one. `verify --deep` re-derives every instance
  from template + seed and proves content hashes still match. A hash chain
  cannot see its own tail — deep verification exists precisely for that.
- **Content-free ledger**: hashes and ids only — a leaked ledger leaks
  nothing (redaction contract, ADR-0002).
- Design pre-registered in `docs/HOLDOUT_DESIGN.md` + [ADR-0012](docs/adr/0012-holdout-families.md)
  BEFORE code; hardening fixes from a fresh-eyes review landed before release (validation on every operation, seq-stamped ledger, exclusive operation lock, full-digest content hashing, 2^63 slot-range cap, budget counts skips only). 106 tests (34 new).

## v0.3.3 — 2026-09-18

`guard audit` — the zero-setup hook — and a README that answers "is this my
problem?" before asking for install.

- `gauntlet guard audit [roots...]` walks the machine (default: home; caps:
  depth 6, 250k entries, 20 s — reported honestly when truncated) and reports
  agent memory surfaces: memory files, agent state dirs, transcript/log dirs,
  vector stores. Content-free by construction: **it never opens a file** —
  names, sizes, dates only (extends ADR-0002; recorded in ADR-0011).
- Discovery is name-based and heuristic: it finds the surfaces to scan, not
  the leaks. Exit code is always 0 — an audit is information, not a verdict.
  The report funnels into the existing protocol: `manifest add` → `guard scan`.
- Dogfooding on a real home directory: 98k entries in 2.3 s. Package-manager
  and plugin caches (which ship bundled `AGENTS.md` docs) are skipped as noise.
- README rebuilt around the first-time visitor: a problem-fit checklist with
  an honest disqualifier ("stateless agent, one-shot evals? you don't need
  this"), the 30-second machine audit as the hook, "why not just keep the
  test set secret?", a plain-language glossary, real captured output for the
  grade verdict (the audit sample is the same output with paths abbreviated),
  and a copy-paste end-to-end example (`examples/mini/walkthrough.sh`, ~15 s,
  $0, no LLM).
- 69 tests (15 new for audit: content-never-read pinned mechanically,
  caps as truncation, symlink cycles, missing roots surfaced, deterministic
  ordering, no false positives on plain DBs, CLI wiring).

## v0.3.2 — 2026-09-18

`gauntlet demo` — the failure mode, made impossible to miss.

- Three acts, ten seconds, $0, deterministic: an agent "improves" by +1.0 by
  writing the task into its own memory; guard catches the EXACT contamination
  (content-free report), the instance retires, a fresh holdout collapses the
  verdict back to provisional. Scripted agents exercise the real public API.
- The demo asserts its own narrative and runs in CI: if any act deviates,
  the release goes red. (ADR-0010)
- README rebuilt around the demo: hero question, before/after diagram,
  "How an agent can accidentally cheat your eval" (5 concrete paths).
- First release published through **trusted publishing** (OIDC, no token):
  the pipeline proven in v0.3.0's duplicate-rejection test now ships for real.

## v0.3.0 — 2026-09-18

The verdict engine: `gauntlet grade` — **the full loop now closes.**

- Design pre-registered in `docs/GRADE_DESIGN.md` BEFORE code; the engine
  implements that document literally (pipeline order, frozen decision rule,
  redaction contract, and test commitments T1-T11 each have named tests).
- Pipeline: ledger chain-of-custody hash -> seal re-verification (violations
  abort the verdict, exit 3) -> drift quarantine (exclusions >25% => corrupted
  evidence, no claim) -> deterministic verifiers (`expect_file`, `check_cmd`
  run against a read-only copy of the sealed outputs; `judge` scores merged
  only from an external blind file) -> paired signs -> percentile bootstrap
  (B=10_000, fixed seed: byte-identical reruns) -> `keep|revert|provisional`.
- `provisional` means *absence of proof*, not a third outcome: default posture
  of any claim that cannot clear its margin is revert.
- `--require-every-task`: conservative gate for doctrine changes — one
  heroic task cannot carry an average; missing evidence counts as no-win.
- `--public` face: verdicts are shareable — identities, counts, hashes only;
  expected values never serialize (private face already carries no details).
- Exit codes are the verdict: 0 keep / 1 revert / 2 provisional / 3 integrity.
- Found and fixed en route: `state_of` KeyError on slot-less ledger records
  (blindpack entries) — caught by T8 before any release, as designed.
- 39 tests; gates verified on true 3.11 and 3.13 venvs, exit codes unchecked
  by pipes.

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
