# We ran our own gauntlet first

## The claim we were testing

Gauntlet exists to catch a simple failure mode: an agent's own persistent stores can become
study material for a later evaluation. Before presenting that claim publicly, we scanned the
author's real agent infrastructure.

## What we scanned

The scan used 12 sealed task instances against long-term memory files, journal logs,
working-state directories, and evaluation-result directories. It scanned 271 files in 3.1 seconds
with zero runtime dependencies.

## What we found

The long-term memory files were clean. The unexpected contamination route was the evaluation
result directory: task fixtures had persisted there verbatim. That is enough to contaminate a
future run if the agent can read those artifacts.

Gauntlet classified fixture content as `NEAR` and shared boilerplate as `TRACE`, leaving the
decision visible rather than silently treating every overlap as the same risk.

## Why the finding mattered

The discovery was not an agent intentionally gaming a test. It was ordinary infrastructure
preserving useful run artifacts. That is exactly why it matters: a good memory or logging
feature can turn a repeated test into an open-book exam without anyone noticing.

## Control scan and redaction check

A control scan of unrelated notes produced **zero false positives**. The machine-readable
report was also checked to contain **zero task text**. Findings cite file locations, counts,
and hash references—not the matched prompt or answer—so the evidence can be discussed without
publishing a private evaluation.

## What this does not prove

This was one real-world audit, not a prevalence study of every agent, framework, or benchmark.
It does not prove that every score gain is contaminated, nor that this scanner covers every
possible route by which an agent could learn a task. It proves that this route existed in a
real system, was previously uncounted, and could be detected without exposing the task.

## Reproduce the pattern safely

Start with the deterministic public proof:

```bash
uvx --from gauntlet-guard gauntlet demo
```

Then register only private holdout material and scan the persistent stores your agent can read.
The [README](../README.md) includes the minimal manifest and guard commands.
