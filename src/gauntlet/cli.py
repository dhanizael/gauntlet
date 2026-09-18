"""gauntlet CLI — sealed holdouts, persistence-leak guards, keep/revert verdicts.

commands:
  gauntlet manifest add|list|retire      sealed instance registry (private side)
  gauntlet guard scan|selftest|audit     persistence-leak detection + surface discovery
  gauntlet run init|prep|exec|close|status|verify|blindpack   trial protocol
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from . import __version__
from .audit import audit_surfaces, audit_to_dict, format_report
from .demo import run_demo
from .experiment import init_experiment, load_experiment
from .grade import GradeConfig, exit_code, grade_experiment, public_face
from .guard import finding_to_dict, scan_store
from .holdout import (
    HoldoutIntegrityError,
    HoldoutUsageError,
    generate,
    retire,
    status,
)
from .holdout import (
    verify as holdout_verify,
)
from .manifest import add_instance, load_manifest, retire_instance
from .run import SlotError, blindpack, close, exec_trial, prep, verify

BANNER = f"gauntlet {__version__} — the anti-cheating layer for evaluating self-improving agents"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gauntlet", description=BANNER)
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("manifest", help="manage instance manifests (SECRET — private side only)")
    msub = m.add_subparsers(dest="mcmd", required=True)
    ma = msub.add_parser("add", help="register a task instance from its files")
    ma.add_argument("manifest", type=Path)
    ma.add_argument("--instance", required=True)
    ma.add_argument("--seed", default="")
    ma.add_argument("files", type=Path, nargs="+")
    ml = msub.add_parser("list", help="list instances (metadata only, no content)")
    ml.add_argument("manifest", type=Path)
    mr = msub.add_parser("retire", help="mark an instance retired (its content leaked)")
    mr.add_argument("manifest", type=Path)
    mr.add_argument("--instance", required=True)

    g = sub.add_parser("guard", help="scan agent persistent stores for task leakage")
    gsub = g.add_subparsers(dest="gcmd", required=True)
    gs = gsub.add_parser("scan", help="scan stores against a manifest")
    gs.add_argument("manifest", type=Path)
    gs.add_argument("--store", type=Path, action="append", required=True)
    gs.add_argument("--min-overlap", type=int, default=2)
    gs.add_argument("--max-bytes", type=int, default=8 * 1024 * 1024)
    gs.add_argument("--json", type=Path, default=None)
    gsub.add_parser("selftest", help="plant a synthetic leak and prove it is caught")
    gau = gsub.add_parser(
        "audit",
        help="find agent memory surfaces on this machine (zero setup, content-free)",
    )
    gau.add_argument("roots", type=Path, nargs="*", help="dirs to walk (default: home)")
    gau.add_argument("--max-depth", type=int, default=6)
    gau.add_argument("--max-files", type=int, default=250_000)
    gau.add_argument("--max-seconds", type=float, default=20.0)
    gau.add_argument("--json", type=Path, default=None)

    r = sub.add_parser("run", help="trial protocol: isolated arms, drift checks, sealed outputs")
    rsub = r.add_subparsers(dest="rcmd", required=True)
    ri = rsub.add_parser("init", help="create an experiment (tasks x arms x repeats)")
    ri.add_argument("expdir", type=Path)
    ri.add_argument("--tasks", type=Path, required=True, help="JSON: [{id, prompt}, ...]")
    ri.add_argument("--arms", required=True, help="comma-separated, e.g. harness,raw")
    ri.add_argument("--repeats", type=int, default=3)
    ri.add_argument("--seed", default=None, help="assignment seed (audit trail)")
    rp = rsub.add_parser("prep", help="fresh opaque workspace for one trial")
    rp.add_argument("expdir", type=Path)
    rp.add_argument("--slot", required=True)
    rp.add_argument("--fixtures", type=Path, default=None)
    rx = rsub.add_parser("exec", help="run any agent command inside the trial workspace")
    rx.add_argument("expdir", type=Path)
    rx.add_argument("--slot", required=True)
    rx.add_argument("--timeout", type=float, default=None)
    rx.add_argument("agent_cmd", nargs="*", help="agent command after --")
    rc = rsub.add_parser("close", help="close a prepared trial (drift check + seal)")
    rc.add_argument("expdir", type=Path)
    rc.add_argument("--slot", required=True)
    rs = rsub.add_parser("status", help="trial states (arm hidden unless --reveal)")
    rs.add_argument("expdir", type=Path)
    rs.add_argument("--reveal", action="store_true")
    rv = rsub.add_parser("verify", help="recompute a trial's seal; list any tampering")
    rv.add_argument("expdir", type=Path)
    rv.add_argument("--slot", required=True)
    rb = rsub.add_parser("blindpack", help="emit judge-facing artifacts, pseudonymized")
    rb.add_argument("expdir", type=Path)
    rb.add_argument("--out", type=Path, required=True)

    # argparse's "--" handling differs across 3.11-3.13 (CI caught what local
    # could not); split the agent command off manually so the convention
    # "gauntlet run exec DIR --slot S -- CMD..." works on every version.
    argv = list(sys.argv[1:] if argv is None else argv)
    trailing_cmd: list[str] = []
    if len(argv) >= 2 and argv[0] == "run" and argv[1] == "exec" and "--" in argv[2:]:
        idx = argv.index("--", 2)
        trailing_cmd, argv = argv[idx + 1 :], argv[:idx]
    gr = sub.add_parser(
        "grade", help="verdict engine: keep/revert/provisional (exit code IS the verdict)"
    )
    gr.add_argument("expdir", type=Path)
    gr.add_argument("--primary", required=True, help="arm claiming the improvement")
    gr.add_argument("--baseline", required=True, help="arm to beat")
    gr.add_argument("--margin", type=float, default=0.10)
    gr.add_argument("--bootstrap-b", type=int, default=10_000)
    gr.add_argument("--seed", type=int, default=20260918)
    gr.add_argument("--judge-scores", type=Path, default=None, help="blind pseud->score JSON")
    gr.add_argument("--require-every-task", action="store_true")
    gr.add_argument("--max-excluded-pct", type=float, default=25.0)
    gr.add_argument("--json", type=Path, default=None, help="private-face verdict JSON")
    gr.add_argument("--public", type=Path, default=None, help="redacted shareable verdict JSON")

    sub.add_parser("demo", help="3-minute story: agent that 'improves' by remembering the test")

    h = sub.add_parser(
        "holdout", help="fresh-instance generation + retirement ledger (private side)"
    )
    hsub = h.add_subparsers(dest="hcmd", required=True)
    hn = hsub.add_parser("new", help="generate provably-fresh instances from a family template")
    hn.add_argument("family", type=Path)
    hn.add_argument("--manifest", type=Path, required=True)
    hn.add_argument("--private-dir", type=Path, required=True)
    hn.add_argument("--count", type=int, default=1)
    hn.add_argument("--seed", default=None, help="explicit seed for exact reproduction")
    hn.add_argument("--ledger", type=Path, default=None)
    hr = hsub.add_parser("retire", help="retire a leaked instance (manifest first, ledger second)")
    hr.add_argument("family", type=Path)
    hr.add_argument("--instance", required=True)
    hr.add_argument("--manifest", type=Path, required=True)
    hr.add_argument("--private-dir", type=Path, required=True)
    hr.add_argument("--ledger", type=Path, default=None)
    hs = hsub.add_parser("status", help="family counts, cardinality, warnings")
    hs.add_argument("family", type=Path)
    hs.add_argument("--manifest", type=Path, required=True)
    hs.add_argument("--private-dir", type=Path, required=True)
    hs.add_argument("--ledger", type=Path, default=None)
    hv = hsub.add_parser("verify", help="ledger chain + manifest reconciliation (+ --deep)")
    hv.add_argument("family", type=Path)
    hv.add_argument("--manifest", type=Path, required=True)
    hv.add_argument("--private-dir", type=Path, required=True)
    hv.add_argument("--ledger", type=Path, default=None)
    hv.add_argument(
        "--deep", action="store_true", help="re-derive every instance from template+seed"
    )

    args = ap.parse_args(argv)
    if getattr(args, "rcmd", None) == "exec" and trailing_cmd:
        args.agent_cmd = trailing_cmd

    if args.cmd == "holdout":
        return _holdout(args)

    if args.cmd == "manifest" and args.mcmd == "add":
        rec = add_instance(args.manifest, args.instance, args.seed, args.files)
        print(f"registered {rec.instance} ({len(rec.shingles)} shingles, seed={rec.seed!r})")
        return 0
    if args.cmd == "manifest" and args.mcmd == "list":
        for r in load_manifest(args.manifest):
            print(
                f"{r.instance:24s} seed={r.seed:12s} retired={r.retired} shingles={len(r.shingles)}"
            )
        return 0
    if args.cmd == "manifest" and args.mcmd == "retire":
        ok = retire_instance(args.manifest, args.instance)
        print("retired" if ok else "instance not found (or already retired)")
        return 0 if ok else 1
    if args.cmd == "guard" and args.gcmd == "scan":
        return _guard_scan(args)
    if args.cmd == "guard" and args.gcmd == "selftest":
        return _guard_selftest()
    if args.cmd == "guard" and args.gcmd == "audit":
        return _guard_audit(args)
    if args.cmd == "run":
        return _run_dispatch(args)
    if args.cmd == "grade":
        return _grade(args)
    if args.cmd == "demo":
        return run_demo()
    return 2


def _holdout(args: argparse.Namespace) -> int:
    try:
        if args.hcmd == "new":
            for line in generate(
                args.family,
                args.manifest,
                args.private_dir,
                count=args.count,
                seed=args.seed,
                ledger=args.ledger,
            ):
                if "warning" in line:
                    print(f"warning: {line['warning']}")
                    continue
                equals = line["task"]["verifier"].get("equals")
                tail = f" verifier equals {equals}" if equals is not None else ""
                print(f"generated {line['instance']} (seed {line['seed']}) -> {line['dir']}{tail}")
            return 0
        if args.hcmd == "retire":
            r = retire(
                args.family, args.instance, args.manifest, args.private_dir, ledger=args.ledger
            )
            print(
                f"retired {r['instance']}: manifest={r['manifest_retired']} "
                f"ledger={r['ledger_retired']}"
            )
            return 0
        if args.hcmd == "status":
            s = status(args.family, args.manifest, args.private_dir, ledger=args.ledger)
            print(
                f"family {s['id']}: generated={s['generated']} skipped={s['skipped']} "
                f"retired={s['retired']} next_counter={s['next_counter']}"
            )
            print(f"cardinality: {s['cardinality_display']}")
            for w in s["warnings"]:
                print(f"warning: {w}")
            return 0
        if args.hcmd == "verify":
            # aliased: run's seal-verify and holdout's verify are different tools
            problems = holdout_verify(
                args.family, args.manifest, args.private_dir, deep=args.deep, ledger=args.ledger
            )
            if problems:
                for p in problems:
                    print(f"  {p}", file=sys.stderr)
                print("holdout verify: FAILED", file=sys.stderr)
                return 1
            depth = " (deep)" if args.deep else ""
            print(f"holdout verify: chain intact, manifest in sync{depth}")
            return 0
    except HoldoutUsageError as exc:
        print(f"gauntlet holdout: {exc}", file=sys.stderr)
        return 2
    except HoldoutIntegrityError as exc:
        print(f"gauntlet holdout: {exc}", file=sys.stderr)
        return 1
    return 2


def _guard_audit(args: argparse.Namespace) -> int:
    """Zero-setup memory-surface discovery (ADR-0011): names & metadata only,
    never content. Always exit 0 — an audit is information, not a verdict."""
    roots = args.roots or [Path.home()]
    result = audit_surfaces(
        roots,
        max_depth=args.max_depth,
        max_files=args.max_files,
        max_seconds=args.max_seconds,
    )
    print(format_report(result, roots))
    if args.json:
        args.json.write_text(json.dumps(audit_to_dict(result, roots), indent=1))
    return 0


def _grade(args: argparse.Namespace) -> int:
    cfg = GradeConfig(
        primary=args.primary,
        baseline=args.baseline,
        margin=args.margin,
        bootstrap_b=args.bootstrap_b,
        seed=args.seed,
        require_every_task=args.require_every_task,
        max_excluded_pct=args.max_excluded_pct,
    )
    judge = None
    if args.judge_scores:
        judge = {k: float(v) for k, v in json.loads(args.judge_scores.read_text()).items()}
    verdict = grade_experiment(args.expdir, cfg, judge)
    if verdict.get("integrity_failure"):
        print("INTEGRITY FAILURE — seal violations; no verdict issued", file=sys.stderr)
        for slot, probs in verdict["violations"].items():
            for p in probs:
                print(f"  {slot}: {p}", file=sys.stderr)
        return exit_code(verdict)
    print(
        f"verdict: {verdict['decision'].upper()}  ({verdict['primary']} vs {verdict['baseline']})"
    )
    print(
        f"  pairs={verdict['pairs_graded']} net={verdict['net_winrate']} CI95={verdict['ci95']} "
        f"excluded={verdict['excluded_pct']}%"
    )
    for r in verdict["reasons"]:
        print(f"  reason: {r}")
    for ex in verdict["excluded"]:
        print(f"  excluded: {ex['slot']} ({ex['task']}/{ex['arm']}): {ex['reason']}")
    if args.json:
        args.json.write_text(json.dumps(verdict, indent=1, sort_keys=True))
    if args.public:
        args.public.write_text(json.dumps(public_face(verdict), indent=1, sort_keys=True))
    return exit_code(verdict)


def _run_dispatch(args: argparse.Namespace) -> int:
    try:
        return _run(args)
    except SlotError as exc:
        print(f"gauntlet run: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"gauntlet run: missing file: {exc.filename}", file=sys.stderr)
        return 2


def _run(args: argparse.Namespace) -> int:
    if args.rcmd == "init":
        tasks = json.loads(args.tasks.read_text())
        exp = init_experiment(args.expdir, tasks, args.arms.split(","), args.repeats, args.seed)
        n = len(exp.header["tasks"]) * len(exp.header["arms"]) * args.repeats
        print(
            f"experiment {exp.header['id']}: {n} trials ({len(exp.header['tasks'])} tasks x "
            f"{len(exp.header['arms'])} arms x {args.repeats} repeats) -> {args.expdir}"
        )
        print(f"slots: gauntlet run status {args.expdir}")
        return 0
    if args.rcmd == "prep":
        exp = load_experiment(args.expdir)
        res = prep(exp, args.slot, args.fixtures)
        print(f"prepared {res['slot']} (task {res['task']}) -> {res['workspace']}")
        return 0
    if args.rcmd == "exec":
        exp = load_experiment(args.expdir)
        cmd = list(args.agent_cmd)
        if not cmd:
            print("gauntlet run exec: no command given after --", file=sys.stderr)
            return 2
        res = exec_trial(exp, args.slot, cmd, args.timeout)
        mark = "DRIFT" if res["drift"] else "clean"
        print(
            f"closed {res['slot']}: exit={res['exit']} {mark} "
            f"({res['files']} files sealed, {res.get('duration_s', '?')}s)"
        )
        for d in res["drift"]:
            print(f"  drift: {d}")
        return 0 if res["exit"] == 0 else 1
    if args.rcmd == "close":
        exp = load_experiment(args.expdir)
        res = close(exp, args.slot)
        print(f"closed {res['slot']}: {res['status']} ({res['files']} files)")
        for d in res["drift"]:
            print(f"  drift: {d}")
        return 0
    if args.rcmd == "status":
        exp = load_experiment(args.expdir)
        states = {s: exp.state_of(s) for s in exp.slots()}
        for slot, created in exp.slots().items():
            st = states[slot].get("kind", "created")
            extra = ""
            if st == "closed":
                st = states[slot]["status"]
                extra = f" exit={states[slot].get('exit')} files={len(states[slot]['outputs'])}"
            line = f"{slot:12s} {created['task']:12s} {st:14s}{extra}"
            if args.reveal:
                line += f"  arm={created['arm']}"
            print(line)
        return 0
    if args.rcmd == "verify":
        exp = load_experiment(args.expdir)
        problems = verify(exp, args.slot)
        if not problems:
            print(f"{args.slot}: seal intact")
            return 0
        print(f"{args.slot}: SEAL VIOLATION", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    if args.rcmd == "blindpack":
        exp = load_experiment(args.expdir)
        res = blindpack(exp, args.out)
        print(f"packed {res['packed']} trial(s) -> {res['pack']}")
        print(f"unblind map (PRIVATE): {res['unblind']}")
        return 0
    return 2


def _guard_scan(args: argparse.Namespace) -> int:
    records = load_manifest(args.manifest)
    result = scan_store(records, args.store, args.min_overlap, args.max_bytes)
    for f in result.findings:
        print(
            f"[{f.severity.upper():5s}] {f.store_file} :: instance {f.instance} "
            f"({f.matched_shingles}/{f.total_shingles} shingles, {f.overlap_pct}% overlap, "
            f"word@{f.first_word_pos}, ref {f.content_ref})"
        )
    if args.json:
        args.json.write_text(json.dumps([finding_to_dict(f) for f in result.findings], indent=1))
    reasons: dict[str, int] = {}
    for _, why in result.skipped:
        reasons[why] = reasons.get(why, 0) + 1
    skip_note = ""
    if result.skipped:
        breakdown = ", ".join(f"{n} {k}" for k, n in sorted(reasons.items()))
        skip_note = f", skipped {len(result.skipped)} ({breakdown})"
    print(f"\nscanned {result.scanned} file(s){skip_note}")
    if not result.findings:
        print("clean: no task content detected in stores")
        return 0
    print(
        f"{len(result.findings)} finding(s). "
        "Retire leaked instances and regenerate from unused seeds."
    )
    return 1


def _guard_selftest() -> int:
    """Synthetic end-to-end proof: plant a paraphrased leak next to one clean note,
    plus one oversized and one binary file that also contain the leak, and assert
    detection, redaction, no false positives, and honest skip accounting."""
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        task = tdp / "task.txt"
        task.write_text(
            "A logistics firm must schedule exactly nine trucks across four docks under the "
            "frostgate constraint: no dock may receive two consecutive refrigerated trucks, "
            "and the vermilion manifest must depart before the azure convoy clears weighbridge "
            "seven. Produce the minimal feasible ordering and prove minimality."
        )
        store = tdp / "agent_memory"
        store.mkdir()
        leak_text = (
            "# Lessons\n- the frostgate constraint (no dock may receive two consecutive "
            "refrigerated trucks, and the vermilion manifest must depart before the azure "
            "convoy clears weighbridge seven) keeps biting us on scheduling tasks\n"
            "- unrelated: prefer uv over pip\n"
        )
        (store / "LESSONS.md").write_text(leak_text)
        (store / "clean_note.md").write_text("# Notes\n- always pin tool versions in CI\n")
        (store / "huge_memory.md").write_text(leak_text + "x" * (4 * 1024 * 1024))
        (store / "blob.bin").write_bytes(b"\x00\x01\x02" + leak_text.encode() + b"\x00")

        mf = tdp / "manifest.jsonl"
        add_instance(mf, "synthetic-1", "seed-42", [task])
        result = scan_store(load_manifest(mf), [store], max_bytes=2 * 1024 * 1024)
        findings = result.findings
        by_file = {Path(f.store_file).name: f for f in findings}
        assert "LESSONS.md" in by_file, "selftest FAILED: planted leak not detected"
        assert "clean_note.md" not in by_file, "selftest FAILED: false positive"
        assert "huge_memory.md" not in by_file, "selftest FAILED: oversize file was scanned"
        assert "blob.bin" not in by_file, "selftest FAILED: binary file was scanned"
        skip_reasons = {Path(p).name: why for p, why in result.skipped}
        assert skip_reasons.get("huge_memory.md") == "too-large", (
            "selftest FAILED: size skip unreported"
        )
        assert skip_reasons.get("blob.bin") == "binary", "selftest FAILED: binary skip unreported"
        leak = by_file["LESSONS.md"]
        print(
            f"selftest PASS: caught planted leak in LESSONS.md [{leak.severity}] "
            f"{leak.matched_shingles} shingles matched"
        )
        print(f"  skipped reported: {sorted(skip_reasons.items())}")
        # verify redaction: no printable content in the serialized findings
        blob = json.dumps([finding_to_dict(f) for f in findings]).lower()
        for probe in ("frostgate", "vermilion manifest must depart", "logistics firm"):
            assert probe not in blob, f"selftest FAILED: report contained task text {probe!r}"
        print("selftest PASS: report is content-free (redaction holds)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
