# Gauntlet Viral Presentation Design

> Internal working design. Keep on the local presentation branch until the
> maintainer explicitly curates public-facing files.

## Goal

Make the first screen of Gauntlet communicate one memorable, defensible reveal:
an AI agent can appear to improve because it learned the test, and Gauntlet
proves the difference on a fresh holdout.

The audience is deliberately broad at the point of attention: anyone worried
that an AI score might be fake. Installation and deeper evaluation workflows
remain for agent builders, evaluators, and teams shipping agents.

## Creative direction

The tone is an evidence-backed accusation, not generic AI imagery:

```
YOUR AI DIDN'T GET SMARTER.
IT GOT THE ANSWERS.
```

The evidence is the product's deterministic three-act demo:

1. `KEEP (net 1.0)` creates the apparent win.
2. The guard finds an `EXACT` memory leak.
3. The fresh holdout returns `PROVISIONAL (net 0.0)`.

No generated faces, robots, stock cyberpunk, fabricated dashboards, or claims
about real third-party products. Every visual derives from the checked-in demo
and its real command output.

## Public experience

### README first screen

The top of README becomes a short, scan-first sequence:

1. repo name and conventional trust badges;
2. all-caps hero claim above a plain-language one-line explanation;
3. one command to reproduce the proof;
4. an autoplay GIF of the real three-act output;
5. a compact action row: run the demo, read the case study, inspect the
   protocol.

The heavy ASCII comparison is removed from the primary path. Detailed protocol,
quickstart, and principles remain lower in the README for serious evaluators.

### Hero GIF

Create a compact, high-contrast terminal animation from the deterministic demo
transcript. It must be readable on GitHub desktop and mobile, loop cleanly,
have no narration requirement, and show only the decisive lines. The final
frame holds the reveal long enough to be understood:

```
KEEP (net 1.0)  ->  [EXACT] LESSONS.md  ->  PROVISIONAL (net 0.0)
the improvement was memory, not intelligence
```

The source transcript remains canonical. Generation must be deterministic and
the repository must test that the GIF-generation input is the current demo
transcript. The GIF is a viewing layer; it is not evidence on its own.

### Share card

Create a 1200x630 PNG for social sharing and launch posts. It is a visual
poster, not a flowchart:

```
YOUR AI DIDN'T GET SMARTER.
IT GOT THE ANSWERS.

  KEEP (net 1.0)       [EXACT] LEAK       PROVISIONAL (net 0.0)
```

Use a restrained black/near-black terminal palette, one danger accent for the
leak, and one proof accent for the fresh-test result. Include `gauntlet` and
the reproducible command in small supporting text. The composition must remain
legible after social-platform cropping.

The image is a reusable attachment for X, Hacker News, LinkedIn, and release
notes. GitHub repository pages do not accept a repository-level custom Open
Graph image through versioned files alone, so the card is treated as a share
asset; a maintainer can upload it in GitHub's social-preview settings later.

### Diagram policy

Retire the six-step causal-loop hero graphic from the first screen. If retained,
place it after the quickstart as protocol depth. Its replacement is the
score-to-leak-to-fresh-test proof strip, because it carries one idea at share
speed.

### About and topics

Set the eventual GitHub About text manually to:

> Your AI "improved." Did it get smarter—or memorize the test? Find out before you trust the score.

Keep technical vocabulary in topics for discovery. Do not dilute the About line
with implementation terms.

## Files and responsibilities

| Path | Responsibility |
| --- | --- |
| `README.md` | Hero hierarchy, GIF embed, concise calls to action, lower-level technical depth. |
| `docs/assets/demo-transcript.txt` | Canonical deterministic input. |
| `docs/assets/gauntlet-demo.gif` | Generated autoplay proof artifact. |
| `docs/assets/gauntlet-social-card.png` | Generated launch/share image. |
| `scripts/render_public_assets.py` | Deterministically turns canonical copy/transcript into GIF and PNG. |
| `tests/test_public_assets.py` | Asserts generated assets exist, have intended formats/dimensions, and remain current. |
| `docs/assets/gauntlet-causal-loop.svg` | Removed from the hero; retained only if it earns a lower-page role. |

## Constraints

- No runtime dependency is added to the Gauntlet package.
- Asset-generation dependencies, if needed, are development-only and locked.
- Every numerical claim shown in an asset comes from `gauntlet demo`.
- Assets have descriptive alt text and a readable static fallback.
- The cast link is not described as playable unless linked to an actual player.
- Do not push, release, change GitHub settings, or modify the public About field
  during this work.

## Verification

1. Run the deterministic demo and check the transcript freshness gate.
2. Generate assets twice and compare hashes for determinism.
3. Test GIF and PNG headers and dimensions from Python.
4. Render/inspect the assets at GitHub-like width, including dark and light
   backgrounds where relevant.
5. Run the full Python suite, Ruff, formatting, and type check scoped to `src/`
   (the repository's test fixture baseline currently has known diagnostics when
   checking all tests).
6. Review `git diff` to ensure no public operation, remote push, or release is
   included.
