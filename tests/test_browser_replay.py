from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from pathlib import Path

import pytest

from helpme_green.application import ApplicationProcessor
from helpme_green.knowledge import KnowledgeBase
from helpme_green.persistence import SessionStore
from helpme_green.server import _HelpmeServer

ROOT = Path(__file__).resolve().parents[1]


def _browser_executable() -> str | None:
    configured = os.environ.get("HELPME_BROWSER_PATH", "").strip()
    candidates = [
        configured,
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    return next(
        (
            command
            for command in (
                shutil.which("google-chrome"),
                shutil.which("chromium"),
                shutil.which("chromium-browser"),
            )
            if command
        ),
        None,
    )


def test_browser_replay_script_passes_node_syntax_gate() -> None:
    result = subprocess.run(
        ["node", "--check", str(ROOT / "scripts/browser_replay.mjs")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(
    _browser_executable() is None, reason="Chromium-compatible browser is unavailable"
)
@pytest.mark.parametrize("viewport", ["desktop", "mobile"])
def test_browser_replay_exercises_real_ui_and_survives_reload(
    tmp_path: Path, monkeypatch, viewport: str
) -> None:
    monkeypatch.setenv("HELPME_AI_ENABLED", "1")
    monkeypatch.setenv("HELPME_QUALITY_JUDGES", "0")
    monkeypatch.setenv("HELPME_MODEL", "localai:test-model")
    monkeypatch.setenv("HELPME_EMBEDDING_QUERY_ENABLED", "0")

    knowledge = KnowledgeBase.from_repository(ROOT)
    store = SessionStore(tmp_path / "data", knowledge_digest=knowledge.digest)
    processor = ApplicationProcessor(knowledge, store)
    prompts: list[str] = []

    def fake_complete_json(messages, **kwargs):
        del kwargs
        prompts.append(str(messages[-1]["content"]))
        return {
            "reply": f"Fake model answer {len(prompts)}: inspect the sample and record one more detail.",
            "hearing": {"subject": "sample", "situation": "", "aim": ""},
        }

    processor.model_router.complete_json = fake_complete_json
    server = _HelpmeServer(("127.0.0.1", 0), processor, store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    screenshot = tmp_path / f"browser-replay-{viewport}.png"
    browser = _browser_executable()
    assert browser is not None
    try:
        result = subprocess.run(
            [
                "node",
                str(ROOT / "scripts/browser_replay.mjs"),
                "--url",
                f"http://127.0.0.1:{server.server_port}/",
                "--browser",
                browser,
                "--viewport",
                viewport,
                "--screenshot",
                str(screenshot),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=45,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert payload["title"] == "helpme.green — Lab Notebook"
    assert payload["viewport"]["name"] == viewport
    expected_width, expected_height = (1280, 900) if viewport == "desktop" else (390, 844)
    assert payload["viewport"]["width"] == expected_width
    assert payload["viewport"]["height"] == expected_height
    assert payload["initial"]["horizontalOverflow"] is False
    assert payload["initial"]["coreControlsVisible"] is True
    assert payload["afterReload"]["observationCount"] == "2 saved"
    assert payload["afterReload"]["assistantVisible"] is True
    assert payload["afterReload"]["frameworkOverlay"] is False
    assert payload["afterReload"]["horizontalOverflow"] is False
    assert payload["afterReload"]["coreControlsVisible"] is True
    assert payload["consoleIssues"] == []
    assert screenshot.is_file() and screenshot.stat().st_size > 0
    assert len(prompts) == 2
    assert "rubber sample" in prompts[0]
    assert "What is the capital of Portugal?" in prompts[1]
