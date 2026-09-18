# Gauntlet launch copy

Use these as evidence-first starting points. Replace only links and release-specific details;
do not add claims that have no executable or documented proof.

## One-sentence social hook

Your AI agent improved 40% overnight. Did it get smarter—or did it just learn the test?

The demo uses scripted agents and real Gauntlet APIs; it is deterministic and runs without an LLM.

## Primary launch post

We ran a simple experiment. An agent failed an eval. Its feedback loop wrote task-derived
information into persistent memory. On the same task, its verdict became `KEEP (+1.0)`.

Then we scanned that memory against a sealed manifest. Gauntlet found the leak without printing
the task text, retired the compromised instance, and ran the same agents against a fresh holdout.
The verdict went back to `PROVISIONAL`.

That +1.0 was memory, not intelligence.

The demo uses scripted agents and real Gauntlet APIs; it is deterministic and runs without an LLM.
Run it: `uvx --from gauntlet-guard gauntlet demo`.

Read the real self-audit, including what it does not prove: `docs/CASE_STUDY.md`.

## Show HN body

I built Gauntlet after finding a blind spot in stateful-agent evaluation: an agent can write task
material into memory, transcripts, or run artifacts, then look much better the next time it sees
the same eval.

The repository includes a deterministic three-act reproduction. A scripted agent first fails,
then gets a `KEEP (+1.0)` after task-derived feedback persists, then loses that apparent gain once
Gauntlet finds the persistence leak and the claim is retested on a fresh holdout.

The demo uses scripted agents and real Gauntlet APIs; it is deterministic and runs without an LLM.

This is not a claim that every agent is intentionally cheating, that every score is invalid, or
that Gauntlet replaces an evaluation framework. It is an integrity layer that checks whether a
covered persistence path turned a repeated test into an open-book exam.

The project is zero-runtime-dependency Python. I would value adversarial feedback, clean scan
reports, negative results, and reports from real harness integrations.

## Reply starters

### Is this intentional cheating?

Not necessarily. The demo's point is that ordinary feedback, transcript, or artifact persistence
can produce a false improvement without intent. The relevant question is whether the score still
holds on a fresh, unexposed task.

The demo uses scripted agents and real Gauntlet APIs; it is deterministic and runs without an LLM.

### How is this different from a benchmark?

A benchmark asks how well an agent performs. Gauntlet checks whether the conditions behind an
improvement claim stayed trustworthy: sealed instances, blind grading, persistence-leak scans,
and retirement of compromised holdouts.

The demo uses scripted agents and real Gauntlet APIs; it is deterministic and runs without an LLM.

### Does it work with my framework?

Gauntlet intentionally does not replace your runner. It wraps a command and scans stores your
agent can read. Named framework support should be treated as unverified until an end-to-end guide
exists; generic shell and CI use are the honest starting point.

The demo uses scripted agents and real Gauntlet APIs; it is deterministic and runs without an LLM.

### What does it miss?

It covers the persistence paths represented by its sealed manifest and scanned stores. It does
not prove that every possible contamination path is absent. A clean scan is evidence about the
surface that was checked, not a blanket security guarantee.

The demo uses scripted agents and real Gauntlet APIs; it is deterministic and runs without an LLM.

### Why not just reset memory?

Resetting memory may remove one channel, but transcripts, result directories, retrieval stores,
and helper artifacts can remain readable. Gauntlet makes those surfaces explicit and treats a
leaked holdout as a lifecycle event rather than a warning to ignore.

The demo uses scripted agents and real Gauntlet APIs; it is deterministic and runs without an LLM.
