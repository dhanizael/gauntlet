# The gauntlet run protocol

`gauntlet run` is a **trial coordinator**, not an agent runner: it prepares
isolated workspaces, wraps any command you point at them, and seals the result
with an environment-drift check. Your harness (`claude -p`, a script, a docker
run, `python agent.py`) is just the command between `prep` and `close`.

## Lifecycle

```
run init      tasks x arms x repeats -> opaque slot ids (assignment hidden)
   |
run prep      fresh workspace, task/prompt.txt (+ fixtures, sha-verified,
   |          symlinks refused), environment fingerprint #1
run exec      your agent command, cwd = workspace, exit+duration captured
   |          (or drive manually: run close when your harness is done)
run close     environment fingerprint #2 -> DRIFT diff (python/packages),
   |          outputs manifest (path, size, sha256) = the seal
run verify    recompute seal -> detects post-close edits (tamper evidence)
run status    per-slot state; arm names hidden unless --reveal
run blindpack judge-facing pack: pseudonym -> outputs, shuffled jobs.json;
              the unblind map (pseud -> slot/arm) is written only into the
              experiment dir, chmod 600
```

## What each mechanism defends against

| mechanism | failure mode it kills | proven by |
|---|---|---|
| opaque slots | arm identity leaking into paths/grades | `test_blindpack_hides_arms_and_slots` |
| copy-verify fixtures | hardlink "copies" that corrupt siblings (2026-09-15 incident) | `test_prep_verifies_fixture_shas` |
| symlink refusal | fixture trees smuggling reads of /etc/passwd | `test_prep_rejects_symlink_fixtures` |
| env fingerprint | mid-experiment pip installs invalidating later arms (drift incident) | `test_exec_seals_outputs_with_exit` + envfp unit diffs |
| seal + verify | quiet post-run edits of trial outputs | `test_verify_detects_post_close_edit` |
| blindpack | judge bias from arm names in artifacts | `test_blindpack_hides_arms_and_slots` |

Deliberate scope boundary: `run` records and proves. The *verdict* (win-rate,
keep/revert) is `grade` (v0.3) — deterministic checks first, blinded LLM judge
second, with >=N repeats and spread, consuming `jobs.json` + `unblind.json`.

## Transcript (real, generated 2026-09-18, `gauntlet` 0.2.0)

```
$ gauntlet run init exp --tasks tasks.json --arms harness,raw --repeats 1
experiment exp-874b0a85: 4 trials (2 tasks x 2 arms x 1 repeats) -> exp

$ gauntlet run prep exp --slot t-95fc1114 --fixtures fx
prepared t-95fc1114 (task count) -> exp/trials/t-95fc1114

$ gauntlet run exec exp --slot t-95fc1114 -- python3 -c '<agent>'
closed t-95fc1114: exit=0 clean (1 files sealed, 0.014s)

$ gauntlet run status exp
t-95fc1114   count        sealed         exit=0 files=1
t-84bea411   median       sealed         exit=0 files=1
t-9c30a02c   median       sealed         exit=0 files=1
t-4bf763b5   count        sealed         exit=0 files=1

$ gauntlet run verify exp --slot t-95fc1114
t-95fc1114: seal intact

$ gauntlet run blindpack exp --out pack
packed 4 trial(s) -> pack
unblind map (PRIVATE): exp/unblind.json

$ ls pack/outputs
s-3d1656da2a  s-6dd7c682b9  s-a4c4e9d7a6  s-ef74ae5f12
# jobs.json keys: pseud, task, status — no arm, anywhere.
```

Close the loop with `guard`: after an experiment, scan your agent's real
memory stores with the task manifest — a trial workspace that leaks task
text into `LESSONS.md` is the contamination this protocol was built to catch.
