"""holdout: provably-fresh generation + retirement ledger (docs/HOLDOUT_DESIGN.md).

Test commitments T1-T15 map to the frozen design; names below carry the T numbers.
"""

import json
import stat
from pathlib import Path

import pytest

from gauntlet.cli import main
from gauntlet.holdout import (
    GENESIS,
    HoldoutIntegrityError,
    HoldoutUsageError,
    SeedStream,
    append_entry,
    cardinality,
    derive_slots,
    generate,
    ledger_path_for,
    load_family,
    load_ledger,
    render,
    retire,
    slot_digest,
    status,
    validate_family,
    verify,
    verify_chain,
)

FAMILY = {
    "schema": 1,
    "id": "frostgate",
    "prompt": (
        "Task frostgate-{{ tag }}: read task/fixtures/nums.txt and write the "
        "SUM OF SQUARES OF THE EVEN numbers in it to result.txt."
    ),
    "slots": {
        "tag": {"kind": "permutation", "of": ["A", "B", "C", "D"]},
        "nums": {"kind": "int_list", "count": 4, "min": 1, "max": 15},
    },
    "fixtures": {"nums.txt": "{{ nums }}"},
    "verifier": {"type": "expect_file", "path": "result.txt", "equals": "20"},
}

# T2: measured once (T1 determinism), pinned here; CI matrix (3.11 + 3.13)
# then proves byte-identical derivation across Python versions.
GOLDEN = "872712b8a4b2cb91bf2e97bdaf3cfde4bde67ec496e37cb58473eab30b3043fa"


def write_family(tmp_path: Path, family: dict, name: str = "family.json") -> Path:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(family, indent=1))
    return p


def setup_gen(tmp_path: Path, family: dict, name: str = "family.json"):
    fam = write_family(tmp_path, family, name)
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text("")
    private = tmp_path / "private"
    private.mkdir()
    return fam, manifest, private


def ledger_hashes(path: Path) -> list[dict]:
    return [e for e, _ in load_ledger(path)]


# ---------------------------------------------------------------- T4: PRNG


def test_seedstream_deterministic_per_key():
    a, b = SeedStream("frostgate/a"), SeedStream("frostgate/a")
    seq_a = [a.below(1000) for _ in range(50)]
    seq_b = [b.below(1000) for _ in range(50)]
    assert seq_a == seq_b


def test_seedstream_divergent_keys():
    a, b = SeedStream("frostgate/a"), SeedStream("frostgate/b")
    assert [a.below(1000) for _ in range(50)] != [b.below(1000) for _ in range(50)]


def test_below_covers_range_without_bounds_violation():
    s = SeedStream("coverage")
    draws = [s.below(6) for _ in range(600)]
    assert min(draws) == 0 and max(draws) == 5
    assert set(draws) == {0, 1, 2, 3, 4, 5}
    assert SeedStream("x").below(1) == 0


def test_rejection_sampling_no_extreme_bias():
    s = SeedStream("bias")
    counts = {v: 0 for v in range(6)}
    for _ in range(600):
        counts[s.below(6)] += 1
    assert max(counts.values()) - min(counts.values()) < 120  # ~13 sigma slack


# ------------------------------------------------- T3/T14: family templates


def test_validate_family_accepts_well_formed(tmp_path):
    fam = write_family(tmp_path, FAMILY)
    validate_family(load_family(fam), tmp_path)


def test_validation_rejects_unknown_slot_kind(tmp_path):
    bad = {**FAMILY, "slots": {"x": {"kind": "llm"}}}
    with pytest.raises(HoldoutUsageError):
        validate_family(bad, tmp_path)


def test_validation_rejects_dangling_template_ref(tmp_path):
    bad = {**FAMILY, "prompt": "uses {{ missing_slot }} here"}
    with pytest.raises(HoldoutUsageError):
        validate_family(bad, tmp_path)


