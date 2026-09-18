# 0009 — Releases publish via PyPI trusted publishing (OIDC); upload tokens are abolished

- Status: Accepted · 2026-09-18

## Context
Two release tokens passed through a chat log during v0.1-v0.3 (both revoked after use —
the ritual worked, but the class of risk existed). PyPI's trusted publishing binds upload
authority to a specific GitHub Actions workflow identity instead of a bearer secret.

## Decision
`.github/workflows/publish.yml` publishes on version tags, with a hard guard: the tag
must equal `pyproject.toml`'s version. No API token is created, stored, typed, or
transmitted by humans ever again; the publisher config on PyPI names repo + workflow file
(and environment, if set) and nothing else can upload.

## Consequences
- Release authority = code review authority; compromise of a token is no longer a path
  to publishing. Cost: publishing now requires GitHub Actions availability, and a
  mis-named workflow file silently breaks the pipeline — hence the tag-match guard and
  this ADR recording the exact expected identity.
- Discovered during testing: a tag event runs the workflow **as of the tagged commit** —
  a tag older than the workflow file silently never fires. Tags must point at commits
  containing `publish.yml` (v0.3.0 was re-pointed accordingly).
- First live proof: the v0.3.0 re-push (duplicate-version rejection from PyPI = the
  identity handshake worked). Until then the claim is "configured", not "proven" —
  and we say so out loud, because that is the entire product.
