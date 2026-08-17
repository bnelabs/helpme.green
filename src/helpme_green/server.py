from __future__ import annotations

import json
import logging
import os
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .application import ApplicationProcessor
from .knowledge_graphql import execute_graphql
from .persistence import SessionState, SessionStore
from .web import get_index_html, get_static_root

_ASSET_ROOT = Path(os.environ.get("HELPME_ROOT", str(Path.cwd()))) / "assets"
_ASSET_CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
_STATIC_CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}
LOGGER = logging.getLogger(__name__)
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; "
        "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
        "form-action 'self'"
    ),
}


class _Handler(BaseHTTPRequestHandler):
    server: _HelpmeServer

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/healthz":
            audit_chain_valid = self.server.store.verify_audit_chain()
            self._send_json(
                {
                    "status": "ok" if audit_chain_valid else "degraded",
                    "audit_chain_valid": audit_chain_valid,
                },
                HTTPStatus.OK if audit_chain_valid else HTTPStatus.SERVICE_UNAVAILABLE,
            )
            return
        if path == "/":
            self._send(HTTPStatus.OK, get_index_html(), "text/html; charset=utf-8")
            return
        if path.startswith("/assets/"):
            self._send_asset(path)
            return
        if path.startswith("/static/"):
            self._send_static(path)
            return
        if not self._authorized():
            return
        if path == "/api/expert/capabilities":
            self._send_json(
                {
                    "skills": self.server.processor.skill_registry.public_catalog(),
                    "machines": self.server.processor.machine_catalog.public_catalog(),
                    "mcp": self.server.processor.mcp.capabilities(),
                    "knowledge": {
                        "database_version": self.server.processor.knowledge_db.database_version,
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
                embedding_provider=self.server.processor.query_embedding_provider,
                reranker=self.server.processor.reranker,
            )
            self._send_json(result, HTTPStatus.BAD_REQUEST if "errors" in result else HTTPStatus.OK)
            return
        if path == "/api/sessions":
            session = SessionState.new(
                topic=str(body.get("topic", "")),
                geography=str(body.get("geography", "")),
            )
            self.server.store.save_session(session)
            self._send_json(
                {
                    "session_id": session.session_id,
                    "message": "Tell me what you’re exploring, what you have, or what you want to change.",
                    "model": session.model_identity,
                },
                HTTPStatus.CREATED,
            )
            return
        parts = [unquote(item) for item in path.split("/") if item]
        if (
            len(parts) == 5
            and parts[:2] == ["api", "sessions"]
            and parts[3:] == ["message", "stream"]
        ):
            self._stream_message(parts[2], body)
            return
        if len(parts) == 4 and parts[:2] == ["api", "sessions"] and parts[3] == "message":
            try:
                message = body.get("message")
                if not isinstance(message, str) or len(message) > 4000:
                    raise ValueError("message must be a short string")
                with self.server.store.session_lock(parts[2]):
                    session = self.server.store.load_session(parts[2])
                    response = self.server.processor.respond_to_message(session, message)
            except (FileNotFoundError, ValueError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            self._send_json(
                {
                    "text": response.text,
                    "data": response.data,
                    "error": response.error,
                }
            )
            return
        self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def _stream_message(self, session_id: str, body: dict[str, Any]) -> None:
        message = body.get("message")
        if not isinstance(message, str) or len(message) > 4000:
            self._send_json({"error": "message must be a short string"}, HTTPStatus.BAD_REQUEST)
            return
        stream_started = False
        try:
            with self.server.store.session_lock(session_id):
                session = self.server.store.load_session(session_id)
                self._send_sse_headers()
                stream_started = True
                self._send_sse_event("status", {"stage": "reading"})
                response = self.server.processor.respond_to_message(session, message)
                for chunk in _text_chunks(response.text):
                    self._send_sse_event("delta", {"text": chunk})
                self._send_sse_event(
                    "complete",
                    {"text": response.text, "data": response.data, "error": response.error},
                )
        except (FileNotFoundError, ValueError) as exc:
            if stream_started:
                self._send_sse_event("error", {"error": str(exc)})
            else:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:  # pragma: no cover - defensive network boundary
            try:
                if stream_started:
                    self._send_sse_event("error", {"error": "assistant_unavailable"})
                else:
                    self._send_json(
                        {"error": "assistant_unavailable"}, HTTPStatus.SERVICE_UNAVAILABLE
                    )
            except (BrokenPipeError, ConnectionResetError, OSError):
                return

    def _authorized(self) -> bool:
        expected = os.environ.get("HELPME_ACCESS_TOKEN")
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

    def _send_asset(self, path: str) -> None:
        relative = path.removeprefix("/assets/")
        asset = self._safe_file(_ASSET_ROOT, relative)
        if asset is None:
            self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            return
        self._send_bytes(
            HTTPStatus.OK,
            asset.read_bytes(),
            _ASSET_CONTENT_TYPES.get(asset.suffix.casefold(), "application/octet-stream"),
        )

    def _send_static(self, path: str) -> None:
        static_root = get_static_root()
        if static_root is None:
            self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            return
        relative = path.removeprefix("/static/")
        asset = self._safe_file(static_root, relative)
        if asset is None:
            self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            return
        self._send_bytes(
            HTTPStatus.OK,
            asset.read_bytes(),
            _STATIC_CONTENT_TYPES.get(asset.suffix.casefold(), "application/octet-stream"),
        )

    @staticmethod
    def _safe_file(root: Path, relative: str) -> Path | None:
        if not relative or "/" in relative or "\\" in relative:
            return None
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            return None
        return candidate if candidate.is_file() else None

    def _send(self, status: HTTPStatus, body: str, content_type: str) -> None:
        encoded = body.encode("utf-8")
        self._send_bytes(status, encoded, content_type)

    def _send_bytes(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in _SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_sse_headers(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.send_header("Connection", "close")
        for name, value in _SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()

    def _send_sse_event(self, event: str, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False)
        self.wfile.write(f"event: {event}\ndata: {encoded}\n\n".encode())
        self.wfile.flush()

    def log_message(self, format: str, *args: Any) -> None:
        message = (format % args).replace("\r", "\\r").replace("\n", "\\n")
        LOGGER.info("http_request remote=%s %s", self.client_address[0], message)


class _HelpmeServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self, address: tuple[str, int], processor: ApplicationProcessor, store: SessionStore
    ) -> None:
        super().__init__(address, _Handler)
        self.processor = processor
        self.store = store


def _text_chunks(text: str, size: int = 160) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)] or [""]


def serve(processor: ApplicationProcessor, store: SessionStore, *, host: str, port: int) -> None:
    server = _HelpmeServer((host, port), processor, store)
    print(f"helpme.green listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
