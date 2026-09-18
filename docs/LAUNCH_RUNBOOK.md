# Gauntlet public proof launch runbook

## Stop conditions

Do not publish any launch post if a box under "Public surface" or "Evidence package" in
[`LAUNCH_READINESS.md`](LAUNCH_READINESS.md) is unchecked. Do not replace an unchecked proof
with a promise that it will arrive later.

## 24 hours before

- [ ] Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and
  `uv run ty check src/` from a clean checkout.
- [ ] Run `uvx --from gauntlet-guard gauntlet demo` from a fresh temporary directory.
- [ ] Open the GitHub README, SVG, case study, and PyPI page in an unauthenticated browser.
- [ ] Verify the visible GitHub default branch, tag, package version, and hero all tell the
  same v0.3.2 story.
- [ ] Re-read every launch link on mobile-width and desktop-width views.

## Launch-hour verification

- [ ] Complete every box in `LAUNCH_READINESS.md` with date, commit, and observed URL.
- [ ] Regenerate the transcript with `uv run python scripts/refresh_demo_transcript.py` and
  confirm `git diff --exit-code -- docs/assets/demo-transcript.txt` exits 0.
- [ ] Verify that the case study names its limits and contains no task or answer text.
- [ ] Confirm the primary post links both the runnable demo and the case study.

## Primary post

- [ ] Lead with the concrete sequence: failed task → feedback persisted → +1.0 score → leak
  caught → fresh holdout collapsed the claim.
- [ ] Attach or embed the canonical cast when available; otherwise link the exact demo command.
- [ ] Link [the self-audit case study](CASE_STUDY.md), not only the repository root.
- [ ] End with one specific invitation: "Run it against the stores your agent can read, and
  report what it finds—including a clean result."

## Show HN post

- [ ] Use this title exactly: **Show HN: I caught my AI agent's benchmark gain coming from its own memory**
- [ ] State that the demo uses scripted agents and real Gauntlet APIs; it is deterministic and
  runs without an LLM.
- [ ] Explain the limits before commenters need to ask: this detects covered persistence leaks;
  it does not replace every evaluator or prove every score is invalid.
- [ ] Invite technical criticism, negative results, and integration reports rather than stars.

## Reply discipline

- [ ] Answer with a concrete mechanism, command, ADR, or case-study evidence before offering
  opinion.
- [ ] Say "I do not know" when a framework has not been tested; do not imply support.
- [ ] Treat reports of clean scans as valuable evidence, not failed marketing.
- [ ] Do not turn a disagreement about scope into a global AI-safety claim or a claim to cover
  every benchmark-contamination route.

## 24-hour review

- [ ] Collect questions people actually repeat and compare them with the intended causal story.
- [ ] Record demo runs, installs, stars/forks, issues, clean scans, leak reports, and substantive
  technical critiques separately.
- [ ] If discussion repeats an incorrect claim, revise the relevant README/copy line before
  amplifying it further.
- [ ] Publish no fabricated success metric or selective screenshot.

## v0.4 follow-up event

- [ ] Do not announce automatic fresh-instance generation before the `holdout` contract, ledger,
  implementation, and tests ship.
- [ ] When shipped, lead with: "A leaked test is dead. Gauntlet retires it and retests the claim
  on a fresh holdout."
- [ ] Re-run the same readiness process against the released version.
