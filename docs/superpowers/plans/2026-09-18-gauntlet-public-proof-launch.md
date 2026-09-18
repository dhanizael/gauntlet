# Gauntlet Public Proof Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Gauntlet's real three-act demo into a high-trust public proof experience that broad audiences can understand and builders can reproduce.

**Architecture:** Keep GitHub and PyPI as the only launch surfaces in phase one. A small, versioned asset set—an executable demo transcript, an accessible SVG causal loop, and a dogfood case study—feeds a reordered README and evidence-first distribution copy. Product behavior is not broadened for marketing; the current CLI remains the source of truth.

**Tech Stack:** Python 3.11+, existing `pytest`/`ruff`/`ty` gates, Markdown, hand-authored SVG, GitHub Actions, PyPI.

**Spec:** `docs/superpowers/specs/2026-09-18-gauntlet-launch-design.md`

## Global Constraints

- Preserve the no-runtime-dependencies rule from `ROADMAP.md`.
- Every public claim must be derived from executable output, a checked-in source, or a named external reference.
- Do not claim Gauntlet detects every possible contamination route, replaces all evaluators, or guarantees agent safety.
- Use the public phrase "did it get smarter—or did it learn the test?" and retain precise technical language beneath it.
- Never expose task, fixture, answer, or matched content in demo, diagram, screenshots, case study, or reports.
- Do not add a website, dashboard, telemetry, analytics, or named framework integration in this phase.
- Keep the current three-act demo as the canonical public proof; visual assets must be regenerated from or exactly match it.
- Every task must pass `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run ty check src/` before its commit.

---

### Task 1: Verify public-surface integrity before publishing any asset

**Files:**
- Create: `docs/LAUNCH_READINESS.md`
- Modify: no source files
- Test: manual unauthenticated browser and command-line checks recorded in the readiness document

**Interfaces:**
- Consumes: repository URL from `pyproject.toml`, package URL from `pyproject.toml`, latest tag `v0.3.2`.
- Produces: an auditable launch-readiness checklist that later launch tasks must link from.

- [ ] **Step 1: Write the failing readiness checklist**

Create `docs/LAUNCH_READINESS.md` with every item initially unchecked:

```markdown
# Launch readiness

## Public surface

- [ ] An unauthenticated visit to `https://github.com/dhanizael/gauntlet` shows the v0.3.2 README.
- [ ] The visible README includes `gauntlet demo`, `run`, and `grade` as shipped.
- [ ] The GitHub default branch resolves to the commit intended for launch.
- [ ] `https://pypi.org/project/gauntlet-guard/` renders the same hero and current package version.
- [ ] `uvx --from gauntlet-guard gauntlet demo` succeeds from a clean temporary environment.

## Evidence package

- [ ] The cast transcript matches `uv run gauntlet demo`.
- [ ] README diagram text matches the demo's causal story.
- [ ] Case-study metrics cite checked-in evidence and disclose limits.
```

- [ ] **Step 2: Establish the current public-state mismatch**

Run from the repository root:

```bash
git ls-remote --symref origin HEAD
git ls-remote --heads origin main master
git log --oneline --decorate -3
```

Open GitHub in an unauthenticated session and record the visible branch, README status table, and latest commit. Do not check any public-surface boxes until the result agrees with local `main` and tag `v0.3.2`.

- [ ] **Step 3: Correct GitHub repository settings and remote branch relationship**

In GitHub repository settings, make `main` the default branch if it is not already. Ensure the public page resolves to commit `256fc93` or its descendant. Do not delete `master` in this task; preserve it until the public page and clone behavior are verified.

Update the local upstream to follow the intended default only after GitHub is correct:

```bash
git branch --set-upstream-to=origin/main main
git fetch origin
git status --branch --short
```

- [ ] **Step 4: Verify the clean-install proof**

Run:

```bash
TASK_TMPDIR=$(mktemp -d)
uvx --from gauntlet-guard gauntlet demo > "$TASK_TMPDIR/demo.txt"
rg -n "ACT 1|ACT 2|ACT 3|memory, not intelligence" "$TASK_TMPDIR/demo.txt"
```

Expected: exit status 0; all four patterns appear. Remove only the explicitly created temporary directory after inspecting it.

- [ ] **Step 5: Mark only verified boxes and record evidence**

For each passing check, add the date, current commit/tag, and a concise observation below the checklist. If a check fails, record the observed state and leave its box unchecked; do not rewrite the requirement to make it pass.

- [ ] **Step 6: Run documentation quality gates**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check src/
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 7: Commit the readiness gate**

```bash
git add docs/LAUNCH_READINESS.md
git commit -m "docs: add public launch readiness gate"
```

### Task 2: Make the canonical demo output consumable as a versioned public artifact

**Files:**
- Create: `docs/assets/demo-transcript.txt`
- Create: `scripts/refresh_demo_transcript.py`
- Modify: `tests/test_demo.py`
- Modify: `.github/workflows/ci.yml`
- Test: `tests/test_demo.py`

**Interfaces:**
- Consumes: `gauntlet.demo.run_demo() -> int` in `src/gauntlet/demo.py`.
- Produces: `docs/assets/demo-transcript.txt`, byte-for-byte generated by `scripts/refresh_demo_transcript.py`; CI rejects a stale transcript.

- [ ] **Step 1: Write the failing transcript freshness test**

Add to `tests/test_demo.py`:

```python
from pathlib import Path

