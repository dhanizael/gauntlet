# 0011 — Zero-config surface audit

- Status: Accepted
- Date: 2026-09-18
- Deciders: author

## Context
The demo tells the failure-mode story about a fictional agent; a first-time
visitor's real question is "does this happen on MY machine?" — and until
v0.3.3 the answer required a manifest, which requires a protocol, which
requires reading the docs. Every step of that funnel loses people. Meanwhile
the leak channels themselves (memory files, state dirs, transcript dirs,
vector stores) are discoverable by name alone, with no secret knowledge at
all. A discovery step that touches nothing private can sit before the
manifest exists and turn "maybe this applies to me" into "these five paths on
my machine are the open book".

## Decision
`gauntlet guard audit [roots...]` (default root: home) walks the filesystem
and reports agent memory surfaces in four classes — memory files
(`LESSONS.md`, `MEMORY.md`, `now.md`, `AGENTS.md`, `CLAUDE.md`, ...), agent
state dirs (`.agent-state`, `.claude`, `memory`, ...), transcript/log dirs
(`logs`, `sessions`, `runs`, ... — only when they contain a text file), and
vector stores (by format dir, or DB name hints). It is **discovery only**:

- it never opens file content — evidence is path, kind, size, mtime. This
  extends the redaction contract (ADR-0002) from "reports carry no content"
  to "the tooling cannot leak content it never read";
- it is name-based and heuristic. It finds the surfaces to scan, not the
  leaks; the leak check still requires a manifest (`guard scan`);
- caps are applied and reported: depth 6, 250k entries, 20 s — a truncated
  walk says `STOPPED EARLY` out loud rather than passing as complete;
- exit code is always 0. An audit is information, not a verdict; the
  exit-code-as-verdict contract (v0.3) remains reserved for grading;
- cache noise (package-manager and plugin caches ship bundled `AGENTS.md`
  docs) is excluded by skipping `cache`/`caches` directories, learned by
  dogfooding on a real home directory (98k entries, 2.3 s).

## Consequences
- Positive: the adoption funnel gains a zero-setup first command that talks
  about the visitor's own machine; the README can show the visitor something
  real in 30 seconds without any protocol knowledge.
- Positive: pairs naturally with the existing funnel — audit surfaces →
  `manifest add` → `guard scan` — so discovery converts directly into use.
- Negative: name-based discovery has unavoidable false negatives (files with
  unexpected names) and false positives (a project's `logs/` dir is a
  surface even when it never touched an eval). Accepted: the report is
  informational and cheap to skim; precision comes from the manifest scan.
- Negative: a truncated walk (entry/time cap) can hide real surfaces behind
  an honest-looking summary. Mitigated by surfacing `STOPPED EARLY` and the
  per-root scoping flag; a home that hits the cap should be audited root by
  root.
- Negative: skipping `.local` and `.config` (entry-cap defense against
  gigabytes of app data) creates an XDG blind spot — agent CLIs that keep
  sessions or memory under `~/.local/share/...` are invisible at their
  default location even when their tool dir is advertised. Users on such
  stacks should audit those paths explicitly: `gauntlet guard audit
  ~/.local/share`.
