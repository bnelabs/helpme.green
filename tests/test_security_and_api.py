from __future__ import annotations

import http.client
import json
import threading
from pathlib import Path

from cryptography.fernet import Fernet

from helpme_green.console import CommandProcessor
from helpme_green.knowledge import KnowledgeBase
from helpme_green.persistence import SecretStore, SessionStore
from helpme_green.server import _ConsoleServer

ROOT = Path(__file__).resolve().parents[1]


def test_byok_is_encrypted_and_not_present_as_plaintext(tmp_path: Path) -> None:
    secret = "deepseek-secret-value-that-must-not-be-logged"
    store = SecretStore(tmp_path / "secrets", master_key=Fernet.generate_key())
    store.set("deepseek", secret)
    raw = (tmp_path / "secrets" / "deepseek.json").read_text(encoding="utf-8")

    assert secret not in raw
    assert store.get("deepseek") == secret
    assert store.names() == ("deepseek",)


def test_http_console_api_is_command_only_and_has_health_gate(tmp_path: Path) -> None:
    knowledge = KnowledgeBase.from_repository(ROOT)
    sessions = SessionStore(tmp_path / "data", knowledge_digest=knowledge.digest)
    processor = CommandProcessor(knowledge, sessions)
    server = _ConsoleServer(("127.0.0.1", 0), processor, sessions)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request(
            "POST",
            "/api/sessions",
            body=json.dumps({"material": "copper cable"}),
            headers={"Content-Type": "application/json"},
        )
        created = json.loads(connection.getresponse().read())
        session_id = created["session_id"]
        connection.request(
            "POST",
            f"/api/sessions/{session_id}/command",
            body=json.dumps({"command": "/status"}),
            headers={"Content-Type": "application/json"},
        )
        response = json.loads(connection.getresponse().read())
        connection.request("GET", "/healthz")
        health = json.loads(connection.getresponse().read())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert response["error"] is None
    assert response["data"]["mcp"].startswith("read-only")
    assert health["status"] == "ok"
    assert health["audit_chain_valid"]


def test_http_conversation_api_accepts_ordinary_language(tmp_path: Path) -> None:
    knowledge = KnowledgeBase.from_repository(ROOT)
    sessions = SessionStore(tmp_path / "data", knowledge_digest=knowledge.digest)
    processor = CommandProcessor(knowledge, sessions)
    processor.model_router.complete_json = lambda messages, *, system_contract, max_tokens: {
        "reply": "A dusty light bulb is a useful place to start. What do you want to do with it?",
        "hearing": {
            "object": "light bulb",
            "condition": "dusty",
            "goal": "understand the useful next step",
        },
    }
    server = _ConsoleServer(("127.0.0.1", 0), processor, sessions)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
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
            body=json.dumps({"message": "I have a dusty light bulb and want to understand it."}),
            headers={"Content-Type": "application/json"},
        )
        response_http = connection.getresponse()
        response_status = response_http.status
        response = json.loads(response_http.read())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert created_response.status == 201
    assert response_status == 200
    assert response["error"] is None
    assert "/ask" not in response["text"]
    assert response["data"]["hearing"]["object"] == "light bulb"


def test_health_endpoint_stays_available_when_console_token_is_enabled(
    tmp_path: Path, monkeypatch
) -> None:
    knowledge = KnowledgeBase.from_repository(ROOT)
    sessions = SessionStore(tmp_path / "data", knowledge_digest=knowledge.digest)
    processor = CommandProcessor(knowledge, sessions)
    monkeypatch.setenv("HELPME_CONSOLE_TOKEN", "synthetic-console-token")
    server = _ConsoleServer(("127.0.0.1", 0), processor, sessions)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
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
            body=json.dumps({"material": "copper cable"}),
            headers={"Content-Type": "application/json"},
        )
        unauthorized_api_response = connection.getresponse()
        unauthorized_api_response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert health_response.status == 200
    assert health["status"] == "ok"
    assert public_response.status == 200
    assert "Console token" in public_body
    assert unauthorized_api_response.status == 401


def test_homepage_is_conversation_first(tmp_path: Path) -> None:
    knowledge = KnowledgeBase.from_repository(ROOT)
    sessions = SessionStore(tmp_path / "data", knowledge_digest=knowledge.digest)
    processor = CommandProcessor(knowledge, sessions)
    server = _ConsoleServer(("127.0.0.1", 0), processor, sessions)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
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
    assert "What are you trying to figure out?" in body
    assert "Tell me what you’re dealing with" in body
    assert "New conversation" in body
    assert "Shift+Enter for a new line" in body
    assert "/ask" not in body
    assert "/evidence" not in body
    assert "Start intake" not in body