def test_validation_rejects_answer_cmd_without_expect_file(tmp_path):
    bad = {
        **FAMILY,
        "answer_cmd": ["python3", "answer.py"],
        "verifier": {"type": "judge"},
    }
    with pytest.raises(HoldoutUsageError):
        validate_family(bad, tmp_path)


def test_validation_rejects_bad_schema_and_id(tmp_path):
    with pytest.raises(HoldoutUsageError):
        validate_family({**FAMILY, "schema": 99}, tmp_path)
    with pytest.raises(HoldoutUsageError):
        validate_family({**FAMILY, "id": "Bad_Id!"}, tmp_path)


def test_cardinality_math():
    fam = {**FAMILY, "slots": {"nums": {"kind": "int_list", "count": 4, "min": 1, "max": 15}}}
    assert cardinality(fam) == 15**4
    fam_p = {**FAMILY, "slots": {"tag": {"kind": "permutation", "of": ["A", "B", "C", "D"]}}}
    assert cardinality(fam_p) == 24
    fam_i = {**FAMILY, "slots": {"n": {"kind": "int", "min": 3, "max": 9}}}
    assert cardinality(fam_i) == 7
    fam_c = {**FAMILY, "slots": {"c": {"kind": "choice", "of": ["x", "y", "z"]}}}
    assert cardinality(fam_c) == 3


def test_derive_slots_in_range_and_deterministic():
    v1 = derive_slots(FAMILY, "frostgate/frostgate:0")
    v2 = derive_slots(FAMILY, "frostgate/frostgate:0")
    assert v1 == v2
    assert len(v1["nums"]) == 4 and all(1 <= x <= 15 for x in v1["nums"])
    assert sorted(v1["tag"]) == ["A", "B", "C", "D"]
    v3 = derive_slots(FAMILY, "frostgate/frostgate:1")
    assert v3["nums"] != v1["nums"] or v3["tag"] != v1["tag"]


def test_render_substitutes_slots():
    values = {"tag": ["B", "A"], "nums": [3, 9, 4, 7]}
    out = render("task {{ tag }}: {{ nums }} -> {{nums}}", values, FAMILY["slots"])
    assert out == "task B A: 3 9 4 7 -> 3 9 4 7"


def test_slot_digest_separates_values():
    assert slot_digest({"n": [1, 2]}) != slot_digest({"n": [2, 1]})
    assert slot_digest({"n": [1, 2]}) == slot_digest({"n": [1, 2]})


# ----------------------------------------------------- T8: ledger integrity


def test_ledger_append_load_and_permissions(tmp_path):
    path = ledger_path_for(tmp_path, "frostgate")
    first = append_entry(path, {"kind": "generated", "seed": "frostgate:0"})
    append_entry(path, {"kind": "generated", "seed": "frostgate:1"})
    entries = ledger_hashes(path)
    assert [e["seed"] for e in entries] == ["frostgate:0", "frostgate:1"]
    assert entries[0]["prev"] == GENESIS
    assert entries[1]["prev"] == first
    assert stat.S_IMODE(path.stat().st_mode) & 0o777 == 0o600
    assert verify_chain(path) == []


def test_chain_tamper_is_named(tmp_path):
    path = ledger_path_for(tmp_path, "frostgate")
    append_entry(path, {"kind": "generated", "seed": "frostgate:0"})
    append_entry(path, {"kind": "generated", "seed": "frostgate:1"})
    append_entry(path, {"kind": "generated", "seed": "frostgate:2"})
    raw = path.read_bytes().replace(b"frostgate:1", b"frostgate:X")
    path.write_bytes(raw)
    problems = verify_chain(path)
    assert problems and "chain" in problems[0]
    with pytest.raises(HoldoutIntegrityError):
        load_ledger(path)


