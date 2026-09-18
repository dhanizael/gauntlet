# 0001 — Distribution name is `gauntlet-guard`; everything else is `gauntlet`

- Status: Accepted · 2026-09-18

## Context
The product is "gauntlet". PyPI `gauntlet` is squatted by a placeholder; our planned
`agent-gauntlet` was rejected at upload: PEP-503 normalization makes it identical to
**live unrelated project `agentgauntlet`** (chaos engineering for LLM agents) — PyPI's
similarity guard refused it with HTTP 400 even though the literal name 404'd.

## Decision
Publish as `gauntlet-guard` (pip/pipx/uvx name only). Repository, Python package,
import path, CLI binary, and all documentation keep the name **gauntlet**.

## Consequences
- Two names forever coexist; README/CHANGELOG state the mapping at every first mention.
- "one-command install" marketing line stays true (`pipx install gauntlet-guard`).
- Accepted trade-off: brand friction < blocked release; renaming the product was not on the table.
