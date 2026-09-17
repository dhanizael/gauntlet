# gauntlet

**The anti-cheating layer for evaluating self-improving agents.**

> Your agent has memory now. That makes your agent evaluations quietly lie.

Everyone evaluates their agents, skills, prompts, and AGENTS.md files. Almost nobody
audits **the evaluator itself**. `gauntlet` closes that gap: sealed holdouts generated
from private seeds, a persistence-leak guard that treats your agent's own memory files
as the cheating channel they are, and blind paired-arm verdicts (`keep / revert /
provisional`) with repeated-run statistics — because agents are stochastic and a
single run proves nothing.

## The problem, concretely

You improved a skill. You A/B tested it on your eval tasks. It won. You shipped it.
Two weeks later you find out:

- the eval task text was paraphrased into `LESSONS.md` / `now.md` / a vector store by
  the agent **during** an earlier run — the next runs studied for the test;
- the winning arm won by noise (n=1, no spread reported);
- your `provisional → verified` promotion was decided by vibes, not a gate.

Benchmark contamination literature worries about *pretraining corpora* (n-grams,
MinHash, memorized MMLU). None of it addresses the agent-native leak path:
**persistent memory inside the evaluated system itself.** gauntlet's threat model
starts there.

## Quickstart

```bash
pipx install agent-gauntlet        # or: uv tool install agent-gauntlet

# 1. Register a holdout instance (run this from the PRIVATE side, never in agent context)
gauntlet manifest add ~/.private/eval/manifest.jsonl \
    --instance sched-frostgate-0001 --seed s-77 \
    task-input.txt answer-key.md

# 2. After every eval session: scan the agent's persistent stores for leakage
gauntlet guard scan ~/.private/eval/manifest.jsonl \
    --store ~/agent-workspace/.agent-state/ \
    --store ~/agent-workspace/LESSONS.md \
    --store ~/agent-transcripts/
# findings are reported by hash reference, never by content (see Design principles)
# exit code 1 = leak found → retire the instance, regenerate from an unused seed

# 3. Prove the tool works (synthetic planted leak + skip accounting):
gauntlet guard selftest
```

## We ran our own gauntlet first

The first real scan target was the author's actual agent infrastructure: 12 sealed
task instances (the development pack of a private eval suite), scanned against the
agent's persistent stores — long-term memory file, journal log, working-state
directories, and evaluation run results. 271 files, **3.1 seconds**, zero runtime
dependencies.

```
$ gauntlet guard scan manifest.jsonl --store LESSONS.md --store journal.log ...
[NEAR ] results/…/L5-lens-r1/config.py          :: instance L5 (20/217 shingles, 9.22%)
[NEAR ] results/…/L5-lens-r2/config.py          :: instance L5 (14/217 shingles, 6.45%)
[TRACE] results/…/L5-raw-r1/config.py           :: instance L5 (9/217 shingles, 4.15%)
[TRACE] results/…/L5-*/test_config_loader.py    :: instance L5 (6/217 shingles)  ×3
[TRACE] results/…/L1-raw-r1/count_patterns.py   :: instance L1 (3/133 shingles, 2.26%)

scanned 239 file(s), skipped 32 (17 binary, 15 too-large)
7 finding(s).
```

The result is a perfect demonstration of why this tool exists: the agent's own memory
files were **clean**, but task fixtures persisted verbatim into run-result directories —
real, previously uncounted contamination vectors, exactly the failure mode a sealed
holdout is designed to survive. Severity tracking is calibrated: shared boilerplate
surfaced as `TRACE` (human look), fixture content surfaced as `NEAR` (retire it). A
control scan of unrelated notes returned clean with no false positives, and the
machine-readable report contains **zero task text** — verified by assertion in CI.

## Design principles

1. **The scanner must not leak.** Guard reports file, word-position, match counts and
   *hash references only* — never the matched text. The report is safe to paste into
   an issue even when the task is secret.
2. **Manifests are private keys.** Task content lives only in the manifest file;
   guard consumes it without echoing it. Keep manifests out of any agent-readable
   surface (`chmod 700` the directory).
3. **Deterministic first, judge second.** Hash/shingle evidence outranks any LLM
   opinion; `guard` is fully executable in CI.
4. **Leaks are lifecycle events, not warnings.** Detection → `retire` → regenerate
   from an unused seed. A benchmark instance that leaked once is dead; say so in
   the record.
5. **Verdicts over scores.** `keep / revert / provisional` with ≥N repeated runs and
   reported spread — an improvement that cannot survive the gauntlet is not an
   improvement.

## How detection works

Task content is fingerprinted into 8-word normalized shingles (unicode-folded,
punctuation-free, case-folded → SHA-256 prefixes). A store is scanned in a single
pass; findings are classified:

| severity | trigger | action |
|---|---|---|
| `exact` | normalized task text appears verbatim | retire + regenerate |
| `near`  | ≥5% of task shingles matched (paraphrase, copy-edit) | retire + regenerate |
| `trace` | ≥2 matched shingles, below the near threshold | human review |

Oversize (>8 MiB default, configurable) and binary files are skipped **and reported** —
a guard that silently hides what it didn't scan is the bug we found on day one of
real-world use and refused to keep.

## Status

- `guard` + `manifest`: **shipped (v0.1)** — 12 tests, CI on pytest/ruff/ty, selftest
  in the build pipeline
- `run` (blind paired arms, isolated workspaces, environment drift fingerprinting): next
- `grade` (verdict engine, ≥N repeats + spread, provisional→verified lifecycle): next
- `holdout` (seed generators + retirement ledger, contract spec): next

Built from a battle-tested private protocol: doctrine changes tagged `PROVISIONAL`
until they beat the previous version on repeated, holdout-guarded evals — gauntlet
is that gauntlet, made a tool.

## Development

```bash
uv sync
uv run pytest
uv run ruff check && uv run ruff format --check
uv run ty check src/
uv run gauntlet guard selftest
```

## License

MIT
