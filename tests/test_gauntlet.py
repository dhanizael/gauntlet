import json
from pathlib import Path

import pytest

from gauntlet.fingerprint import normalize, shingle_set, word_shingles
from gauntlet.guard import finding_to_dict, scan_store
from gauntlet.manifest import add_instance, load_manifest, retire_instance

TASK = (
    "The quarantine protocol requires that every sample passing through gate "
    "nineteen be logged under the hollowkey cipher, otherwise the audit yields "
    "no admissible evidence for the tribunal review cycle described in annex twelve."
)


def make_env(tmp_path: Path):
    task = tmp_path / "task.txt"
    task.write_text(TASK)
    mf = tmp_path / "manifest.jsonl"
    add_instance(mf, "inst-1", "seed-a", [task])
    return tmp_path, mf


def scan(mf_path: Path, store: Path):
    return scan_store(load_manifest(mf_path), [store]).findings


def test_normalize_strips_punct_case():
    assert normalize("Hello, WORLD!! 1 2") == "hello world 1 2"


def test_shingle_positions_and_overlap():
    norm = normalize(TASK)
    sh = word_shingles(norm, 8)
    assert len(sh) == len(norm.split()) - 7
    assert sh[0][0] == 0
    assert shingle_set("the hollowkey cipher otherwise the audit yields no") <= shingle_set(norm)


def test_exact_leak_detected(tmp_path):
    _, mf = make_env(tmp_path)
    store = tmp_path / "LESSONS.md"
    store.write_text("# notes\n- " + TASK + "\n")
    f = scan(mf, store)
    assert len(f) == 1
    assert f[0].severity == "exact"
    assert f[0].instance == "inst-1"


def test_near_leak_paraphrase_detected(tmp_path):
    _, mf = make_env(tmp_path)
    store = tmp_path / "memory.md"
    store.write_text(
        "Recall: samples must go through gate nineteen logged under the hollowkey "
        "cipher or the audit yields no admissible evidence for the tribunal review. "
        "Also: use tabs not spaces."
    )
    f = scan(mf, store)
    assert len(f) == 1
    assert f[0].severity in ("near", "exact")
    assert f[0].matched_shingles >= 2


def test_clean_store_no_findings(tmp_path):
    _, mf = make_env(tmp_path)
    store = tmp_path / "notes.md"
    store.write_text("# Notes\n- pin tool versions in CI; unrelated project memory\n")
    assert scan(mf, store) == []


def test_report_contains_no_task_text(tmp_path):
    _, mf = make_env(tmp_path)
    store = tmp_path / "mem.md"
    store.write_text("summary: " + TASK)
    blob = json.dumps([finding_to_dict(f) for f in scan(mf, store)])
    for probe in ("quarantine protocol", "hollowkey cipher", "tribunal review"):
        assert probe not in blob.lower()


def test_retired_instances_are_skipped(tmp_path):
    _, mf = make_env(tmp_path)
    store = tmp_path / "mem.md"
    store.write_text(TASK)
    assert len(scan(mf, store)) == 1
    assert retire_instance(mf, "inst-1") is True
    assert scan(mf, store) == []


def test_retire_missing_instance(tmp_path):
    _, mf = make_env(tmp_path)
    assert retire_instance(mf, "nope") is False


def test_manifest_roundtrip(tmp_path):
    _, mf = make_env(tmp_path)
    recs = load_manifest(mf)
    assert len(recs) == 1
    assert recs[0].seed == "seed-a"
    assert recs[0].full_sha256
    assert recs[0].shingles


def test_oversize_file_skipped_and_reported(tmp_path):
    _, mf = make_env(tmp_path)
    store = tmp_path / "mem.md"
    store.write_text(TASK + "x" * 10_000)
    res = scan_store(load_manifest(mf), [store], max_bytes=2000)
    assert res.findings == []
    assert res.skipped == [(str(store), "too-large")]


def test_binary_file_skipped_and_reported(tmp_path):
    _, mf = make_env(tmp_path)
    store = tmp_path / "blob.bin"
    store.write_bytes(b"\x00\x01" + TASK.encode())
    res = scan_store(load_manifest(mf), [store])
    assert res.findings == []
    assert res.skipped == [(str(store), "binary")]


def test_scanned_count_tracks_real_files(tmp_path):
    _, mf = make_env(tmp_path)
    store = tmp_path / "mem.md"
    store.write_text("benign content here")
    res = scan_store(load_manifest(mf), [store])
    assert res.scanned == 1


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
