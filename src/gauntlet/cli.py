"""gauntlet CLI — sealed holdouts, persistence-leak guards, keep/revert verdicts.

v0 commands:
  gauntlet manifest add  MANIFEST --instance ID --seed S FILES...
  gauntlet manifest list MANIFEST
  gauntlet manifest retire MANIFEST --instance ID
  gauntlet guard scan    MANIFEST --store PATH [--store PATH] [--json OUT]
  gauntlet guard selftest
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from .guard import finding_to_dict, scan_store
from .manifest import add_instance, load_manifest, retire_instance

BANNER = "gauntlet 0.1.0 — the anti-cheating layer for evaluating self-improving agents"


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

    args = ap.parse_args(argv)

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