def test_tail_tamper_needs_deep_verify(tmp_path):
    """A hash chain cannot see its own tail: altering the LAST line leaves no
    later line to carry the mismatched hash. The design's answer is --deep:
    re-derivation from the tampered seed produces a different content hash."""
    fam, mf, priv = setup_gen(tmp_path, FAMILY)
    generate(fam, mf, priv)
    assert verify(fam, mf, priv, deep=True) == []
    lpath = ledger_path_for(priv, "frostgate")
    lpath.write_bytes(
        lpath.read_bytes().replace(b'"seed": "frostgate:0"', b'"seed": "frostgate:9"')
    )
    assert verify_chain(lpath) == []  # chain is blind to its tail, as designed
    problems = verify(fam, mf, priv, deep=True)
    assert problems and "drifted" in problems[0]


# --------------------------------------------- T1/T5/T6/T7/T11/T12: generate


def test_generate_deterministic_content_and_registration(tmp_path):
    fam_a, mf_a, priv_a = setup_gen(tmp_path / "a", FAMILY)
    fam_b, mf_b, priv_b = setup_gen(tmp_path / "b", FAMILY)
    out_a = generate(fam_a, mf_a, priv_a)
    out_b = generate(fam_b, mf_b, priv_b)
    digests = {e["content_sha256"] for e in ledger_hashes(ledger_path_for(priv_a, "frostgate"))}
    same = {e["content_sha256"] for e in ledger_hashes(ledger_path_for(priv_b, "frostgate"))}
    assert digests == same and len(digests) == 1
    assert out_a[0]["instance"] == "frostgate-0" and out_a[0]["seed"] == "frostgate:0"
    inst_dir = Path(out_a[0]["dir"])
    assert (inst_dir / "prompt.txt").exists()
    assert (inst_dir / "fixtures" / "nums.txt").exists()
    assert "frostgate" in (inst_dir / "prompt.txt").read_text()


def test_generate_consumes_counters_in_order(tmp_path):
    fam, mf, priv = setup_gen(tmp_path, FAMILY)
    out = generate(fam, mf, priv, count=2)
    assert [(s["instance"], s["seed"]) for s in out] == [
        ("frostgate-0", "frostgate:0"),
        ("frostgate-1", "frostgate:1"),
    ]
    entries = ledger_hashes(ledger_path_for(priv, "frostgate"))
    assert [e["kind"] for e in entries] == ["generated", "generated"]


def test_slot_collision_is_skipped_honestly_then_exhausts(tmp_path):
    tiny = {
        **FAMILY,
        "slots": {
            "tag": {"kind": "choice", "of": ["X"]},
            "nums": {"kind": "int_list", "count": 1, "min": 1, "max": 1},
        },
    }
    fam, mf, priv = setup_gen(tmp_path, tiny)
    out = generate(fam, mf, priv, count=1)  # first attempt: empty ledger, nothing to collide with
    assert out[0]["instance"] == "frostgate-0"
    with pytest.raises(HoldoutIntegrityError):
        generate(fam, mf, priv, count=1)  # every further attempt collides with frostgate-0
    entries = ledger_hashes(ledger_path_for(priv, "frostgate"))
    assert entries[0]["kind"] == "generated"
    assert all(e["kind"] == "skipped" and e["reason"] == "slot-collision" for e in entries[1:])
    assert mf.read_text().count("frostgate-0") == 1  # collisions register nothing


def test_used_seed_refused_for_reproduction(tmp_path):
    fam, mf, priv = setup_gen(tmp_path, FAMILY)
    generate(fam, mf, priv)
    with pytest.raises(HoldoutUsageError):
        generate(fam, mf, priv, seed="frostgate:0")


def test_cross_family_overlap_is_refused(tmp_path):
    fam_a, mf, priv = setup_gen(tmp_path, FAMILY)
    generate(fam_a, mf, priv)
    a_prompt = (priv / "frostgate-0" / "prompt.txt").read_text()
    mirror = {
        "schema": 1,
        "id": "mirror",
        "prompt": a_prompt + " Mirror variant {{ t }}.",
        "slots": {"t": {"kind": "choice", "of": ["q", "r", "s"]}},
        "verifier": {"type": "expect_file", "path": "result.txt", "equals": "1"},
    }
    fam_b = write_family(tmp_path, mirror, "mirror.json")
    with pytest.raises(HoldoutIntegrityError):
        generate(fam_b, mf, priv, count=1)
    mirror_entries = ledger_hashes(ledger_path_for(priv, "mirror"))
    assert mirror_entries and all(e["kind"] == "skipped" for e in mirror_entries)


