from __future__ import annotations

import os
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .knowledge_store import KnowledgeDatabase, KnowledgeStoreError
from .persistence import SessionStore
from .source_ingest import EmbeddingProvider
from .upload_ingest import (
    MAX_FILES_PER_REQUEST,
    MultipartPart,
    UploadError,
    UploadIngestor,
    UploadResult,
    UploadStorage,
)

_ALLOWED_EXTENSIONS = (".pdf", ".html", ".htm", ".xml", ".txt", ".csv", ".json", ".xlsx")
_RETRYABLE_ERRORS = {"invalid_upload_state"}


@dataclass(frozen=True)
class KbConfig:
    enabled: bool
    upload_dir: Path
    max_file_bytes: int
    max_request_bytes: int
    max_storage_bytes: int
    external_processing_enabled: bool


class KbService:
    """Operator knowledge-base console service: uploads, review, jobs, graph, retrieval policy."""

    def __init__(
        self,
        database: KnowledgeDatabase,
        store: SessionStore,
        *,
        config: KbConfig,
        embedding_provider: EmbeddingProvider | None = None,
        digest_router: Any | None = None,
        digest_skills: Any | None = None,
    ) -> None:
        self.database = database
        self.store = store
        self.config = config
        self.storage = UploadStorage(config.upload_dir, max_storage_bytes=config.max_storage_bytes)
        self.ingestor = UploadIngestor(
            database, self.storage, max_file_bytes=config.max_file_bytes, audit=self._audit
        )
        self.embedding_provider = embedding_provider
        self.digest_router = digest_router
        self.digest_skills = digest_skills
        self._worker_lock = threading.Lock()
        recovered = self.database.recover_jobs()
        if recovered:
            self._audit("kb.jobs.recovered", {"count": recovered})

    # ------------------------------------------------------------------ audit

    def _audit(self, event_type: str, payload: Mapping[str, Any]) -> str:
        try:
            return self.store.append_audit("", event_type, payload)
        except Exception:
            return ""

    # ------------------------------------------------------------------ capabilities

    def capabilities(self) -> dict[str, Any]:
        return {
            "enabled": self.config.enabled,
            "fileTypes": list(_ALLOWED_EXTENSIONS),
            "maxFileBytes": self.config.max_file_bytes,
            "maxRequestBytes": self.config.max_request_bytes,
            "maxFilesPerRequest": MAX_FILES_PER_REQUEST,
            "maxStorageBytes": self.config.max_storage_bytes,
            "externalProcessingEnabled": self.config.external_processing_enabled,
            "embeddingConfigured": self.embedding_provider is not None,
            "digestConfigured": self.digest_router is not None and self.digest_skills is not None,
            "embeddingAvailable": (
                self.embedding_provider is not None and self.config.external_processing_enabled
            ),
            "digestAvailable": (
                self.digest_router is not None
                and self.digest_skills is not None
                and self.config.external_processing_enabled
            ),
            "retrievalPolicy": {
                "manifest": {"catalogued": "allowed", "active": "allowed", "blocked": "excluded"},
                "userUpload": {
                    "review": "excluded",
                    "active": "allowed-with-unverified-label",
                    "blocked": "excluded",
                    "deleted": "excluded",
                },
            },
        }

    def overview(self) -> dict[str, Any]:
        overview = self.database.kb_overview()
        upload_status_counts: dict[str, int] = {}
        for upload in self.database.list_uploads(limit=1000):
            upload_status_counts[upload["status"]] = (
                upload_status_counts.get(upload["status"], 0) + 1
            )
        overview["uploads"] = {"byStatus": upload_status_counts}
        overview["storage"] = {
            "uploadDirBytes": self.storage.total_bytes(),
            "maxStorageBytes": self.config.max_storage_bytes,
        }
        return overview

    # ------------------------------------------------------------------ documents

    def list_documents(self, **params: Any) -> dict[str, Any]:
        return self.database.documents_list(**params)

    def document_detail(self, document_id: str) -> dict[str, Any] | None:
        return self.database.document_detail(document_id)

    def related(self, document_id: str, *, include_derived: bool) -> list[dict[str, Any]]:
        return self.database.related_documents(document_id, include_derived=include_derived)

    def graph(
        self,
        *,
        include_derived: bool = False,
        max_nodes: int = 200,
        selected_document_id: str | None = None,
    ) -> dict[str, Any]:
        return self.database.graph_projection(
            max_nodes=max_nodes,
            include_derived=include_derived,
            selected_document_id=selected_document_id,
        )

    # ------------------------------------------------------------------ uploads

    def create_uploads(
        self, parts: list[MultipartPart], fields: Mapping[str, str]
    ) -> list[UploadResult]:
        if len(parts) > MAX_FILES_PER_REQUEST:
            raise UploadError(
                "too_many_files", f"At most {MAX_FILES_PER_REQUEST} files per request."
            )
        results = [self.ingestor.ingest(part, fields=fields) for part in parts]
        # Process extract jobs synchronously so an HTTP response reflects durable state; the
        # background worker also reclaims any queued job left behind on a crash.
        self.run_available_jobs(max_jobs=len(results))
        return results

    # ------------------------------------------------------------------ review transitions

    def approve(self, upload_id: str, *, reviewed_by: str = "", review_note: str = "") -> str:
        source_id = self.database.approve_upload(
            upload_id, reviewed_by=reviewed_by, review_note=review_note
        )
        self._audit(
            "kb.source.approved",
            {"uploadId": upload_id, "sourceId": source_id, "reviewedBy": reviewed_by},
        )
        return source_id

    def quarantine(self, upload_id: str, *, reviewed_by: str = "", review_note: str = "") -> str:
        source_id = self.database.quarantine_upload(
            upload_id, reviewed_by=reviewed_by, review_note=review_note
        )
        self._audit(
            "kb.source.quarantined",
            {"uploadId": upload_id, "sourceId": source_id, "reviewedBy": reviewed_by},
        )
        return source_id

    def retry(self, upload_id: str) -> str:
        upload = self.database.get_upload(upload_id)
        if upload is None:
            raise UploadError("not_found", "Upload not found.")
        if upload["status"] != "failed":
            raise UploadError("not_retryable", "Only failed uploads can be retried.")
        if upload["errorCode"] in _RETRYABLE_ERRORS:
            raise UploadError("not_retryable", "This failure is not retryable.")
        self.database.update_upload(
            upload_id, status="validated", error_code=None, error_detail=None
        )
        job_id = self.database.create_job(
            "extract", upload_id, idempotency_key=upload["rawSha256"], progress_total=1
        )
        self.run_available_jobs(max_jobs=1)
        return job_id

    def delete(self, upload_id: str) -> dict[str, Any] | None:
        result = self.database.delete_upload(upload_id)
        if result is None:
            return None
        source_id, storage_key, raw_sha256 = result
        self.storage.delete(storage_key)
        self._audit(
            "kb.source.deleted",
            {"uploadId": upload_id, "sourceId": source_id, "rawSha256": raw_sha256},
        )
        return {"uploadId": upload_id, "sourceId": source_id, "deleted": True}

    # ------------------------------------------------------------------ optional processing

    def queue_digest(self, document_id: str) -> str:
        if not self.config.external_processing_enabled:
            raise UploadError("processing_disabled", "External processing is disabled by policy.")
        if self.digest_router is None or self.digest_skills is None:
            raise UploadError("processing_unavailable", "No digest provider is configured.")
        detail = self.database.document_detail(document_id, preview_chars=0, max_chunks=1)
        if detail is None:
            raise UploadError("not_found", "Document not found.")
        return self.database.create_job("digest", document_id, progress_total=1)

    def queue_embed(self, document_id: str) -> str:
        if not self.config.external_processing_enabled:
            raise UploadError("processing_disabled", "External processing is disabled by policy.")
        if self.embedding_provider is None:
            raise UploadError("processing_unavailable", "No embedding provider is configured.")
        detail = self.database.document_detail(document_id, preview_chars=0, max_chunks=1)
        if detail is None:
            raise UploadError("not_found", "Document not found.")
        return self.database.create_job("embed", document_id, progress_total=1)

    # ------------------------------------------------------------------ jobs / worker

    def list_jobs(
        self, *, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        return self.database.list_jobs(status=status, limit=limit, offset=offset)

    def job_detail(self, job_id: str) -> dict[str, Any] | None:
        return self.database.get_job(job_id)

    def run_available_jobs(self, *, max_jobs: int = 20) -> int:
        completed = 0
        for _ in range(max_jobs):
            job = self.database.claim_job(("extract", "embed", "digest", "delete", "graph-rebuild"))
            if job is None:
                break
            self._audit("kb.job.started", {"jobId": job["jobId"], "kind": job["kind"]})
            try:
                self._run_job(job)
                self.database.complete_job(job["jobId"])
                self._audit("kb.job.completed", {"jobId": job["jobId"], "kind": job["kind"]})
            except UploadError as exc:
                self.database.fail_job(
                    job["jobId"], error_code=exc.code, error_detail=str(exc), retryable=False
                )
                self._audit(
                    "kb.job.failed", {"jobId": job["jobId"], "kind": job["kind"], "code": exc.code}
                )
            except Exception as exc:  # noqa: BLE001 - bounded worker boundary
                self.database.fail_job(
                    job["jobId"],
                    error_code="worker_error",
                    error_detail=str(exc)[:500],
                    retryable=True,
                )
                self._audit(
                    "kb.job.failed",
                    {"jobId": job["jobId"], "kind": job["kind"], "code": "worker_error"},
                )
            completed += 1
        return completed

    def _run_job(self, job: Mapping[str, Any]) -> None:
        kind = str(job["kind"])
        target_id = str(job["targetId"])
        if kind == "extract":
            self.ingestor.extract(target_id)
        elif kind == "embed":
            self._run_embed(target_id)
        elif kind == "digest":
            self._run_digest(target_id)
        elif kind == "delete":
            self.storage.delete(target_id)
        elif kind == "graph-rebuild":
            self.database.rebuild_graph()
        else:
            raise UploadError("unknown_job_kind", f"Unsupported job kind {kind}.")

    def _run_embed(self, document_id: str) -> None:
        if self.embedding_provider is None:
            raise UploadError("processing_unavailable", "No embedding provider is configured.")
        pending = self.database.chunks_missing_embeddings(
            document_id, self.embedding_provider.model
        )
        for offset in range(0, len(pending), 32):
            batch = pending[offset : offset + 32]
            vectors = self.embedding_provider.embed([text for _, text in batch])
            self.database.set_chunk_embeddings(
                [chunk_id for chunk_id, _ in batch], vectors, self.embedding_provider.model
            )

    def _run_digest(self, document_id: str) -> None:
        if self.digest_router is None or self.digest_skills is None:
            raise UploadError("processing_unavailable", "No digest provider is configured.")
        from .source_digest import _DIGEST_CONTRACT

        detail = self.database.document_detail(document_id, preview_chars=0, max_chunks=1)
        if detail is None:
            raise UploadError("not_found", "Document not found.")
        chunks = self.database.chunk_catalog(document_id)
        for chunk in chunks:
            prompt = (
                f"Source ID: {detail['sourceId']}\n"
                f"Source title: {detail['title']}\n"
                f"Publisher: {detail['publisher']}\n"
                f"<source_passage>\n{chunk['text'][:5000]}\n</source_passage>"
            )
            try:
                response = self.digest_router.complete_json(
                    [{"role": "user", "content": prompt}],
                    system_contract=_DIGEST_CONTRACT,
                    max_tokens=500,
                )
            except Exception as exc:
                raise UploadError(
                    "digest_failed", "Digest provider request failed safely."
                ) from exc
            raw_notes = response.get("notes", [])
            if not isinstance(raw_notes, list):
                continue
            for raw_note in raw_notes[:4]:
                if not isinstance(raw_note, dict):
                    continue
                summary = raw_note.get("summary")
                applicability = raw_note.get("applicability")
                limitations = raw_note.get("limitations")
                if not all(isinstance(item, str) for item in (summary, applicability, limitations)):
                    continue
                try:
                    self.database.add_source_note(
                        source_id=detail["sourceId"],
                        summary=str(summary),
                        skill_id="general-conversation",
                        chunk_id=chunk["chunkId"],
                        applicability=str(applicability),
                        limitations=str(limitations),
                    )
                except KnowledgeStoreError:
                    continue


def kb_config_from_environment(data_dir: Path) -> KbConfig:
    """Read optional KB settings; the console is disabled by default."""

    def enabled(name: str) -> bool:
        return os.environ.get(name, "").casefold() in {"1", "true", "yes", "on"}

    def positive_int(name: str, default: int) -> int:
        raw = os.environ.get(name, "")
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            return default
        return value if value > 0 else default

    upload_dir = Path(os.environ.get("HELPME_UPLOAD_DIR", str(data_dir / "uploads"))).expanduser()
    return KbConfig(
        enabled=enabled("HELPME_KB_ENABLED"),
        upload_dir=upload_dir,
        max_file_bytes=positive_int("HELPME_KB_MAX_FILE_BYTES", 20_971_520),
        max_request_bytes=positive_int("HELPME_KB_MAX_REQUEST_BYTES", 84_000_000),
        max_storage_bytes=positive_int("HELPME_KB_MAX_STORAGE_BYTES", 1_073_741_824),
        external_processing_enabled=enabled("HELPME_KB_EXTERNAL_PROCESSING"),
    )
