"""The demo is a contract: the story must hold, or CI fails."""

import io
from contextlib import redirect_stdout

from gauntlet.demo import run_demo


def test_demo_story_holds():
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = run_demo()
    assert rc == 0
    out = buf.getvalue()
    for act in ("ACT 1", "ACT 2", "ACT 3", "ACT 3b"):
        assert act in out
    assert "PROVISIONAL" in out and "KEEP" in out
    assert "[EXACT]" in out  # contamination caught, content-free
    assert "memory, not intelligence" in out


def test_demo_leaves_no_task_text_in_findings_lines():
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        run_demo()
    finding_lines = [ln for ln in buf.getvalue().splitlines() if "[EXACT]" in ln]
    assert finding_lines
    assert not any("SUM OF SQUARES" in ln for ln in finding_lines)
