"""T1-T11 from docs/GRADE_DESIGN.md — every committed test exists."""

import json
from pathlib import Path

import pytest

from gauntlet.experiment import append_record, init_experiment, load_experiment
from gauntlet.grade import GradeConfig, bootstrap_ci, exit_code, grade_experiment, public_face
from gauntlet.run import blindpack, prep, exec_trial

GOOD = "import pathlib;pathlib.Path('result.txt').write_text('42')"
BAD = "import pathlib;pathlib.Path('result.txt').write_text('0')"
VER = {"type": "expect_file", "path": "result.txt", "equals": "42"}


_build_n = 0


def build(tmp_path, tasks, arms=("good", "bad"), repeats=3, good_on=None, scripts=None):
    """Full experiment through exec; good/bad write correct/wrong answers per task."""
    global _build_n
    _build_n += 1
    tf = tmp_path / "tasks.json"
    tf.write_text(json.dumps(tasks))
    exp = init_experiment(tmp_path / f"exp{_build_n}", tasks, list(arms), repeats=repeats, seed="t")
    scripts = scripts or {}
    for slot, created in exp.slots().items():
        prep(exp, slot, None)
        correct = created["arm"] == "good"
        if good_on is not None:
            correct = correct and created["task"] in good_on
        script = scripts.get((created["task"], created["arm"]), GOOD if correct else BAD)
        exec_trial(exp, slot, ["python3", "-c", script])
    return exp


def cfg(**kw):
    base = dict(primary="good", baseline="bad")
    base.update(kw)
    return GradeConfig(**base)


def task(tid="median", verifier=None):
    return {"id": tid, "prompt": "write the answer", "verifier": verifier or VER}


# ---- T2: unanimous wins => keep, exit 0
def test_keep_unanimous(tmp_path):
    exp = build(tmp_path, [task()])
    v = grade_experiment(exp.dir, cfg())
    assert v["decision"] == "keep" and exit_code(v) == 0
    assert v["pairs_graded"] == 9 and v["net_winrate"] == 1.0


# ---- T3: identical arms => provisional, exit 2
def test_tie_provisional(tmp_path):
    exp = build(tmp_path, [task()], scripts={("median", "bad"): GOOD})
    v = grade_experiment(exp.dir, cfg())
    assert v["decision"] == "provisional" and exit_code(v) == 2


# ---- T1: byte-identical reproducibility
def test_determinism(tmp_path):
    exp = build(tmp_path, [task()])
    a = json.dumps(grade_experiment(exp.dir, cfg()), sort_keys=True)
    b = json.dumps(grade_experiment(exp.dir, cfg()), sort_keys=True)
    assert a == b
    assert json.loads(a)["ledger_sha256"]


# ---- T6: tampered output => integrity failure, exit 3, no verdict
def test_seal_violation_blocks_verdict(tmp_path):
    exp = build(tmp_path, [task()])
    slot = next(iter(exp.slots()))
    (exp.dir / "trials" / slot / "result.txt").write_text("42")  # rewrite with same value
    # same bytes => same sha; tamper with an ACTUALLY different value on another trial:
    slot2 = list(exp.slots())[1]
    (exp.dir / "trials" / slot2 / "result.txt").write_text("TAMPERED")
    v = grade_experiment(exp.dir, cfg())
    assert v.get("integrity_failure") and v["decision"] is None and exit_code(v) == 3


# ---- T4: drift trials excluded and named
def test_drift_excluded_and_listed(tmp_path):
    exp = build(tmp_path, [task()], repeats=2)
    # forge a sealed-drift record for one slot (consumer-side contract test)
    exp = load_experiment(exp.dir)
    slot = list(exp.slots())[0]
    prep_rec = next(r for r in exp.records if r["kind"] == "prepared" and r["slot"] == slot)
    close_rec = next(r for r in exp.records if r["kind"] == "closed" and r["slot"] == slot)
    append_record(
        exp.dir,
        {
            "kind": "closed",
            "slot": slot,
            "env_end": prep_rec["env_start"],
            "drift": ["pkg+evil==1.0"],
            "outputs": close_rec["outputs"],
            "exit": 0,
            "duration_s": 0.1,
            "argv": [],
            "status": "sealed-drift",
        },
    )
    exp2 = load_experiment(exp.dir)
    v = grade_experiment(exp2.dir, cfg())
    assert any(e["slot"] == slot and "env-drift" in e["reason"] for e in v["excluded"])
    assert v["decision"] == "keep"  # 6 honest pairs still all win


