# 0004 — Decision rules are written down before the code that applies them

- Status: Accepted · 2026-09-18

## Context
The failure mode of evaluation everywhere: run the experiment, stare at the numbers,
invent the threshold that reads well afterward. Our own doctrine governance already
required "criteria lolos ditetapkan sebelum eksperimen". `grade` is where that becomes
product: `docs/GRADE_DESIGN.md` froze pipeline order, margin δ=0.10, bootstrap B/seed,
exit-code semantics, and tests T1–T11 **before the engine had a single line**.

## Decision
Any change to a decision rule (rule, threshold, statistic, redaction, wire format)
requires an ADR first or with the code. The engine implements the design document
literally; divergence is classified as a bug, not a finding.

## Consequences
- Verdicts are pre-registered claims — auditable and non-p-hackable by construction.
- Cost: contribution velocity drops for anyone not reading the docs. Intended.
- The design doc doubles as the spec for T1–T11; "tested before implemented" is now
  a property of our history, not a claim about it.
