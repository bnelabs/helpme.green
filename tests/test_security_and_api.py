from __future__ import annotations

import http.client
import json
import threading
from pathlib import Path

from cryptography.fernet import Fernet

from helpme_green.application import ApplicationProcessor
from helpme_green.knowledge import KnowledgeBase
from helpme_green.persistence import SecretStore, SessionStore
from helpme_green.server import _HelpmeServer

ROOT = Path(__file__).resolve().parents[1]


def _running_server(tmp_path: Path) -> tuple[_HelpmeServer, threading.Thread]:
    knowledge = KnowledgeBase.from_repository(ROOT)
    sessions = SessionStore(tmp_path / "data", knowledge_digest=knowledge.digest)
    processor = ApplicationProcessor(knowledge, sessions)
    server = _HelpmeServer(("127.0.0.1", 0), processor, sessions)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _running_server_with_secret(
    tmp_path: Path,
) -> tuple[_HelpmeServer, threading.Thread, SecretStore]:
    knowledge = KnowledgeBase.from_repository(ROOT)
    sessions = SessionStore(tmp_path / "data", knowledge_digest=knowledge.digest)
    secrets = SecretStore(tmp_path / "secrets", master_key=Fernet.generate_key())
    processor = ApplicationProcessor(knowledge, sessions, secret_store=secrets)
    server = _HelpmeServer(("127.0.0.1", 0), processor, sessions)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, secrets


def test_http_conversation_api_and_health_surface(tmp_path: Path) -> None:
    server, thread = _running_server(tmp_path)
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request(
            "POST",
            "/api/sessions",
            body=json.dumps({}),
            headers={"Content-Type": "application/json"},
        )
        created_response = connection.getresponse()
        created_response.read()
        connection.request("GET", "/healthz")
        health_response = connection.getresponse()
        health = json.loads(health_response.read())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert created_response.status == 201
    assert health_response.status == 200
    assert health["status"] == "ok"
    assert health["audit_chain_valid"]


def test_runtime_model_identity_exposes_provider_and_model_without_secrets(tmp_path: Path) -> None:
    server, thread = _running_server(tmp_path)
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request("GET", "/api/runtime/model")
        response = connection.getresponse()
        body = json.loads(response.read())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert response.status == 200
    assert body["identity"] == body["provider"] + ":" + body["model"]
    assert "key" not in json.dumps(body).casefold()


