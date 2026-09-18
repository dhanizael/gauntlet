# Gauntlet broad-reach launch design

## Decision

Launch Gauntlet as the proof layer for a question every AI user can understand:

> Did the AI get smarter, or did it learn the test?

The public story is deliberately broader than the implementation. The product remains a
precise, auditable integrity tool for stateful-agent evaluations; the entry point is the
universal distrust people already feel when an AI suddenly reports a dramatic improvement.

This is not a campaign to manufacture hype. It is a proof-led launch designed to make a
real failure mode emotionally legible, then give builders a way to verify it themselves.

## Positioning

### Public language

**Hero:** "Your AI agent improved. Gauntlet proves whether it got smarter—or just learned
the test."

**One-sentence explanation:** "When an AI remembers old tasks, feedback, transcripts, or
answers, its next benchmark score can look like progress even when nothing new was learned."

**Call to action:** "Watch the 20-second proof. Then run the same check on your agent."

### Technical language

"Gauntlet is a sealed-evaluation integrity layer: it isolates trials, blind-grades results,
scans persistent stores for task leakage, and retires compromised holdouts."

The public phrase is not a simplification that changes the technical claim. It is the
human-readable consequence of the same mechanism.

### Category

Gauntlet must not present itself as another memory benchmark, agent framework, dashboard, or
leaderboard. It owns the question of *integrity of claimed improvement*. Existing work on
stateful memory evaluation and benchmark contamination validates the urgency; Gauntlet's
distinct role is to prevent a task instance from becoming its own agent's study material.

## Audiences and paths

| Audience | First reaction we want | Next step |
| --- | --- | --- |
| AI-curious public, creators, founders | "Wait—AI can appear to improve by remembering the test?" | Watch/share the demo and read the case study. |
| AI builders and indie hackers | "My agent writes memories, transcripts, or artifacts. I should check that." | Run the one-command demo, then scan their own stores. |
| Evaluation, research, and security teams | "The evidence model and lifecycle are credible." | Adopt the protocol or assess an integration with their existing harness. |
| Reviewers and critics | "The claims are bounded and reproducible." | Inspect tests, ADRs, contracts, and the dogfood report. |

Mass reach is the top of the funnel, not a promise that every viewer will install a Python
CLI. Success means many people understand and share the problem, while the people with
agent infrastructure receive a frictionless, credible route to adoption.

## Proof architecture

Every public surface tells the same causal story.

```text
Agent fails task
  -> feedback or artifacts persist
  -> same task scores better
  -> Gauntlet finds task-derived memory without revealing task content
  -> compromised instance is retired
  -> a fresh holdout tests the claim again
```

The demo is the canonical proof. All visuals are derived from it; no fabricated dashboard,
synthetic growth number, or edited outcome may stand in for evidence.

### Claim boundaries

- Say "can produce a false improvement"; do not claim every agent is cheating.
- Say "memory, transcript, and artifact leakage"; do not reduce all contamination to one
  vendor or one model.
- Say "detects the covered leakage modes"; do not imply a security guarantee against every
  avenue an agent could use.
- Do not promise GitHub rank, user count, or viral reach. Optimize for a launch worthy of
  those outcomes.

## Launch assets

### 1. README as a high-trust landing page

Keep the existing strong hook and three-act demo at the top. Add, in this order:

1. a short terminal cast immediately after the command;
2. an accessible SVG of the causal loop;
3. a two-path call to action: "see the proof" and "scan your own agent";
4. the self-audit case study before deep architecture;
5. integration examples for existing harnesses, after the core quickstart;
6. ADRs, contracts, contributing details, and development material below the conversion path.

The first screen must make a nontechnical visitor capable of accurately repeating the
problem. The technical sections must make a skeptical engineer capable of reproducing it.

### 2. Canonical terminal cast

A 20–30 second, loopable recording of the real `gauntlet demo` output. It must show all three
acts and end on the line "The +1.0 was memory, not intelligence." It should have no voiceover
required to understand it and include a text transcript for accessibility.

The recording is a real executable artifact: the script used to create it runs in CI or has a
documented regeneration command. That preserves the demo-as-contract philosophy.

### 3. One SVG, not a design system

