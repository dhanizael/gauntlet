"""demo — the failure mode this project exists for, in seconds, $0, deterministic.

Three acts, using the real public APIs (run/grade/guard), with a scripted
"agent" so no LLM or network is needed:

  Act 1  baseline: v2 (memory-equipped agent) fails a task like v1. provisional.
  Act 2  v2's feedback loop writes the task + correct answer into its own
         persistent memory ("learning from mistakes" — a good feature!).
         Re-grade: KEEP, net +1.0. The improvement is real... and fake.
  Act 3  guard finds the task EXACTLY in the memory store -> instance retired;
         a FRESH holdout instance (new numbers) collapses the verdict to
         provisional. The +1.0 was memory, not intelligence.

The demo asserts its own narrative: if any act deviates, it exits non-zero.
"""

from __future__ import annotations

import tempfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from .experiment import Experiment, init_experiment, load_experiment
from .grade import GradeConfig, grade_experiment
from .guard import scan_store
from .manifest import add_instance, load_manifest, retire_instance
from .run import exec_trial, prep

TASK = (
    "Task frostgate-{k}: read task/fixtures/nums.txt, write the SUM OF SQUARES "
    "OF THE EVEN numbers to result.txt."
)
NUMS = {"A": "1 2 3 4", "B": "3 5 8 11"}
ANS = {"A": "20", "B": "64"}  # 2^2+4^2 ; 8^2

V1 = (
    "import pathlib;"
    "nums=[int(x) for x in pathlib.Path('task/fixtures/nums.txt').read_text().split()];"
    "pathlib.Path('result.txt').write_text(str(sum(nums)))"  # wrong method: plain sum
)
V2_TMPL = (
    "import pathlib, re\n"
    "mem = pathlib.Path({mem!r})\n"
    "t = pathlib.Path('task/prompt.txt').read_text()\n"
    "tid = re.search(r'frostgate-(\\w)', t).group(0)\n"
    "hit = None\n"
    "if mem.exists():\n"
    "    for line in mem.read_text().splitlines():\n"
    "        if tid in line and 'ANSWER:' in line:\n"
    "            hit = line.split('ANSWER:')[1].strip()\n"
    "if hit is None:\n"
    "    nums = [int(x) for x in pathlib.Path('task/fixtures/nums.txt').read_text().split()]\n"
    "    hit = str(sum(nums))\n"
    "pathlib.Path('result.txt').write_text(hit)\n"
)


def _experiment(root: Path, name: str, k: str) -> Experiment:
    tasks = [
        {
            "id": f"frostgate-{k}",
            "prompt": TASK.format(k=k),
            "verifier": {"type": "expect_file", "path": "result.txt", "equals": ANS[k]},
        }
    ]
    fx = root / f"fx-{name}"
    fx.mkdir()
    (fx / "nums.txt").write_text(NUMS[k])
    exp = init_experiment(root / name, tasks, ["v1", "v2"], repeats=1, seed=name)
    for slot in exp.slots():
        prep(exp, slot, fx)
    return exp


def _run_arms(exp: Path, mem: Path) -> None:
    e = load_experiment(exp)
    for slot, created in e.slots().items():
        script = V1 if created["arm"] == "v1" else V2_TMPL.format(mem=str(mem))
        exec_trial(e, slot, ["python3", "-c", script])


def _verdict(exp: Path) -> tuple[str, dict]:
    v = grade_experiment(exp, GradeConfig(primary="v2", baseline="v1", bootstrap_b=200))
    return str(v["decision"]), v


def run_demo() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        mem = root / "agent_memory" / "LESSONS.md"
        mem.parent.mkdir()
        mem.write_text("# agent memory\n")
        mf = root / "manifest.jsonl"
        prompt_a = root / "promptA.txt"
        prompt_a.write_text(TASK.format(k="A"))
        add_instance(mf, "frostgate-A", "seed-A", [prompt_a])

        print("gauntlet demo — 'did your agent improve, or did it remember the test?'")
        print("(scripted agents + the real public API; isolated temporary workdir)\n")

        # ---- Act 1: honest baseline ----------------------------------------------
        print("ACT 1 — baseline eval, task frostgate-A (both agents use the wrong method)")
        _experiment(root, "act1", "A")
        _run_arms(root / "act1", mem)
        d1, v1 = _verdict(root / "act1")
        print(
            f"  verdict: {d1.upper()} (net {v1['net_winrate']}) — "
            "v2's memory has nothing to offer yet"
        )
        assert d1 == "provisional", f"act 1 deviated: {d1}"

        # ---- Act 2: the agent 'learns from feedback' ------------------------------
        print("\nACT 2 — v2's feedback loop persists the task + correct answer to its memory")
        mem.write_text(mem.read_text() + f"{TASK.format(k='A')} ANSWER:{ANS['A']}\n")
        _experiment(root, "act2", "A")
        _run_arms(root / "act2", mem)
        d2, v2 = _verdict(root / "act2")
        print(f"  verdict: {d2.upper()} (net {v2['net_winrate']}) — ship it! v2 is +1.0 better!")
        assert d2 == "keep", f"act 2 deviated: {d2}"

        # ---- Act 3: the gauntlet ---------------------------------------------------
        print("\nACT 3 — guard scans the agent's persistent memory against the sealed manifest")
        res = scan_store(load_manifest(mf), [mem.parent])
        for f in res.findings:
            print(
                f"  [{f.severity.upper()}] {Path(f.store_file).name} :: {f.instance} "
                f"({f.matched_shingles}/{f.total_shingles} shingles) — hashes, not content"
            )
        assert any(f.severity == "exact" for f in res.findings), "act 3: contamination missed"
        retire_instance(mf, "frostgate-A")
        print("  instance frostgate-A RETIRED (a leaked holdout is dead; regenerate, don't repair)")

        print(
            "\nACT 3b — fresh holdout instance (same shape, new numbers), same agents, same memory"
        )
        _experiment(root, "act3", "B")
        _run_arms(root / "act3", mem)
        d3, v3 = _verdict(root / "act3")
        print(
            f"  verdict: {d3.upper()} (net {v3['net_winrate']}) — "
            "the +1.0 was memory, not intelligence"
        )
        assert d3 == "provisional", f"act 3b deviated: {d3}"

        print("\n" + "=" * 72)
        print("Traditional benchmarks assume every trial starts clean. Stateful agents")
        print("break that assumption. gauntlet is the integrity layer that notices.")
        print("\nreproduce anytime:  gauntlet demo   (exit 0 if the story holds)")
    return 0


def render_demo() -> str:
    """Run the self-asserting demo and return its complete public transcript."""
    buffer = StringIO()
    with redirect_stdout(buffer):
        assert run_demo() == 0
    return buffer.getvalue()
