from __future__ import annotations

import http.client
import json
import threading
from pathlib import Path

from helpme_green.application import ApplicationProcessor
from helpme_green.knowledge import KnowledgeBase
from helpme_green.persistence import SessionStore
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
    assert "What are you trying to figure out?" in body
    assert "Tell me what you’re dealing with" in body
    assert "New conversation" in body
    assert "Shift+Enter for a new line" in body
    assert "access token" not in body.casefold()
