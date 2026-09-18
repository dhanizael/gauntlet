# Viral Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Gauntlet README into a proof-first viral presentation with an autoplay demo GIF and reusable social card, without changing product behavior or pushing public changes.

**Architecture:** A standard-library Python renderer reads the canonical public demo transcript, emits temporary SVG frames, and invokes the already-available ImageMagick CLI to produce checked-in GIF and PNG artifacts. README is then rebuilt around those artifacts; tests check evidence copy, image formats/dimensions, and that the previous non-playable cast is not presented as a player.

**Tech Stack:** Python 3.11+, ImageMagick (`magick`), checked-in SVG/GIF/PNG assets, pytest, Ruff, ty.

**Spec:** `docs/superpowers/specs/2026-09-18-viral-presentation-design.md`

## Global Constraints

- Add no runtime dependency to `gauntlet-guard`.
- Render only from checked-in public demo text; never include task secret text or answers.
- Use actual demo values: `KEEP (net 1.0)`, `[EXACT] LESSONS.md`, and `PROVISIONAL (net 0.0)`.
- Do not call GitHub APIs, change repository settings, create releases, or push.
- Do not describe a raw `.cast` file as playable.
- The README must provide descriptive alternative text for raster assets.

---

### Task 1: Deterministic public asset renderer

**Files:**
- Create: `scripts/render_public_assets.py`
- Create: `docs/assets/gauntlet-demo.gif`
- Create: `docs/assets/gauntlet-social-card.png`
- Test: `tests/test_public_assets.py`

**Interfaces:**
- Consumes: `docs/assets/demo-transcript.txt` as the public evidence source.
- Produces: `main(argv: Sequence[str] | None = None) -> int`, supporting `--check`; fixed artifacts at the two asset paths.

- [ ] **Step 1: Write failing proof-asset tests**

```python
def test_proof_assets_have_real_image_headers_and_expected_dimensions():
    assert Path("docs/assets/gauntlet-demo.gif").read_bytes().startswith(b"GIF89a")
    assert png_dimensions(Path("docs/assets/gauntlet-social-card.png")) == (1200, 630)


def test_public_assets_preserve_only_the_demo_reveal():
    text = Path("scripts/render_public_assets.py").read_text()
    for phrase in ("KEEP (net 1.0)", "[EXACT] LESSONS.md", "PROVISIONAL (net 0.0)"):
        assert phrase in text
    assert "SUM OF SQUARES" not in text
    assert "ANSWER:" not in text
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `uv run pytest tests/test_public_assets.py -q`

Expected: FAIL because the renderer and the two proof assets do not exist.

- [ ] **Step 3: Implement renderer with fixed visual vocabulary**

```python
ASSET_DIR = Path("docs/assets")
DEMO_GIF = ASSET_DIR / "gauntlet-demo.gif"
SOCIAL_CARD = ASSET_DIR / "gauntlet-social-card.png"

REVEAL = ("KEEP (net 1.0)", "[EXACT] LESSONS.md", "PROVISIONAL (net 0.0)")

def main(argv: Sequence[str] | None = None) -> int:
    # Render SVG frames with no secret content, then call `magick` with fixed
    # delay/disposal settings. In --check mode, compare fresh temporary bytes
    # to the checked-in artifacts and return nonzero on drift.
```

The SVG frame generator must use the near-black, danger-red, and proof-green palette specified in the design. The social card must be exactly 1200x630. Fail with an actionable message if `magick` is unavailable; no install is attempted.

- [ ] **Step 4: Generate assets and rerun focused tests**

Run: `uv run python scripts/render_public_assets.py && uv run pytest tests/test_public_assets.py -q`

Expected: renderer writes both assets; tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/render_public_assets.py docs/assets/gauntlet-demo.gif docs/assets/gauntlet-social-card.png tests/test_public_assets.py
git commit -m "docs: add proof-first launch assets"
```

### Task 2: Rebuild README above the fold

**Files:**
- Modify: `README.md:1-106`
- Modify: `tests/test_public_assets.py`

