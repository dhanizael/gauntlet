# gauntlet

[![ci](https://github.com/dhanizael/gauntlet/actions/workflows/ci.yml/badge.svg)](https://github.com/dhanizael/gauntlet/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/gauntlet-guard)](https://pypi.org/project/gauntlet-guard/)
[![python](https://img.shields.io/pypi/pyversions/gauntlet-guard)](https://pypi.org/project/gauntlet-guard/)
[![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

repo `dhanizael/gauntlet` · PyPI package **`gauntlet-guard`** · command **`gauntlet`**

The integrity layer for evaluating **stateful** AI agents: sealed holdouts,
persistence-leak guards, and keep/revert verdicts.

**YOUR AI DIDN'T GET SMARTER. IT GOT THE ANSWERS.**

An agent can look dramatically better after it has seen the test. Gauntlet shows
whether that score survives a fresh one — and finds the leak that made it fake.

## Is this your problem?

Gauntlet is for you if **both** of these are true:

- your agent carries state across sessions: a memory file (`LESSONS.md`,
  `MEMORY.md`, `now.md`), saved trajectories, a vector store, or result
  directories a later session can read;
- you evaluate it more than once on the same tasks.

Then memory quietly becomes the open book for the next exam, and your eval
measures memory and capability as one number. It takes one good feature
("learn from feedback") and one reused task set — no malice required:

- `MEMORY.md` / `LESSONS.md` / `now.md` — "what I learned this run" writes, verbatim,
  the task you just evaluated it on;
- saved trajectories & transcripts — the full prompt survives in a log directory the
  next session retrieves from;
- result/eval output directories — fixtures copied into run artifacts stay agent-readable;
- vector stores / retrieval memory — the paraphrase you thought was safe is 6 shingles
  away from a `near` hit;
- generated helper artifacts — the "summary" file that quotes the task to explain it.

**Stateless agent, one-shot evals? You don't need this.** Gauntlet solves a problem
only repeated evaluation of a stateful agent can have — and says so on the box.

## Your machine, in 30 seconds

Zero setup, $0, no LLM. Find the memory surfaces *your* machine would leak through —
names, sizes, dates only; the audit never reads file content. Sample below is real
tool output (paths abbreviated to `~/` for width):

```bash
uvx --from gauntlet-guard gauntlet guard audit
```

```text
gauntlet guard audit — agent memory surfaces (content-free: names, sizes, dates only)
roots: ~/dev
visited 11 entries in 0.0s

memory files (3)
  ~/dev/MEMORY.md                                          37 B  2026-09-18
  ~/dev/Projects/price-bot/.agent-state/now.md             43 B  2026-09-18
  ~/dev/Projects/price-bot/LESSONS.md                      61 B  2026-09-18

agent state dirs (1)
  ~/dev/Projects/price-bot/.agent-state                     -  2026-09-18

transcript/log dirs (1) ... vector stores (1) ...

next steps:
  seal your holdout:   gauntlet manifest add mf.jsonl --instance t-1 --seed s-1 prompt.txt
  scan them for leaks: gauntlet guard scan mf.jsonl --store <path from above>
```

Every line above is a place last month's eval could still be living.

## The failure mode, in 8 seconds

```bash
uvx --from gauntlet-guard gauntlet demo
```

**Eight seconds. $0. No LLM. Deterministic.** The demo makes an agent look
better on the same test, catches the leaked memory, and asks the claim to
survive a fresh holdout.

![A three-act Gauntlet proof: the same-test score reaches KEEP net 1.0; Gauntlet catches an exact leak in LESSONS.md; a fresh test returns provisional net 0.0.](docs/assets/gauntlet-demo.gif)

**[Run the proof](#quickstart)** · **[Read the real self-audit](docs/CASE_STUDY.md)** · **[Inspect the protocol](docs/RUN_PROTOCOL.md)** · **[Use the share card](docs/assets/gauntlet-social-card.png)**

## Why not just keep the test set secret?

Because the test set is not the only copy of the test. A secret holdout protects
against *you* leaking it — it does nothing about the *agent* leaking it into
itself. "Learning from feedback" is a good feature, and it writes last week's
task into next week's open book.

Gauntlet doesn't replace your eval harness; it wraps it: sealed runs, a
content-free memory scan, retirement of any holdout that leaked, and a
retest on a fresh instance — ending in a verdict, not a score.

## The words, in plain language

| word | plain meaning |
|---|---|
| holdout / instance | a task kept out of the agent's reach, registered from a seed |
| manifest | the private key: fingerprints of your holdout tasks (never published) |
| slot | one sealed, single-use trial workspace |
| blindpack | the judge-facing pack — arms renamed to pseudonyms |
| shingle | an 8-word sliding fingerprint used to spot textual overlap |
| verdict | keep / revert / provisional — and it *is* the exit code |

## Quickstart

```bash
pipx install gauntlet-guard        # or: uv tool install gauntlet-guard
uvx --from gauntlet-guard gauntlet guard selftest   # prove the scanner before trusting it

# the loop, end to end:
gauntlet run init exp --tasks tasks.json --arms harness,raw --repeats 3
gauntlet run prep   exp --slot t-xxxxxxxx --fixtures fx/
gauntlet run exec   exp --slot t-xxxxxxxx -- python3 my_agent.py
gauntlet run blindpack exp --out pack              # pseudonyms only; judges see no arms
gauntlet run status exp
gauntlet grade    exp --primary harness --baseline raw
# exit code IS the verdict: 0 keep · 1 revert · 2 provisional · 3 integrity failure
```

What grading actually looks like (real output from
[examples/mini](examples/mini/walkthrough.sh)):

```text
verdict: KEEP  (careful vs quick)
  pairs=8 net=1.0 CI95=[1.0, 1.0] excluded=0.0%
  reason: 95% CI lower bound 1.000 > margin 0.1
```

```bash
# the memory audit: seal the tasks, then catch them if they leak
gauntlet manifest add ~/.private/eval/manifest.jsonl --instance task-0001 --seed s-77 prompt.txt
gauntlet guard scan   ~/.private/eval/manifest.jsonl --store ~/agent/LESSONS.md --store ~/agent/logs/
# findings cite hash references, never content — safe to paste into issues

# a leaked holdout is dead: retire it, then generate a provably-fresh one
gauntlet holdout retire family.json --instance task-0001 --manifest mf.jsonl --private-dir ~/.private/holdout/
gauntlet holdout new    family.json --manifest mf.jsonl --private-dir ~/.private/holdout/
```

### A worked example you can copy

[examples/mini](examples/mini) runs the entire protocol on two toy tasks in
~15 seconds — `bash walkthrough.sh` — and ends by planting a leak in a
`LESSONS.md` and catching it:

```text
verdict: KEEP  (careful vs quick)
  pairs=8 net=1.0 CI95=[1.0, 1.0] excluded=0.0%
grade exit code: 0   (0 keep · 1 revert · 2 provisional · 3 integrity failure)
[EXACT] .../notes/LESSONS.md :: instance mini-A (13/13 shingles, 100.0% overlap, ...)
guard scan exit code: 1   (1 = leakage found -> retire, regenerate)
```

Swap `agent.py` for your real agent; the loop stays identical.

## We scanned ourselves first

The first real target was the author's own agent infrastructure: 12 sealed task
instances against memory files, journals, working-state dirs, and eval results —
271 files, **3.1 seconds**, zero false positives on the control scan. Fixtures
had persisted verbatim into run-result directories: real contamination vectors,
correctly calibrated (`NEAR`/`TRACE`). Full write-up:
[docs/CASE_STUDY.md](docs/CASE_STUDY.md).

## Design principles

1. **The scanner must not leak.** Findings are file, position, counts, hash
   references — never matched text ([ADR-0002](docs/adr/0002-redaction-contract.md)).
   The audit goes further: it never opens a file at all ([ADR-0011](docs/adr/0011-zero-config-surface-audit.md)).
2. **Manifests are private keys.** Task content lives only in the manifest
   ([ADR-0007](docs/adr/0007-private-side-doctrine.md)).
3. **Deterministic first, judge second.** Shingle/hash evidence outranks LLM
   opinion ([ADR-0006](docs/adr/0006-deterministic-first-external-judges.md)).
4. **Leaks are lifecycle events.** Detection → retire → regenerate from an unused
   seed. A holdout that leaked once is dead.
5. **Verdicts over scores.** `provisional` means the claim failed to be proven
   ([ADR-0005](docs/adr/0005-provisional-is-absence-of-proof.md)).
6. **Decisions written before implementation.** Verdict rules frozen in
   [docs/GRADE_DESIGN.md](docs/GRADE_DESIGN.md) before the code existed.

## Status

| module | what it is | state |
|---|---|---|
| `guard` + `manifest` (v0.1) | persistence-leak scanner, content-free reports | shipped |
| `run` (v0.2) | sealed isolated trials: opaque slots, drift forensics, blind packs | shipped |
| `grade` (v0.3) | preregistered verdict engine, bootstrap CI, exit codes as verdicts | shipped |
| `demo` (v0.3.2) | the three-act failure mode, $0, self-asserting in CI | shipped |
| `guard audit` (v0.3.3) | zero-setup memory-surface discovery, content-free | shipped |
| `holdout` (v0.4) | family templates, provably-fresh generation, retirement ledger | shipped |

Built from a private protocol that runs on its own author: doctrine changes stay
`PROVISIONAL` until they beat the previous version on repeated, holdout-guarded evals.

## Written down before it shipped

Decisions precede code and both are public: **[docs/adr/](docs/adr/)** records every
frozen call (12 ADRs), **[ROADMAP.md](ROADMAP.md)** pins non-goals as firmly as
targets, **[SECURITY.md](SECURITY.md)** treats "silent untrustworthiness" as the
vulnerability class, **[CONTRIBUTING.md](CONTRIBUTING.md)** states the gates
honestly, and the [negative-result issue template](.github/ISSUE_TEMPLATE/negative_result.md)
makes publishing a failure as easy as publishing a win.

## Development

```bash
uv sync
uv run pytest                          # 106 tests, incl. the demo's self-assertion
uv run ruff check && uv run ruff format --check
uv run ty check src/
uv run gauntlet demo                   # the story must hold, or CI goes red
```

## License

MIT