def test_answer_cmd_derives_verifier_equals(tmp_path):
    (tmp_path / "answer.py").write_text(
        "import json,sys\n"
        "v = json.load(sys.stdin)\n"
        "print(sum(x * x for x in v['nums'] if x % 2 == 0))\n"
    )
    fam_def = {
        **FAMILY,
        "answer_cmd": ["python3", str(tmp_path / "answer.py")],
        "verifier": {"type": "expect_file", "path": "result.txt"},
    }
    fam, mf, priv = setup_gen(tmp_path, fam_def)
    out = generate(fam, mf, priv)
    task = json.loads((Path(out[0]["dir"]) / "task.json").read_text())
    nums = derive_slots(FAMILY, "frostgate/frostgate:0")["nums"]
    expected = str(sum(x * x for x in nums if x % 2 == 0))
    assert task["verifier"]["equals"] == expected
    assert task["id"] == "frostgate-0"


def test_ledger_never_contains_prompt_content(tmp_path):
    fam, mf, priv = setup_gen(tmp_path, FAMILY)
    generate(fam, mf, priv)
    prompt = (priv / "frostgate-0" / "prompt.txt").read_text()
    blob = ledger_path_for(priv, "frostgate").read_text()
    for word in ("SQUARES", "frostgate-A", "read task/fixtures"):
        assert word not in blob or word == "frostgate"  # ids ok, content not
    assert "SQUARES" not in blob and "result.txt" not in blob


# ------------------------------------------- T7/T9/T10/T13: retire/verify/status


def test_retire_propagates_and_kills_seed(tmp_path):
    fam, mf, priv = setup_gen(tmp_path, FAMILY)
    generate(fam, mf, priv)
    result = retire(fam, "frostgate-0", mf, priv)
    assert result["manifest_retired"] and result["ledger_retired"]
    entries = ledger_hashes(ledger_path_for(priv, "frostgate"))
    assert entries[-1]["kind"] == "retired" and entries[-1]["instance"] == "frostgate-0"
    assert verify(fam, mf, priv) == []
    with pytest.raises(HoldoutUsageError):
        generate(fam, mf, priv, seed="frostgate:0")


def test_retire_unknown_instance(tmp_path):
    fam, mf, priv = setup_gen(tmp_path, FAMILY)
    with pytest.raises(HoldoutUsageError):
        retire(fam, "frostgate-99", mf, priv)


def test_verify_names_manifest_ledger_divergence(tmp_path):
    fam, mf, priv = setup_gen(tmp_path, FAMILY)
    generate(fam, mf, priv)
    # crash window 1: retired in manifest only (retire_instance called directly)
    from gauntlet.manifest import retire_instance

    retire_instance(mf, "frostgate-0")
    problems = verify(fam, mf, priv)
    assert problems and "frostgate-0" in problems[0] and "manifest" in problems[0]
    # crash window 2: retired in ledger only
    fam2, mf2, priv2 = setup_gen(tmp_path / "w2", FAMILY)
    generate(fam2, mf2, priv2)
    append_entry(
        ledger_path_for(priv2, "frostgate"), {"kind": "retired", "instance": "frostgate-0"}
    )
    problems2 = verify(fam2, mf2, priv2)
    assert problems2 and "frostgate-0" in problems2[0] and "ledger" in problems2[0]


def test_deep_verify_catches_template_change(tmp_path):
    fam, mf, priv = setup_gen(tmp_path, FAMILY)
    generate(fam, mf, priv)
    assert verify(fam, mf, priv, deep=True) == []
    original = fam.read_text()
    fam.write_text(original.replace("SUM OF SQUARES", "SUM OF SQUARES X2"))
    problems = verify(fam, mf, priv, deep=True)
    assert problems and "template changed" in problems[0]
    fam.write_text(original)
    assert verify(fam, mf, priv, deep=True) == []


