from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = ROOT / "static"


def test_frontend_shell_is_external_and_csp_compatible() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    web_loader = (ROOT / "src/helpme_green/web.py").read_text(encoding="utf-8")

    assert len(html) < 20_000
    assert len(web_loader) < 12_000
    assert '<link rel="stylesheet" href="/static/app.css">' in html
    assert '<script src="/static/app.js" defer></script>' in html
    assert "<style" not in html.lower()
    assert " style=" not in html.lower()
    assert "Explore" not in html
    assert "profile-button" not in html


def test_frontend_script_passes_node_syntax_gate() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.fail("Node.js is required to run the frontend syntax gate")

    result = subprocess.run(
        [node, "--check", str(STATIC_ROOT / "app.js")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_frontend_contract_covers_state_and_accessibility_fixes() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")

    assert 'id="retryRequest"' in html
    assert 'id="assistantRead" aria-live="polite"' in html
    assert 'id="comparisonRead" aria-live="polite"' in html
    assert 'aria-describedby="evidenceFieldsHint evidenceGuidance"' in html
    assert 'id="library"' in html and 'role="dialog"' in html
    assert "indexedDB" in javascript
    assert "MAX_PHOTO_DIMENSION = 640" in javascript
    assert "PHOTO_QUALITY = .7" in javascript
    assert "state.sessionId" in javascript
    assert "lastFailedRequest" in javascript
    assert "navigator.onLine" in javascript
    assert "message/stream" in javascript
