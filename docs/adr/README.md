# Architecture Decision Records

One decision per file, written **before or with** the code it governs. Status:
Proposed | Accepted | Superseded by NNNN. The ADR is the memory; the CHANGELOG is the movie.

| # | decision | status |
|---|---|---|
| 0001 | Distribution name `gauntlet-guard` (repo/import/CLI stay `gauntlet`) | Accepted |
| 0002 | The scanner must not leak: redaction contract | Accepted |
| 0003 | Drift = environment only; workspace tree is forensics, not drift | Accepted |
| 0004 | Decision rules are preregistered (design doc before engine) | Accepted |
| 0005 | `provisional` = absence of proof; default posture of unproven claims is revert | Accepted |
| 0006 | Deterministic verifiers first; LLM judges only as external blind score files | Accepted |
| 0007 | Manifests are private keys; the private side never enters the repo | Accepted |
| 0008 | Fixed-seed bootstrap: byte-reproducible verdicts over sampling purity | Accepted |
