"""Environment fingerprints: the drift detector.

Born from a real incident: a subagent pip-installed mid-experiment, silently
invalidating every trial that ran after it. A gauntlet trial is only
comparable to its siblings if the environment at close matches the
environment at prep — anything else must be *detected and reported*, not
assumed away.

A fingerprint is (python version, platform, installed package set,
merkle-ish tree hash of the workspace file set). diff() enumerates exactly
what changed between two fingerprints.
"""

from __future__ import annotations

import hashlib
import platform as _platform
import sys
from importlib import metadata
from pathlib import Path

MAX_TREE_FILES = 20_000


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def package_set() -> list[str]:
    """Sorted installed distribution specs, e.g. 'requests==2.32.3'."""
    out = set()
    for dist in metadata.distributions():
        name = (dist.name or "").strip()
        ver = (dist.version or "").strip()
        if name and ver:
            out.add(f"{name.lower()}=={ver}")
    return sorted(out)


def tree_hash(root: Path) -> tuple[str, int]:
    """(hash of sorted (relpath, file-sha) pairs, file count)."""
    entries: list[str] = []
    n = 0
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.is_symlink():
            continue
        n += 1
        if n > MAX_TREE_FILES:
            return ("too-many-files", n)
        entries.append(f"{f.relative_to(root)}\n{sha_file(f)}")
    digest = hashlib.sha256("\n".join(entries).encode()).hexdigest()[:16]
    return digest, n


def fingerprint(root: Path) -> dict:
    pkgs = package_set()
    th, nf = tree_hash(root)
    return {
        "python": sys.version.split()[0],
        "platform": f"{_platform.system()}/{_platform.machine()}",
        "pkg_count": len(pkgs),
        "pkg_sha": hashlib.sha256("\n".join(pkgs).encode()).hexdigest()[:16],
        "packages": pkgs,
        "tree_sha": th,
        "files": nf,
    }


def diff(start: dict, end: dict) -> list[str]:
    """Environment drift: interpreter or installed packages changed between
    prep and close. The workspace tree intentionally grows during a trial
    (that is the output); its hash is recorded in both fingerprints for
    forensics but is NOT drift. Anything touching packages mid-trial is."""
    out: list[str] = []
    if start["python"] != end["python"]:
        out.append(f"python {start['python']} -> {end['python']}")
    if start["platform"] != end["platform"]:
        out.append(f"platform {start['platform']} -> {end['platform']}")
    if start["pkg_sha"] != end["pkg_sha"]:
        a, b = set(start["packages"]), set(end["packages"])
        out += [f"pkg+{p}" for p in sorted(b - a)]
        out += [f"pkg-{p}" for p in sorted(a - b)]

        def name_of(spec: str) -> str:
            return spec.split("==", maxsplit=1)[0]

        amap = {name_of(p): p for p in a}
        bmap = {name_of(p): p for p in b}
        out += [
            f"pkg~{n}: {amap[n].split('==')[-1]} -> {bmap[n].split('==')[-1]}"
            for n in sorted(set(amap) & set(bmap))
            if amap[n] != bmap[n]
        ]
    return out
