"""Leak guard: detect holdout task content inside agent persistent stores.

The threat model is agent-native: agents now carry memory across sessions
(LESSONS.md, now.md, journal logs, vector stores, transcripts). Holdout
secrecy fails silently through these channels: a paraphrase saved today
becomes an unfair advantage next week.

This module scans persistent stores against an instance manifest and reports
LEAKAGE WITHOUT EMITTING CONTENT: every finding is file, word-position,
match counts, and shingle hash references — never the matched text. The
scanner itself must not become a leak channel.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

from .fingerprint import normalize, word_shingles
from .manifest import InstanceRecord

SEVERITY_ORDER = {"trace": 0, "near": 1, "exact": 2}

DEFAULT_SKIP_NAMES = {".git", ".venv", "node_modules", "__pycache__", ".uv-cache"}


@dataclass(frozen=True)
class Finding:
    store_file: str
    instance: str
    seed: str
    severity: str  # exact | near | trace
    matched_shingles: int
    total_shingles: int
    overlap_pct: float
    first_word_pos: int
    evidence_shingle: str  # hash reference only — never printable content
    content_ref: str  # double indirection: sha256 of the instance's full-content hash


def iter_store_files(
    store_paths: list[Path], skip: set[str] = DEFAULT_SKIP_NAMES
) -> Iterator[Path]:
    for p in store_paths:
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and not any(part in skip for part in f.parts):
                    yield f


def scan_store(
    records: list[InstanceRecord],
    store_paths: list[Path],
    min_overlap_shingles: int = 2,
) -> list[Finding]:
    active = [r for r in records if not r.retired]
    findings: list[Finding] = []
    for path in iter_store_files(store_paths):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for rec in active:
            f = _match_one(path, text, rec, min_overlap_shingles)
            if f is not None:
                findings.append(f)
    findings.sort(key=lambda x: (-SEVERITY_ORDER[x.severity], -x.overlap_pct))
    return findings


def _match_one(path: Path, store_text: str, rec: InstanceRecord, min_hits: int) -> Finding | None:
    norm = normalize(store_text)
    severity = "near"
    first_pos = -1
    matched: set[str] = set()

    exact = (
        rec.normalized is not None
        and len(rec.normalized.split()) >= rec.shingle_words
        and rec.normalized in norm
    )
    if exact:
        severity = "exact"
        first_pos = norm.find(rec.normalized)
        matched.update(h for _, h in word_shingles(rec.normalized, rec.shingle_words))
    else:
        hits = word_shingles(norm, rec.shingle_words)
        for pos, h in hits:
            if h in rec.shingles:
                matched.add(h)
                if first_pos < 0:
                    first_pos = pos
        if len(matched) < min_hits:
            return None
        total = max(1, len(rec.shingles))
        severity = "near" if len(matched) / total >= 0.05 else "trace"

    total = max(1, len(rec.shingles))
    overlap = len(matched) / total * 100.0
    return Finding(
        store_file=str(path),
        instance=rec.instance,
        seed=rec.seed,
        severity=severity,
        matched_shingles=len(matched),
        total_shingles=total,
        overlap_pct=round(overlap, 2),
        first_word_pos=first_pos,
        evidence_shingle=min(matched),
        content_ref=hashlib.sha256(rec.full_sha256.encode()).hexdigest()[:16],
    )


def finding_to_dict(f: Finding) -> dict:
    return asdict(f)
