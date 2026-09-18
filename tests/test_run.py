import json
import sys
from pathlib import Path

import pytest

from gauntlet.cli import main as cli
from gauntlet.experiment import init_experiment, load_experiment
from gauntlet.run import SlotError, blindpack, close, exec_trial, prep, verify

TASKS = [
    {"id": "T1", "prompt": "Sort the numbers and report the median."},
    {"id": "T2", "prompt": "Count words that start with 'qu'."},
]
ARMS = ["harness", "raw"]


@pytest.fixture()
def exp(tmp_path):
    tf = tmp_path / "tasks.json"
    tf.write_text(json.dumps(TASKS))
    e = init_experiment(tmp_path / "exp", TASKS, ARMS, repeats=2, seed="test-seed")
    return e


def first_slot(e, task="T1"):
    return next(s for s, r in e.slots().items() if r["task"] == task)


# ---------- init ----------


def test_init_creates_full_trial_matrix(exp):
    assert len(exp.slots()) == 2 * 2 * 2  # tasks x arms x repeats
    arms = {r["arm"] for r in exp.slots().values()}
    assert arms == set(ARMS)
    assert (exp.dir / "exp.json").exists()
    assert len(exp.records) == 8


def test_init_rejects_single_arm(tmp_path):
    with pytest.raises(ValueError):
        init_experiment(tmp_path / "e", TASKS, ["only"], 2)


def test_init_rejects_dirty_dir(exp):
    with pytest.raises(FileExistsError):
        init_experiment(exp.dir, TASKS, ARMS, 1)


# ---------- prep ----------


def test_prep_workspace_and_prompt(exp):
    slot = first_slot(exp)
    res = prep(exp, slot, None)
    ws = Path(res["workspace"])
    assert (ws / "task" / "prompt.txt").read_text().startswith("Sort")
    state = load_experiment(exp.dir).state_of(slot)
    assert state["kind"] == "prepared"
    assert state["env_start"]["python"]


def test_prep_rejects_double_use(exp, tmp_path):
    slot = first_slot(exp)
    prep(exp, slot, None)
    with pytest.raises(SlotError):
        prep(exp, slot, None)


def test_prep_rejects_symlink_fixtures(exp, tmp_path):
    fx = tmp_path / "fx"
    fx.mkdir()
    (fx / "real.txt").write_text("ok")
    (fx / "evil.txt").symlink_to("/etc/passwd")
    slot = first_slot(exp)
    with pytest.raises(SlotError, match="symlink"):
        prep(exp, slot, fx)


def test_prep_verifies_fixture_shas(exp, tmp_path):
    fx = tmp_path / "fx"
    fx.mkdir()
    (fx / "data.csv").write_text("a,b\n1,2\n")
    slot = first_slot(exp)
    res = prep(exp, slot, fx)
    state = load_experiment(exp.dir).state_of(slot)
    copied = Path(state["workspace"]) / "task" / "fixtures" / "data.csv"
    assert copied.read_text() == "a,b\n1,2\n"
    assert state["fixtures"][0]["sha"]


# ---------- exec / close / drift ----------


def test_exec_seals_outputs_with_exit(exp):
    slot = first_slot(exp)
    prep(exp, slot, None)
    res = exec_trial(exp, slot, [sys.executable, "-c", "open('answer.txt','w').write('42')"])
    assert res["status"] == "sealed"
    assert res["exit"] == 0
    assert res["files"] == 1
    state = load_experiment(exp.dir).state_of(slot)
    assert state["outputs"][0]["path"] == "answer.txt"


def test_exec_captures_failure_exit(exp):
    slot = first_slot(exp)
    prep(exp, slot, None)
    res = exec_trial(exp, slot, [sys.executable, "-c", "raise SystemExit(3)"])
    assert res["exit"] == 3
    assert res["status"] == "sealed"


