"""run — the trial protocol: prep, exec, close, verify, blindpack.

Every mechanism here exists because of a real failure mode:
  prep      — fresh opaque workspace per trial; fixtures copied (never linked)
              with per-file sha verification (the 2026-09-15 hardlink incident:
              subagents editing "copies" that shared inodes, corrupting
              sibling runs).
  exec      — runs any agent command with cwd=workspace, records exit + duration.
  close     — environment fingerprint at close must equal prep (the drift
              incident: mid-run pip installs); diffs are enumerated, never hidden.
  verify    — recompute the seal; a post-close file edit is detectable.
  blindpack — artifacts handed to any judge contain pseudonyms only; arm
              labels and slot ids live exclusively in the private unblind map.
"""

from __future__ import annotations

import json
import os
import random
import secrets as sec
import shutil
import subprocess
import time
from pathlib import Path

from . import envfp
from .experiment import Experiment, append_record, files_manifest, load_ledger, workspace_of


class SlotError(RuntimeError):
    pass


def prep(exp: Experiment, slot: str, fixtures: Path | None) -> dict:
    exp.records = load_ledger(exp.dir)
    created = exp.slots().get(slot)
    if created is None:
        raise SlotError(f"unknown slot {slot!r}")
    if exp.state_of(slot).get("kind") == "prepared":
        raise SlotError(f"{slot} already prepared")
    ws = workspace_of(exp.dir, slot)
    if ws.exists():
        raise SlotError(f"workspace {ws} already exists (slots are single-use)")
    (ws / "task").mkdir(parents=True)
    from .experiment import task_prompt  # late import: keeps header read path cheap

    (ws / "task" / "prompt.txt").write_text(task_prompt(exp, created["task"]))
    fixture_files: list[dict] = []
    if fixtures is not None:
        _copy_verified(fixtures, ws / "task" / "fixtures", fixture_files)
    start = envfp.fingerprint(ws)
    append_record(
        exp.dir,
        {
            "kind": "prepared",
            "slot": slot,
            "workspace": str(ws),
            "env_start": start,
            "fixtures": fixture_files,
        },
    )
    return {"slot": slot, "workspace": str(ws), "task": created["task"]}


def close(
    exp: Experiment,
    slot: str,
    exit_code: int | None = None,
    duration: float | None = None,
    argv: list[str] | None = None,
) -> dict:
    exp.records = load_ledger(exp.dir)
    state = exp.state_of(slot)
    if state.get("kind") != "prepared":
        raise SlotError(f"{slot} is not prepared (state: {state.get('kind', 'created')})")
    ws = workspace_of(exp.dir, slot)
    end = envfp.fingerprint(ws)
    drift = envfp.diff(state["env_start"], end)
    outputs = files_manifest(ws, exclude_prefixes=("task",))
    status = "sealed-drift" if drift else "sealed"
    append_record(
        exp.dir,
        {
            "kind": "closed",
            "slot": slot,
            "env_end": end,
            "drift": drift,
            "outputs": outputs,
            "exit": exit_code,
            "duration_s": None if duration is None else round(duration, 3),
            "argv": argv,
            "status": status,
        },
    )
    return {
        "slot": slot,
        "status": status,
        "drift": drift,
        "files": len(outputs),
        "exit": exit_code,
        "duration_s": None if duration is None else round(duration, 3),
    }


def exec_trial(exp: Experiment, slot: str, cmd: list[str], timeout: float | None = None) -> dict:
    exp.records = load_ledger(exp.dir)
    state = exp.state_of(slot)
    if state.get("kind") != "prepared":
        raise SlotError(f"{slot} must be prepared before exec")
    ws = workspace_of(exp.dir, slot)
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, cwd=ws, timeout=timeout)
        code, err = proc.returncode, None
    except subprocess.TimeoutExpired:
        code, err = -1, "timeout"
    dur = time.perf_counter() - t0
    res = close(exp, slot, exit_code=code, duration=dur, argv=cmd)
    res["timeout"] = err
    return res


def verify(exp: Experiment, slot: str) -> list[str]:
    """Recompute the seal of a closed trial; returns mismatch lines ([] = intact)."""
    exp.records = load_ledger(exp.dir)
    state = exp.state_of(slot)
    if state.get("kind") != "closed":
        raise SlotError(f"{slot} is not closed (state: {state.get('kind', 'created')})")
    ws = workspace_of(exp.dir, slot)
    sealed = {o["path"]: o for o in state["outputs"]}
    current = {o["path"]: o for o in files_manifest(ws, exclude_prefixes=("task",))}
    problems: list[str] = []
    for path, meta in sorted(sealed.items()):
        if path not in current:
            problems.append(f"missing {path}")
        elif current[path]["sha"] != meta["sha"]:
            problems.append(f"modified {path}")
    for path in sorted(set(current) - set(sealed)):
        problems.append(f"added {path}")
    return problems


def blindpack(exp: Experiment, packdir: Path) -> dict:
    """Emit judge-facing artifacts: pseudonym -> outputs, shuffled job list.
    The unblind map (pseudonym -> slot/arm) is written ONLY into the experiment
    directory (private side) with 0600 intent."""
    exp.records = load_ledger(exp.dir)
    sealed = [r for r in exp.records if r["kind"] == "closed"]
    if not sealed:
        raise SlotError("nothing to pack: no closed trials")
    packdir.mkdir(parents=True, exist_ok=True)
    jobs: list[dict] = []
    unblind: dict[str, dict] = {}
    for rec in sealed:
        slot = rec["slot"]
        created = exp.slots()[slot]
        pseud = f"s-{sec.token_hex(5)}"
        src = workspace_of(exp.dir, slot)
        dst = packdir / "outputs" / pseud
        for out in rec["outputs"]:
            s = src / out["path"]
            d = dst / out["path"]
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(s, d)
        jobs.append({"pseud": pseud, "task": created["task"], "status": rec["status"]})
        unblind[pseud] = {"slot": slot, "arm": created["arm"], "task": created["task"]}
    rng = random.Random()
    rng.shuffle(jobs)
    (packdir / "jobs.json").write_text(json.dumps(jobs, indent=1))
    (packdir / "BLIND.md").write_text(
        "This pack is BLIND: file paths and job entries identify trials only by\n"
        "pseudonym. Arm assignments are in the experiment's unblind.json (private side).\n"
        "Judge each output against its task rubric without speculating on provenance.\n"
    )
    unblind_path = exp.dir / "unblind.json"
    fd = unblind_path.open("w")
    fd.write(json.dumps(unblind, indent=1, sort_keys=True))
    fd.close()
    os.chmod(unblind_path, 0o600)
    append_record(exp.dir, {"kind": "blindpacked", "count": len(jobs), "pack": str(packdir)})
    return {"packed": len(jobs), "pack": str(packdir), "unblind": str(unblind_path)}


def _copy_verified(src_root: Path, dst_root: Path, audit: list[dict]) -> None:
    dst_root.mkdir(parents=True, exist_ok=True)
    for f in sorted(src_root.rglob("*")):
        if f.is_symlink():
            raise SlotError(f"symlink in fixtures refused: {f}")
        if not f.is_file():
            continue
        rel = f.relative_to(src_root)
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, dst)
        src_sha, dst_sha = envfp.sha_file(f), envfp.sha_file(dst)
        if src_sha != dst_sha:
            raise SlotError(f"copy verification FAILED for {rel}")
        audit.append({"path": str(rel), "sha": src_sha})
