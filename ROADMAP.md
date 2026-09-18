# Roadmap

One protocol, shipped in verifiable increments. Every item below maps to a public issue;
completed items link to the release that closed them.

## Done
- **v0.1** — `guard` + `manifest`: persistence-leak detection with a redaction contract. *(closed)*
- **v0.2** — `run`: opaque single-use slots, sha-verified isolated workspaces,
  environment-drift forensics, tamper-evident seals, blind judge packs. *(issue #1)*
- **v0.3** — `grade`: preregistered verdict engine (keep/revert/provisional, bootstrap CI,
  integrity-first pipeline). *(issue #2)*
- **v0.3.x** — repository conventions: ADRs, security & contributing policy, templates,
  roadmap, badges. *(this file's neighborhood)*

## Next
- **v0.4 — `holdout`** *(issue #3)*: seed → fresh instance generation at eval time (instances
  never persist agent-side), retirement ledger wired to `guard` (leak ⇒ retire ⇒ regenerate
  from unused seed), versioned `HOLDOUT-CONTRACT` between generator / runner / grader.
- **v0.5 — release integrity**: PyPI trusted publishing via GitHub Actions OIDC (no human-
  handled upload tokens, ever again), signed release artifacts, schema freeze candidate for
  `exp.json` / `ledger.jsonl` / verdict.
- **v1.0 — protocol stable**: no breaking changes to ledger/verdict schemas; real-world
  adoption documented; judge-adapter guide (external blind scoring) documented as first-class.

## Non-goals (pinned, to save everyone time)
- Not an agent runner: `run exec` wraps *your* command; we do not grow a model backend.
- Not a leaderboard: verdicts are per-claim; there is no global skill ranking.
- No runtime dependencies, ever: the stdlib bar is a security property (supply chain).
- No version inflation: docs-only changes do not bump the package version.
