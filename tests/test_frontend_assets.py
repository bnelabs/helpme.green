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

    assert len(html) < 30_000
    assert len(web_loader) < 12_000
    assert '<link rel="stylesheet" href="../static/app.css">' in html
    assert '<script src="../static/file-launch-guard.js" defer></script>' in html
    assert '<script src="../static/app.js" defer></script>' in html
    assert "<style" not in html.lower()
    assert " style=" not in html.lower()
    assert "Explore" not in html
    assert "profile-button" not in html
    assert 'class="file-launch-guard"' in html and 'class="app-shell" hidden' in html


def test_frontend_script_passes_node_syntax_gate() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.fail("Node.js is required to run the frontend syntax gate")

    for script in (STATIC_ROOT / "app.js", STATIC_ROOT / "file-launch-guard.js"):
        result = subprocess.run(
            [node, "--check", str(script)],
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
    assert 'id="modelDisclosure"' in html
    assert 'id="clearDetachedPhotos"' in html
    assert 'aria-describedby="evidenceFieldsHint evidenceGuidance"' in html
    assert 'id="library"' in html and 'role="dialog"' in html
    assert "indexedDB" in javascript
    assert "SUPPORTED_VISION_IMAGE_TYPES" in javascript
    assert "modelImagesForPage" in javascript
    assert 'accept="image/png,image/jpeg,image/webp,image/gif"' in html
    assert "state.sessionId" in javascript
    assert "lastFailedRequest" in javascript
    assert "navigator.onLine" in javascript
    assert "message/stream" in javascript
    assert '<textarea class="note-title" id="noteTitle"' in html
    assert "fitNoteTitle" in javascript
    assert "modelDisclosure" in javascript
    assert "full image and every saved detail" in html
    assert "ASSISTANT_VERIFICATION_NOTICE" in javascript
    assert "MAX_LIBRARY_REFERENCE_IMAGES" in javascript
    assert "original photo" in javascript
    assert 'href="#settings"' in html
    assert 'id="settingsForm"' in html
    assert 'id="settingsApiKey"' in html
    assert 'id="settingsAdvancedOptions"' in html
    assert 'request("/api/settings"' in javascript


def test_frontend_navigation_isolates_kb_and_returns_to_notebook_for_library() -> None:
    javascript = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    stylesheet = (STATIC_ROOT / "app.css").read_text(encoding="utf-8")

    assert ".notebook-workspace[hidden] { display: none; }" in stylesheet
    assert (
        'if (window.location.hash === "#kb" || window.location.hash === "#settings") window.location.hash = "#notebook";'
        in javascript
    )
    assert '"helpme.green — Knowledge base"' in javascript
    assert '"helpme.green — Settings"' in javascript
    assert 'const settingsView = document.getElementById("settingsView");' in javascript
    assert "settingsView.hidden = !settingsActive;" in javascript
    assert 'remove.setAttribute("aria-label", "Remove observation " + (index + 1));' in javascript
    assert (
        '"Next: click Compare carefully · attached photo + all page details will be analyzed"'
        in javascript
    )
