"""audit — zero-config discovery of agent memory surfaces on this machine.

The demo tells a story about a fictional agent; `guard audit` tells visitors
the truth about THEIR machine. It walks the given roots (default: home) and
reports known agent memory surfaces — the leak channels from the README's
vector list: memory files (LESSONS.md, MEMORY.md, now.md, ...), agent state
dirs, transcript/log dirs, and vector stores.

Contract (extends the redaction contract, ADR-0002): audit never opens a
file's content. Evidence is path, kind, size, mtime — nothing else. If a
secret hides inside LESSONS.md, the audit output cannot leak it, because the
content is never read. (Pinned mechanically by tests: read_text/open are
monkeypatched to raise and the audit must still succeed.)

Discovery is name-based and heuristic: it finds the surfaces to scan, not
the leaks. The actual leak check needs a manifest (`guard scan`). Caps
(depth, entries, seconds) are applied and reported honestly as truncation —
a partial map must never masquerade as a full one. The walk itself always
exits 0: an audit is information, not a verdict (operator errors such as an
unwritable --json path still fail loudly, consistent with scan/grade).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .guard import DEFAULT_SKIP_NAMES

SCHEMA = 1

# memory files agents write "what I learned this run" into (name, case-insensitive)
MEMORY_FILE_NAMES = {
    "memory.md",
    "memories.md",
    "lessons.md",
    "learnings.md",
    "now.md",
    "agents.md",
    "claude.md",
    "journal.md",
    "aider.chat.history.md",
}

# directories that ARE the agent's persistent state
AGENT_STATE_DIRS = {
    ".agent-state",
    "agent-state",
    ".memory",
    "memory",
    "memories",
    "journal",
    "journals",
    ".claude",
    ".codex",
    ".cursor",
    ".continue",
    ".gemini",
    ".opencode",
}

# directories that hold saved runs/transcripts — reported only when they
# actually contain a text file (generic names like "logs" need evidence)
TRANSCRIPT_DIRS = {
    "logs",
    "log",
    "transcripts",
    "trajectories",
    "sessions",
    ".sessions",
    "evals",
    "eval-outputs",
    "runs",
    "outputs",
    "results",
}

TEXT_SUFFIXES = {".md", ".txt", ".jsonl", ".ndjson", ".json", ".log", ".yaml", ".yml"}

# vector stores: format dirs, and database files whose name says what they hold
VECTOR_DIRS = {".chroma", ".chromadb", ".lancedb", ".qdrant", "faiss_indexes", ".mem0"}
VECTOR_FILE_SUFFIXES = {".faiss", ".lance"}
VECTOR_DB_SUFFIXES = {".sqlite", ".sqlite3", ".db", ".duckdb"}
VECTOR_NAME_HINTS = (
    "vector",
    "vectors",
    "memory",
    "memories",
    "embedding",
    "embeddings",
    "chroma",
    "lancedb",
    "qdrant",
    "faiss",
    "mem0",
    "memgpt",
    "letta",
)

# never descend into these while walking (noise, gigabytes, none of it memory)
SKIP_DIRS = DEFAULT_SKIP_NAMES | {
    ".cache",
    "cache",
    "caches",  # package-manager/plugin caches ship bundled AGENTS.md docs — noise
    ".npm",
    ".cargo",
    ".rustup",
    ".local",
    ".volta",
    ".nvm",
    ".rbenv",
    ".pyenv",
    ".gradle",
    ".m2",
    ".android",
    ".docker",
    ".kube",
    ".terraform",
    ".ollama",
    ".lm-studio",
    ".vscode",
    ".config",
    "Library",
    ".Trash",
    "snap",
    "target",
    "dist",
    "build",
    ".next",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".hypothesis",
    ".eggs",
}

KIND_ORDER = {"memory-file": 0, "agent-state": 1, "transcripts": 2, "vector-store": 3}


@dataclass(frozen=True)
class Surface:
    path: str
    kind: str  # memory-file | agent-state | transcripts | vector-store
    size: int  # bytes; -1 for directories (size of a dir is a lie)
    modified: str  # ISO date only; "?" when the mtime itself is corrupt


@dataclass
class AuditResult:
    surfaces: list[Surface] = field(default_factory=list)
    entries_seen: int = 0
    dirs_skipped: int = 0  # not descended: noise dirs (caches, VCS, deps)
    deep_skipped: int = 0  # not descended: beyond max_depth
    truncated: bool = False  # stopped early on a cap — partial map, said out loud
    unknown_roots: list[str] = field(default_factory=list)  # missing/unreadable
    duration_s: float = 0.0


def audit_surfaces(
    roots: list[Path],
    *,
    max_depth: int = 6,
    max_files: int = 250_000,
    max_seconds: float = 20.0,
) -> AuditResult:
    result = AuditResult()
    t0 = time.monotonic()
    deadline = t0 + max_seconds
    stack: list[tuple[Path, int]] = []
    for r in roots:
        resolved = r.expanduser().resolve()
        if resolved.is_dir():
            stack.append((resolved, 0))
        else:
            result.unknown_roots.append(str(r))
    while stack:
        root, depth = stack.pop()
        try:
            entries = sorted(root.iterdir())
        except OSError:
            continue
        for entry in entries:
            # caps are enforced per entry: an overshoot is at most one file
            if result.entries_seen >= max_files or time.monotonic() > deadline:
                result.truncated = True
                break
            result.entries_seen += 1
            _classify(entry, result)
            if not entry.is_dir() or entry.is_symlink():
                continue  # symlinked dirs are not descended: no cycles
            if _is_skipped(entry):
                result.dirs_skipped += 1
            elif depth >= max_depth:
                result.deep_skipped += 1
            else:
                stack.append((entry, depth + 1))
    result.duration_s = round(time.monotonic() - t0, 2)
    result.surfaces.sort(key=lambda s: (KIND_ORDER[s.kind], s.path))
    return result


def _is_skipped(entry: Path) -> bool:
    return entry.name in SKIP_DIRS


def _classify(entry: Path, result: AuditResult) -> None:
    name = entry.name.lower()
    try:
        is_dir = entry.is_dir()
        is_file = entry.is_file()
        if not is_dir and not is_file:
            return  # broken symlink, socket, ...
        meta = entry.stat()
    except OSError:
        return
    if is_dir and _is_skipped(entry):
        return
    try:
        modified = datetime.fromtimestamp(meta.st_mtime, UTC).date().isoformat()
    except (OSError, ValueError, OverflowError):
        modified = "?"  # corrupt clock / out-of-range mtime: report, don't crash
    kind: str | None = None
    if is_file and name in MEMORY_FILE_NAMES:
        kind = "memory-file"
    elif is_dir and name in AGENT_STATE_DIRS:
        kind = "agent-state"
    elif is_dir and name in TRANSCRIPT_DIRS and _has_text_file(entry):
        kind = "transcripts"
    elif (is_dir and name in VECTOR_DIRS) or (is_file and _is_vector_file(name)):
        kind = "vector-store"
    if kind is not None:
        result.surfaces.append(
            Surface(
                path=str(entry),
                kind=kind,
                size=meta.st_size if is_file else -1,
                modified=modified,
            )
        )


def _is_vector_file(name: str) -> bool:
    suffix = Path(name).suffix.lower()
    if suffix in VECTOR_FILE_SUFFIXES:
        return True
    return suffix in VECTOR_DB_SUFFIXES and any(h in name for h in VECTOR_NAME_HINTS)


def _has_text_file(directory: Path) -> bool:
    try:
        return any(f.is_file() and f.suffix.lower() in TEXT_SUFFIXES for f in directory.iterdir())
    except OSError:
        return False


def audit_to_dict(result: AuditResult, roots: list[Path]) -> dict:
    return {
        "schema": SCHEMA,
        "roots": [str(r) for r in roots],
        "surfaces": [s.__dict__ for s in result.surfaces],
        "entries_seen": result.entries_seen,
        "dirs_skipped": result.dirs_skipped,
        "deep_skipped": result.deep_skipped,
        "truncated": result.truncated,
        "unknown_roots": result.unknown_roots,
        "duration_s": result.duration_s,
    }


def _human_size(size: int) -> str:
    if size < 0:
        return "     -"
    if size < 1024:
        return f"{size:5d} B"
    if size < 1024 * 1024:
        return f"{size / 1024:5.1f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):5.1f} MB"
    return f"{size / (1024 * 1024 * 1024):5.1f} GB"


def format_report(result: AuditResult, roots: list[Path]) -> str:
    lines = [
        "gauntlet guard audit — agent memory surfaces (content-free: names, sizes, dates only)",
        f"roots: {', '.join(str(r) for r in roots)}",
    ]
    if result.unknown_roots:
        lines.append(f"not found or not readable: {', '.join(result.unknown_roots)}")
    cap_note = "  — STOPPED EARLY: entry/time cap reached" if result.truncated else ""
    lines.append(f"visited {result.entries_seen} entries in {result.duration_s}s{cap_note}")
    labels = {
        "memory-file": "memory files",
        "agent-state": "agent state dirs",
        "transcripts": "transcript/log dirs",
        "vector-store": "vector stores",
    }
    for kind, label in labels.items():
        found = [s for s in result.surfaces if s.kind == kind]
        lines.append(f"\n{label} ({len(found)})")
        lines.extend(f"  {s.path:<68} {_human_size(s.size)}  {s.modified}" for s in found)
    lines.append(
        "\nThese surfaces can silently remember eval tasks between runs. "
        "Discovery only — leak checks need a manifest."
    )
    lines.append("next steps:")
    lines.append(
        "  seal your holdout:   gauntlet manifest add mf.jsonl --instance t-1 --seed s-1 prompt.txt"
    )
    lines.append("  scan them for leaks: gauntlet guard scan mf.jsonl --store <path from above>")
    lines.append(
        "  prove the scanner:   gauntlet guard selftest    ·    the 8-second story: gauntlet demo"
    )
    return "\n".join(lines)
