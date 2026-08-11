from __future__ import annotations

import json
import os
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import unquote, urlparse

from .console import CommandProcessor
from .knowledge_graphql import execute_graphql
from .persistence import SessionState, SessionStore
from .web import INDEX_HTML as _CONVERSATION_HTML


class _Handler(BaseHTTPRequestHandler):
    server: _ConsoleServer

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/healthz":
            self._send_json(
                {"status": "ok", "audit_chain_valid": self.server.store.verify_audit_chain()}
            )
            return
        if path == "/":
            self._send(HTTPStatus.OK, _CONVERSATION_HTML, "text/html; charset=utf-8")
            return
        if not self._authorized():
            return
        if path == "/api/expert/capabilities":
            self._send_json(
                {
                    "skills": self.server.processor.skill_registry.public_catalog(),
                    "machines": self.server.processor.machine_catalog.public_catalog(),
                    "agent_contracts": self.server.processor.skill_registry.expert_contracts(),
                    "mcp": self.server.processor.mcp.capabilities(),
                    "knowledge": {
                        "schema_version": self.server.processor.knowledge_db.schema_version,
                        "digest": self.server.processor.knowledge_db.digest(),
                        "sources": len(self.server.processor.knowledge_db.source_catalog()),
                        "machine_profiles": len(self.server.processor.machine_catalog.profiles),
                        "ingestion": self.server.processor.knowledge_db.ingestion_summary(),
                    },
                }
            )
            return
        if path == "/api/knowledge/sources":
            self._send_json({"sources": self.server.processor.knowledge_db.source_catalog()})
            return
        parts = [unquote(item) for item in path.split("/") if item]
        if len(parts) == 3 and parts[:2] == ["api", "sessions"]:
            try:
                session = self.server.store.load_session(parts[2])
            except (FileNotFoundError, ValueError):
                self._send_json({"error": "session_not_found"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json({"session": session.to_dict()})
            return
        self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorized():
            return
        path = urlparse(self.path).path
        body = self._read_json()
        if body is None:
            return
        if path == "/graphql":
            query = body.get("query")
            if not isinstance(query, str) or len(query) > 20_000:
                self._send_json(
                    {"errors": [{"message": "query must be a short string"}]},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            result = execute_graphql(
                self.server.processor.knowledge_db,
                self.server.processor.skill_registry,
                query,
                self.server.processor.machine_catalog,
            )
            self._send_json(result, HTTPStatus.BAD_REQUEST if "errors" in result else HTTPStatus.OK)
            return
        if path == "/api/sessions":
            session = SessionState.new(
                material=str(body.get("material", "")),
                geography=str(body.get("geography", "")),
            )
            self.server.store.save_session(session)
            self._send_json(
                {
                    "session_id": session.session_id,
                    "message": "Tell me what you have, what you are trying to figure out, or what you want to change.",
                    "model": session.model_identity,
                },
                HTTPStatus.CREATED,
            )
            return
        parts = [unquote(item) for item in path.split("/") if item]
        if len(parts) == 4 and parts[:2] == ["api", "sessions"] and parts[3] == "message":
            try:
                session = self.server.store.load_session(parts[2])
                message = body.get("message")
                if not isinstance(message, str) or len(message) > 4000:
                    raise ValueError("message must be a short string")
                response = self.server.processor.respond_to_message(session, message)
            except (FileNotFoundError, ValueError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            self._send_json(
                {
                    "text": response.text,
                    "data": response.data,
                    "error": response.error,
                    "exit_requested": response.exit_requested,
                }
            )
            return
        if len(parts) == 4 and parts[:2] == ["api", "sessions"] and parts[3] == "command":
            try:
                session = self.server.store.load_session(parts[2])
                command = body.get("command")
                if not isinstance(command, str) or len(command) > 4000:
                    raise ValueError("command must be a short string")
                response = self.server.processor.execute(session, command)
            except (FileNotFoundError, ValueError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            status = HTTPStatus.BAD_REQUEST if response.error else HTTPStatus.OK
            self._send_json(
                {
                    "text": response.text,
                    "data": response.data,
                    "error": response.error,
                    "exit_requested": response.exit_requested,
                },
                status,
            )
            return
        self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def _authorized(self) -> bool:
        expected = os.environ.get("HELPME_CONSOLE_TOKEN")
        if not expected:
            return True
        supplied = self.headers.get("Authorization", "")
        actual = supplied.removeprefix("Bearer ")
        if not secrets.compare_digest(actual, expected):
            self._send_json({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
            return False
        return True

    def _read_json(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 64_000:
                raise ValueError("request body limit exceeded")
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("JSON object required")
            return data
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return None

    def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        self._send(
            status, json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8"
        )

    def _send(self, status: HTTPStatus, body: str, content_type: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: Any) -> None:
        del format, args


class _ConsoleServer(ThreadingHTTPServer):
    def __init__(
        self, address: tuple[str, int], processor: CommandProcessor, store: SessionStore
    ) -> None:
        super().__init__(address, _Handler)
        self.processor = processor
        self.store = store


def serve(processor: CommandProcessor, store: SessionStore, *, host: str, port: int) -> None:
    server = _ConsoleServer((host, port), processor, store)
    print(f"helpme.green console listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
