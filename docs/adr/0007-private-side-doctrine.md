# 0007 — Manifests are private keys; the private side never enters the repository

- Status: Accepted · 2026-09-18 (inherited from geniusmind-eval operations, formalized here)

## Context
Holdout secrecy is the load assumption of the whole protocol. The evaluated agent is an
adversary in the *statistical* sense: it cannot be trusted with the answer key, and
anything agent-readable eventually becomes agent-known. The eval suite this tool came
from had already learned that hashing proves integrity, not secrecy.

## Decision
Task content exists agent-side only as generated instances, ephemeral by policy; the
manifest (`normalized` + shingle fingerprints of task and, optionally, key material),
`unblind.json`, and seeds live outside agent-readable surfaces, are chmod-600'd, and are
never committed or published — including in tests, docs, ADRs, or examples (real content
is always replaced by synthetic fixtures like the `frostgate` selftest).

## Consequences
- Public repo = the contract and the tools; private infra = the actual holdout. Users
  run their own private side (v0.4 automates exactly this half).
- Every doc in this repo is therefore safe to read by an evaluated agent — which is a
  property, not a convention.