def test_task_input_never_sealed_as_output(exp):
    slot = first_slot(exp)
    prep(exp, slot, None)
    res = close(exp, slot)
    # task/ is input; a sealed trial with only inputs has zero outputs
    assert res["files"] == 0


# ---------- verify (tamper evidence) ----------


def test_verify_detects_post_close_edit(exp):
    slot = first_slot(exp)
    prep(exp, slot, None)
    exec_trial(exp, slot, [sys.executable, "-c", "open('out.txt','w').write('v1')"])
    assert verify(exp, slot) == []
    ws = exp.dir / "trials" / slot
    (ws / "out.txt").write_text("v2-TAMPERED")
    problems = verify(exp, slot)
    assert problems == ["modified out.txt"]


def test_verify_detects_deletion(exp):
    slot = first_slot(exp)
    prep(exp, slot, None)
    exec_trial(exp, slot, [sys.executable, "-c", "open('out.txt','w').write('x')"])
    (exp.dir / "trials" / slot / "out.txt").unlink()
    assert verify(exp, slot) == ["missing out.txt"]


# ---------- blindpack (judging artifacts must hide arms) ----------


def test_blindpack_hides_arms_and_slots(exp, tmp_path):
    for slot in list(exp.slots())[:4]:
        prep(exp, slot, None)
        exec_trial(exp, slot, [sys.executable, "-c", "open('result.txt','w').write('done')"])
    pack = tmp_path / "pack"
    res = blindpack(exp, pack)
    assert res["packed"] == 4
    blob = (
        (pack / "jobs.json").read_text().lower() + pack.joinpathpath
        if False
        else (pack / "jobs.json").read_text()
    )
    names = [p.name for p in (pack / "outputs").iterdir()]
    assert all("harness" not in n and "raw" not in n and not n.startswith("t-") for n in names)
    for line in json.loads(blob):
        assert "arm" not in line
    # unblind map stays private, inside expdir only
    unblind = json.loads((exp.dir / "unblind.json").read_text())
    assert len(unblind) == 4
    assert all(v["arm"] in ARMS for v in unblind.values())
    assert (exp.dir / "unblind.json").stat().st_mode & 0o777 == 0o600


def test_blindpack_copies_content_matching_seal(exp, tmp_path):
    slot = first_slot(exp)
    prep(exp, slot, None)
    exec_trial(exp, slot, [sys.executable, "-c", "open('result.txt','w').write('payload')"])
    pack = tmp_path / "pack"
    blindpack(exp, pack)
    pseud = next(iter(json.loads((exp.dir / "unblind.json").read_text())))
    assert (pack / "outputs" / pseud / "result.txt").read_text() == "payload"


# ---------- version consistency (release hygiene) ----------


def test_version_single_source():
    import tomllib
    from gauntlet import __version__

    pyproj = tomllib.loads(Path("pyproject.toml").read_text())
    assert pyproj["project"]["version"] == __version__


# ---------- CLI end-to-end ----------


def test_cli_run_flow(tmp_path, capsys):
    tf = tmp_path / "tasks.json"
    tf.write_text(json.dumps(TASKS))
    ed = tmp_path / "exp"
    assert cli(["run", "init", str(ed), "--tasks", str(tf), "--arms", "a,b", "--repeats", "1"]) == 0
    exp = load_experiment(ed)
    slot = first_slot(exp)
    assert cli(["run", "prep", str(ed), "--slot", slot]) == 0
    assert cli(["run", "exec", str(ed), "--slot", slot, "--", "sh", "-c", "echo hi > o.txt"]) == 0
    st = cli(["run", "status", str(ed)])
    assert st == 0
    out = capsys.readouterr().out
    assert slot in out
    assert "arm=" not in out  # arm assignment hidden by default
    assert cli(["run", "verify", str(ed), "--slot", slot]) == 0
    assert cli(["run", "blindpack", str(ed), "--out", str(tmp_path / "pack")]) == 0