def test_status_counts_warnings_and_cardinality_cap(tmp_path):
    fam, mf, priv = setup_gen(tmp_path, FAMILY)
    generate(fam, mf, priv)
    st = status(fam, mf, priv)
    assert st["id"] == "frostgate" and st["generated"] == 1 and st["next_counter"] == 1
    assert st["cardinality"] == 15**4 * 24
    big = {
        **FAMILY,
        "id": "big",
        "slots": {"nums": {"kind": "int_list", "count": 12, "min": 1, "max": 1000}},
    }
    fam_b = write_family(tmp_path, big, "big.json")
    st_big = status(fam_b, mf, priv)
    assert st_big["cardinality_display"] == "≥ 10^12"
    tiny = {
        **FAMILY,
        "id": "tiny",
        "slots": {"n": {"kind": "int", "min": 1, "max": 3}},
        "prompt": "tiny {{ n }}",
    }
    st_tiny = status(write_family(tmp_path, tiny, "tiny.json"), mf, priv)
    assert any("enumerable" in w for w in st_tiny["warnings"])


def test_status_flags_template_change(tmp_path):
    fam, mf, priv = setup_gen(tmp_path, FAMILY)
    generate(fam, mf, priv)
    original = fam.read_text()
    fam.write_text(original.replace("SUM OF SQUARES", "SUM OF SQUARES X2"))
    st = status(fam, mf, priv)
    assert any("template changed" in w for w in st["warnings"])


# --------------------------------------------------- T15/T2: CLI + golden pin


def test_cli_holdout_surface(tmp_path):
    fam, mf, priv = setup_gen(tmp_path, FAMILY)
    assert (
        main(["holdout", "new", str(fam), "--manifest", str(mf), "--private-dir", str(priv)]) == 0
    )
    assert (
        main(["holdout", "status", str(fam), "--manifest", str(mf), "--private-dir", str(priv)])
        == 0
    )
    assert (
        main(["holdout", "verify", str(fam), "--manifest", str(mf), "--private-dir", str(priv)])
        == 0
    )
    assert (
        main(
            [
                "holdout",
                "retire",
                str(fam),
                "--instance",
                "frostgate-0",
                "--manifest",
                str(mf),
                "--private-dir",
                str(priv),
            ]
        )
        == 0
    )
    assert (
        main(["holdout", "verify", str(fam), "--manifest", str(mf), "--private-dir", str(priv)])
        == 0
    )


def test_cli_exit_codes_validation_and_gate(tmp_path):
    fam, mf, priv = setup_gen(tmp_path, FAMILY)
    bad = write_family(tmp_path, {**FAMILY, "schema": 9}, "bad.json")
    assert (
        main(["holdout", "new", str(bad), "--manifest", str(mf), "--private-dir", str(priv)]) == 2
    )
    tiny = {
        **FAMILY,
        "id": "tiny",
        "slots": {"n": {"kind": "int", "min": 1, "max": 1}},
        "prompt": "tiny {{ n }}",
        "fixtures": {},  # FAMILY's fixtures reference nums, which tiny has no slot for
    }
    fam_t = write_family(tmp_path, tiny, "tiny.json")
    # first instance succeeds (empty ledger); every further attempt collides -> exit 1
    assert (
        main(["holdout", "new", str(fam_t), "--manifest", str(mf), "--private-dir", str(priv)]) == 0
    )
    assert (
        main(["holdout", "new", str(fam_t), "--manifest", str(mf), "--private-dir", str(priv)]) == 1
    )


def test_golden_hash_cross_version_pin(tmp_path):
    if not GOLDEN:
        pytest.fail("T2: pin GOLDEN by running test_generate_deterministic_content once")
    fam, mf, priv = setup_gen(tmp_path, FAMILY)
    generate(fam, mf, priv)
    digests = {e["content_sha256"] for e in ledger_hashes(ledger_path_for(priv, "frostgate"))}
    assert digests == {GOLDEN}
