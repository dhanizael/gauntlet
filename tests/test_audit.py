"""guard audit: zero-config discovery of agent memory surfaces.

Contract under test:
- finds memory files, agent state dirs, transcript/log dirs, vector stores
- NEVER reads file content (redaction, ADR-0002): a secret inside a found
  surface cannot appear in the report because it is never read
- honest caps: depth and entry caps are reported as truncation, not hidden
- deterministic ordering, content-free JSON, CLI exit 0 always
"""

import json
from pathlib import Path

from gauntlet.audit import AuditResult, Surface, audit_surfaces
from gauntlet.cli import main

SECRET = "the vermilion manifest must depart before weighbridge seven"


def make_home(tmp_path: Path) -> Path:
    (tmp_path / "LESSONS.md").write_text(f"# lessons\n- {SECRET}\n")
    (tmp_path / ".agent-state").mkdir()
    (tmp_path / ".agent-state" / "now.md").write_text("state")
    (tmp_path / "proj").mkdir()
    (tmp_path / "proj" / "logs").mkdir()
    (tmp_path / "proj" / "logs" / "run.log").write_text("log line")
    (tmp_path / "proj" / "empty-logs").mkdir()  # no text file -> not a surface
    (tmp_path / "memory.sqlite").write_bytes(b"\x00stack")
    (tmp_path / "app.sqlite").write_bytes(b"\x00plain app db")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "LESSONS.md").write_text("ignored: inside .git")
    return tmp_path


def kinds(result: AuditResult) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for s in result.surfaces:
        out.setdefault(s.kind, []).append(s.path)
    return out


def test_memory_file_found(tmp_path):
    home = make_home(tmp_path)
    r = audit_surfaces([home])
    assert str(home / "LESSONS.md") in kinds(r)["memory-file"]
    assert str(home / ".agent-state" / "now.md") in kinds(r)["memory-file"]


def test_agent_state_dir_found(tmp_path):
    home = make_home(tmp_path)
    assert str(home / ".agent-state") in kinds(audit_surfaces([home]))["agent-state"]


def test_transcript_dir_needs_a_text_file(tmp_path):
    home = make_home(tmp_path)
    k = kinds(audit_surfaces([home]))["transcripts"]
    assert str(home / "proj" / "logs") in k
    assert not any("empty-logs" in p for p in k)


def test_vector_store_by_hint_not_by_suffix_alone(tmp_path):
    home = make_home(tmp_path)
    k = kinds(audit_surfaces([home]))["vector-store"]
    assert str(home / "memory.sqlite") in k
    assert not any(p.endswith("app.sqlite") for p in k)


def test_report_never_contains_file_content(tmp_path):
    home = make_home(tmp_path)
    r = audit_surfaces([home])
    blob = json.dumps({"surfaces": [s.__dict__ for s in r.surfaces], "meta": "x"})
    assert "weighbridge" not in blob and SECRET not in blob


def test_skips_noise_dirs(tmp_path):
    home = make_home(tmp_path)
    assert not any("/.git/" in s.path for s in audit_surfaces([home]).surfaces)


def test_depth_cap_skips_deep_files(tmp_path):
    deep = tmp_path / "a" / "b" / "c" / "d" / "e" / "f" / "g"
    deep.mkdir(parents=True)
    (deep / "LESSONS.md").write_text("too deep to matter")
    r = audit_surfaces([tmp_path], max_depth=3)
    assert not any("LESSONS" in s.path for s in r.surfaces)


def test_entry_cap_is_reported_as_truncated(tmp_path):
    home = make_home(tmp_path)
    r = audit_surfaces([home], max_files=3)
    assert r.truncated is True
    assert len(r.surfaces) > 0  # partial results are still reported honestly


def test_deterministic_ordering(tmp_path):
    home = make_home(tmp_path)
    r1, r2 = audit_surfaces([home]), audit_surfaces([home])
    assert [s.path for s in r1.surfaces] == [s.path for s in r2.surfaces]


def test_cli_audit_zero_setup(tmp_path, capsys):
    home = make_home(tmp_path)
    code = main(["guard", "audit", str(home)])
    out = capsys.readouterr().out
    assert code == 0  # an audit is information, not a verdict
    assert "LESSONS.md" in out
    assert "weighbridge" not in out  # redaction holds through the CLI too


def test_cli_audit_json(tmp_path, capsys, tmp_path_factory):
    home = make_home(tmp_path)
    out_json = tmp_path / "audit.json"
    code = main(["guard", "audit", str(home), "--json", str(out_json)])
    assert code == 0
    data = json.loads(out_json.read_text())
    assert data["schema"] == 1
    assert any(s["kind"] == "memory-file" for s in data["surfaces"])
    assert "weighbridge" not in json.dumps(data)


def test_surface_holds_metadata_only():
    s = Surface(path="/x/LESSONS.md", kind="memory-file", size=10, modified="2026-09-18")
    assert set(s.__dict__) == {"path", "kind", "size", "modified"}


def test_audit_never_opens_file_content(tmp_path, monkeypatch):
    """Mechanical pin of the ADR-0011 contract: content is never read, not
    merely withheld from the report. Any read attempt explodes the audit."""
    home = make_home(tmp_path)

    def forbidden(self, *args, **kwargs):
        raise AssertionError("audit attempted to read file content")

    for attr in ("read_text", "read_bytes", "open"):
        monkeypatch.setattr(Path, attr, forbidden)
    r = audit_surfaces([home])
    assert any(s.kind == "memory-file" for s in r.surfaces)


def test_symlink_cycle_terminates(tmp_path):
    d = tmp_path / "loop"
    d.mkdir()
    (d / "inside").symlink_to(d)
    (d / "LESSONS.md").write_text("x")
    r = audit_surfaces([d])  # must terminate, not hang
    assert any(s.path.endswith("LESSONS.md") for s in r.surfaces)


def test_missing_root_is_reported_not_silenced(tmp_path):
    r = audit_surfaces([tmp_path / "does-not-exist"])
    assert r.unknown_roots == [str(tmp_path / "does-not-exist")]
    assert r.surfaces == []