def test_settings_api_persists_model_configuration_without_returning_provider_key(
    tmp_path: Path, monkeypatch
) -> None:
    for name in (
        "HELPME_MODEL",
        "HELPME_PROVIDER",
        "HELPME_MODEL_PROFILES",
        "HELPME_AI_ENABLED",
        "OPENROUTER_API_KEY",
        "DEEPSEEK_API_KEY",
        "HELPME_LOCALAI_API_KEY",
        "LOCALAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    secret = "api-key-that-must-never-return"
    server, thread, secrets = _running_server_with_secret(tmp_path)
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request("GET", "/api/settings")
        initial_response = connection.getresponse()
        initial = json.loads(initial_response.read())
        connection.request(
            "POST",
            "/api/settings",
            body=json.dumps(
                {
                    "provider": "openrouter",
                    "model": "example/model",
                    "ai_enabled": True,
                    "localai_base_url": "",
                    "localai_tls_verify": True,
                    "quality_judges": False,
                    "model_retries": 0,
                    "model_discovery_timeout": 10,
                    "max_model_timeout_seconds": 120,
                    "profile": {"vision": True, "temperature": 0.4, "max_tokens": 800},
                    "api_key": secret,
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        saved_response = connection.getresponse()
        saved = json.loads(saved_response.read())
        connection.request("GET", "/api/runtime/model")
        runtime_response = connection.getresponse()
        runtime = json.loads(runtime_response.read())
        connection.request(
            "POST",
            "/api/sessions",
            body=json.dumps({}),
            headers={"Content-Type": "application/json"},
        )
        session_response = connection.getresponse()
        session = json.loads(session_response.read())
        connection.request(
            "POST",
            "/api/settings",
            body=json.dumps({"profile": {"messages": "blocked"}}),
            headers={"Content-Type": "application/json"},
        )
        invalid_response = connection.getresponse()
        invalid = json.loads(invalid_response.read())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    settings_file = (tmp_path / "data" / "settings.json").read_text(encoding="utf-8")
    encrypted_key = secrets.get("provider_api_key_openrouter")
    assert initial_response.status == 200
    assert initial["api_keys"]["openrouter"]["configured"] is False
    assert saved_response.status == 200
    assert saved["settings"]["identity"] == "openrouter:example/model"
    assert saved["settings"]["api_keys"]["openrouter"]["source"] == "encrypted"
    assert runtime_response.status == 200
    assert runtime["identity"] == "openrouter:example/model"
    assert session_response.status == 201
    assert session["model"] == "openrouter:example/model"
    assert invalid_response.status == 400
    assert invalid["code"] == "invalid_settings"
    assert secret not in settings_file
    assert secret not in json.dumps(saved)
    assert encrypted_key == secret


def test_concurrent_messages_on_one_session_are_serialized(tmp_path: Path) -> None:
    server, thread = _running_server(tmp_path)
    first_started = threading.Event()
    second_started = threading.Event()
    release_first = threading.Event()
    call_lock = threading.Lock()
    call_count = 0

    def fake_complete_json(messages, **kwargs):
        del kwargs
        nonlocal call_count
        with call_lock:
            call_count += 1
            current_call = call_count
        if current_call == 1:
            first_started.set()
            assert release_first.wait(timeout=5)
        else:
            second_started.set()
        return {
            "reply": f"Saved observation {current_call}.",
            "hearing": {"subject": "material", "situation": "", "aim": ""},
        }

    server.processor.model_router.complete_json = fake_complete_json

    def post(path: str, message: str | None = None) -> tuple[int, dict[str, object]]:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
        body = {} if message is None else {"message": message}
        connection.request(
            "POST", path, body=json.dumps(body), headers={"Content-Type": "application/json"}
        )
        response = connection.getresponse()
        payload = json.loads(response.read())
        connection.close()
        return response.status, payload

    try:
        status, created = post("/api/sessions")
        assert status == 201
        session_id = str(created["session_id"])
        first_result: list[tuple[int, dict[str, object]]] = []
        second_result: list[tuple[int, dict[str, object]]] = []
        first_thread = threading.Thread(
            target=lambda: first_result.append(
                post(f"/api/sessions/{session_id}/message", "first observation")
            )
        )
        second_thread = threading.Thread(
            target=lambda: second_result.append(
                post(f"/api/sessions/{session_id}/message", "second observation")
            )
        )
        first_thread.start()
        assert first_started.wait(timeout=5)
        second_thread.start()
        assert not second_started.wait(timeout=0.15)
        release_first.set()
        first_thread.join(timeout=10)
        second_thread.join(timeout=10)

        assert first_result and first_result[0][0] == 200
        assert second_result and second_result[0][0] == 200
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request("GET", f"/api/sessions/{session_id}")
        response = connection.getresponse()
        session = json.loads(response.read())["session"]
        connection.close()
    finally:
        release_first.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    messages = session["conversation"]
    assert [item["content"] for item in messages if item["role"] == "user"] == [
        "first observation",
        "second observation",
    ]
    assert len(messages) == 4


def test_api_shapes_and_invalid_graphql_are_stable(tmp_path: Path) -> None:
    server, thread = _running_server(tmp_path)
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request("GET", "/api/expert/capabilities")
        capability_response = connection.getresponse()
        capabilities = json.loads(capability_response.read())
        connection.request("GET", "/api/knowledge/sources")
        source_response = connection.getresponse()
        sources = json.loads(source_response.read())
        connection.request(
            "POST",
            "/graphql",
            body=json.dumps({"query": "{"}),
            headers={"Content-Type": "application/json"},
        )
        graphql_response = connection.getresponse()
        graphql = json.loads(graphql_response.read())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert capability_response.status == 200
    assert {"skills", "machines", "knowledge", "mcp"}.issubset(capabilities)
    assert capabilities["mcp"]["read_only"] is True
    assert capabilities["mcp"]["web_exposed"] is False
    assert source_response.status == 200
    assert isinstance(sources["sources"], list)
    assert graphql_response.status == 400
    assert isinstance(graphql.get("errors"), list)


def test_tampered_audit_chain_makes_health_degraded(tmp_path: Path) -> None:
    server, thread = _running_server(tmp_path)
    try:
        server.store.audit_path.write_text('{"event_type":"tampered"}\n', encoding="utf-8")
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request("GET", "/healthz")
        response = connection.getresponse()
        payload = json.loads(response.read())
        connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert response.status == 503
    assert payload == {"status": "degraded", "audit_chain_valid": False}


def test_http_conversation_api_accepts_ordinary_language(tmp_path: Path) -> None:
    server, thread = _running_server(tmp_path)
    server.processor.model_router.complete_json = lambda messages, **kwargs: {
        "reply": "Rubber can mean several different materials. What kind is it, and what do you want to do with it?",
        "hearing": {"subject": "rubber", "situation": "", "aim": ""},
    }
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request(
            "POST",
            "/api/sessions",
            body=json.dumps({}),
            headers={"Content-Type": "application/json"},
        )
        created_response = connection.getresponse()
        created = json.loads(created_response.read())
        connection.request(
            "POST",
            f"/api/sessions/{created['session_id']}/message",
            body=json.dumps({"message": "I have rubber"}),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert created_response.status == 201
    assert response.status == 200
    assert payload["error"] is None
    assert "Precious Plastic" not in payload["text"]
    assert payload["data"]["hearing"]["subject"] == "rubber"


def test_http_conversation_api_forwards_images_without_persisting_bytes(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HELPME_AI_ENABLED", "1")
    monkeypatch.setenv("HELPME_QUALITY_JUDGES", "0")
    monkeypatch.setenv("HELPME_MODEL", "localai:test-model")
    server, thread = _running_server(tmp_path)
    captured: dict[str, object] = {}

    def fake_complete_json(messages, **kwargs):
        del messages
        captured.update(kwargs)
        return {
            "reply": "I can inspect the supplied image.",
            "hearing": {"subject": "sample", "situation": "", "aim": ""},
        }

    server.processor.model_router.complete_json = fake_complete_json
    image_data = "aGVsbG8="
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request(
            "POST",
            "/api/sessions",
            body=json.dumps({}),
            headers={"Content-Type": "application/json"},
        )
        created_response = connection.getresponse()
        created = json.loads(created_response.read())
        connection.request(
            "POST",
            f"/api/sessions/{created['session_id']}/message",
            body=json.dumps(
                {
                    "message": "Look at this uploaded sample.",
                    "images": [{"data_url": f"data:image/png;base64,{image_data}"}],
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read())
        connection.request("GET", f"/api/sessions/{created['session_id']}")
        session_response = connection.getresponse()
        session_body = session_response.read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert created_response.status == 201
    assert response.status == 200
    assert payload["text"].startswith("I can inspect the supplied image.")
    assert "Models can make mistakes" in payload["text"]
    assert captured["images"] == [{"mime_type": "image/png", "data": image_data}]
    assert image_data not in session_body


def test_http_streaming_conversation_api_emits_progress_and_deltas(tmp_path: Path) -> None:
    server, thread = _running_server(tmp_path)
    server.processor.model_router.complete_json = lambda messages, **kwargs: {
        "reply": "The sample needs one more detail.",
        "hearing": {"subject": "sample", "situation": "", "aim": ""},
    }
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request(
            "POST",
            "/api/sessions",
            body=json.dumps({}),
            headers={"Content-Type": "application/json"},
        )
        created_response = connection.getresponse()
        created = json.loads(created_response.read())
        connection.request(
            "POST",
            f"/api/sessions/{created['session_id']}/message/stream",
            body=json.dumps({"message": "I have a sample"}),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        stream = response.read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert created_response.status == 201
    assert response.status == 200
    assert response.getheader("Content-Type") == "text/event-stream; charset=utf-8"
    assert "event: status" in stream
    assert "event: delta" in stream
    assert "event: complete" in stream
    assert "The sample needs one more detail." in stream


def test_health_and_homepage_remain_public_when_token_is_enabled(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HELPME_ACCESS_TOKEN", "synthetic-access-token")
    server, thread = _running_server(tmp_path)
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request("GET", "/healthz")
        health_response = connection.getresponse()
        health = json.loads(health_response.read())
        connection.request("GET", "/")
        public_response = connection.getresponse()
        public_body = public_response.read().decode("utf-8")
        connection.request(
            "POST",
            "/api/sessions",
            body=json.dumps({}),
            headers={"Content-Type": "application/json"},
        )
        unauthorized_response = connection.getresponse()
        unauthorized_response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert health_response.status == 200
    assert health["status"] == "ok"
    assert public_response.status == 200
    assert "Connection key" in public_body
    assert public_response.getheader("X-Content-Type-Options") == "nosniff"
    content_security_policy = public_response.getheader("Content-Security-Policy", "")
    assert "default-src 'self'" in content_security_policy
    assert "script-src 'self'" in content_security_policy
    assert "unsafe-inline" not in content_security_policy
    assert unauthorized_response.status == 401


def test_homepage_has_natural_conversation_surface(tmp_path: Path) -> None:
    server, thread = _running_server(tmp_path)
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request("GET", "/")
        response = connection.getresponse()
        body = response.read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert response.status == 200
    assert "New material note" in body
    assert "Describe what is in front of you" in body
    assert "Material library" in body
    assert "Add a photo" in body
    assert "What form is the sample?" in body
    assert "Powder / dust" in body
    assert "modelDisclosure" in body
    assert "full image and every saved detail" in body
    assert "Clear removed originals" in body
    assert "Compare with assistant" in body
    assert "not a test or a final answer" in body
    assert "Nothing is lost when you move between phases." in body
    assert "Shift+Enter for a new line" in body
    assert 'rel="icon" href="/assets/favicon.png"' in body
    assert 'src="/assets/brand-mark.png"' in body
    assert "access token" not in body.casefold()


def test_homepage_serves_external_frontend_assets_with_security_headers(tmp_path: Path) -> None:
    server, thread = _running_server(tmp_path)
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request("GET", "/static/app.css")
        css_response = connection.getresponse()
        css = css_response.read()
        connection.request("GET", "/static/app.js")
        js_response = connection.getresponse()
        javascript = js_response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert css_response.status == 200
    assert css_response.getheader("Content-Type") == "text/css; charset=utf-8"
    assert css_response.getheader("Content-Security-Policy")
    assert b".status-note" in css
    assert js_response.status == 200
    assert js_response.getheader("Content-Type") == "text/javascript; charset=utf-8"
    assert b"indexedDB" in javascript


def test_homepage_serves_the_owned_visual_asset(tmp_path: Path) -> None:
    server, thread = _running_server(tmp_path)
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request("GET", "/assets/helpme-field-journal.png")
        response = connection.getresponse()
        asset = response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert response.status == 200
    assert response.getheader("Content-Type") == "image/png"
    assert asset.startswith(b"\x89PNG\r\n\x1a\n")


def test_homepage_serves_material_reference_assets(tmp_path: Path) -> None:
    server, thread = _running_server(tmp_path)
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        for path in (
            "/assets/material-plastics.webp",
            "/assets/material-metals.webp",
            "/assets/material-pp.webp",
            "/assets/material-textiles.webp",
        ):
            connection.request("GET", path)
            response = connection.getresponse()
            asset = response.read()
            assert response.status == 200
            assert response.getheader("Content-Type") == "image/webp"
            assert asset.startswith(b"RIFF") and asset[8:12] == b"WEBP"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_homepage_serves_the_brand_mark_for_logo_and_favicon(tmp_path: Path) -> None:
    server, thread = _running_server(tmp_path)
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        for path in ("/assets/brand-mark.png", "/assets/favicon.png"):
            connection.request("GET", path)
            response = connection.getresponse()
            asset = response.read()
            assert response.status == 200
            assert response.getheader("Content-Type") == "image/png"
            assert asset.startswith(b"\x89PNG\r\n\x1a\n")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
