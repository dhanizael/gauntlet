"""Regenerate the checked-in public transcript from the executable demo."""

from pathlib import Path

from gauntlet.demo import render_demo


def main() -> None:
    """Write the deterministic demo transcript used by public launch assets."""
    output = Path("docs/assets/demo-transcript.txt")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_demo())


if __name__ == "__main__":
    main()