# ---- T5: >25% exclusions => corrupted evidence => provisional
def test_corruption_threshold(tmp_path):
    exp = build(tmp_path, [task()], repeats=1)  # 2 trials total
    exp = load_experiment(exp.dir)
    preps = {r["slot"]: r for r in exp.records if r["kind"] == "prepared"}
    closes = {r["slot"]: r for r in exp.records if r["kind"] == "closed"}
    for slot in preps:
        append_record(
            exp.dir,
            {
                "kind": "closed",
                "slot": slot,
                "env_end": preps[slot]["env_start"],
                "drift": ["pkg+evil==1"],
                "outputs": closes[slot]["outputs"],
                "exit": 0,
                "duration_s": 0.1,
                "argv": [],
                "status": "sealed-drift",
            },
        )
    v = grade_experiment(exp.dir, cfg())
    assert v["decision"] == "provisional"
    assert any("corrupted" in r for r in v["reasons"])


# ---- T7: require-every-task blocks one-task heroics (and missing evidence)
def test_require_every_task(tmp_path):
    tasks = [task("a"), task("b"), task("c"), task("d")]
    exp = build(tmp_path, tasks, repeats=3, good_on={"a", "b", "c"})  # loses on d
    v = grade_experiment(exp.dir, cfg())
    assert v["decision"] == "keep"  # net 18+/9- clears margin
    v2 = grade_experiment(exp.dir, cfg(require_every_task=True))
    assert v2["decision"] == "provisional"
    assert any("require-every-task" in r for r in v2["reasons"])


# ---- T8: judge scores break pass/pass ties
def test_judge_breaks_ties(tmp_path):
    jver = {"type": "judge"}
    tasks = [task("j", verifier=jver)]
    scripts = {("j", "good"): GOOD, ("j", "bad"): GOOD}  # both produce output
    exp = build(tmp_path, tasks, scripts=scripts, repeats=2)
    pack = tmp_path / "pack"
    blindpack(exp, pack)
    unblind = json.loads((exp.dir / "unblind.json").read_text())
    scores = {p: (0.9 if m["arm"] == "good" else 0.1) for p, m in unblind.items()}
    sf = tmp_path / "scores.json"
    sf.write_text(json.dumps(scores))
    v = grade_experiment(exp.dir, cfg(), judge_scores=json.loads(sf.read_text()))
    assert v["decision"] == "keep"
    # without judge scores: all trials quarantined -> no pairs -> provisional
    v2 = grade_experiment(exp.dir, cfg())
    assert v2["decision"] == "provisional" and v2["pairs_graded"] == 0


# ---- T9: verdict is redacted by construction, public face hashes exclusions
def test_redaction(tmp_path):
    exp = build(tmp_path, [task()])
    v = grade_experiment(exp.dir, cfg())
    blob = json.dumps(v)
    assert '"42"' not in blob  # expected values never serialize (private face already clean)
    pub = json.dumps(public_face(v))
    assert '"42"' not in pub
    assert "reason_hash" in pub or not v["excluded"]


# ---- T10: exit codes exhaustive
def test_exit_codes_exhaustive(tmp_path):
    keep = grade_experiment(build(tmp_path, [task()]).dir, cfg())
    assert exit_code(keep) == 0
    rev = build(
        tmp_path,
        [task()],
        scripts={
            ("median", "bad"): GOOD,
            ("median", "good"): "import pathlib;pathlib.Path('result.txt').write_text('0')",
        },
    )
    v = grade_experiment(rev.dir, cfg())
    assert v["decision"] == "revert" and exit_code(v) == 1


# ---- T11: bootstrap determinism and boundary values
def test_bootstrap():
    assert bootstrap_ci([1] * 8) == (1.0, 1.0)
    a = bootstrap_ci([1, -1] * 20)
    assert a == bootstrap_ci([1, -1] * 20)
    assert a[0] < 0 < a[1]
    assert bootstrap_ci([]) == (0.0, 0.0)
