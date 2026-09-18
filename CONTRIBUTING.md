# Contributing

gauntlet's engineering culture in one line: **decisions are written down before they are
implemented, and gates report honest exit codes.**

## Setup

```bash
uv sync
uv run pytest            # 39+ tests
uv run ruff check .      # lint (select = ALL, curated ignores documented in pyproject)
uv run ty check src/     # typecheck
uv run gauntlet guard selftest   # end-to-end proof must pass
```

## The gates (Definition of Done)

- All of the above exit 0 — and a CI/merge is only trusted from **unmasked** exit codes
  (a pipe to `tail`/`grep` reports the pipe's exit code, not the command's; we have been
  bitten three times and it is now written into `ci.yml`'s step list implicitly).
- Behavior runs on **both 3.11 and 3.13** (CI matrix). Local passing is not passing
  until both venvs agree — argparse's `--` taught us this the hard way.
- New statistical or protocol behavior ⇒ a test whose name cites its commitment
  (`T<n>` in `docs/GRADE_DESIGN.md`).

## When to write an ADR first (`docs/adr/`)

Any change to: decision rules, thresholds/margins, statistical method, redaction
contract, ledger/manifest wire format, or "what counts as drift". Copy
`docs/adr/0000-template.md`, one PR with the ADR merged before or with the code.

## Style

Python stdlib only (no runtime dependencies is a product property, not an aesthetic).
Smallest change that fully solves; no speculative hooks. `provisional` also applies to
features: unproven features don't ship as defaults.

## What to open first

- Feature ideas ⇒ issue (the *negative-result* template is welcome and never mocked).
- Vulnerabilities ⇒ SECURITY.md, never a public issue.
