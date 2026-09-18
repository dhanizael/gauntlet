# 0006 — Deterministic verifiers first; LLM judges enter only as external blind score files

- Status: Accepted · 2026-09-18

## Context
judge-before-verifier is the standard industry shape (cheap and overtrusted). This tool
exists because measurement instruments are unsound. Also: embedding judge APIs would add
runtime deps and silent nondeterminism to a reproducibility tool.

## Decision
`expect_file`/`check_cmd` run first and their output is the score when present. A
verifier of type `judge` is legal **only** with a score supplied by the user through
`--judge-scores <pseud→score>.json`, produced outside gauntlet against blindpack artifacts
(pseudonyms ⇒ the judge can see no arms/slots). Deterministic output precedes opinion
wherever both exist. Missing judge score quarantines the trial — never silently defaults.

## Consequences
- Zero dependencies holds; judge choice is the user's honest responsibility.
- Cost: no batteries-included judge. Roadmap v1.0 ships an adapter guide instead of
  an adapter with our trust baked in.
