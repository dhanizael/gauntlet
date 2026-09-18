## Change
<!-- what & why; link the issue/ADR -->

## Gates (all unchecked = red; CI cannot accept a masked run)
- [ ] `uv run pytest` — 0 exit, unmasked
- [ ] `uv run ruff check .` + `uv run ruff format --check .`
- [ ] `uv run ty check src/`
- [ ] `uv run gauntlet guard selftest`
- [ ] behavior verified on **3.11 AND 3.13** (true venvs, not a masked `--no-sync`)
- [ ] touching decision rules/stats/redaction/wire format ⇒ ADR included or already merged
- [ ] docs-only ⇒ version NOT bumped (no inflation); code change ⇒ CHANGELOG entry
