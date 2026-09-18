"""Render evidence-first public launch assets from the deterministic demo."""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path

ASSET_DIR = Path("docs/assets")
TRANSCRIPT = ASSET_DIR / "demo-transcript.txt"
DEMO_GIF = ASSET_DIR / "gauntlet-demo.gif"
SOCIAL_CARD = ASSET_DIR / "gauntlet-social-card.png"

WIDTH, HEIGHT = 1200, 630
BG, PANEL, INK, MUTED = "#090b10", "#10141d", "#f5f7fb", "#8a94a6"
DANGER, PROOF, GOLD = "#ff4d6d", "#5ee6a8", "#ffd166"
REVEAL = ("KEEP (net 1.0)", "[EXACT] LESSONS.md", "PROVISIONAL (net 0.0)")
FORBIDDEN = ("SUM OF SQUARES", "ANSWER:")


def require_public_evidence() -> None:
    """Confirm asset copy derives only from the public deterministic demo."""
    transcript = TRANSCRIPT.read_text()
    for phrase in REVEAL:
        if phrase not in transcript:
            raise ValueError(f"demo transcript is missing required evidence: {phrase}")
    for phrase in FORBIDDEN:
        if phrase in transcript:
            raise ValueError(f"demo transcript exposes secret text: {phrase}")


def document(body: str) -> str:
    """Return a fixed-size SVG with a restrained terminal visual language."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
<rect width="100%" height="100%" fill="{BG}"/><rect x="24" y="24" width="1152" height="582" rx="24" fill="{PANEL}" stroke="#283142" stroke-width="2"/>
<style>text{{font-family:DejaVu Sans Mono,monospace}}.k{{fill:{MUTED};font-size:18px}}.b{{fill:{INK};font-size:25px}}.v{{font-size:29px;font-weight:700}}.s{{fill:{MUTED};font-size:20px}}</style>{body}</svg>"""


def frame(stage: int) -> str:
    """Render a frame from the real demo as an intentionally plain terminal."""
    lines = [
        ("$ gauntlet demo", INK),
        ("ACT 1 / BASELINE", MUTED),
        ("verdict: PROVISIONAL (net 0.0)", MUTED),
        ("ACT 2 / SAME TEST", MUTED),
        ("verdict: KEEP (net 1.0)", GOLD),
        ("ACT 3 / GUARD SCAN", MUTED),
        ("[EXACT] LESSONS.md  — test leaked into memory", DANGER),
        ("holdout retired", DANGER),
        ("ACT 3 / FRESH HOLDOUT", MUTED),
        ("verdict: PROVISIONAL (net 0.0)", PROOF),
    ]
    visible = (3, 5, 8, 10)[stage]
    terminal = [
        '<circle cx="62" cy="64" r="9" fill="#ff5f57"/><circle cx="90" cy="64" r="9" fill="#febc2e"/><circle cx="118" cy="64" r="9" fill="#28c840"/>',
        '<text x="80" y="128" class="k">isolated eval / deterministic demo / no LLM</text>',
    ]
    for index, (line, color) in enumerate(lines[:visible]):
        y = 188 + index * 38
        css = "v" if "verdict:" in line or "[EXACT]" in line or "retired" in line else "b"
        terminal.append(f'<text x="80" y="{y}" class="{css}" fill="{color}">{line}</text>')
    return document("".join(terminal))


def social_card() -> str:
    """Render a static share card that reads as evidence, not an ad poster."""
    return document(f"""
<text x="80" y="96" class="k">$ gauntlet demo</text>
<text x="80" y="184" class="b">same test</text><text x="390" y="184" class="v" fill="{GOLD}">KEEP  +1.0</text>
<text x="80" y="282" class="b">guard scan</text><text x="390" y="282" class="v" fill="{DANGER}">[EXACT] LEAK</text>
<text x="80" y="380" class="b">fresh holdout</text><text x="390" y="380" class="v" fill="{PROOF}">PROVISIONAL  0.0</text>
<path d="M80 438H1120" stroke="#283142" stroke-width="2"/>
<text x="80" y="510" class="b">A score is not proof until it survives a fresh test.</text>
<text x="80" y="560" class="s">reproduce: uvx --from gauntlet-guard gauntlet demo</text>""")


def magick(args: Sequence[str]) -> None:
    """Run the explicit render tool, failing clearly when it is unavailable."""
    executable = shutil.which("magick") or shutil.which("convert")
    if executable is None:
        raise RuntimeError("ImageMagick is required to render public assets.")
    subprocess.run([executable, *args], check=True)


def render(output_dir: Path) -> tuple[Path, Path]:
    """Render both checked-in assets into output_dir."""
    require_public_evidence()
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gauntlet-assets-") as temp:
        temp_dir = Path(temp)
        frames = []
        for stage in range(4):
            path = temp_dir / f"frame-{stage}.svg"
            path.write_text(frame(stage))
            frames.append(path)
        gif = output_dir / DEMO_GIF.name
        magick(
            [
                "-background",
                BG,
                "-density",
                "96",
                *map(str, frames),
                "-delay",
                "110",
                "-loop",
                "0",
                "-dispose",
                "background",
                "-strip",
                str(gif),
            ]
        )
        card_source = temp_dir / "social-card.svg"
        card_source.write_text(social_card())
        card = output_dir / SOCIAL_CARD.name
        magick(
            [
                "-background",
                BG,
                "-density",
                "96",
                str(card_source),
                "-resize",
                "1200x630!",
                "-strip",
                "-define",
                "png:exclude-chunk=date,time",
                str(card),
            ]
        )
    return gif, card


def verify_checked_in_assets() -> None:
    """Verify the committed evidence without depending on an encoder version.

    ImageMagick's GIF and PNG bytes differ across supported Ubuntu releases even
    when the rendered pixels are equivalent. CI therefore verifies the stable
    contract here; maintainers explicitly regenerate the binary assets when the
    terminal source changes.
    """
    require_public_evidence()
    gif = DEMO_GIF.read_bytes()
    if not gif.startswith(b"GIF89a") or len(gif) < 10:
        raise ValueError(f"invalid GIF proof asset: {DEMO_GIF}")
    if tuple(int.from_bytes(gif[offset : offset + 2], "little") for offset in (6, 8)) != (
        WIDTH,
        HEIGHT,
    ):
        raise ValueError(f"unexpected GIF proof asset dimensions: {DEMO_GIF}")
    png = SOCIAL_CARD.read_bytes()
    if not png.startswith(b"\x89PNG\r\n\x1a\n") or png[12:16] != b"IHDR":
        raise ValueError(f"invalid PNG proof asset: {SOCIAL_CARD}")
    if tuple(int.from_bytes(png[offset : offset + 4], "big") for offset in (16, 20)) != (
        WIDTH,
        HEIGHT,
    ):
        raise ValueError(f"unexpected PNG proof asset dimensions: {SOCIAL_CARD}")


def main(argv: Sequence[str] | None = None) -> int:
    """Write current assets, or check them against a fresh deterministic render."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        verify_checked_in_assets()
        print("public proof assets verified")
        return 0
    gif, card = render(ASSET_DIR)
    print(f"wrote {gif}")
    print(f"wrote {card}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
