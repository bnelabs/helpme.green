from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEBSITE = ROOT / "website"


def test_public_onboarding_page_has_grounded_get_started_content() -> None:
    html = (WEBSITE / "index.html").read_text(encoding="utf-8")

    assert "A practical guide for" in html
    assert 'id="get-started"' in html
    assert "Release binary" in html
    assert "Docker" in html
    assert "From source" in html
    assert "v0.1.0-rc.6" in html
    assert "may occasionally break" in html
    assert "SHA256SUMS" in html
    assert "helpme-green.exe" in html
    assert "The library shows examples, not proof of identity." in html
    assert "does not prove what a sample is or what is safe" in html
    assert "https://github.com/bnelabs/helpme.green/releases" in html
    for asset in (
        "assets/brand-mark.png",
        "assets/favicon.png",
        "assets/screenshots/notebook-viewport-desktop.png",
        "assets/helpme-field-journal.png",
        "assets/material-plastics.webp",
    ):
        assert (WEBSITE / asset).is_file(), asset


def test_public_onboarding_script_passes_node_syntax_gate() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.fail("Node.js is required to run the public website syntax gate")

    result = subprocess.run(
        [node, "--check", str(WEBSITE / "app.js")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
