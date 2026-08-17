from __future__ import annotations

import json
import logging
import os
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .application import ApplicationProcessor
from .knowledge_graphql import execute_graphql
from .knowledge_store import KnowledgeStoreError
from .persistence import SessionState, SessionStore
from .upload_ingest import UploadError, parse_multipart
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
        if path.startswith("/api/kb/"):
            if not self._kb_authorized():
                return
            self._handle_kb_get(path)
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
        if path == "/api/kb/uploads":
            if not self._kb_authorized():
                return
            self._handle_kb_upload()
            return
        if path.startswith("/api/kb/"):
            if not self._kb_authorized():
                return
            body = self._read_json()
            if body is None:
                return
            self._handle_kb_post(path, body)
            return
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

    def do_DELETE(self) -> None:  # noqa: N802
        if not self._authorized():
            return
        path = urlparse(self.path).path
        if path.startswith("/api/kb/"):
            if not self._kb_authorized():
                return
            self._handle_kb_delete(path)
            return
        self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    # ------------------------------------------------------------------ KB console

    def _kb_authorized(self) -> bool:
        kb = self.server.processor.kb_service
        if not kb.config.enabled:
            self._kb_error(
                "kb_disabled", "The knowledge-base console is disabled.", HTTPStatus.FORBIDDEN
            )
            return False
        operator_token = os.environ.get("HELPME_KB_ACCESS_TOKEN", "")
        if operator_token:
            supplied = self.headers.get("Authorization", "").removeprefix("Bearer ")
            if not secrets.compare_digest(supplied, operator_token):
                self._kb_error(
                    "unauthorized", "Operator authorization required.", HTTPStatus.UNAUTHORIZED
                )
                return False
            return True
        if self._kb_loopback_dev():
            return True
        self._kb_error(
            "kb_operator_unconfigured",
            "No KB operator token is configured; access is refused.",
            HTTPStatus.FORBIDDEN,
        )
        return False

    def _kb_loopback_dev(self) -> bool:
        if os.environ.get("HELPME_KB_ALLOW_LOOPBACK_DEV", "").casefold() not in {
            "1",
            "true",
            "yes",
            "on",
        }:
            return False
        return str(self.server.server_address[0]) in {"127.0.0.1", "::1", "localhost"}

    def _kb_error(self, code: str, message: str, status: HTTPStatus) -> None:
        self._send_json({"error": {"code": code, "message": message}}, status)

    def _handle_kb_get(self, path: str) -> None:
        parts = [unquote(item) for item in path.split("/") if item]
        query = parse_qs(urlparse(self.path).query)
        kb = self.server.processor.kb_service
        if len(parts) == 3 and parts[2] == "capabilities":
            self._send_json(kb.capabilities())
            return
        if len(parts) == 3 and parts[2] == "overview":
            self._send_json(kb.overview())
            return
        if len(parts) == 3 and parts[2] == "documents":
            self._send_json(kb.list_documents(**self._kb_document_params(query)))
            return
        if len(parts) == 4 and parts[2] == "documents":
            detail = kb.document_detail(parts[3])
            if detail is None:
                self._kb_error("not_found", "Document not found.", HTTPStatus.NOT_FOUND)
                return
            self._send_json(detail)
            return
        if len(parts) == 5 and parts[2] == "documents" and parts[4] == "related":
            related = kb.related(parts[3], include_derived=self._kb_bool(query, "include_derived"))
            self._send_json({"related": related})
            return
        if len(parts) == 3 and parts[2] == "graph":
            self._send_json(
                kb.graph(
                    include_derived=self._kb_bool(query, "include_derived"),
                    max_nodes=self._kb_int(query, "max_nodes", 200),
                    selected_document_id=self._kb_str(query, "selected"),
                )
            )
            return
        if len(parts) == 3 and parts[2] == "jobs":
            self._send_json(
                {
                    "jobs": kb.list_jobs(
                        status=self._kb_str(query, "status"),
                        limit=self._kb_int(query, "limit", 50),
                        offset=self._kb_int(query, "offset", 0),
                    )
                }
            )
            return
        if len(parts) == 4 and parts[2] == "jobs":
            job = kb.job_detail(parts[3])
            if job is None:
                self._kb_error("not_found", "Job not found.", HTTPStatus.NOT_FOUND)
                return
            self._send_json(job)
            return
        if len(parts) == 3 and parts[2] == "uploads":
            self._send_json(
                {
                    "uploads": self.server.processor.knowledge_db.list_uploads(
                        status=self._kb_str(query, "status"),
                        limit=self._kb_int(query, "limit", 50),
                        offset=self._kb_int(query, "offset", 0),
                    )
                }
            )
            return
        self._kb_error("not_found", "Unknown knowledge-base route.", HTTPStatus.NOT_FOUND)

    def _handle_kb_upload(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        length = self._content_length()
        if length is None or length <= 0:
            self._kb_error(
                "invalid_request", "A content length is required.", HTTPStatus.BAD_REQUEST
            )
            return
        kb = self.server.processor.kb_service
        if length > kb.config.max_request_bytes:
            self._kb_error(
                "request_too_large",
                "Upload request exceeds the aggregate limit.",
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
            return
        body = self.rfile.read(length)
        if len(body) > kb.config.max_request_bytes:
            self._kb_error(
                "request_too_large",
                "Upload request exceeds the aggregate limit.",
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
            return
        try:
            parts, fields = parse_multipart(content_type, body)
        except UploadError as exc:
            self._kb_error(exc.code, str(exc), self._upload_error_status(exc))
            return
        try:
            results = kb.create_uploads(parts, fields)
        except UploadError as exc:
            self._kb_error(exc.code, str(exc), self._upload_error_status(exc))
            return
        self._send_json({"uploads": [result.to_dict() for result in results]}, HTTPStatus.ACCEPTED)

    def _handle_kb_post(self, path: str, body: dict[str, Any]) -> None:
        parts = [unquote(item) for item in path.split("/") if item]
        kb = self.server.processor.kb_service
        reviewed_by = str(body.get("reviewedBy", ""))[:200]
        review_note = str(body.get("reviewNote", ""))[:1000]
        try:
            if len(parts) == 5 and parts[2] == "uploads" and parts[3]:
                action = parts[4]
                upload_id = parts[3]
                if action == "approve":
                    kb.approve(upload_id, reviewed_by=reviewed_by, review_note=review_note)
                    self._send_json({"uploadId": upload_id, "status": "approved"})
                    return
                if action == "quarantine":
                    kb.quarantine(upload_id, reviewed_by=reviewed_by, review_note=review_note)
                    self._send_json({"uploadId": upload_id, "status": "quarantined"})
                    return
                if action == "retry":
                    job_id = kb.retry(upload_id)
                    self._send_json({"uploadId": upload_id, "jobId": job_id}, HTTPStatus.ACCEPTED)
                    return
            if (
                len(parts) == 5
                and parts[2] == "documents"
                and parts[3]
                and parts[4] in {"digest", "embed"}
            ):
                if parts[4] == "digest":
                    job_id = kb.queue_digest(parts[3])
                else:
                    job_id = kb.queue_embed(parts[3])
                self._send_json({"documentId": parts[3], "jobId": job_id}, HTTPStatus.ACCEPTED)
                return
        except (UploadError, KnowledgeStoreError) as exc:
            self._kb_error(
                getattr(exc, "code", "invalid_transition"),
                str(exc),
                self._kb_post_error_status(exc),
            )
            return
        self._kb_error("not_found", "Unknown knowledge-base route.", HTTPStatus.NOT_FOUND)

    def _handle_kb_delete(self, path: str) -> None:
        parts = [unquote(item) for item in path.split("/") if item]
        if len(parts) == 4 and parts[2] == "uploads" and parts[3]:
            try:
                result = self.server.processor.kb_service.delete(parts[3])
            except UploadError as exc:
                self._kb_error(exc.code, str(exc), HTTPStatus.NOT_FOUND)
                return
            if result is None:
                self._kb_error("not_found", "Upload not found.", HTTPStatus.NOT_FOUND)
                return
            self._send_json(result)
            return
        self._kb_error("not_found", "Unknown knowledge-base route.", HTTPStatus.NOT_FOUND)

    def _kb_document_params(self, query: dict[str, list[str]]) -> dict[str, Any]:
        return {
            "status": self._kb_str(query, "status"),
            "origin": self._kb_str(query, "origin"),
            "family": self._kb_str(query, "family"),
            "q": self._kb_str(query, "q"),
            "limit": self._kb_int(query, "limit", 50),
            "offset": self._kb_int(query, "offset", 0),
            "sort": self._kb_str(query, "sort", "updated"),
        }

    @staticmethod
    def _kb_str(query: dict[str, list[str]], key: str, default: str | None = None) -> str | None:
        values = query.get(key)
        if not values:
            return default
        return str(values[0])[:200]

    @staticmethod
    def _kb_int(query: dict[str, list[str]], key: str, default: int) -> int:
        values = query.get(key)
        if not values:
            return default
        try:
            return int(values[0])
        except ValueError:
            return default

    @staticmethod
    def _kb_bool(query: dict[str, list[str]], key: str) -> bool:
        values = query.get(key)
        if not values:
            return False
        return str(values[0]).casefold() in {"1", "true", "yes", "on"}

    @staticmethod
    def _upload_error_status(exc: UploadError) -> HTTPStatus:
        if exc.code == "invalid_content_type":
            return HTTPStatus.UNSUPPORTED_MEDIA_TYPE
        if exc.code in {"no_files", "too_many_files"}:
            return HTTPStatus.UNPROCESSABLE_ENTITY
        return HTTPStatus.BAD_REQUEST

    @staticmethod
    def _kb_post_error_status(exc: Exception) -> HTTPStatus:
        code = getattr(exc, "code", "")
        if code == "not_found":
            return HTTPStatus.NOT_FOUND
        if code == "not_retryable":
            return HTTPStatus.CONFLICT
        if code in {"processing_disabled", "processing_unavailable"}:
            return HTTPStatus.FORBIDDEN
        return HTTPStatus.UNPROCESSABLE_ENTITY

    def _content_length(self) -> int | None:
        try:
            return int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None

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
