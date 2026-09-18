# examples/mini — the whole loop, ~15 seconds, $0, no LLM

```bash
bash walkthrough.sh
```

Two arms — `quick` (a buggy method) and `careful` (the right one) — run
through the full protocol: sealed trials, blind pack, preregistered verdict.
Then the toy tasks are sealed into a manifest and "caught" leaking out of an
agent's `LESSONS.md`, the way real agent memory leaks real eval tasks.

What you should see: `verdict: KEEP`, `grade exit code: 0`, and guard finding
the planted leak (`[EXACT] ... mini-A`). Swap `agent.py` for your real agent
and the same loop measures it.
