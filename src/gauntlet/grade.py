"""grade — the verdict engine. Implements docs/GRADE_DESIGN.md literally.

Pipeline order is the design (chain of custody -> seal verify -> drift
quarantine -> deterministic grading -> paired signs -> bootstrap -> frozen
decision rule). Deviations are bugs; the design doc is the authority.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from .experiment import load_experiment
from .run import verify as verify_seal
from .verifier import VerifierError, grade_trial

ALPHA = 0.05
EXIT_KEEP, EXIT_REVERT, EXIT_PROVISIONAL, EXIT_INTEGRITY = 0, 1, 2, 3


@dataclass(frozen=True)
class GradeConfig:
    """Preregistered decision parameters — echoed verbatim into the verdict."""

    primary: str
    baseline: str
    margin: float = 0.10
    bootstrap_b: int = 10_000
    seed: int = 20260918
    require_every_task: bool = False
    max_excluded_pct: float = 25.0


def bootstrap_ci(
    signs: list[int], b: int = 10_000, seed: int = 20260918, alpha: float = ALPHA
) -> tuple[float, float]:
    """Percentile bootstrap CI of the mean, fixed seed => byte-reproducible."""
    n = len(signs)
    if n == 0:
        return (0.0, 0.0)
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(signs, k=n)) / n for _ in range(b))
    return means[int(b * alpha / 2)], means[min(b - 1, int(b * (1 - alpha / 2)))]


def grade_experiment(
    expdir: Path | str,
    cfg: GradeConfig,
    judge_scores: dict[str, float] | None = None,
) -> dict:
    expdir = Path(expdir)
    exp = load_experiment(expdir)
    arms = exp.header["arms"]
    for a in (cfg.primary, cfg.baseline):
        if a not in arms:
            raise VerifierError(f"unknown arm {a!r}; arms are {arms}")
    tasks_by_id = {t["id"]: t for t in exp.header["tasks"]}
    unblind_path = expdir / "unblind.json"
    unblind = json.loads(unblind_path.read_text()) if unblind_path.exists() else {}
    pseud_of = {v["slot"]: k for k, v in unblind.items()}

    ledger_sha = hashlib.sha256((expdir / "ledger.jsonl").read_bytes()).hexdigest()
    closed = [r for r in exp.records if r["kind"] == "closed"]
    created = exp.slots()

    def excl(slot: str, reason: str) -> dict:
        return {
            "slot": slot,
            "task": created[slot]["task"],
            "arm": created[slot]["arm"],
            "reason": reason,
        }

    # -- step 2: seal re-verification (fail-fast) --------------------------------
    violations = {s: v for s in (r["slot"] for r in closed) if (v := verify_seal(exp, s))}
    if violations:
        return {
            "schema": 1,
            "decision": None,
            "integrity_failure": True,
            "violations": violations,
            "ledger_sha256": ledger_sha,
            "reasons": ["seal violations detected; no verdict may be issued"],
        }

    # -- steps 3+4: quarantine and deterministic grading --------------------------
    excluded: list[dict] = []
    scored: dict[str, dict[str, list[float]]] = {}  # task -> arm -> scores
    for rec in closed:
        slot = rec["slot"]
        if rec["status"] == "sealed-drift":
            excluded.append(excl(slot, "env-drift"))
            continue
        task = tasks_by_id[created[slot]["task"]]
        verifier = task.get("verifier")
        if not verifier:
            excluded.append(excl(slot, "no-verifier"))
            continue
        try:
            res = grade_trial(exp, slot, verifier, judge_scores, pseud_of.get(slot))
        except VerifierError as exc:
            excluded.append(excl(slot, f"quarantined: {exc}"))
            continue
        scored.setdefault(task["id"], {}).setdefault(created[slot]["arm"], []).append(res["score"])

    excl_pct = 100.0 * len(excluded) / max(1, len(closed))

    # -- step 5: paired signs ------------------------------------------------------
    pairs: list[int] = []
    per_task: dict[str, dict] = {}
    for task_id, by_arm in sorted(scored.items()):
        pa, pb = by_arm.get(cfg.primary, []), by_arm.get(cfg.baseline, [])
        signs = [1 if a > b else -1 if a < b else 0 for a in pa for b in pb]
        per_task[task_id] = {
            "pairs": len(signs),
            "mean_sign": round(sum(signs) / len(signs), 4) if signs else None,
        }
        pairs += signs
    for task_id in tasks_by_id:
        per_task.setdefault(task_id, {"pairs": 0, "mean_sign": None, "note": "no graded trials"})

    # -- step 6: frozen decision rule ----------------------------------------------
    reasons: list[str] = []
    lo = hi = net = None
    if not pairs:
        decision: str | None = "provisional"
        reasons.append("no comparable pairs were graded")
    else:
        net = sum(pairs) / len(pairs)
        lo, hi = bootstrap_ci(pairs, b=cfg.bootstrap_b, seed=cfg.seed)
        if excl_pct > cfg.max_excluded_pct:
            decision = "provisional"
            reasons.append(
                f"evidence corrupted: {excl_pct:.0f}% trials excluded (> {cfg.max_excluded_pct}%)"
            )
        elif lo > cfg.margin:
            decision = "keep"
            if cfg.require_every_task:
                # no-evidence counts as no-win: absence of proof is absence of win
                bad = [
                    t
                    for t, s in per_task.items()
                    if s.get("mean_sign") is None or s["mean_sign"] <= 0
                ]
                if bad:
                    decision = "provisional"
                    reasons.append(f"require-every-task: no net win on {bad}")
            if decision == "keep":
                reasons.append(f"95% CI lower bound {lo:.3f} > margin {cfg.margin}")
        elif hi < -cfg.margin:
            decision = "revert"
            reasons.append(f"95% CI upper bound {hi:.3f} < -margin {cfg.margin}")
        else:
            decision = "provisional"
            reasons.append(f"CI [{lo:.3f}, {hi:.3f}] spans margin {cfg.margin}: no proof")

    return {
        "schema": 1,
        "decision": decision,
        "primary": cfg.primary,
        "baseline": cfg.baseline,
        "ledger_sha256": ledger_sha,
        "config": asdict(cfg),
        "pairs_graded": len(pairs),
        "net_winrate": None if net is None else round(net, 4),
        "ci95": None if lo is None or hi is None else [round(lo, 4), round(hi, 4)],
        "per_task": per_task,
        "excluded": excluded,
        "excluded_pct": round(excl_pct, 1),
        "reasons": reasons,
    }


def public_face(verdict: dict) -> dict:
    """Shareable view: identities and hashes only — no expected values, no
    stderr tails, no prompts (design: a report must never leak what it grades)."""
    v = json.loads(json.dumps(verdict))  # deep copy
    for ex in v.get("excluded", []):
        reason = ex.pop("reason", "")
        ex["reason_hash"] = hashlib.sha256(reason.encode()).hexdigest()[:12]
    return v


def exit_code(verdict: dict) -> int:
    if verdict.get("integrity_failure"):
        return EXIT_INTEGRITY
    return {"keep": EXIT_KEEP, "revert": EXIT_REVERT}.get(verdict.get("decision"), EXIT_PROVISIONAL)
