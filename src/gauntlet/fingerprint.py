"""Text fingerprinting: normalize, shingle, hash.

Everything the scanner needs to compare stores against instances without
ever treating task content as printable output.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

SHINGLE_WORDS = 8


def normalize(text: str) -> str:
    """Aggressive but deterministic: unicode-fold, lowercase, strip punctuation."""
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def word_shingles(norm_text: str, k: int = SHINGLE_WORDS) -> list[tuple[int, str]]:
    """Return (word_position, shingle_hash) for every k-word window of normalized text."""
    words = norm_text.split()
    out: list[tuple[int, str]] = []
    for i in range(max(0, len(words) - k + 1)):
        window = " ".join(words[i : i + k])
        out.append((i, hashlib.sha256(window.encode()).hexdigest()[:16]))
    return out


def shingle_set(norm_text: str, k: int = SHINGLE_WORDS) -> set[str]:
    return {h for _, h in word_shingles(norm_text, k)}


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