A dark/light-mode-safe, screen-reader-described flow diagram. The visual language is an
incident report or laboratory receipt—clear state changes, evidence, and verdicts—not generic
neon AI branding. It should be legible as a social preview crop and in a GitHub README.

### 4. Dogfood case study

Working title: **"We tested whether our agent got smarter. It had memorized the exam."**

It documents the actual self-audit: scope, scan time, clean memory result, leaked run-result
fixtures, calibrated findings, control scan, redaction assertion, and limits. The point is not
to create fear. The point is to make a previously invisible failure mode undeniable.

### 5. Adoption bridge

Create short integration recipes with the promise: "Keep your evaluator. Add an integrity
check around it." Start with generic shell/CI and then only add named integrations when each
is tested against its real workflow. Avoid claiming support for a framework merely because a
user can invoke a shell command next to it.

## Distribution sequence

### Gate 0 — public-surface integrity

Before promotion, confirm that GitHub's default branch and unauthenticated public page show
the current v0.3.2 README, demo, `run`, and `grade` status. Confirm PyPI, repository metadata,
release/tag, and README tell one consistent story. A visitor must never land on an older product
than the post advertises.

### Gate 1 — proof assets ready

The cast, SVG, case study, and README have to be complete and tested. The public launch cannot
depend on an asset marked "coming soon."

### Gate 2 — soft proof distribution

Publish a small number of evidence-first posts. The lead is the three-act experiment, not a
request for stars. Observe which words people repeat back; that tells us whether the causal
story is understood.

### Gate 3 — Show HN launch

Proposed title: **Show HN: I caught my AI agent's benchmark gain coming from its own memory**

The post opens with the concrete demo outcome, links to the runnable reproduction, states the
limits plainly, and invites failure reports. It does not claim to solve alignment, defeat every
benchmark issue, or replace existing evaluators.

### Gate 4 — v0.4 as the second event

Release the retirement ledger and fresh-instance generation only after their contract and tests
are complete. The message then becomes: "A leaked test is dead; Gauntlet replaces it with a
fresh one." This is a stronger, separate news event rather than a feature footnote.

## Quality gates

An asset is ready only if it satisfies its gate.

| Asset | Acceptance criteria |
| --- | --- |
| Hero and README | A reader can name the problem, mechanism, and one action without knowing eval terminology. All commands execute from a clean environment. |
| Cast | Generated from the real demo; transcript matches current output; its final verdict is asserted by tests. |
| SVG | No claim absent from the product; readable in light/dark contexts; meaningful text alternative exists. |
| Case study | Every metric and finding has a reproducible source; limitations are explicit; no secret task material is exposed. |
| Integration guide | Each named integration was run end-to-end or is labeled conceptual. |
| Launch copy | Uses a concrete observed event, links to proof, makes no manufactured urgency, and withstands a hostile technical reading. |

## Metrics and learning loop

Track signals by stage rather than vanity alone:

- **Comprehension:** comments and replies accurately restate the false-improvement mechanism.
- **Activation:** demo runs, PyPI installs, stars/forks, issue reports, and self-audit reports.
- **Trust:** quality of technical discussion, reproducible negative results, external reviews,
  and verified integrations.
- **Retention:** projects that keep Gauntlet in CI or return for v0.4.

Stars and trending placement are useful signals, not the score to game. If a broad post gets
attention but produces misunderstanding, the copy is revised before it is amplified.

## Explicit non-goals

- Do not build a marketing website or dashboard before the evidence assets prove demand.
- Do not expand the core product merely to appeal to every AI user.
- Do not imitate viral AI aesthetics, make untestable performance claims, or use fake scarcity.
- Do not position Gauntlet as a replacement for all benchmarks, all agent frameworks, or human
  judgment.

## References informing timing, not product claims

- Microsoft, "Introducing STATE-Bench: A benchmark for AI agent memory," 2026-05-19.
  https://opensource.microsoft.com/blog/2026/05/19/introducing-state-bench-a-benchmark-for-ai-agent-memory/
- Wang et al., "Search-Time Contamination in Deep Research Agents," 2026-06-03.
  https://arxiv.org/abs/2606.05241
