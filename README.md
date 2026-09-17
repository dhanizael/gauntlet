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

Benchmark contamination literature worries about *pretraining corpora*. None of it
addresses the agent-native leak path: **persistent memory in the evaluated system
itself.** gauntlet's threat model starts there.

## Quickstart

```bash
pipx install gauntlet        # or: uv tool install gauntlet

# 1. Register a holdout instance (run this from the PRIVATE side, never in agent context)
gauntlet manifest add ~/.private/eval/manifest.jsonl \
    --instance sched-frostgate-0001 --seed s-77 \
    task-input.txt answer-key.md

# 2. After every eval session: scan the agent's persistent stores for leakage
gauntlet guard scan ~/.private/eval/manifest.jsonl \
    --store ~/agent-workspace/.agent-state/ \
    --store ~/agent-workspace/LESSONS.md \
    --store ~/agent-transcripts/
# exit code 1 = leak found → retire the instance, regenerate from an unused seed

# 3. Prove the tool works (synthetic planted leak, three detection checks):
gauntlet guard selftest
```

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

## Severity model

| severity | trigger |
|---|---|
| `exact` | normalized task text appears verbatim in a store |
| `near` | ≥5% of task shingles (8-word fingerprints) matched — paraphrase/copy-paste edits |
| `trace` | ≥2 matched shingles below the near threshold — worth a human look |

## Status

- `guard` + `manifest`: **implemented, tested** (v0.1)
- `run` (blind paired arms, isolated workspaces, environment drift fingerprinting): next
- `grade` (verdict engine, statistics, provisional→verified lifecycle): next
- `holdout` (seed generators + retirement ledger, contract spec): next

Built from a battle-tested private protocol: doctrine changes that were tagged
`PROVISIONAL` until they beat the previous version on repeated, holdout-guarded
evals — gauntlet is that gauntlet, made a tool.

## Development

```bash
uv sync
uv run pytest
uv run ruff check && uv run ruff format --check
uv run ty check src/
```

## License

MIT