from gauntlet.demo import render_demo


def test_checked_in_demo_transcript_is_current():
    transcript = Path("docs/assets/demo-transcript.txt").read_text()
    assert transcript == render_demo()
```

Expected initial failure: `ImportError` because `render_demo` does not exist.

- [ ] **Step 2: Run the focused test to verify failure**

Run:

```bash
uv run pytest tests/test_demo.py::test_checked_in_demo_transcript_is_current -v
```

Expected: FAIL with an import error for `render_demo`.

- [ ] **Step 3: Refactor demo rendering without changing CLI behavior**

In `src/gauntlet/demo.py`, introduce:

```python
def render_demo() -> str:
    """Run the self-asserting demo and return its complete public transcript."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        assert run_demo() == 0
    return buffer.getvalue()
```

Import `io` and `redirect_stdout`. Keep `run_demo()` as the CLI implementation and do not make it call `render_demo()`; that would recurse. This makes the checked-in public artifact derive from the same executable path used by users.

- [ ] **Step 4: Add the deterministic refresh script**

Create `scripts/refresh_demo_transcript.py`:

```python
from pathlib import Path

from gauntlet.demo import render_demo


def main() -> None:
    Path("docs/assets").mkdir(parents=True, exist_ok=True)
    Path("docs/assets/demo-transcript.txt").write_text(render_demo())


if __name__ == "__main__":
    main()
```

Generate the artifact with `uv run python scripts/refresh_demo_transcript.py`. Do not hand-edit the generated transcript.

- [ ] **Step 5: Run focused tests and inspect redaction**

Run:

```bash
uv run pytest tests/test_demo.py -v
rg -n "SUM OF SQUARES|ANSWER:" docs/assets/demo-transcript.txt
```

Expected: tests pass; `rg` returns exit 1 because the transcript contains neither task text nor answer text.

- [ ] **Step 6: Add transcript freshness to CI**

Add after the existing test step in `.github/workflows/ci.yml`:

```yaml
      - name: public demo transcript is current
        run: |
          uv run python scripts/refresh_demo_transcript.py
          git diff --exit-code -- docs/assets/demo-transcript.txt
```

- [ ] **Step 7: Run full gates and commit**

Run the global gates, then:

```bash
git add src/gauntlet/demo.py tests/test_demo.py scripts/refresh_demo_transcript.py docs/assets/demo-transcript.txt .github/workflows/ci.yml
git commit -m "docs: publish a verified gauntlet demo transcript"
```

### Task 3: Add an accessible, evidence-only causal-loop SVG

**Files:**
- Create: `docs/assets/gauntlet-causal-loop.svg`
- Create: `tests/test_public_assets.py`
- Modify: `README.md`
- Test: `tests/test_public_assets.py`

**Interfaces:**
- Consumes: the state sequence asserted by `tests/test_demo.py`.
- Produces: a self-contained SVG embedded by README Markdown with a `<title>`, `<desc>`, and only claims present in the demo/spec.

- [ ] **Step 1: Write the failing structural asset test**

Create `tests/test_public_assets.py`:

```python
from pathlib import Path


def test_causal_loop_svg_has_accessible_evidence_labels():
    svg = Path("docs/assets/gauntlet-causal-loop.svg").read_text()
    for phrase in (
        "<title>",
        "<desc>",
        "Agent fails task",
        "Memory persists",
        "Score appears to improve",
        "Leak caught",
        "Retire compromised holdout",
        "Fresh holdout retests claim",
    ):
        assert phrase in svg


def test_causal_loop_svg_does_not_expose_demo_secret_text():
    svg = Path("docs/assets/gauntlet-causal-loop.svg").read_text()
    assert "SUM OF SQUARES" not in svg
    assert "ANSWER:" not in svg
```

- [ ] **Step 2: Run the focused test to verify failure**

Run:

```bash
uv run pytest tests/test_public_assets.py -v
```

Expected: FAIL because the SVG is absent.

- [ ] **Step 3: Create the SVG as an incident-report receipt**

Create a 1600×900 self-contained SVG with CSS variables for dark/light display. Include a `<title>` and `<desc>`, five numbered rectangular stages, high-contrast arrows, and the exact labels from Step 1. Use text and simple geometric shapes only; no raster image, logo, brand gradient, or unverified metric. The final stage must show a return arrow to "Agent fails task" to make the retest loop obvious.

- [ ] **Step 4: Embed the diagram below the demo in README**

Immediately after the terminal demo block in `README.md`, add:

```markdown
![Gauntlet's causal loop: an apparent improvement is checked for memory leakage, then retested on a fresh holdout.](docs/assets/gauntlet-causal-loop.svg)
```

Keep the existing ASCII comparison below the plain-language problem explanation; it serves readers who want implementation detail.

- [ ] **Step 5: Verify asset and README claims**

Run:

```bash
uv run pytest tests/test_public_assets.py -v
rg -n "did it actually improve|memory, not intelligence|Fresh holdout" README.md docs/assets/gauntlet-causal-loop.svg
```

Expected: all tests pass; each proof phrase is present in an appropriate public asset.

- [ ] **Step 6: Run full gates and commit**

Run the global gates, then:

```bash
git add docs/assets/gauntlet-causal-loop.svg tests/test_public_assets.py README.md
git commit -m "docs: add accessible gauntlet causal loop"
```

### Task 4: Publish the self-audit case study and two-path adoption guide

**Files:**
- Create: `docs/CASE_STUDY.md`
- Modify: `README.md`
- Test: `tests/test_public_assets.py`

**Interfaces:**
- Consumes: dogfood facts already stated in `README.md`: 12 sealed instances, 271 files, 3.1 seconds, clean memory files, task fixtures in results, control scan with zero false positives, and redacted machine report.
- Produces: an evidence-bounded case study and README links for public learners and technical adopters.

- [ ] **Step 1: Write failing documentation assertions**

Append to `tests/test_public_assets.py`:

```python
def test_case_study_states_evidence_and_limits():
    case_study = Path("docs/CASE_STUDY.md").read_text()
    for phrase in (
        "271 files",
        "3.1 seconds",
        "zero false positives",
        "What this does not prove",
        "zero task text",
    ):
        assert phrase in case_study


def test_readme_links_to_case_study_and_self_scan_path():
    readme = Path("README.md").read_text()
    assert "docs/CASE_STUDY.md" in readme
    assert "Scan your own agent" in readme
```

- [ ] **Step 2: Run the focused test to verify failure**

Run:

```bash
uv run pytest tests/test_public_assets.py -v
```

Expected: FAIL because the case study and adoption link do not yet exist.

- [ ] **Step 3: Write the case study as an incident report**

Create `docs/CASE_STUDY.md` with these exact sections:

```markdown
# We ran our own gauntlet first

## The claim we were testing
## What we scanned
## What we found
## Why the finding mattered
## Control scan and redaction check
## What this does not prove
## Reproduce the pattern safely
```

Use only the verified facts listed in **Consumes**. Explain that this was one real scan, not a prevalence study or proof about every agent. Do not include task fixtures, prompts, answers, matched text, directory names that reveal private work, or claims about other tools.

- [ ] **Step 4: Add two explicit README paths**

After the diagram and before the detailed Quickstart, add a short section with:

```markdown
## See it. Then check yours.

- **See the proof:** read [the self-audit case study](docs/CASE_STUDY.md).
- **Scan your own agent:** run `uvx --from gauntlet-guard gauntlet demo`, then follow the memory-audit commands below.
```

This gives the general reader a narrative path and the builder a command path without inventing a product for nontechnical users.

- [ ] **Step 5: Run focused tests and manually read the public path**

Run:

```bash
uv run pytest tests/test_public_assets.py -v
sed -n '1,125p' README.md
sed -n '1,220p' docs/CASE_STUDY.md
```

Expected: tests pass; the README can be read top-to-bottom without encountering unexplained terminology before the problem and proof are clear.

- [ ] **Step 6: Run full gates and commit**

Run the global gates, then:

```bash
git add README.md docs/CASE_STUDY.md tests/test_public_assets.py
git commit -m "docs: add gauntlet self-audit case study"
```

### Task 5: Prepare evidence-first launch copy and a reproducible release runbook

**Files:**
- Create: `docs/LAUNCH_RUNBOOK.md`
- Create: `docs/launch-copy.md`
- Modify: `docs/LAUNCH_READINESS.md`
- Test: manual readiness gate from Task 1

**Interfaces:**
- Consumes: public asset paths from Tasks 2–4 and the current versioned demo.
- Produces: a human-executed launch sequence that never posts an unsupported claim or a broken link.

- [ ] **Step 1: Write the runbook preflight failure condition**

In `docs/LAUNCH_RUNBOOK.md`, begin with:

```markdown
# Gauntlet public proof launch runbook

## Stop conditions

Do not publish any launch post if a box under "Public surface" or "Evidence package" in
[`LAUNCH_READINESS.md`](LAUNCH_READINESS.md) is unchecked.
```

- [ ] **Step 2: Add the exact launch sequence**

Add these ordered sections, each with checkboxes:

```markdown
## 24 hours before
## Launch-hour verification
## Primary post
## Show HN post
## Reply discipline
## 24-hour review
## v0.4 follow-up event
```

Require each post to link the runnable demo and case study, not just the repository root. Include the exact Show HN title: `Show HN: I caught my AI agent's benchmark gain coming from its own memory`.

- [ ] **Step 3: Write copy variants that share one factual spine**

Create `docs/launch-copy.md` containing only these variant types:

1. a one-sentence social hook;
2. a 100–150 word primary launch post;
3. a Show HN body;
4. five technically honest reply starters for common questions: "Is this intentional cheating?", "How is this different from a benchmark?", "Does it work with my framework?", "What does it miss?", and "Why not just reset memory?".

Every variant must include the sentence: "The demo uses scripted agents and real Gauntlet APIs; it is deterministic and runs without an LLM." Do not use words such as "revolutionary", "solves alignment", "guaranteed", "everyone", or promised star/download counts.

- [ ] **Step 4: Fill and verify launch-readiness evidence**

Run the checks from Task 1 after all assets have merged. Put actual date, commit, and URL observations under each checked item. Confirm links resolve in an unauthenticated browser and commands run from a fresh temporary directory.

- [ ] **Step 5: Review for unsupported claims**

Run:

```bash
rg -n -i "revolutionary|solves alignment|guaranteed|millions|everyone|#1|trending" docs/LAUNCH_RUNBOOK.md docs/launch-copy.md
```

Expected: exit 1. Then manually check that every factual sentence links to the README, case study, source, or executable demo.

- [ ] **Step 6: Run full gates and commit**

Run the global gates, then:

```bash
git add docs/LAUNCH_READINESS.md docs/LAUNCH_RUNBOOK.md docs/launch-copy.md
git commit -m "docs: add gauntlet proof launch runbook"
```

## Deferred follow-on plans

- `holdout` v0.4 implementation and its retirement ledger contract are a separate product plan. Do not announce automatic regeneration until that plan's code and tests ship.
- Named integrations are separate plans, one verified integration at a time.
- A public interactive experience or standalone website is a separate discovery/design cycle triggered only by evidence of nontechnical demand.