**Interfaces:**
- Consumes: `docs/assets/gauntlet-demo.gif`, `docs/assets/gauntlet-social-card.png`, case study, protocol docs.
- Produces: an above-the-fold README sequence with headline, one-line meaning, reproduce command, GIF, and three links.

- [ ] **Step 1: Write failing README-copy tests**

```python
def test_readme_leads_with_the_proof_reveal_and_autoplay_asset():
    readme = Path("README.md").read_text()
    assert "YOUR AI DIDN'T GET SMARTER." in readme
    assert "IT GOT THE ANSWERS." in readme
    assert "docs/assets/gauntlet-demo.gif" in readme
    assert "docs/assets/gauntlet-social-card.png" in readme
    assert "playable terminal cast" not in readme
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `uv run pytest tests/test_public_assets.py::test_readme_leads_with_the_proof_reveal_and_autoplay_asset -q`

Expected: FAIL because the current README lacks the new hero and calls its raw cast playable.

- [ ] **Step 3: Rewrite the hero and move protocol density downward**

Use this exact top-level copy:

```markdown
## YOUR AI DIDN'T GET SMARTER.
## IT GOT THE ANSWERS.

An agent can look dramatically better after it has seen the test. Gauntlet
shows whether the score survives a fresh one.
```

Embed the GIF immediately after the reproduction command using descriptive alt text. Add a concise action row linking the case study, run protocol, and social card. Remove the primary-path ASCII before/after block and remove the raw cast link rather than mislabel it. Retain technical quickstart and design principles below the proof and self-audit sections.

- [ ] **Step 4: Run focused tests and inspect Markdown structure**

Run: `uv run pytest tests/test_public_assets.py -q && rg -n 'YOUR AI|gauntlet-demo.gif|playable terminal cast|without gauntlet' README.md`

Expected: tests pass; first two search terms occur; latter two do not.

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_public_assets.py
git commit -m "docs: lead with gauntlet proof reveal"
```

### Task 3: Reproducibility and visual QA

**Files:**
- Modify: `scripts/render_public_assets.py` only if visual inspection exposes a readability defect.
- Modify: `docs/assets/gauntlet-demo.gif`, `docs/assets/gauntlet-social-card.png` only if renderer output changes.
- Test: `tests/test_public_assets.py`

**Interfaces:**
- Consumes: renderer output and README embeds from Tasks 1–2.
- Produces: deterministic binary assets and a verified local presentation branch.

- [ ] **Step 1: Prove renderer determinism**

Run:

```bash
sha256sum docs/assets/gauntlet-demo.gif docs/assets/gauntlet-social-card.png > /tmp/gauntlet-assets-before.sha256
uv run python scripts/render_public_assets.py
sha256sum --check /tmp/gauntlet-assets-before.sha256
uv run python scripts/render_public_assets.py --check
```

Expected: both hash checks succeed and `--check` exits zero.

- [ ] **Step 2: Visually inspect produced images at native dimensions**

Run: `magick identify docs/assets/gauntlet-demo.gif docs/assets/gauntlet-social-card.png`

Expected: GIF has multiple frames; PNG is exactly 1200x630. Open the PNG and first/last GIF frames with the local image viewer; confirm headline, three proof states, and final reveal are readable without zooming.

- [ ] **Step 3: Run complete repository verification**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check src/
uv run python scripts/refresh_demo_transcript.py --check
uv run python scripts/render_public_assets.py --check
git diff main...HEAD --check
```

Expected: all commands exit zero. Type checking is scoped to `src/` because the existing all-test type check has unrelated fixture-dict diagnostics.

- [ ] **Step 4: Commit only if QA required a correction**

```bash
git add scripts/render_public_assets.py docs/assets/gauntlet-demo.gif docs/assets/gauntlet-social-card.png tests/test_public_assets.py
git commit -m "docs: polish proof asset readability"
```

- [ ] **Step 5: Report local-only result**

Report the branch name, commit list, test evidence, generated asset paths, and the explicit fact that no remote, GitHub setting, release, or public About field was changed.
