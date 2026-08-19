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
    assert '<script type="module" src="../static/app.js" defer></script>' in html
    assert '<script type="module" src="../static/app-kb.js" defer></script>' in html
    assert "<style" not in html.lower()
    assert " style=" not in html.lower()
    assert "Explore" not in html
    assert "profile-button" not in html
    assert 'class="file-launch-guard"' in html and 'class="app-shell" hidden' in html


def test_frontend_script_passes_node_syntax_gate() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.fail("Node.js is required to run the frontend syntax gate")

    for script in (
        STATIC_ROOT / "app.js",
        STATIC_ROOT / "app-kb.js",
        STATIC_ROOT / "app-stream.js",
        STATIC_ROOT / "app-storage.js",
        STATIC_ROOT / "file-launch-guard.js",
    ):
        result = subprocess.run(
            [node, "--check", str(script)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr


def test_frontend_contract_covers_state_and_accessibility_fixes() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    stylesheet = (STATIC_ROOT / "app.css").read_text(encoding="utf-8")
    javascript = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    kb_javascript = (STATIC_ROOT / "app-kb.js").read_text(encoding="utf-8")
    stream = (STATIC_ROOT / "app-stream.js").read_text(encoding="utf-8")
    storage = (STATIC_ROOT / "app-storage.js").read_text(encoding="utf-8")

    assert 'id="retryRequest"' in html
    assert 'id="assistantRead" aria-live="polite"' in html
    assert 'id="comparisonRead" aria-live="polite"' in html
    assert 'id="modelDisclosure"' in html
    assert 'id="clearDetachedPhotos"' in html
    assert 'aria-describedby="evidenceFieldsHint evidenceGuidance"' in html
    assert 'id="library"' in html and 'role="dialog"' in html
    assert "createPhotoStorage" in javascript
    assert "indexedDB" in storage
    assert "SUPPORTED_VISION_IMAGE_TYPES" in javascript
    assert "modelImagesForPage" in javascript
    assert 'accept="image/png,image/jpeg,image/webp,image/gif"' in html
    assert "state.sessionId" in javascript
    assert "lastFailedRequest" in javascript
    assert "navigator.onLine" in javascript
    assert "message/stream" in javascript
    assert "ReadableStream" not in javascript
    assert "getReader" in stream
    assert "Transfer-Encoding" not in stream
    assert "@media (max-width: 760px)" in stylesheet
    assert ".notebook-spread { border-radius: 14px; display: block; min-height: 0; }" in stylesheet
    assert (
        ".material-search {\n  background: var(--paper);\n  border: 1px solid var(--line);\n  border-radius: 9px;\n  display: block;"
        in stylesheet
    )
    assert "@media (prefers-reduced-motion: reduce)" in stylesheet
    assert "animation-duration: .001ms !important" in stylesheet
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
    assert "KB_TOKEN_KEY" not in javascript
    assert "kbFetch" in kb_javascript
    assert "KB_TOKEN_KEY" in kb_javascript
    assert "kbView.hidden = !kbActive;" in kb_javascript


def test_frontend_navigation_isolates_kb_and_returns_to_notebook_for_library() -> None:
    javascript = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    kb_javascript = (STATIC_ROOT / "app-kb.js").read_text(encoding="utf-8")
    stylesheet = (STATIC_ROOT / "app.css").read_text(encoding="utf-8")

    assert ".notebook-workspace[hidden] { display: none; }" in stylesheet
    assert (
        'if (window.location.hash === "#kb" || window.location.hash === "#settings") window.location.hash = "#notebook";'
        in javascript
    )
    assert '"helpme.green — Knowledge base"' in kb_javascript
    assert '"helpme.green — Settings"' in kb_javascript
    assert 'const settingsView = document.getElementById("settingsView");' in kb_javascript
    assert "settingsView.hidden = !settingsActive;" in kb_javascript
    assert 'remove.setAttribute("aria-label", "Remove observation " + (index + 1));' in javascript
    assert (
        '"Next: click Compare carefully · attached photo + all page details will be analyzed"'
        in javascript
    )


def test_mobile_layout_keeps_phase_rail_and_typography_readable() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    stylesheet = (STATIC_ROOT / "app.css").read_text(encoding="utf-8")

    assert "body { font-size: 16px; }" in stylesheet
    assert 'id="mobilePhaseSelect"' in html
    assert 'id="mobilePhaseProgress"' in html
    assert "mobilePhaseSelect.replaceChildren()" in javascript
    assert 'elements.mobilePhaseSelect.addEventListener("change"' in javascript
    assert ".phase-list { display: none; }" in stylesheet
    assert ".mobile-phase-control select" in stylesheet
    assert ".mobile-phase-progress span" in stylesheet
    assert ".page-lede { font-size: 14px; line-height: 1.6; }" in stylesheet
    assert ".observation-composer textarea { font-size: 16px; min-height: 96px; }" in stylesheet
    assert (
        ".settings-field input, .settings-field select, .settings-field textarea { "
        "font-size: 16px; min-height: 48px; }" in stylesheet
    )
    assert ".check-field { font-size: 14px; line-height: 1.4; min-height: 48px; }" in stylesheet
    assert (
        '.kb-toolbar input[type="search"], .kb-toolbar select, .kb-toolbar button '
        "{ font-size: 16px; min-height: 44px; }" in stylesheet
    )
