# Security policy

gauntlet is an integrity tool: its failure mode is *silent untrustworthiness*. We treat the
following as **vulnerabilities**, not "bugs":

1. A `guard` report or `grade` verdict can leak graded/secret content (redaction contract broken).
2. `blindpack` artifacts disclose arm assignment or slot identity (blinding broken).
3. `grade` issues a verdict without re-verifying seals (integrity failure bypassed).
4. A forged or malformed ledger record can alter a verdict without detection
   (chain-of-custody / state_of projection broken).
5. Fixture handling follows symlinks or escapes its destination (path traversal).
6. `check_cmd` verifiers can write outside their read-only copy or outlive their timeout.

**Out of scope:** the security of your own agent runtime; the cryptography of manifests
(manifests are private-side secrets by design — filesystem ACLs, `chmod 600`, and
repository hygiene are the control plane).

## Reporting

Use [GitHub private vulnerability reporting](https://github.com/dhanizael/gauntlet/security/advisories/new).
Maintainer acknowledges within 7 days. We publish advisories — and, consistent with this
project's whole reason to exist, **negative results and design mistakes we find ourselves**
(see `docs/adr/` — several record bugs we caught pre-release). No bounty program.
