"""Experiment records: header, append-only ledger, opaque trial slots.

The ledger is the protocol's memory. It is append-only (flush + fsync per
record) so the sequence "prepared -> closed -> sealed" cannot be quietly
back-dated, and trial slots carry opaque ids so that arm assignment never
leaks through paths, filenames, or judge-visible artifacts. Blinding is a
property of the artifacts you hand the judge; the unblinding map lives only
on the private side.
"""

from __future__ import annotations

import json
import os
import random
import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .envfp import sha_file

LEDGER = "ledger.jsonl"
HEADER = "exp.json"
SLOT_PREFIX = "t-"


@dataclass
class Experiment:
    dir: Path
    header: dict
    records: list[dict] = field(default_factory=list)

    def slots(self) -> dict[str, dict]:
        return {r["slot"]: r for r in self.records if r["kind"] == "trial-created"}

    def state_of(self, slot: str) -> dict:
        """Latest record per slot: the state machine projects over the log."""
        latest: dict[str, dict] = {}
        for r in self.records:
            if r["kind"] != "trial-created":
                latest[r["slot"]] = r
        return latest.get(slot, {})


def init_experiment(
    expdir: Path | str,
    tasks: list[dict],
    arms: list[str],
    repeats: int,
    seed: str | None = None,
) -> Experiment:
    expdir = Path(expdir)
    if expdir.exists() and any(expdir.iterdir()):
        raise FileExistsError(f"{expdir} exists and is not empty")
    if len(arms) < 2:
        raise ValueError("a run needs at least two arms to compare")
    if repeats < 1 or not tasks:
        raise ValueError("need >=1 repeats and >=1 tasks")
    expdir.mkdir(parents=True, exist_ok=True)
    (expdir / "trials").mkdir()
    used_seed = seed or f"time-{int(time.time())}"
    rng = random.Random(used_seed)
    header = {
        "schema": 1,
        "id": f"exp-{secrets.token_hex(4)}",
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "tasks": tasks,
        "arms": arms,
        "repeats": repeats,
        "assignment_seed": used_seed,
    }
    exp = Experiment(dir=expdir, header=header)
    _write_json_atomic(expdir / HEADER, header)
    combos = [(t, a) for t in range(len(tasks)) for a in range(len(arms)) for _ in range(repeats)]
    rng.shuffle(combos)
    for ti, ai in combos:
        slot = f"{SLOT_PREFIX}{secrets.token_hex(4)}"
        append_record(
            expdir,
            {
                "kind": "trial-created",
                "slot": slot,
                "task": tasks[ti]["id"],
                "arm": arms[ai],
                "created": datetime.now(UTC).isoformat(timespec="seconds"),
            },
        )
    exp.records = load_ledger(expdir)
    return exp


def load_experiment(expdir: Path | str) -> Experiment:
    expdir = Path(expdir)
    header = json.loads((expdir / HEADER).read_text())
    return Experiment(dir=expdir, header=header, records=load_ledger(expdir))


def append_record(expdir: Path, rec: dict) -> None:
    rec = {**rec, "at": datetime.now(UTC).isoformat(timespec="seconds")}
    with (expdir / LEDGER).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def load_ledger(expdir: Path) -> list[dict]:
    path = expdir / LEDGER
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def workspace_of(expdir: Path | str, slot: str) -> Path:
    expdir = Path(expdir)
    if not slot.startswith(SLOT_PREFIX) or len(slot) != len(SLOT_PREFIX) + 8:
        raise ValueError(f"malformed slot id: {slot!r}")
    return expdir / "trials" / slot


def task_prompt(exp: Experiment, task_id: str) -> str:
    for t in exp.header["tasks"]:
        if t["id"] == task_id:
            return t["prompt"]
    raise KeyError(f"unknown task {task_id!r}")


def files_manifest(root: Path, exclude_prefixes: tuple[str, ...] = ()) -> list[dict]:
    """Seal artifact: every file's relpath, size, sha. Used by close + verify."""
    out = []
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.is_symlink():
            continue
        rel = str(f.relative_to(root))
        if rel.startswith(exclude_prefixes):
            continue
        out.append({"path": rel, "size": f.stat().st_size, "sha": sha_file(f)})
    return out


def _write_json_atomic(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=True))
    tmp.replace(path)
