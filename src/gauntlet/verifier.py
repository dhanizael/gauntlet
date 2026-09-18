"""verifier — deterministic scoring of sealed trial outputs.

Runs against a READ-ONLY COPY of the sealed outputs in a temp dir: evidence
is never mutated, check commands are sandboxed by cwd and timeout. Verifier
specs live in the experiment header (private side); details returned here may
contain expected values and are therefore private-face by default.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .envfp import sha_file
from .experiment import Experiment, load_ledger, workspace_of


class VerifierError(RuntimeError):
    pass


def grade_trial(
    exp: Experiment,
    slot: str,
    verifier: dict,
    judge_scores: dict[str, float] | None = None,
    pseud: str | None = None,
) -> dict:
    """Returns {"score": 0|1, "detail": str, "kind": str}."""
    kind = verifier.get("type")
    if kind == "judge":
        if judge_scores is None or pseud is None or pseud not in judge_scores:
            raise VerifierError(f"trial {slot}: judge score missing (quarantine)")
        s = float(judge_scores[pseud])
        return {"score": s, "detail": f"judge={s:.3f}", "kind": kind}
    ws = workspace_of(exp.dir, slot)
    state = _closed_state(exp, slot)
    with tempfile.TemporaryDirectory() as td:
        copy = Path(td)
        for out in state["outputs"]:
            dst = copy / out["path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ws / out["path"], dst)
        if kind == "expect_file":
            return _expect_file(copy, verifier)
        if kind == "check_cmd":
            return _check_cmd(copy, verifier)
    raise VerifierError(f"unknown verifier type {kind!r}")


def _closed_state(exp: Experiment, slot: str) -> dict:
    exp.records = load_ledger(exp.dir)
    state = exp.state_of(slot)
    if state.get("kind") != "closed":
        raise VerifierError(f"trial {slot} is not closed")
    return state


def _expect_file(copy: Path, v: dict) -> dict:
    target = copy / v["path"]
    if not target.exists():
        return {"score": 0, "detail": f"missing {v['path']}", "kind": "expect_file"}
    actual = target.read_text(encoding="utf-8", errors="replace")
    if "equals" in v:
        ok = actual.strip() == str(v["equals"]).strip()
        detail = f"equals {'OK' if ok else 'FAIL'} (sha {sha_file(target)[:8]})"
    elif "regex" in v:
        ok = re.search(v["regex"], actual) is not None
        detail = f"regex {'OK' if ok else 'FAIL'} (sha {sha_file(target)[:8]})"
    else:
        raise VerifierError("expect_file needs equals or regex")
    return {"score": 1 if ok else 0, "detail": detail, "kind": "expect_file"}


def _check_cmd(copy: Path, v: dict) -> dict:
    argv = v["argv"]
    if not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
        raise VerifierError("check_cmd argv must be list[str]")
    try:
        proc = subprocess.run(
            argv,
            cwd=copy,
            capture_output=True,
            text=True,
            timeout=float(v.get("timeout", 30)),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"score": 0, "detail": f"timeout cmd argv[0]={argv[0]}", "kind": "check_cmd"}
    except OSError as exc:
        raise VerifierError(f"check_cmd unrunnable: {exc}") from exc
    tail = (proc.stderr or "").strip()[-200:]
    detail = f"exit={proc.returncode}" + (
        f" stderr_tail={tail!r}" if tail and proc.returncode else ""
    )
    return {"score": 1 if proc.returncode == 0 else 0, "detail": detail, "kind": "check_cmd"}
