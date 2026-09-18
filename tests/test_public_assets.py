"""Public launch assets must remain accessible and evidence-only."""

import struct
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


def test_terminal_cast_contains_the_public_demo_without_secret_text():
    cast = Path("docs/assets/gauntlet-demo.cast").read_text()
    assert '"version": 2' in cast
    assert "ACT 1" in cast and "ACT 2" in cast and "ACT 3" in cast
    assert "memory, not intelligence" in cast
    assert "SUM OF SQUARES" not in cast
    assert "ANSWER:" not in cast


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
    assert "gauntlet guard scan" in readme


def test_readme_leads_with_the_proof_reveal_and_autoplay_asset():
    readme = Path("README.md").read_text()
    assert "YOUR AI DIDN'T GET SMARTER." in readme
    assert "IT GOT THE ANSWERS." in readme
    assert "docs/assets/gauntlet-demo.gif" in readme
    assert "docs/assets/gauntlet-social-card.png" in readme
    assert "playable terminal cast" not in readme


def png_dimensions(path: Path) -> tuple[int, int]:
    """Read a PNG's IHDR size without a production image dependency."""
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert data[12:16] == b"IHDR"
    return struct.unpack(">II", data[16:24])


def test_proof_assets_have_real_image_headers_and_expected_dimensions():
    gif = Path("docs/assets/gauntlet-demo.gif")
    gif_data = gif.read_bytes()
    assert gif_data.startswith(b"GIF89a")
    assert struct.unpack("<HH", gif_data[6:10]) == (1200, 630)
    assert png_dimensions(Path("docs/assets/gauntlet-social-card.png")) == (1200, 630)


def test_public_assets_preserve_only_the_demo_reveal():
    renderer = Path("scripts/render_public_assets.py").read_text()
    transcript = Path("docs/assets/demo-transcript.txt").read_text()
    for phrase in ("KEEP (net 1.0)", "[EXACT] LESSONS.md", "PROVISIONAL (net 0.0)"):
        assert phrase in renderer
    for secret in ("SUM OF SQUARES", "ANSWER:"):
        assert secret not in transcript
        assert secret in renderer  # renderer rejects secret-bearing input before rendering


def test_ci_keeps_generated_proof_assets_current():
    workflow = Path(".github/workflows/ci.yml").read_text()
    assert "install -y imagemagick" in workflow
    assert "scripts/render_public_assets.py --check" in workflow
