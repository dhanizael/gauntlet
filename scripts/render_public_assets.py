"""Render evidence-first public launch assets from the deterministic demo."""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import hashlib
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
    """Return a fixed-size SVG with a shared terminal-poster visual language."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
<rect width="100%" height="100%" fill="{BG}"/><rect x="24" y="24" width="1152" height="582" rx="24" fill="{PANEL}" stroke="#283142" stroke-width="2"/>
<style>text{{font-family:DejaVu Sans Mono,monospace}}.k{{fill:{MUTED};font-size:22px;font-weight:700;letter-spacing:2px}}.h{{fill:{INK};font-size:50px;font-weight:800}}.b{{fill:{MUTED};font-size:24px}}.v{{font-size:42px;font-weight:800}}.s{{fill:{MUTED};font-size:18px}}</style>{body}</svg>"""


def frame(stage: int) -> str:
    """Render one of the three public proof stages."""
    states = (
        ("ACT 1  BASELINE", "PROVISIONAL (net 0.0)", MUTED),
        ("ACT 2  SAME TEST", "KEEP (net 1.0)", GOLD),
        ("ACT 3  FRESH TEST", "PROVISIONAL (net 0.0)", PROOF),
    )
    rows = []
    for index, (label, verdict, color) in enumerate(states[: stage + 1]):
        y = 278 + index * 82
        rows.append(
            f'<text x="80" y="{y}" class="s">{label}</text><text x="520" y="{y}" class="v" fill="{color}">{verdict}</text>'
        )
    leak = ""
    if stage == 2:
        leak = f'<rect x="72" y="510" width="1056" height="64" rx="12" fill="#29131c" stroke="{DANGER}" stroke-width="2"/><text x="96" y="552" class="v" fill="{DANGER}">[EXACT] LESSONS.md</text><text x="650" y="551" class="b">the test leaked into memory</text>'
    return document(
        '<text x="80" y="96" class="k">GAUNTLET — SCORE INTEGRITY CHECK</text><text x="80" y="165" class="h">YOUR AI DIDN&apos;T GET SMARTER.</text><text x="80" y="218" class="h">IT GOT THE ANSWERS.</text>'
        + "".join(rows)
        + leak
    )


def social_card() -> str:
    """Render a static 1200x630 share card from the three verified events."""
    return document(f"""
<text x="80" y="86" class="k">GAUNTLET / SCORE INTEGRITY</text>
<text x="80" y="160" class="h">YOUR AI DIDN&apos;T GET SMARTER.</text>
<text x="80" y="216" class="h">IT GOT THE ANSWERS.</text>
<text x="80" y="264" class="b">A score is not proof until it survives a fresh test.</text>
<rect x="80" y="330" width="290" height="150" rx="18" fill="#202128"/><text x="108" y="378" class="s">SAME TEST</text><text x="108" y="440" class="v" fill="{GOLD}">KEEP (net 1.0)</text>
<path d="M388 405H468M458 393L480 405L458 417" fill="none" stroke="{MUTED}" stroke-width="4"/>
<rect x="492" y="330" width="260" height="150" rx="18" fill="#29131c" stroke="{DANGER}" stroke-width="2"/><text x="520" y="378" class="s">GUARD</text><text x="520" y="440" class="v" fill="{DANGER}">EXACT LEAK</text>
<path d="M770 405H850M840 393L862 405L840 417" fill="none" stroke="{MUTED}" stroke-width="4"/>
<rect x="874" y="330" width="246" height="150" rx="18" fill="#10251d" stroke="{PROOF}" stroke-width="2"/><text x="902" y="378" class="s">FRESH TEST</text><text x="902" y="440" class="v" fill="{PROOF}">net 0.0</text>
<text x="80" y="560" class="s">reproduce: uvx --from gauntlet-guard gauntlet demo</text><text x="1010" y="560" class="s">gauntlet</text>""")


def magick(args: Sequence[str]) -> None:
    """Run the explicit render tool, failing clearly when it is unavailable."""
    executable = shutil.which("magick")
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
        for stage in range(3):
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
                "90",
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


def same_bytes(left: Path, right: Path) -> bool:
    """Compare file contents independently of timestamps."""
    return hashlib.sha256(left.read_bytes()).digest() == hashlib.sha256(right.read_bytes()).digest()


def main(argv: Sequence[str] | None = None) -> int:
    """Write current assets, or check them against a fresh deterministic render."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        with tempfile.TemporaryDirectory(prefix="gauntlet-assets-check-") as temp:
            gif, card = render(Path(temp))
            stale = [
                target
                for source, target in ((gif, DEMO_GIF), (card, SOCIAL_CARD))
                if not target.exists() or not same_bytes(source, target)
            ]
        if stale:
            print("public assets are stale: " + ", ".join(map(str, stale)))
            return 1
        return 0
    gif, card = render(ASSET_DIR)
    print(f"wrote {gif}")
    print(f"wrote {card}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
