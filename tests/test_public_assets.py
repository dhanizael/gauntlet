"""Public launch assets must remain accessible and evidence-only."""

from pathlib import Path


def test_causal_loop_svg_has_accessible_evidence_labels():
    svg = Path("docs/assets/gauntlet-causal-loop.svg").read_text()
    for phrase in (
        "<title",
        "<desc",
        "Agent fails task",
        "Memory persists",
        "Score appears to improve",
        "Leak caught",
        "Retire compromised holdout",
        "Fresh holdout retests claim",
    ):
        assert phrase in svg


def test_causal_loop_svg_does_not_expose_demo_secret_text():
    svg = Path("docs/assets/gauntlet-causal-loop.svg").read_text()
    assert "SUM OF SQUARES" not in svg
    assert "ANSWER:" not in svg


def test_case_study_states_evidence_and_limits():
    case_study = Path("docs/CASE_STUDY.md").read_text()
    for phrase in (
        "271 files",
        "3.1 seconds",
        "zero false positives",
        "What this does not prove",
        "zero task text",
    ):
        assert phrase in case_study


def test_readme_links_to_case_study_and_self_scan_path():
    readme = Path("README.md").read_text()
    assert "docs/CASE_STUDY.md" in readme
    assert "Scan your own agent" in readme
