from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import sqlite3
import threading
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class KnowledgeStoreError(ValueError):
    """Raised when a knowledge store operation would violate its contract."""


_AUTHORITY_TIERS = {"primary", "secondary", "industry", "low-tech", "community"}
_ACCESS_MODES = {"web", "pdf", "api", "local-reference"}
_MANIFEST_STATUSES = {"catalogued", "active", "blocked"}
_UPLOAD_STATUSES = {"review", "active", "blocked", "deleted"}
_ORIGINS = {"manifest", "user-upload"}
_UPLOAD_LIFECYCLE = {"received", "validated", "processing", "ingested", "failed", "deleted"}
_JOB_STATUSES = {"queued", "running", "done", "failed", "cancelled"}
_JOB_KINDS = {"upload", "extract", "embed", "digest", "delete", "graph-rebuild"}
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    title: str
    url: str
    publisher: str
    source_type: str
    material_families: tuple[str, ...] = ()
    jurisdiction: str = ""
    license_note: str = ""
    limitations: str = ""
    authority_tier: str = "secondary"
    scale: str = ""
    access_mode: str = "web"
    fetch_urls: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise KnowledgeStoreError("Knowledge sources must use an explicit HTTPS URL.")
        if not self.source_id.strip() or not self.title.strip():
            raise KnowledgeStoreError("Knowledge sources require an ID and title.")
        if self.authority_tier not in _AUTHORITY_TIERS:
            raise KnowledgeStoreError(
                f"Knowledge source authority tier must be one of {sorted(_AUTHORITY_TIERS)}."
            )
        if self.access_mode not in _ACCESS_MODES:
            raise KnowledgeStoreError(
                f"Knowledge source access mode must be one of {sorted(_ACCESS_MODES)}."
            )
        for fetch_url in self.fetch_urls:
            parsed_fetch_url = urlparse(fetch_url)
            if parsed_fetch_url.scheme != "https" or not parsed_fetch_url.hostname:
                raise KnowledgeStoreError("Knowledge source fallback URLs must use HTTPS.")


@dataclass(frozen=True)
class IngestResult:
    source_id: str
    document_id: str
    chunk_count: int
    content_sha256: str
    reused: bool


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    document_id: str
    source_id: str
    title: str
    url: str
    publisher: str
    material_families: tuple[str, ...]
    source_status: str
    authority_tier: str
    scale: str
    text: str
    score: float
    retrieval_mode: str = "lexical"
    origin: str = "manifest"

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunkId": self.chunk_id,
            "documentId": self.document_id,
            "sourceId": self.source_id,
            "title": self.title,
            "url": self.url,
            "publisher": self.publisher,
            "materialFamilies": list(self.material_families),
            "sourceStatus": self.source_status,
            "authorityTier": self.authority_tier,
            "scale": self.scale,
            "text": self.text,
            "score": self.score,
            "retrievalMode": self.retrieval_mode,
            "origin": self.origin,
        }


@dataclass(frozen=True)
class GraphRecord:
    node_id: str
    node_type: str
    label: str
    edge_type: str
    related_node_id: str
    related_node_type: str
    related_label: str

    def to_dict(self) -> dict[str, str]:
        return {
            "nodeId": self.node_id,
            "nodeType": self.node_type,
            "label": self.label,
            "edgeType": self.edge_type,
            "relatedNodeId": self.related_node_id,
            "relatedNodeType": self.related_node_type,
            "relatedLabel": self.related_label,
        }


_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+./-]*", re.IGNORECASE)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _normalise_text(value: str) -> str:
    lines = [" ".join(line.split()) for line in value.replace("\x00", " ").splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _cosine_similarity(left: list[float], right: list[Any]) -> float | None:
    if len(left) != len(right) or not right:
        return None
    try:
        values = [float(value) for value in right]
    except (TypeError, ValueError):
        return None
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in values))
    if left_norm == 0 or right_norm == 0:
        return None
    return sum(a * b for a, b in zip(left, values, strict=True)) / (left_norm * right_norm)


def _chunks(value: str, maximum: int = 1400) -> tuple[str, ...]:
    paragraphs = [item.strip() for item in re.split(r"\n{2,}", value) if item.strip()]
    if not paragraphs:
        return ()
    result: list[str] = []
    current = ""
    for paragraph in paragraphs:
        while len(paragraph) > maximum:
            if current:
                result.append(current)
                current = ""
            cut = paragraph.rfind(" ", 0, maximum)
            cut = cut if cut >= maximum // 2 else maximum
            result.append(paragraph[:cut].strip())
            paragraph = paragraph[cut:].strip()
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) > maximum and current:
            result.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        result.append(current)
    return tuple(result)


_FRESH_SCHEMA = """
CREATE TABLE sources (
    source_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT,
    publisher TEXT NOT NULL,
    source_type TEXT NOT NULL,
    material_families TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    license_note TEXT NOT NULL,
    limitations TEXT NOT NULL,
    source_status TEXT NOT NULL DEFAULT 'catalogued',
    content_sha256 TEXT,
    content_type TEXT,
    fetched_at TEXT,
    authority_tier TEXT NOT NULL DEFAULT 'secondary',
    scale TEXT NOT NULL DEFAULT '',
    access_mode TEXT NOT NULL DEFAULT 'web',
    origin TEXT NOT NULL DEFAULT 'manifest',
    metadata_origin TEXT NOT NULL DEFAULT 'declared',
    reviewed_at TEXT,
    reviewed_by TEXT,
    review_note TEXT,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    content_type TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    extraction_status TEXT NOT NULL,
    UNIQUE(source_id, content_sha256)
);
CREATE TABLE chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    ordinal INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding_json TEXT,
    embedding_model TEXT,
    UNIQUE(document_id, ordinal)
);
CREATE VIRTUAL TABLE chunk_fts USING fts5(
    chunk_id UNINDEXED,
    source_id UNINDEXED,
    material_families,
    text
);
CREATE TABLE source_notes (
    note_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),
    skill_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    applicability TEXT NOT NULL,
    limitations TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(source_id, chunk_id, skill_id, summary)
);
CREATE TABLE graph_nodes (
    node_id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL,
    label TEXT NOT NULL
);
CREATE TABLE graph_edges (
    edge_id TEXT PRIMARY KEY,
    from_node TEXT NOT NULL REFERENCES graph_nodes(node_id),
    to_node TEXT NOT NULL REFERENCES graph_nodes(node_id),
    edge_type TEXT NOT NULL,
    directed INTEGER NOT NULL DEFAULT 0,
    edge_origin TEXT NOT NULL DEFAULT 'declared',
    reason_code TEXT,
    reason_detail TEXT,
    projection_version INTEGER NOT NULL DEFAULT 0,
    UNIQUE(from_node, to_node, edge_type)
);
CREATE TABLE ingestion_runs (
    run_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    detail TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL
);
"""

_UPLOADS_AND_JOBS_SCHEMA = """
CREATE TABLE IF NOT EXISTS uploads (
    upload_id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    raw_sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    declared_content_type TEXT NOT NULL,
    detected_content_type TEXT NOT NULL,
    extension TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'received',
    source_id TEXT,
    document_id TEXT,
    error_code TEXT,
    error_detail TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    target_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    step TEXT NOT NULL DEFAULT '',
    progress_current INTEGER NOT NULL DEFAULT 0,
    progress_total INTEGER NOT NULL DEFAULT 0,
    detail TEXT NOT NULL DEFAULT '',
    error_code TEXT,
    error_detail TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    idempotency_key TEXT,
    claimed_at TEXT,
    lease_until TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    updated_at TEXT NOT NULL,
    finished_at TEXT
);
"""

_INDEXES_SCHEMA = """
CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(source_status);
CREATE INDEX IF NOT EXISTS idx_sources_origin ON sources(origin);
CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source_id, version);
CREATE INDEX IF NOT EXISTS idx_source_notes_source ON source_notes(source_id);
CREATE INDEX IF NOT EXISTS idx_uploads_status ON uploads(status);
CREATE INDEX IF NOT EXISTS idx_uploads_raw_sha256 ON uploads(raw_sha256);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_kind ON jobs(kind);
CREATE INDEX IF NOT EXISTS idx_jobs_lease ON jobs(lease_until);
"""


class KnowledgeDatabase:
    """SQLite knowledge-management store with a rebuildable graph and FTS index.

    Downloaded documents, source notes, and retrieval projections live here at runtime. The
    checked-in YAML packs remain registered source metadata; this store never silently turns a
    fetch into an independent fact. One shared connection and re-entrant lock serialize access
    inside the local process; WAL mode and a bounded busy timeout cover short-lived coordination
    with another process. A multi-process deployment still requires a separately designed writer
    or database service.
    """

    database_version = 4

    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.path.parent.chmod(0o700)
        except OSError:
            pass
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(str(self.path), timeout=5.0, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._digest_cache: str | None = None
        self._digest_cache_signature: tuple[int, int] | None = None
        self._initialize()

    def _initialize(self) -> None:
        self._connection.executescript(
            "CREATE TABLE IF NOT EXISTS store_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
        )
        self._connection.execute("DELETE FROM store_meta WHERE key = 'schema_version'")
        fresh = self._table_exists("sources") is False
        version = self._stored_version()
        if fresh:
            with self._connection:
                self._connection.executescript(_FRESH_SCHEMA)
                self._write_version(self.database_version)
        elif version < self.database_version:
            # Migration runs outside a transaction so PRAGMA foreign_keys takes effect.
            self._migrate_to_v4()
            self._write_version(self.database_version)
        with self._connection:
            self._connection.executescript(_UPLOADS_AND_JOBS_SCHEMA)
            self._connection.executescript(_INDEXES_SCHEMA)
            self._cleanup_legacy()

    def _table_exists(self, name: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
        ).fetchone()
        return row is not None

    def _stored_version(self) -> int:
        row = self._connection.execute(
            "SELECT value FROM store_meta WHERE key = 'database_version'"
        ).fetchone()
        if row is None:
            return 0
        try:
            return int(str(row["value"]))
        except ValueError:
            return 0

    def _write_version(self, version: int) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO store_meta(key, value) VALUES ('database_version', ?)",
            (str(version),),
        )

    def _cleanup_legacy(self) -> None:
        """Idempotent cleanup applied whenever the store is at the current version."""
        self._connection.execute("DROP TABLE IF EXISTS claim_reviews")
        self._connection.execute("DROP TABLE IF EXISTS claims")
        self._connection.execute(
            "DELETE FROM graph_edges WHERE from_node IN "
            "(SELECT node_id FROM graph_nodes WHERE node_type = 'claim') "
            "OR to_node IN (SELECT node_id FROM graph_nodes WHERE node_type = 'claim')"
        )
        self._connection.execute("DELETE FROM graph_nodes WHERE node_type = 'claim'")
        self._connection.execute(
            "UPDATE sources SET source_status = 'catalogued' WHERE source_status = 'candidate'"
        )

    def _migrate_to_v4(self) -> None:
        """Forward-only migration from the v3 layout to the v4 operator-KB layout.

        Foreign keys are disabled only for the duration of this migration so the parent-table
        rebuilds do not trip SQLite's implicit row-deletion checks. The migration is idempotent:
        reopening a database that already carries the `origin` column skips the rebuild.
        """
        # Clear any implicit transaction so the foreign_keys pragma is not a no-op.
        self._connection.commit()
        self._connection.execute("PRAGMA foreign_keys = OFF")
        try:
            self._connection.execute("DROP TABLE IF EXISTS claim_reviews")
            self._connection.execute("DROP TABLE IF EXISTS claims")
            self._connection.execute(
                "DELETE FROM graph_edges WHERE from_node IN "
                "(SELECT node_id FROM graph_nodes WHERE node_type = 'claim') "
                "OR to_node IN (SELECT node_id FROM graph_nodes WHERE node_type = 'claim')"
            )
            self._connection.execute("DELETE FROM graph_nodes WHERE node_type = 'claim'")
            self._connection.execute(
                "UPDATE sources SET source_status = 'catalogued' WHERE source_status = 'candidate'"
            )
            columns = {
                str(row[1])
                for row in self._connection.execute("PRAGMA table_info(sources)").fetchall()
            }
            for name, definition in (
                ("authority_tier", "TEXT NOT NULL DEFAULT 'secondary'"),
                ("scale", "TEXT NOT NULL DEFAULT ''"),
                ("access_mode", "TEXT NOT NULL DEFAULT 'web'"),
            ):
                if name not in columns:
                    self._connection.execute(f"ALTER TABLE sources ADD COLUMN {name} {definition}")
            if "origin" not in columns:
                self._rebuild_sources_table()
                self._rebuild_graph_edges_table()
        finally:
            self._connection.execute("PRAGMA foreign_keys = ON")

    def _rebuild_sources_table(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE sources_migrated (
                source_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT,
                publisher TEXT NOT NULL,
                source_type TEXT NOT NULL,
                material_families TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                license_note TEXT NOT NULL,
                limitations TEXT NOT NULL,
                source_status TEXT NOT NULL DEFAULT 'catalogued',
                content_sha256 TEXT,
                content_type TEXT,
                fetched_at TEXT,
                authority_tier TEXT NOT NULL DEFAULT 'secondary',
                scale TEXT NOT NULL DEFAULT '',
                access_mode TEXT NOT NULL DEFAULT 'web',
                origin TEXT NOT NULL DEFAULT 'manifest',
                metadata_origin TEXT NOT NULL DEFAULT 'declared',
                reviewed_at TEXT,
                reviewed_by TEXT,
                review_note TEXT,
                deleted_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            INSERT INTO sources_migrated(
                source_id, title, url, publisher, source_type, material_families, jurisdiction,
                license_note, limitations, source_status, content_sha256, content_type, fetched_at,
                authority_tier, scale, access_mode, origin, metadata_origin, created_at, updated_at
            )
            SELECT source_id, title, url, publisher, source_type, material_families, jurisdiction,
                license_note, limitations, source_status, content_sha256, content_type, fetched_at,
                authority_tier, scale, access_mode, 'manifest', 'declared', created_at, updated_at
            FROM sources;
            DROP TABLE sources;
            ALTER TABLE sources_migrated RENAME TO sources;
            """
        )

    def _rebuild_graph_edges_table(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS graph_edges_migrated (
                edge_id TEXT PRIMARY KEY,
                from_node TEXT NOT NULL REFERENCES graph_nodes(node_id),
                to_node TEXT NOT NULL REFERENCES graph_nodes(node_id),
                edge_type TEXT NOT NULL,
                directed INTEGER NOT NULL DEFAULT 0,
                edge_origin TEXT NOT NULL DEFAULT 'declared',
                reason_code TEXT,
                reason_detail TEXT,
                projection_version INTEGER NOT NULL DEFAULT 0,
                UNIQUE(from_node, to_node, edge_type)
            );
            INSERT INTO graph_edges_migrated(
                edge_id, from_node, to_node, edge_type, directed, edge_origin, reason_code,
                reason_detail, projection_version
            )
            SELECT edge_id, from_node, to_node, edge_type, 0, 'declared', NULL, NULL, 0
            FROM graph_edges;
            DROP TABLE graph_edges;
            ALTER TABLE graph_edges_migrated RENAME TO graph_edges;
            """
        )

    def close(self) -> None:
        with self._lock:
            try:
                self._connection.execute("PRAGMA wal_checkpoint(PASSIVE)")
            except sqlite3.OperationalError:
                pass
            finally:
                self._connection.close()

    def register_source(self, source: SourceSpec, *, status: str = "catalogued") -> None:
        """Register source metadata without downloading or treating it as a conclusion."""
        if status not in {"catalogued", "active", "blocked"}:
            raise KnowledgeStoreError("Invalid source status.")
        timestamp = _now()
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO sources(
                    source_id, title, url, publisher, source_type, material_families,
                    jurisdiction, license_note, limitations, source_status, created_at, updated_at,
                    authority_tier, scale, access_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    title=excluded.title, url=excluded.url, publisher=excluded.publisher,
                    source_type=excluded.source_type, material_families=excluded.material_families,
                    jurisdiction=excluded.jurisdiction, license_note=excluded.license_note,
                    limitations=excluded.limitations, updated_at=excluded.updated_at,
                    authority_tier=excluded.authority_tier, scale=excluded.scale,
                    access_mode=excluded.access_mode
                """,
                (
                    source.source_id,
                    source.title,
                    source.url,
                    source.publisher,
                    source.source_type,
                    _canonical(list(source.material_families)),
                    source.jurisdiction,
                    source.license_note,
                    source.limitations,
                    status,
                    timestamp,
                    timestamp,
                    source.authority_tier,
                    source.scale,
                    source.access_mode,
                ),
            )
            self._graph_node(f"source:{source.source_id}", "source", source.title)
            for family in source.material_families:
                family_id = f"material:{family}"
                self._graph_node(family_id, "material_family", family)
                self._graph_edge(f"source:{source.source_id}", family_id, "covers")

    def register_user_upload_source(
        self,
        *,
        source_id: str,
        title: str,
        publisher: str,
        source_type: str,
        material_families: tuple[str, ...] = (),
        jurisdiction: str = "",
        license_note: str = "",
        limitations: str = "",
        authority_tier: str = "secondary",
        scale: str = "",
        metadata_origin: str = "operator-supplied",
    ) -> str:
        """Register a user-uploaded source in `review` without a fabricated public URL."""
        if not source_id.strip() or not title.strip():
            raise KnowledgeStoreError("User uploads require a source ID and title.")
        timestamp = _now()
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO sources(
                    source_id, title, url, publisher, source_type, material_families,
                    jurisdiction, license_note, limitations, source_status, authority_tier,
                    scale, access_mode, origin, metadata_origin, created_at, updated_at
                ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, 'review', ?, ?, 'local-reference',
                    'user-upload', ?, ?, ?)
                """,
                (
                    source_id,
                    title,
                    publisher,
                    source_type,
                    _canonical(list(material_families)),
                    jurisdiction,
                    license_note,
                    limitations,
                    authority_tier,
                    scale,
                    metadata_origin,
                    timestamp,
                    timestamp,
                ),
            )
            self._graph_node(f"source:{source_id}", "source", title)
            for family in material_families:
                family_id = f"material:{family}"
                self._graph_node(family_id, "material_family", family)
                self._graph_edge(f"source:{source_id}", family_id, "covers")
        return source_id

    def ingest_document(
        self,
        source: SourceSpec,
        content: str,
        *,
        content_type: str,
        fetched_at: str | None = None,
        extraction_status: str = "extracted",
    ) -> IngestResult:
        normalized = _normalise_text(content)
        if not normalized:
            raise KnowledgeStoreError("A knowledge document cannot be empty.")
        timestamp = fetched_at or _now()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        material_families = _canonical(list(source.material_families))
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO sources(
                    source_id, title, url, publisher, source_type, material_families,
                    jurisdiction, license_note, limitations, source_status, content_sha256,
                    content_type, fetched_at, authority_tier, scale, access_mode, origin,
                    metadata_origin, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'catalogued', ?, ?, ?, ?, ?, ?,
                    'manifest', 'declared', ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    title=excluded.title, url=excluded.url, publisher=excluded.publisher,
                    source_type=excluded.source_type, material_families=excluded.material_families,
                    jurisdiction=excluded.jurisdiction, license_note=excluded.license_note,
                    limitations=excluded.limitations, content_sha256=excluded.content_sha256,
                    content_type=excluded.content_type, fetched_at=excluded.fetched_at,
                    updated_at=excluded.updated_at, authority_tier=excluded.authority_tier,
                    scale=excluded.scale, access_mode=excluded.access_mode
                """,
                (
                    source.source_id,
                    source.title,
                    source.url,
                    source.publisher,
                    source.source_type,
                    material_families,
                    source.jurisdiction,
                    source.license_note,
                    source.limitations,
                    digest,
                    content_type,
                    timestamp,
                    source.authority_tier,
                    source.scale,
                    source.access_mode,
                    timestamp,
                    timestamp,
                ),
            )
            return self._insert_document(
                source_id=source.source_id,
                title=source.title,
                material_families=source.material_families,
                normalized=normalized,
                digest=digest,
                content_type=content_type,
                timestamp=timestamp,
                extraction_status=extraction_status,
            )

    def ingest_upload_document(
        self,
        *,
        source_id: str,
        title: str,
        material_families: tuple[str, ...],
        content: str,
        content_type: str,
        fetched_at: str | None = None,
        extraction_status: str = "extracted",
    ) -> IngestResult:
        """Insert an extracted document for a user-uploaded source already in `review`."""
        normalized = _normalise_text(content)
        if not normalized:
            raise KnowledgeStoreError("A knowledge document cannot be empty.")
        timestamp = fetched_at or _now()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT source_id FROM sources WHERE source_id = ? AND origin = 'user-upload'",
                (source_id,),
            ).fetchone()
            if row is None:
                raise KnowledgeStoreError("User-upload source is not registered.")
            self._connection.execute(
                "UPDATE sources SET content_sha256 = ?, content_type = ?, fetched_at = ?, "
                "updated_at = ? WHERE source_id = ?",
                (digest, content_type, timestamp, timestamp, source_id),
            )
            return self._insert_document(
                source_id=source_id,
                title=title,
                material_families=material_families,
                normalized=normalized,
                digest=digest,
                content_type=content_type,
                timestamp=timestamp,
                extraction_status=extraction_status,
            )

    def _insert_document(
        self,
        *,
        source_id: str,
        title: str,
        material_families: tuple[str, ...],
        normalized: str,
        digest: str,
        content_type: str,
        timestamp: str,
        extraction_status: str,
    ) -> IngestResult:
        existing = self._connection.execute(
            "SELECT document_id FROM documents WHERE source_id = ? AND content_sha256 = ?",
            (source_id, digest),
        ).fetchone()
        if existing is not None:
            return IngestResult(source_id, str(existing["document_id"]), 0, digest, True)
        row = self._connection.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 AS next_version FROM documents WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        version = int(row["next_version"])
        document_id = f"doc-{source_id}-{version}-{digest[:12]}"
        self._connection.execute(
            """
            INSERT INTO documents(
                document_id, source_id, version, content, content_sha256, content_type,
                fetched_at, extraction_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                source_id,
                version,
                normalized,
                digest,
                content_type,
                timestamp,
                extraction_status,
            ),
        )
        chunks = _chunks(normalized)
        families_text = " ".join(material_families)
        for ordinal, chunk in enumerate(chunks):
            chunk_id = f"chunk-{document_id}-{ordinal}"
            self._connection.execute(
                "INSERT INTO chunks(chunk_id, document_id, ordinal, text) VALUES (?, ?, ?, ?)",
                (chunk_id, document_id, ordinal, chunk),
            )
            self._connection.execute(
                "INSERT INTO chunk_fts(chunk_id, source_id, material_families, text) "
                "VALUES (?, ?, ?, ?)",
                (chunk_id, source_id, families_text, chunk),
            )
        self._graph_node(f"source:{source_id}", "source", title)
        self._graph_node(document_id, "document", f"{title} v{version}")
        self._graph_edge(f"source:{source_id}", document_id, "has_document")
        for family in material_families:
            family_id = f"material:{family}"
            self._graph_node(family_id, "material_family", family)
            self._graph_edge(f"source:{source_id}", family_id, "covers")
        for ordinal in range(len(chunks)):
            chunk_id = f"chunk-{document_id}-{ordinal}"
            self._graph_node(chunk_id, "chunk", f"{title} passage {ordinal + 1}")
            self._graph_edge(document_id, chunk_id, "contains")
        return IngestResult(source_id, document_id, len(chunks), digest, False)

    def record_run(
        self, source_id: str, outcome: str, detail: str, started_at: str, finished_at: str
    ) -> str:
        run_id = f"run-{uuid.uuid4()}"
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO ingestion_runs(run_id, source_id, outcome, detail, started_at, finished_at) VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, source_id, outcome, detail[:2000], started_at, finished_at),
            )
        return run_id

    def set_embeddings(self, document_id: str, embeddings: list[list[float]], model: str) -> None:
        with self._lock, self._connection:
            rows = self._connection.execute(
                "SELECT chunk_id FROM chunks WHERE document_id = ? ORDER BY ordinal", (document_id,)
            ).fetchall()
            if len(rows) != len(embeddings):
                raise KnowledgeStoreError(
                    "Embedding count does not match the document chunk count."
                )
            for row, embedding in zip(rows, embeddings, strict=True):
                if not embedding or any(not isinstance(value, (int, float)) for value in embedding):
                    raise KnowledgeStoreError("Embeddings must be non-empty numeric vectors.")
                self._connection.execute(
                    "UPDATE chunks SET embedding_json = ?, embedding_model = ? WHERE chunk_id = ?",
                    (_canonical(embedding), model, row["chunk_id"]),
                )

    def chunks_missing_embeddings(self, document_id: str, model: str) -> list[tuple[str, str]]:
        """Return chunks that are absent or stale for the requested embedding model."""
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT chunk_id, text
                FROM chunks
                WHERE document_id = ?
                  AND (embedding_json IS NULL OR embedding_model <> ?)
                ORDER BY ordinal
                """,
                (document_id, model),
            ).fetchall()
        return [(str(row["chunk_id"]), str(row["text"])) for row in rows]

    def documents_missing_embeddings(self, model: str) -> list[tuple[str, str]]:
        """Return latest extracted documents with at least one missing or stale vector."""
        with self._lock:
            rows = self._connection.execute(
                """
                WITH latest_documents AS (
                    SELECT d.*,
                           ROW_NUMBER() OVER (
                               PARTITION BY d.source_id ORDER BY d.version DESC
                           ) AS row_number
                    FROM documents AS d
                )
                SELECT d.document_id, d.source_id
                FROM latest_documents AS d
                WHERE d.row_number = 1
                  AND d.extraction_status = 'extracted'
                  AND EXISTS (
                      SELECT 1
                      FROM chunks AS c
                      WHERE c.document_id = d.document_id
                        AND (c.embedding_json IS NULL OR c.embedding_model <> ?)
                  )
                ORDER BY d.source_id
                """,
                (model,),
            ).fetchall()
        return [(str(row["document_id"]), str(row["source_id"])) for row in rows]

    def latest_extracted_source_ids(self) -> set[str]:
        """Return sources whose latest document is currently extracted and searchable."""
        with self._lock:
            rows = self._connection.execute(
                """
                WITH latest_documents AS (
                    SELECT d.source_id, d.extraction_status,
                           ROW_NUMBER() OVER (
                               PARTITION BY d.source_id ORDER BY d.version DESC
                           ) AS row_number
                    FROM documents AS d
                )
                SELECT source_id
                FROM latest_documents
                WHERE row_number = 1 AND extraction_status = 'extracted'
                """
            ).fetchall()
        return {str(row["source_id"]) for row in rows}

    def set_chunk_embeddings(
        self, chunk_ids: list[str], embeddings: list[list[float]], model: str
    ) -> None:
        if len(chunk_ids) != len(embeddings):
            raise KnowledgeStoreError("Embedding count does not match the chunk count.")
        if not model.strip():
            raise KnowledgeStoreError("Embedding model is required.")
        with self._lock, self._connection:
            for chunk_id, embedding in zip(chunk_ids, embeddings, strict=True):
                if not embedding or any(not isinstance(value, (int, float)) for value in embedding):
                    raise KnowledgeStoreError("Embeddings must be non-empty numeric vectors.")
                cursor = self._connection.execute(
                    """
                    UPDATE chunks
                    SET embedding_json = ?, embedding_model = ?
                    WHERE chunk_id = ?
                    """,
                    (_canonical(embedding), model, chunk_id),
                )
                if cursor.rowcount != 1:
                    raise KnowledgeStoreError(f"Embedding chunk {chunk_id!r} is not present.")

    def chunks_for_document(self, document_id: str) -> list[str]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT text FROM chunks WHERE document_id = ? ORDER BY ordinal", (document_id,)
            ).fetchall()
        return [str(row["text"]) for row in rows]

    def chunk_catalog(self, document_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT chunk_id, ordinal, text FROM chunks WHERE document_id = ? ORDER BY ordinal",
                (document_id,),
            ).fetchall()
        return [
            {
                "chunkId": str(row["chunk_id"]),
                "ordinal": int(row["ordinal"]),
                "text": str(row["text"]),
            }
            for row in rows
        ]

    def quarantine_documents(self, document_ids: Iterable[str], *, reason: str) -> int:
        """Exclude known bad extractions from retrieval without deleting the audit record."""
        values = tuple(str(item) for item in document_ids if str(item).strip())
        if not values or not reason.strip():
            return 0
        placeholders = ",".join("?" for _ in values)
        with self._lock, self._connection:
            cursor = self._connection.execute(
                f"UPDATE documents SET extraction_status = ? WHERE document_id IN ({placeholders})",
                (f"blocked:{reason.strip()[:120]}", *values),
            )
        return int(cursor.rowcount)

    def documents_for_digesting(self, *, limit: int = 20) -> list[dict[str, Any]]:
        """Return the latest extracted source documents for an explicit digest run."""
        with self._lock:
            rows = self._connection.execute(
                """
                WITH latest_documents AS (
                    SELECT d.*,
                           ROW_NUMBER() OVER (
                               PARTITION BY d.source_id ORDER BY d.version DESC
                           ) AS row_number
                    FROM documents AS d
                )
                SELECT d.document_id, d.source_id, d.version, d.content_type, d.fetched_at,
                       d.extraction_status,
                       s.title, s.publisher, s.material_families, s.authority_tier, s.scale,
                       s.source_status
                FROM latest_documents AS d
                JOIN sources AS s ON s.source_id = d.source_id
                WHERE d.row_number = 1 AND d.extraction_status = 'extracted'
                ORDER BY d.fetched_at DESC, d.document_id
                LIMIT ?
                """,
                (max(1, min(limit, 100)),),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "documentId": str(row["document_id"]),
                    "sourceId": str(row["source_id"]),
                    "version": int(row["version"]),
                    "contentType": str(row["content_type"]),
                    "extractionStatus": str(row["extraction_status"]),
                    "fetchedAt": str(row["fetched_at"]),
                    "title": str(row["title"]),
                    "publisher": str(row["publisher"]),
                    "materialFamilies": list(json.loads(str(row["material_families"]))),
                    "authorityTier": str(row["authority_tier"]),
                    "scale": str(row["scale"]),
                    "sourceStatus": str(row["source_status"]),
                    "chunks": self.chunks_for_document(str(row["document_id"])),
                }
            )
        return result

    def document_catalog(self, *, limit: int = 200) -> list[dict[str, Any]]:
        """Return document metadata for audit export without returning source text."""
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT d.document_id, d.source_id, d.version, d.content_sha256, d.content_type,
                       d.fetched_at, d.extraction_status, COUNT(c.chunk_id) AS chunk_count,
                       s.title, s.publisher, s.material_families, s.authority_tier, s.scale,
                       s.source_status
                FROM documents AS d
                JOIN sources AS s ON s.source_id = d.source_id
                LEFT JOIN chunks AS c ON c.document_id = d.document_id
                GROUP BY d.document_id
                ORDER BY d.fetched_at DESC, d.document_id
                LIMIT ?
                """,
                (max(1, min(limit, 500)),),
            ).fetchall()
        return [
            {
                "documentId": str(row["document_id"]),
                "sourceId": str(row["source_id"]),
                "version": int(row["version"]),
                "contentSha256": str(row["content_sha256"]),
                "contentType": str(row["content_type"]),
                "extractionStatus": str(row["extraction_status"]),
                "fetchedAt": str(row["fetched_at"]),
                "chunkCount": int(row["chunk_count"]),
                "title": str(row["title"]),
                "publisher": str(row["publisher"]),
                "materialFamilies": list(json.loads(str(row["material_families"]))),
                "authorityTier": str(row["authority_tier"]),
                "scale": str(row["scale"]),
                "sourceStatus": str(row["source_status"]),
            }
            for row in rows
        ]

    @staticmethod
    def _retrievable(status: str, origin: str, include_catalogued: bool) -> bool:
        """Apply the origin-aware retrieval policy.

        Manifest `catalogued`/`active` sources follow the existing relevance policy; manifest
        `blocked` sources are excluded. User uploads are excluded in `review`, `blocked`, or
        `deleted` and only become eligible once explicitly `active`.
        """
        if origin == "user-upload":
            return status == "active"
        if status == "deleted":
            return False
        if status == "blocked":
            return False
        if status == "active":
            return True
        if status == "catalogued":
            return include_catalogued
        return False

    def search(
        self,
        query: str,
        *,
        material_family: str | None = None,
        limit: int = 6,
        include_catalogued: bool = True,
        max_per_source: int | None = 2,
    ) -> list[SearchResult]:
        terms = tuple(dict.fromkeys(item.casefold() for item in _TOKEN_RE.findall(query)))
        if not terms:
            return []
        safe_query = " OR ".join(f'"{term.replace(chr(34), "")}"' for term in terms[:12])
        with self._lock:
            try:
                rows = self._connection.execute(
                    """
                    SELECT f.chunk_id, f.source_id, f.text, c.document_id,
                           s.title, s.url, s.publisher, s.material_families, s.source_status,
                           s.authority_tier, s.scale, s.origin,
                           bm25(chunk_fts) AS rank
                    FROM chunk_fts AS f
                    JOIN chunks AS c ON c.chunk_id = f.chunk_id
                    JOIN documents AS d ON d.document_id = c.document_id
                    JOIN sources AS s ON s.source_id = f.source_id
                    WHERE d.extraction_status = 'extracted'
                      AND d.version = (
                          SELECT MAX(latest.version)
                          FROM documents AS latest
                          WHERE latest.source_id = d.source_id
                      )
                      AND chunk_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (safe_query, max(1, min(limit * 4, 50))),
                ).fetchall()
            except sqlite3.OperationalError as exc:
                LOGGER.warning("FTS search failed; using the bounded LIKE fallback: %s", exc)
                rows = self._connection.execute(
                    """
                    SELECT c.chunk_id, s.source_id, c.text, c.document_id,
                           s.title, s.url, s.publisher, s.material_families, s.source_status,
                           s.authority_tier, s.scale, s.origin,
                           0 AS rank
                    FROM chunks AS c
                    JOIN documents AS d ON d.document_id = c.document_id
                    JOIN sources AS s ON s.source_id = d.source_id
                    WHERE d.extraction_status = 'extracted'
                      AND d.version = (
                          SELECT MAX(latest.version)
                          FROM documents AS latest
                          WHERE latest.source_id = d.source_id
                      )
                      AND c.text LIKE ?
                    ORDER BY c.ordinal
                    LIMIT ?
                    """,
                    (f"%{terms[0]}%", max(1, min(limit * 4, 50))),
                ).fetchall()
        result: list[SearchResult] = []
        source_counts: dict[str, int] = {}
        for row in rows:
            families = tuple(json.loads(str(row["material_families"])))
            if material_family and material_family not in families:
                continue
            if not self._retrievable(
                str(row["source_status"]), str(row["origin"]), include_catalogued
            ):
                continue
            source_id = str(row["source_id"])
            if max_per_source is not None and source_counts.get(source_id, 0) >= max_per_source:
                continue
            result.append(self._search_result(row, float(row["rank"]), "lexical"))
            source_counts[source_id] = source_counts.get(source_id, 0) + 1
            if len(result) >= limit:
                break
        return result

    @staticmethod
    def _search_result(row: sqlite3.Row, score: float, retrieval_mode: str) -> SearchResult:
        return SearchResult(
            chunk_id=str(row["chunk_id"]),
            document_id=str(row["document_id"]),
            source_id=str(row["source_id"]),
            title=str(row["title"]),
            url=str(row["url"] or ""),
            publisher=str(row["publisher"]),
            material_families=tuple(json.loads(str(row["material_families"]))),
            source_status=str(row["source_status"]),
            authority_tier=str(row["authority_tier"]),
            scale=str(row["scale"]),
            text=str(row["text"]),
            score=score,
            retrieval_mode=retrieval_mode,
            origin=str(row["origin"] if "origin" in row.keys() else "manifest"),
        )

    def semantic_search(
        self,
        query_embedding: list[float],
        *,
        material_family: str | None = None,
        limit: int = 6,
        include_catalogued: bool = True,
        model: str | None = None,
        max_per_source: int | None = 2,
    ) -> list[SearchResult]:
        """Search the latest extracted chunks by cosine similarity.

        This deliberately uses SQLite as the durable store and a bounded Python scan as the
        derived retrieval layer. It keeps the index portable and makes a future ANN index
        replaceable without changing source provenance or the public API.
        """
        if not query_embedding or any(
            not isinstance(value, (int, float)) for value in query_embedding
        ):
            return []
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT c.chunk_id, c.document_id, c.text, c.embedding_json, c.embedding_model,
                       s.source_id, s.title, s.url, s.publisher, s.material_families,
                       s.source_status, s.authority_tier, s.scale, s.origin
                FROM chunks AS c
                JOIN documents AS d ON d.document_id = c.document_id
                JOIN sources AS s ON s.source_id = d.source_id
                WHERE d.extraction_status = 'extracted'
                  AND d.version = (
                      SELECT MAX(latest.version)
                      FROM documents AS latest
                      WHERE latest.source_id = d.source_id
                  )
                  AND c.embedding_json IS NOT NULL
                """
            ).fetchall()
        ranked: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            families = tuple(json.loads(str(row["material_families"])))
            if material_family and material_family not in families:
                continue
            if not self._retrievable(
                str(row["source_status"]), str(row["origin"]), include_catalogued
            ):
                continue
            if model and str(row["embedding_model"] or "") != model:
                continue
            try:
                vector = json.loads(str(row["embedding_json"]))
            except (TypeError, json.JSONDecodeError):
                continue
            if not isinstance(vector, list):
                continue
            score = _cosine_similarity(query_embedding, vector)
            if score is not None:
                ranked.append((score, row))
        ranked.sort(key=lambda item: item[0], reverse=True)
        result: list[SearchResult] = []
        source_counts: dict[str, int] = {}
        for score, row in ranked:
            source_id = str(row["source_id"])
            if max_per_source is not None and source_counts.get(source_id, 0) >= max_per_source:
                continue
            result.append(self._search_result(row, score, "semantic"))
            source_counts[source_id] = source_counts.get(source_id, 0) + 1
            if len(result) >= max(1, min(limit, 100)):
                break
        return result

    def hybrid_search(
        self,
        query: str,
        *,
        query_embedding: list[float] | None = None,
        model: str | None = None,
        material_family: str | None = None,
        limit: int = 6,
        include_catalogued: bool = True,
        reranker: Callable[[str, list[str], int], list[tuple[int, float]]] | None = None,
        max_per_source: int | None = 2,
    ) -> list[SearchResult]:
        """Fuse exact-term and semantic retrieval, with an optional second-stage reranker."""
        bounded_limit = max(1, min(limit, 100))
        pool_limit = max(24, bounded_limit * 6)
        lexical = self.search(
            query,
            material_family=material_family,
            limit=pool_limit,
            include_catalogued=include_catalogued,
            max_per_source=max_per_source,
        )
        if query_embedding is None:
            return lexical[:bounded_limit]
        semantic = self.semantic_search(
            query_embedding,
            material_family=material_family,
            limit=pool_limit,
            include_catalogued=include_catalogued,
            model=model,
            max_per_source=max_per_source,
        )
        if not semantic:
            return lexical[:bounded_limit]
        by_id: dict[str, SearchResult] = {item.chunk_id: item for item in lexical}
        by_id.update({item.chunk_id: item for item in semantic})
        scores: dict[str, float] = {}
        for rank, item in enumerate(lexical, start=1):
            scores[item.chunk_id] = scores.get(item.chunk_id, 0.0) + 1.0 / (60 + rank)
        for rank, item in enumerate(semantic, start=1):
            scores[item.chunk_id] = scores.get(item.chunk_id, 0.0) + 1.0 / (60 + rank)
        candidates = [
            replace(by_id[chunk_id], score=score, retrieval_mode="hybrid")
            for chunk_id, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
        ]
        if max_per_source is not None:
            source_counts: dict[str, int] = {}
            diverse_candidates: list[SearchResult] = []
            for item in candidates:
                if source_counts.get(item.source_id, 0) >= max_per_source:
                    continue
                diverse_candidates.append(item)
                source_counts[item.source_id] = source_counts.get(item.source_id, 0) + 1
            candidates = diverse_candidates
        if reranker and candidates:
            try:
                reranked = reranker(
                    query,
                    [item.text for item in candidates],
                    min(pool_limit, len(candidates)),
                )
            except (OSError, TypeError, ValueError):
                reranked = []
            if reranked:
                ordered: list[SearchResult] = []
                seen: set[int] = set()
                for index, score in reranked:
                    if 0 <= index < len(candidates) and index not in seen:
                        seen.add(index)
                        ordered.append(
                            replace(
                                candidates[index],
                                score=float(score),
                                retrieval_mode="hybrid+rerank",
                            )
                        )
                ordered.extend(item for index, item in enumerate(candidates) if index not in seen)
                candidates = ordered
        return candidates[:bounded_limit]

    def context_for_query(
        self,
        query: str,
        *,
        material_family: str | None = None,
        limit: int = 4,
        query_embedding: list[float] | None = None,
        embedding_model: str | None = None,
        reranker: Callable[[str, list[str], int], list[tuple[int, float]]] | None = None,
    ) -> tuple[str, list[dict[str, str]]]:
        results = self.hybrid_search(
            query,
            query_embedding=query_embedding,
            model=embedding_model,
            material_family=material_family,
            limit=limit,
            reranker=reranker,
            max_per_source=1,
        )
        if not results:
            return "", []
        passages: list[str] = []
        cards: list[dict[str, str]] = []
        for item in results:
            if item.origin == "user-upload":
                status_note = "user-supplied; not independently verified"
            elif item.source_status != "active":
                status_note = "catalogued reference; not a case-specific conclusion"
            else:
                status_note = "active source reference"
            tier_note = "; ".join(item for item in (item.authority_tier, item.scale) if item)
            passages.append(f"[{item.source_id}; {status_note}; {tier_note}] {item.text[:900]}")
            cards.append(
                {
                    "label": item.title,
                    "detail": f"{item.publisher} · {status_note} · {item.retrieval_mode}",
                }
            )
        context = (
            "Relevant reference material (background only; use it to inform the answer, not as a final answer):\n"
            + "\n\n".join(passages)
        )
        return context, cards

    def source_catalog(
        self, material_family: str | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM sources ORDER BY title LIMIT ?", (max(1, min(limit, 200)),)
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            families = tuple(json.loads(str(row["material_families"])))
            if material_family and material_family not in families:
                continue
            result.append(
                {
                    "id": str(row["source_id"]),
                    "title": str(row["title"]),
                    "url": str(row["url"] or ""),
                    "publisher": str(row["publisher"]),
                    "sourceType": str(row["source_type"]),
                    "jurisdiction": str(row["jurisdiction"]),
                    "licenseNote": str(row["license_note"]),
                    "limitations": str(row["limitations"]),
                    "materialFamilies": list(families),
                    "status": str(row["source_status"]),
                    "origin": str(row["origin"]),
                    "metadataOrigin": str(row["metadata_origin"]),
                    "reviewedAt": str(row["reviewed_at"] or ""),
                    "reviewedBy": str(row["reviewed_by"] or ""),
                    "reviewNote": str(row["review_note"] or ""),
                    "deletedAt": str(row["deleted_at"] or ""),
                    "authorityTier": str(row["authority_tier"]),
                    "scale": str(row["scale"]),
                    "accessMode": str(row["access_mode"]),
                    "contentSha256": str(row["content_sha256"] or ""),
                    "fetchedAt": str(row["fetched_at"] or ""),
                }
            )
        return result

    def export_catalog(self, path: Path) -> dict[str, Any]:
        """Export metadata and hashes, never raw source text, for versioned audit/reference."""
        documents = self.document_catalog(limit=200)
        catalog: dict[str, Any] = {
            "databaseVersion": self.database_version,
            "generatedAt": _now(),
            "digest": self.digest(),
            "ingestion": self.ingestion_summary(),
            "sources": self.source_catalog(limit=200),
            "documents": documents,
        }
        path = path.expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return catalog

    def ingestion_summary(self) -> dict[str, Any]:
        """Return source, extraction, retrieval, note, and run health without source text."""
        with self._lock:
            source_rows = self._connection.execute(
                "SELECT source_status, COUNT(*) AS count FROM sources GROUP BY source_status"
            ).fetchall()
            source_total = self._connection.execute(
                "SELECT COUNT(*) AS count FROM sources"
            ).fetchone()
            latest_source_row = self._connection.execute(
                """
                WITH latest_documents AS (
                    SELECT d.document_id, d.source_id, d.extraction_status,
                           ROW_NUMBER() OVER (
                               PARTITION BY d.source_id ORDER BY d.version DESC
                           ) AS row_number
                    FROM documents AS d
                )
                SELECT
                    SUM(
                        CASE
                            WHEN latest.document_id IS NOT NULL
                             AND latest.extraction_status = 'extracted' THEN 1
                            ELSE 0
                        END
                    ) AS latest_extracted,
                    SUM(CASE WHEN latest.document_id IS NULL THEN 1 ELSE 0 END) AS no_document,
                    SUM(
                        CASE
                            WHEN latest.document_id IS NOT NULL
                             AND latest.extraction_status <> 'extracted' THEN 1
                            ELSE 0
                        END
                    ) AS blocked_latest
                FROM sources AS s
                LEFT JOIN latest_documents AS latest
                  ON latest.source_id = s.source_id AND latest.row_number = 1
                """
            ).fetchone()
            document_rows = self._connection.execute(
                "SELECT extraction_status, COUNT(*) AS count FROM documents GROUP BY extraction_status"
            ).fetchall()
            document_total = self._connection.execute(
                "SELECT COUNT(*) AS count FROM documents"
            ).fetchone()
            chunk_row = self._connection.execute(
                """
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN d.extraction_status = 'extracted' THEN 1 ELSE 0 END) AS searchable,
                       SUM(CASE WHEN c.embedding_json IS NOT NULL THEN 1 ELSE 0 END) AS embedded
                FROM chunks AS c
                JOIN documents AS d ON d.document_id = c.document_id
                """
            ).fetchone()
            latest_chunk_row = self._connection.execute(
                """
                WITH latest_documents AS (
                    SELECT d.document_id, d.source_id, d.extraction_status,
                           ROW_NUMBER() OVER (
                               PARTITION BY d.source_id ORDER BY d.version DESC
                           ) AS row_number
                    FROM documents AS d
                )
                SELECT COUNT(c.chunk_id) AS total,
                       SUM(CASE WHEN c.embedding_json IS NOT NULL THEN 1 ELSE 0 END) AS embedded
                FROM latest_documents AS d
                JOIN chunks AS c ON c.document_id = d.document_id
                WHERE d.row_number = 1 AND d.extraction_status = 'extracted'
                """
            ).fetchone()
            embedding_model_rows = self._connection.execute(
                """
                SELECT embedding_model, COUNT(*) AS count
                FROM chunks
                WHERE embedding_json IS NOT NULL
                GROUP BY embedding_model
                ORDER BY embedding_model
                """
            ).fetchall()
            note_rows = self._connection.execute(
                "SELECT skill_id, COUNT(*) AS count FROM source_notes GROUP BY skill_id"
            ).fetchall()
            note_total = self._connection.execute(
                "SELECT COUNT(*) AS count FROM source_notes"
            ).fetchone()
            run_rows = self._connection.execute(
                "SELECT outcome, COUNT(*) AS count FROM ingestion_runs GROUP BY outcome"
            ).fetchall()
            run_total = self._connection.execute(
                "SELECT COUNT(*) AS count FROM ingestion_runs"
            ).fetchone()
            failure_rows = self._connection.execute(
                """
                WITH latest_runs AS (
                    SELECT r.*,
                           ROW_NUMBER() OVER (
                               PARTITION BY r.source_id ORDER BY r.finished_at DESC
                           ) AS row_number
                    FROM ingestion_runs AS r
                )
                SELECT r.source_id, s.title, r.outcome, r.detail, r.finished_at
                FROM latest_runs AS r
                LEFT JOIN sources AS s ON s.source_id = r.source_id
                WHERE r.row_number = 1 AND r.outcome <> 'ingested'
                ORDER BY r.finished_at DESC
                LIMIT 25
                """
            ).fetchall()

        return {
            "sources": {
                "total": int(source_total["count"] if source_total else 0),
                "byStatus": {str(row["source_status"]): int(row["count"]) for row in source_rows},
            },
            "documents": {
                "total": int(document_total["count"] if document_total else 0),
                "byExtractionStatus": {
                    str(row["extraction_status"]): int(row["count"]) for row in document_rows
                },
            },
            "retrieval": {
                "latestExtractedSources": int(
                    (latest_source_row["latest_extracted"] or 0) if latest_source_row else 0
                ),
                "sourcesWithoutLatestDocument": int(
                    (latest_source_row["no_document"] or 0) if latest_source_row else 0
                ),
                "sourcesWithBlockedLatestDocument": int(
                    (latest_source_row["blocked_latest"] or 0) if latest_source_row else 0
                ),
                "latestSearchableChunks": int(
                    (latest_chunk_row["total"] or 0) if latest_chunk_row else 0
                ),
                "latestEmbeddedChunks": int(
                    (latest_chunk_row["embedded"] or 0) if latest_chunk_row else 0
                ),
            },
            "chunks": {
                "total": int((chunk_row["total"] or 0) if chunk_row else 0),
                "searchable": int((chunk_row["searchable"] or 0) if chunk_row else 0),
                "embedded": int((chunk_row["embedded"] or 0) if chunk_row else 0),
            },
            "embeddingModels": {
                str(row["embedding_model"] or ""): int(row["count"]) for row in embedding_model_rows
            },
            "sourceNotes": {
                "total": int(note_total["count"] if note_total else 0),
                "bySkill": {str(row["skill_id"]): int(row["count"]) for row in note_rows},
            },
            "runs": {
                "total": int(run_total["count"] if run_total else 0),
                "byOutcome": {str(row["outcome"]): int(row["count"]) for row in run_rows},
                "failures": [
                    {
                        "sourceId": str(row["source_id"]),
                        "title": str(row["title"] or ""),
                        "outcome": str(row["outcome"]),
                        "detail": str(row["detail"]),
                        "finishedAt": str(row["finished_at"]),
                    }
                    for row in failure_rows
                ],
            },
        }

    def add_source_note(
        self,
        *,
        source_id: str,
        summary: str,
        skill_id: str,
        chunk_id: str,
        applicability: str,
        limitations: str,
    ) -> str:
        if not summary.strip() or not applicability.strip() or not limitations.strip():
            raise KnowledgeStoreError(
                "Source notes require a summary, applicability, and limitations."
            )
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT document_id FROM chunks WHERE chunk_id = ?", (chunk_id,)
            ).fetchone()
            if row is None:
                raise KnowledgeStoreError("Source note chunk is not present in the store.")
            source_row = self._connection.execute(
                "SELECT source_id FROM sources WHERE source_id = ?", (source_id,)
            ).fetchone()
            if source_row is None:
                raise KnowledgeStoreError("Source note source is not present in the store.")
            note_id = (
                "note-"
                + hashlib.sha256(
                    _canonical([source_id, chunk_id, skill_id, summary]).encode("utf-8")
                ).hexdigest()[:24]
            )
            self._connection.execute(
                """
                INSERT OR IGNORE INTO source_notes(
                    note_id, source_id, document_id, chunk_id, skill_id, summary,
                    applicability, limitations, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    note_id,
                    source_id,
                    str(row["document_id"]),
                    chunk_id,
                    skill_id,
                    summary.strip(),
                    applicability.strip(),
                    limitations.strip(),
                    _now(),
                ),
            )
            self._graph_node(note_id, "source_note", summary.strip()[:180])
            self._graph_edge(f"source:{source_id}", note_id, "has_note")
            self._graph_edge(chunk_id, note_id, "summarizes")
            return note_id

    def source_note_catalog(self, *, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM source_notes ORDER BY created_at LIMIT ?",
                (max(1, min(limit, 500)),),
            ).fetchall()
        return [
            {
                "id": str(row["note_id"]),
                "sourceId": str(row["source_id"]),
                "documentId": str(row["document_id"]),
                "chunkId": str(row["chunk_id"]),
                "skillId": str(row["skill_id"]),
                "summary": str(row["summary"]),
                "applicability": str(row["applicability"]),
                "limitations": str(row["limitations"]),
            }
            for row in rows
        ]

    def graph_neighbors(self, node_id: str, limit: int = 50) -> list[GraphRecord]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT n.node_id, n.node_type, n.label, e.edge_type,
                       r.node_id AS related_node_id, r.node_type AS related_node_type,
                       r.label AS related_label
                FROM graph_edges AS e
                JOIN graph_nodes AS n ON n.node_id = e.from_node
                JOIN graph_nodes AS r ON r.node_id = e.to_node
                WHERE e.from_node = ? OR e.to_node = ?
                ORDER BY e.edge_type, r.label
                LIMIT ?
                """,
                (node_id, node_id, max(1, min(limit, 200))),
            ).fetchall()
        result: list[GraphRecord] = []
        for row in rows:
            if str(row["node_id"]) != node_id:
                result.append(
                    GraphRecord(
                        node_id=node_id,
                        node_type="unknown",
                        label=node_id,
                        edge_type=str(row["edge_type"]),
                        related_node_id=str(row["node_id"]),
                        related_node_type=str(row["node_type"]),
                        related_label=str(row["label"]),
                    )
                )
            else:
                result.append(
                    GraphRecord(
                        node_id=str(row["node_id"]),
                        node_type=str(row["node_type"]),
                        label=str(row["label"]),
                        edge_type=str(row["edge_type"]),
                        related_node_id=str(row["related_node_id"]),
                        related_node_type=str(row["related_node_type"]),
                        related_label=str(row["related_label"]),
                    )
                )
        return result

    def digest(self) -> str:
        with self._lock:
            signature_row = self._connection.execute("PRAGMA data_version").fetchone()
            signature = (int(signature_row[0]), self._connection.total_changes)
            if self._digest_cache is not None and self._digest_cache_signature == signature:
                return self._digest_cache
            rows = self._connection.execute(
                """
                SELECT source_id, content_sha256, source_status, origin FROM sources
                ORDER BY source_id;
                """
            ).fetchall()
            notes = self._connection.execute(
                "SELECT note_id, skill_id, summary FROM source_notes ORDER BY note_id"
            ).fetchall()
            body = [dict(row) for row in rows] + [dict(row) for row in notes]
            digest = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
            self._digest_cache = digest
            self._digest_cache_signature = signature
            return digest

    def _graph_node(self, node_id: str, node_type: str, label: str) -> None:
        self._connection.execute(
            "INSERT INTO graph_nodes(node_id, node_type, label) VALUES (?, ?, ?) ON CONFLICT(node_id) DO UPDATE SET label=excluded.label",
            (node_id, node_type, label),
        )

    def _graph_edge(
        self,
        from_node: str,
        to_node: str,
        edge_type: str,
        *,
        directed: bool = False,
        edge_origin: str = "declared",
        reason_code: str | None = None,
        reason_detail: str | None = None,
        projection_version: int = 0,
    ) -> None:
        self._connection.execute(
            "INSERT OR IGNORE INTO graph_edges("
            "edge_id, from_node, to_node, edge_type, directed, edge_origin, reason_code, "
            "reason_detail, projection_version"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"edge-{uuid.uuid4()}",
                from_node,
                to_node,
                edge_type,
                1 if directed else 0,
                edge_origin,
                reason_code,
                reason_detail,
                projection_version,
            ),
        )

    # ------------------------------------------------------------------ uploads

    def create_upload(
        self,
        upload_id: str,
        *,
        original_filename: str,
        storage_key: str,
        raw_sha256: str,
        size_bytes: int,
        declared_content_type: str,
        detected_content_type: str,
        extension: str,
        status: str = "received",
    ) -> str:
        if status not in _UPLOAD_LIFECYCLE:
            raise KnowledgeStoreError("Invalid upload status.")
        timestamp = _now()
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO uploads(
                    upload_id, original_filename, storage_key, raw_sha256, size_bytes,
                    declared_content_type, detected_content_type, extension, status, created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    upload_id,
                    original_filename,
                    storage_key,
                    raw_sha256,
                    size_bytes,
                    declared_content_type,
                    detected_content_type,
                    extension,
                    status,
                    timestamp,
                    timestamp,
                ),
            )
        return upload_id

    def update_upload(self, upload_id: str, **fields: Any) -> None:
        allowed = {
            "status",
            "source_id",
            "document_id",
            "detected_content_type",
            "error_code",
            "error_detail",
        }
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return
        updates["updated_at"] = _now()
        assignments = ", ".join(f"{key} = ?" for key in updates)
        with self._lock, self._connection:
            self._connection.execute(
                f"UPDATE uploads SET {assignments} WHERE upload_id = ?",
                (*updates.values(), upload_id),
            )

    def get_upload(self, upload_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM uploads WHERE upload_id = ?", (upload_id,)
            ).fetchone()
        return self._upload_dict(row) if row is not None else None

    def find_upload_by_raw_sha256(self, raw_sha256: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM uploads WHERE raw_sha256 = ? AND status <> 'deleted' "
                "ORDER BY created_at LIMIT 1",
                (raw_sha256,),
            ).fetchone()
        return self._upload_dict(row) if row is not None else None

    def list_uploads(
        self, *, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        clauses = ""
        params: list[Any] = []
        if status:
            clauses = "WHERE status = ?"
            params.append(status)
        params.extend((max(1, min(limit, 200)), max(0, offset)))
        with self._lock:
            rows = self._connection.execute(
                f"SELECT * FROM uploads {clauses} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                tuple(params),
            ).fetchall()
        return [self._upload_dict(row) for row in rows]

    @staticmethod
    def _upload_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "uploadId": str(row["upload_id"]),
            "originalFilename": str(row["original_filename"]),
            "storageKey": str(row["storage_key"]),
            "rawSha256": str(row["raw_sha256"]),
            "sizeBytes": int(row["size_bytes"]),
            "declaredContentType": str(row["declared_content_type"]),
            "detectedContentType": str(row["detected_content_type"]),
            "extension": str(row["extension"]),
            "status": str(row["status"]),
            "sourceId": str(row["source_id"] or ""),
            "documentId": str(row["document_id"] or ""),
            "errorCode": str(row["error_code"] or ""),
            "errorDetail": str(row["error_detail"] or ""),
            "createdAt": str(row["created_at"]),
            "updatedAt": str(row["updated_at"]),
            "deletedAt": str(row["deleted_at"] or ""),
        }

    # ------------------------------------------------------------------ jobs

    max_job_attempts = 3

    def create_job(
        self,
        kind: str,
        target_id: str,
        *,
        idempotency_key: str | None = None,
        step: str = "",
        progress_total: int = 1,
        detail: str = "",
    ) -> str:
        if kind not in _JOB_KINDS:
            raise KnowledgeStoreError("Invalid job kind.")
        job_id = f"job-{uuid.uuid4()}"
        timestamp = _now()
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO jobs(
                    job_id, kind, target_id, status, step, progress_total, detail, attempts,
                    idempotency_key, created_at, updated_at
                ) VALUES (?, ?, ?, 'queued', ?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    job_id,
                    kind,
                    target_id,
                    step,
                    progress_total,
                    detail[:2000],
                    idempotency_key,
                    timestamp,
                    timestamp,
                ),
            )
        return job_id

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        return self._job_dict(row) if row is not None else None

    def find_job(self, kind: str, target_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM jobs WHERE kind = ? AND target_id = ? ORDER BY created_at DESC LIMIT 1",
                (kind, target_id),
            ).fetchone()
        return self._job_dict(row) if row is not None else None

    def job_for_idempotency(self, kind: str, idempotency_key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM jobs WHERE kind = ? AND idempotency_key = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (kind, idempotency_key),
            ).fetchone()
        return self._job_dict(row) if row is not None else None

    def list_jobs(
        self, *, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        clauses = ""
        params: list[Any] = []
        if status:
            clauses = "WHERE status = ?"
            params.append(status)
        params.extend((max(1, min(limit, 200)), max(0, offset)))
        with self._lock:
            rows = self._connection.execute(
                f"SELECT * FROM jobs {clauses} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                tuple(params),
            ).fetchall()
        return [self._job_dict(row) for row in rows]

    def claim_job(self, kinds: Iterable[str], *, lease_seconds: int = 300) -> dict[str, Any] | None:
        allowed = tuple(kind for kind in kinds if kind in _JOB_KINDS)
        if not allowed:
            return None
        placeholders = ",".join("?" for _ in allowed)
        now = _now()
        lease_until = (datetime.now(UTC) + timedelta(seconds=lease_seconds)).isoformat()
        with self._lock, self._connection:
            row = self._connection.execute(
                f"SELECT * FROM jobs WHERE kind IN ({placeholders}) AND status = 'queued' "
                "ORDER BY created_at LIMIT 1",
                allowed,
            ).fetchone()
            if row is None:
                row = self._connection.execute(
                    f"SELECT * FROM jobs WHERE kind IN ({placeholders}) AND status = 'running' "
                    "AND lease_until < ? AND attempts < ? ORDER BY created_at LIMIT 1",
                    (*allowed, now, self.max_job_attempts),
                ).fetchone()
            if row is None:
                return None
            attempts = int(row["attempts"]) + 1
            self._connection.execute(
                "UPDATE jobs SET status = 'running', attempts = ?, claimed_at = ?, "
                "lease_until = ?, started_at = COALESCE(started_at, ?), updated_at = ? "
                "WHERE job_id = ?",
                (attempts, now, lease_until, now, now, str(row["job_id"])),
            )
        claimed = dict(row)
        claimed["status"] = "running"
        claimed["attempts"] = attempts
        claimed["claimed_at"] = now
        claimed["lease_until"] = lease_until
        return self._job_dict(claimed)

    def update_job_progress(
        self, job_id: str, *, step: str, current: int, total: int, detail: str = ""
    ) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE jobs SET step = ?, progress_current = ?, progress_total = ?, detail = ?, "
                "updated_at = ? WHERE job_id = ?",
                (step, current, total, detail[:2000], _now(), job_id),
            )

    def complete_job(self, job_id: str, *, detail: str = "") -> None:
        timestamp = _now()
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE jobs SET status = 'done', step = 'done', detail = ?, finished_at = ?, "
                "lease_until = NULL, updated_at = ? WHERE job_id = ?",
                (detail[:2000], timestamp, timestamp, job_id),
            )

    def fail_job(
        self,
        job_id: str,
        *,
        error_code: str,
        error_detail: str,
        retryable: bool,
    ) -> None:
        timestamp = _now()
        status = "queued" if retryable else "failed"
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE jobs SET status = ?, error_code = ?, error_detail = ?, lease_until = NULL, "
                "finished_at = CASE WHEN ? = 'failed' THEN ? ELSE NULL END, updated_at = ? "
                "WHERE job_id = ?",
                (status, error_code, error_detail[:2000], status, timestamp, timestamp, job_id),
            )

    def cancel_job(self, job_id: str) -> None:
        timestamp = _now()
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE jobs SET status = 'cancelled', finished_at = ?, lease_until = NULL, "
                "updated_at = ? WHERE job_id = ? AND status IN ('queued', 'running')",
                (timestamp, timestamp, job_id),
            )

    def recover_jobs(self, *, lease_seconds: int = 300) -> int:
        """Requeue expired running jobs that are still within retry budget; fail the rest."""
        now = _now()
        recovered = 0
        with self._lock, self._connection:
            rows = self._connection.execute(
                "SELECT job_id, attempts FROM jobs WHERE status = 'running' AND lease_until < ?",
                (now,),
            ).fetchall()
            for row in rows:
                if int(row["attempts"]) < self.max_job_attempts:
                    self._connection.execute(
                        "UPDATE jobs SET status = 'queued', lease_until = NULL, updated_at = ? "
                        "WHERE job_id = ?",
                        (_now(), str(row["job_id"])),
                    )
                    recovered += 1
                else:
                    self._connection.execute(
                        "UPDATE jobs SET status = 'failed', error_code = 'lease_expired', "
                        "error_detail = 'Job exceeded its retry budget after lease expiry.', "
                        "lease_until = NULL, finished_at = ?, updated_at = ? WHERE job_id = ?",
                        (_now(), _now(), str(row["job_id"])),
                    )
        return recovered

    @staticmethod
    def _job_dict(row: sqlite3.Row | Mapping[str, Any]) -> dict[str, Any]:
        def value(key: str) -> Any:
            if isinstance(row, sqlite3.Row):
                return row[key]
            return row.get(key)

        return {
            "jobId": str(value("job_id")),
            "kind": str(value("kind")),
            "targetId": str(value("target_id")),
            "status": str(value("status")),
            "step": str(value("step") or ""),
            "progressCurrent": int(value("progress_current") or 0),
            "progressTotal": int(value("progress_total") or 0),
            "detail": str(value("detail") or ""),
            "errorCode": str(value("error_code") or ""),
            "errorDetail": str(value("error_detail") or ""),
            "attempts": int(value("attempts") or 0),
            "idempotencyKey": str(value("idempotency_key") or ""),
            "claimedAt": str(value("claimed_at") or ""),
            "leaseUntil": str(value("lease_until") or ""),
            "createdAt": str(value("created_at")),
            "startedAt": str(value("started_at") or ""),
            "updatedAt": str(value("updated_at")),
            "finishedAt": str(value("finished_at") or ""),
        }

    # ------------------------------------------------------------------ review lifecycle

    def approve_upload(
        self, upload_id: str, *, reviewed_by: str = "", review_note: str = ""
    ) -> str:
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT * FROM uploads WHERE upload_id = ?", (upload_id,)
            ).fetchone()
            if row is None:
                raise KnowledgeStoreError("Upload not found.")
            if str(row["status"]) != "ingested":
                raise KnowledgeStoreError("Only ingested uploads can be approved.")
            source_id = str(row["source_id"] or "")
            document_id = str(row["document_id"] or "")
            if not source_id or not document_id:
                raise KnowledgeStoreError("Upload is missing provenance records.")
            document = self._connection.execute(
                "SELECT extraction_status FROM documents WHERE document_id = ?", (document_id,)
            ).fetchone()
            if document is None or str(document["extraction_status"]) != "extracted":
                raise KnowledgeStoreError("Upload document is not extracted and usable.")
            timestamp = _now()
            cursor = self._connection.execute(
                "UPDATE sources SET source_status = 'active', reviewed_at = ?, reviewed_by = ?, "
                "review_note = ?, updated_at = ? WHERE source_id = ? AND origin = 'user-upload' "
                "AND source_status = 'review'",
                (timestamp, reviewed_by, review_note, timestamp, source_id),
            )
            if cursor.rowcount != 1:
                raise KnowledgeStoreError("Upload source is not in the review state.")
        return source_id

    def quarantine_upload(
        self, upload_id: str, *, reviewed_by: str = "", review_note: str = ""
    ) -> str:
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT * FROM uploads WHERE upload_id = ?", (upload_id,)
            ).fetchone()
            if row is None:
                raise KnowledgeStoreError("Upload not found.")
            if str(row["status"]) != "ingested":
                raise KnowledgeStoreError("Only ingested uploads can be quarantined.")
            source_id = str(row["source_id"] or "")
            if not source_id:
                raise KnowledgeStoreError("Upload is missing provenance records.")
            timestamp = _now()
            cursor = self._connection.execute(
                "UPDATE sources SET source_status = 'blocked', reviewed_at = ?, reviewed_by = ?, "
                "review_note = ?, updated_at = ? WHERE source_id = ? AND origin = 'user-upload' "
                "AND source_status IN ('review', 'active')",
                (timestamp, reviewed_by, review_note, timestamp, source_id),
            )
            if cursor.rowcount != 1:
                raise KnowledgeStoreError("Upload source is not in a reviewable state.")
        return source_id

    def delete_upload(self, upload_id: str) -> tuple[str, str, str] | None:
        """Tombstone an upload and remove its derived rows; return storage details for cleanup."""
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT * FROM uploads WHERE upload_id = ?", (upload_id,)
            ).fetchone()
            if row is None or str(row["status"]) == "deleted":
                return None
            timestamp = _now()
            source_id = str(row["source_id"] or "")
            self._connection.execute(
                "UPDATE uploads SET status = 'deleted', deleted_at = ?, updated_at = ? "
                "WHERE upload_id = ?",
                (timestamp, timestamp, upload_id),
            )
            if source_id:
                self._connection.execute(
                    "UPDATE sources SET source_status = 'deleted', deleted_at = ?, updated_at = ? "
                    "WHERE source_id = ? AND origin = 'user-upload'",
                    (timestamp, timestamp, source_id),
                )
                self._remove_upload_derived(source_id)
            return (source_id, str(row["storage_key"]), str(row["raw_sha256"]))

    def _remove_upload_derived(self, source_id: str) -> None:
        document_rows = self._connection.execute(
            "SELECT document_id FROM documents WHERE source_id = ?", (source_id,)
        ).fetchall()
        document_ids = [str(row["document_id"]) for row in document_rows]
        chunk_ids: list[str] = []
        if document_ids:
            placeholders = ",".join("?" for _ in document_ids)
            chunk_rows = self._connection.execute(
                f"SELECT chunk_id FROM chunks WHERE document_id IN ({placeholders})",
                tuple(document_ids),
            ).fetchall()
            chunk_ids = [str(row["chunk_id"]) for row in chunk_rows]
        self._connection.execute("DELETE FROM source_notes WHERE source_id = ?", (source_id,))
        if chunk_ids:
            placeholders = ",".join("?" for _ in chunk_ids)
            self._connection.execute(
                f"DELETE FROM chunk_fts WHERE chunk_id IN ({placeholders})", tuple(chunk_ids)
            )
            self._connection.execute(
                f"DELETE FROM chunks WHERE chunk_id IN ({placeholders})", tuple(chunk_ids)
            )
        if document_ids:
            placeholders = ",".join("?" for _ in document_ids)
            self._connection.execute(
                f"DELETE FROM documents WHERE document_id IN ({placeholders})",
                tuple(document_ids),
            )
        node_ids = [f"source:{source_id}", *document_ids, *chunk_ids]
        node_ids = [node for node in node_ids if node]
        if node_ids:
            placeholders = ",".join("?" for _ in node_ids)
            self._connection.execute(
                f"DELETE FROM graph_edges WHERE from_node IN ({placeholders}) "
                f"OR to_node IN ({placeholders})",
                (*node_ids, *node_ids),
            )
            self._connection.execute(
                f"DELETE FROM graph_nodes WHERE node_id IN ({placeholders})", tuple(node_ids)
            )
        self._connection.execute(
            "DELETE FROM jobs WHERE target_id IN "
            "(SELECT upload_id FROM uploads WHERE source_id = ?)",
            (source_id,),
        )

    def update_user_upload_source_metadata(
        self,
        source_id: str,
        *,
        title: str | None = None,
        publisher: str | None = None,
        material_families: tuple[str, ...] | None = None,
        jurisdiction: str | None = None,
        license_note: str | None = None,
        limitations: str | None = None,
        authority_tier: str | None = None,
        scale: str | None = None,
    ) -> None:
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT * FROM sources WHERE source_id = ? AND origin = 'user-upload'", (source_id,)
            ).fetchone()
            if row is None:
                raise KnowledgeStoreError("User-upload source is not registered.")
            updates: dict[str, Any] = {}
            if title is not None:
                updates["title"] = title.strip()
            if publisher is not None:
                updates["publisher"] = publisher.strip()
            if material_families is not None:
                updates["material_families"] = _canonical(list(material_families))
            if jurisdiction is not None:
                updates["jurisdiction"] = jurisdiction.strip()
            if license_note is not None:
                updates["license_note"] = license_note.strip()
            if limitations is not None:
                updates["limitations"] = limitations.strip()
            if authority_tier is not None:
                if authority_tier not in _AUTHORITY_TIERS:
                    raise KnowledgeStoreError("Invalid authority tier.")
                updates["authority_tier"] = authority_tier
            if scale is not None:
                updates["scale"] = scale.strip()
            updates["metadata_origin"] = "operator-supplied"
            updates["updated_at"] = _now()
            assignments = ", ".join(f"{key} = ?" for key in updates)
            self._connection.execute(
                f"UPDATE sources SET {assignments} WHERE source_id = ?",
                (*updates.values(), source_id),
            )
            if "title" in updates:
                self._graph_node(f"source:{source_id}", "source", updates["title"])
            if "material_families" in updates and material_families is not None:
                for family in material_families:
                    family_id = f"material:{family}"
                    self._graph_node(family_id, "material_family", family)
                    self._graph_edge(f"source:{source_id}", family_id, "covers")

    # ------------------------------------------------------------------ document views

    def documents_list(
        self,
        *,
        status: str | None = None,
        origin: str | None = None,
        family: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sort: str = "updated",
    ) -> dict[str, Any]:
        allowed_sorts = {
            "updated": "d.fetched_at DESC",
            "title": "s.title ASC",
            "status": "s.source_status ASC",
        }
        order_clause = allowed_sorts.get(sort, "d.fetched_at DESC")
        clauses = [
            "d.version = (SELECT MAX(l.version) FROM documents AS l WHERE l.source_id = d.source_id)"
        ]
        params: list[Any] = []
        if status:
            clauses.append("s.source_status = ?")
            params.append(status)
        if origin:
            clauses.append("s.origin = ?")
            params.append(origin)
        if family:
            clauses.append("s.material_families LIKE ?")
            params.append(f"%{family}%")
        if q:
            clauses.append("s.title LIKE ?")
            params.append(f"%{q}%")
        where = " AND ".join(clauses)
        count_params = tuple(params)
        with self._lock:
            total = self._connection.execute(
                f"SELECT COUNT(*) AS count FROM documents AS d JOIN sources AS s "
                f"ON s.source_id = d.source_id WHERE {where}",
                count_params,
            ).fetchone()
            rows = self._connection.execute(
                f"SELECT d.document_id, d.source_id, d.version, d.content_sha256, d.content_type, "
                f"d.fetched_at, d.extraction_status, s.title, s.publisher, s.material_families, "
                f"s.authority_tier, s.scale, s.source_status, s.origin "
                f"FROM documents AS d JOIN sources AS s ON s.source_id = d.source_id "
                f"WHERE {where} ORDER BY {order_clause} LIMIT ? OFFSET ?",
                (*params, max(1, min(limit, 200)), max(0, offset)),
            ).fetchall()
        items: list[dict[str, Any]] = []
        for row in rows:
            chunk_count = self._count_chunks(str(row["document_id"]))
            items.append(
                {
                    "documentId": str(row["document_id"]),
                    "sourceId": str(row["source_id"]),
                    "version": int(row["version"]),
                    "contentSha256": str(row["content_sha256"]),
                    "contentType": str(row["content_type"]),
                    "extractionStatus": str(row["extraction_status"]),
                    "fetchedAt": str(row["fetched_at"]),
                    "chunkCount": chunk_count,
                    "title": str(row["title"]),
                    "publisher": str(row["publisher"]),
                    "materialFamilies": list(json.loads(str(row["material_families"]))),
                    "authorityTier": str(row["authority_tier"]),
                    "scale": str(row["scale"]),
                    "sourceStatus": str(row["source_status"]),
                    "origin": str(row["origin"]),
                }
            )
        return {"items": items, "total": int(total["count"])}

    def _count_chunks(self, document_id: str) -> int:
        with self._lock:
            row = self._connection.execute(
                "SELECT COUNT(*) AS count FROM chunks WHERE document_id = ?", (document_id,)
            ).fetchone()
        return int(row["count"])

    def document_detail(
        self, document_id: str, *, preview_chars: int = 2000, max_chunks: int = 50
    ) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT d.*, s.title, s.publisher, s.url, s.material_families, s.jurisdiction, "
                "s.license_note, s.limitations, s.authority_tier, s.scale, s.source_status, "
                "s.origin, s.metadata_origin, s.reviewed_at, s.reviewed_by, s.review_note, "
                "s.deleted_at "
                "FROM documents AS d JOIN sources AS s ON s.source_id = d.source_id "
                "WHERE d.document_id = ?",
                (document_id,),
            ).fetchone()
            if row is None:
                return None
            chunk_rows = self._connection.execute(
                "SELECT chunk_id, ordinal, text, embedding_model FROM chunks "
                "WHERE document_id = ? ORDER BY ordinal LIMIT ?",
                (document_id, max(1, min(max_chunks, 200))),
            ).fetchall()
            note_rows = self._connection.execute(
                "SELECT note_id, skill_id, summary, applicability, limitations, created_at "
                "FROM source_notes WHERE document_id = ? ORDER BY created_at LIMIT 100",
                (document_id,),
            ).fetchall()
            job_rows = self._connection.execute(
                "SELECT * FROM jobs WHERE target_id = ? ORDER BY created_at DESC LIMIT 50",
                (document_id,),
            ).fetchall()
            run_rows = self._connection.execute(
                "SELECT * FROM ingestion_runs WHERE source_id = ? ORDER BY finished_at DESC LIMIT 20",
                (str(row["source_id"]),),
            ).fetchall()
        content = str(row["content"])
        preview = content[: max(1, min(preview_chars, 8000))]
        return {
            "documentId": str(row["document_id"]),
            "sourceId": str(row["source_id"]),
            "version": int(row["version"]),
            "contentSha256": str(row["content_sha256"]),
            "contentType": str(row["content_type"]),
            "extractionStatus": str(row["extraction_status"]),
            "fetchedAt": str(row["fetched_at"]),
            "title": str(row["title"]),
            "publisher": str(row["publisher"]),
            "url": str(row["url"] or ""),
            "jurisdiction": str(row["jurisdiction"]),
            "licenseNote": str(row["license_note"]),
            "limitations": str(row["limitations"]),
            "materialFamilies": list(json.loads(str(row["material_families"]))),
            "authorityTier": str(row["authority_tier"]),
            "scale": str(row["scale"]),
            "sourceStatus": str(row["source_status"]),
            "origin": str(row["origin"]),
            "metadataOrigin": str(row["metadata_origin"]),
            "reviewedAt": str(row["reviewed_at"] or ""),
            "reviewedBy": str(row["reviewed_by"] or ""),
            "reviewNote": str(row["review_note"] or ""),
            "deletedAt": str(row["deleted_at"] or ""),
            "preview": preview,
            "truncated": len(content) > len(preview),
            "chunks": [
                {
                    "chunkId": str(item["chunk_id"]),
                    "ordinal": int(item["ordinal"]),
                    "text": str(item["text"])[:900],
                    "embeddingModel": str(item["embedding_model"] or ""),
                }
                for item in chunk_rows
            ],
            "notes": [
                {
                    "noteId": str(item["note_id"]),
                    "skillId": str(item["skill_id"]),
                    "summary": str(item["summary"]),
                    "applicability": str(item["applicability"]),
                    "limitations": str(item["limitations"]),
                }
                for item in note_rows
            ],
            "jobs": [self._job_dict(item) for item in job_rows],
            "ingestionRuns": [
                {
                    "runId": str(item["run_id"]),
                    "outcome": str(item["outcome"]),
                    "detail": str(item["detail"]),
                    "startedAt": str(item["started_at"]),
                    "finishedAt": str(item["finished_at"]),
                }
                for item in run_rows
            ],
        }

    # ------------------------------------------------------------------ graph projection

    def rebuild_graph(self, *, projection_version: int = 1) -> int:
        """Deterministically rebuild derived navigation edges; declared edges are untouched."""
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM graph_edges WHERE edge_origin = 'derived'")
            derived = 0
            # Directed supersedes edges between consecutive document versions of one source.
            sources = self._connection.execute(
                "SELECT source_id FROM sources WHERE origin = 'manifest' ORDER BY source_id"
            ).fetchall()
            for source in sources:
                documents = self._connection.execute(
                    "SELECT document_id FROM documents WHERE source_id = ? ORDER BY version",
                    (str(source["source_id"]),),
                ).fetchall()
                for previous, current in zip(documents, documents[1:], strict=False):
                    self._graph_edge(
                        str(previous["document_id"]),
                        str(current["document_id"]),
                        "supersedes",
                        directed=True,
                        edge_origin="derived",
                        reason_code="newer_version",
                        reason_detail="A newer extraction of the same source supersedes this version.",
                        projection_version=projection_version,
                    )
                    derived += 1
            # Undirected shared-material-family edges using a canonical node ordering.
            rows = self._connection.execute(
                "SELECT source_id, material_families FROM sources "
                "WHERE origin = 'manifest' ORDER BY source_id"
            ).fetchall()
            family_members: dict[str, list[str]] = {}
            for row in rows:
                for family in json.loads(str(row["material_families"])):
                    family_members.setdefault(str(family), []).append(str(row["source_id"]))
            seen: set[tuple[str, str, str]] = set()
            for family, members in family_members.items():
                for index, left in enumerate(sorted(members)):
                    for right in sorted(members)[index + 1 :]:
                        first, second = sorted((left, right))
                        key = (first, second, "shares_family")
                        if key in seen:
                            continue
                        seen.add(key)
                        self._graph_edge(
                            f"source:{first}",
                            f"source:{second}",
                            "shares_family",
                            edge_origin="derived",
                            reason_code="shared_material_family",
                            reason_detail=f"Both sources cover the {family} material family.",
                            projection_version=projection_version,
                        )
                        derived += 1
            return derived

    def graph_projection(
        self,
        *,
        max_nodes: int = 200,
        include_derived: bool = False,
        selected_document_id: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            version = self._connection.execute(
                "SELECT COALESCE(MAX(projection_version), 0) AS v FROM graph_edges"
            ).fetchone()
            node_rows = self._connection.execute(
                "SELECT node_id, node_type, label FROM graph_nodes ORDER BY node_id"
            ).fetchall()
            edge_rows = self._connection.execute(
                "SELECT from_node, to_node, edge_type, directed, edge_origin, reason_code, "
                "reason_detail FROM graph_edges "
                "WHERE edge_origin = 'declared' OR ? = 1 ORDER BY from_node, to_node, edge_type",
                (1 if include_derived else 0,),
            ).fetchall()
        selected = set()
        if selected_document_id:
            selected.add(selected_document_id)
            for row in edge_rows:
                if str(row["from_node"]) == selected_document_id:
                    selected.add(str(row["to_node"]))
                elif str(row["to_node"]) == selected_document_id:
                    selected.add(str(row["from_node"]))
        chunk_nodes = {str(row["node_id"]) for row in node_rows if str(row["node_type"]) == "chunk"}
        visible_nodes = [
            row
            for row in node_rows
            if str(row["node_type"]) != "chunk" or str(row["node_id"]) in selected
        ]
        visible_ids = {str(row["node_id"]) for row in visible_nodes}
        total_nodes = len(visible_nodes)
        total_edges = sum(
            1
            for row in edge_rows
            if str(row["from_node"]) in visible_ids and str(row["to_node"]) in visible_ids
        )
        bounded_nodes = visible_nodes[: max(1, min(max_nodes, 1000))]
        bounded_ids = {str(row["node_id"]) for row in bounded_nodes}
        bounded_edges = [
            row
            for row in edge_rows
            if str(row["from_node"]) in bounded_ids and str(row["to_node"]) in bounded_ids
        ][: max(1, min(max_nodes, 1000))]
        truncated = len(bounded_nodes) < total_nodes or len(bounded_edges) < total_edges
        return {
            "projectionVersion": int(version["v"]) if version else 0,
            "totalNodes": total_nodes,
            "totalEdges": total_edges,
            "truncated": truncated,
            "chunkNodesExcluded": bool(chunk_nodes),
            "nodes": [
                {
                    "nodeId": str(row["node_id"]),
                    "nodeType": str(row["node_type"]),
                    "label": str(row["label"]),
                }
                for row in bounded_nodes
            ],
            "edges": [
                {
                    "from": str(row["from_node"]),
                    "to": str(row["to_node"]),
                    "edgeType": str(row["edge_type"]),
                    "directed": bool(row["directed"]),
                    "edgeOrigin": str(row["edge_origin"]),
                    "reasonCode": str(row["reason_code"] or ""),
                    "reasonDetail": str(row["reason_detail"] or ""),
                }
                for row in bounded_edges
            ],
        }

    def related_documents(
        self, document_id: str, *, include_derived: bool = False, limit: int = 30
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT e.edge_type, e.directed, e.edge_origin, e.reason_code, e.reason_detail, "
                "n.node_id, n.node_type, n.label "
                "FROM graph_edges AS e "
                "JOIN graph_nodes AS n ON n.node_id = CASE "
                "WHEN e.from_node = ? THEN e.to_node ELSE e.from_node END "
                "WHERE (e.from_node = ? OR e.to_node = ?) AND (e.edge_origin = 'declared' OR ? = 1) "
                "ORDER BY e.edge_type, n.label LIMIT ?",
                (
                    document_id,
                    document_id,
                    document_id,
                    1 if include_derived else 0,
                    max(1, min(limit, 200)),
                ),
            ).fetchall()
        return [
            {
                "edgeType": str(row["edge_type"]),
                "directed": bool(row["directed"]),
                "edgeOrigin": str(row["edge_origin"]),
                "reasonCode": str(row["reason_code"] or ""),
                "reasonDetail": str(row["reason_detail"] or ""),
                "nodeId": str(row["node_id"]),
                "nodeType": str(row["node_type"]),
                "label": str(row["label"]),
            }
            for row in rows
        ]

    # ------------------------------------------------------------------ overview / filtering

    def kb_overview(self) -> dict[str, Any]:
        with self._lock:
            source_rows = self._connection.execute(
                "SELECT origin, source_status, COUNT(*) AS count FROM sources "
                "GROUP BY origin, source_status"
            ).fetchall()
            document_rows = self._connection.execute(
                "SELECT extraction_status, COUNT(*) AS count FROM documents GROUP BY extraction_status"
            ).fetchall()
            job_rows = self._connection.execute(
                "SELECT status, COUNT(*) AS count FROM jobs GROUP BY status"
            ).fetchall()
            upload_rows = self._connection.execute(
                "SELECT status, COUNT(*) AS count FROM uploads GROUP BY status"
            ).fetchall()
            tier_rows = self._connection.execute(
                "SELECT authority_tier, COUNT(*) AS count FROM sources "
                "WHERE authority_tier <> '' GROUP BY authority_tier"
            ).fetchall()
            embedding_rows = self._connection.execute(
                "SELECT embedding_model, COUNT(*) AS count FROM chunks "
                "WHERE embedding_json IS NOT NULL GROUP BY embedding_model"
            ).fetchall()
            note_total = self._connection.execute(
                "SELECT COUNT(*) AS count FROM source_notes"
            ).fetchone()
            version = self._stored_version()
        return {
            "databaseVersion": version,
            "projectionVersion": self.graph_projection(max_nodes=1)["projectionVersion"],
            "sources": {
                "total": sum(int(row["count"]) for row in source_rows),
                "byOriginStatus": {
                    f"{row['origin']}:{row['source_status']}": int(row["count"])
                    for row in source_rows
                },
            },
            "documents": {
                "total": sum(int(row["count"]) for row in document_rows),
                "byExtractionStatus": {
                    str(row["extraction_status"]): int(row["count"]) for row in document_rows
                },
            },
            "uploads": {"byStatus": {str(row["status"]): int(row["count"]) for row in upload_rows}},
            "jobs": {"byStatus": {str(row["status"]): int(row["count"]) for row in job_rows}},
            "tiers": {str(row["authority_tier"]): int(row["count"]) for row in tier_rows},
            "embeddingModels": {
                str(row["embedding_model"]): int(row["count"]) for row in embedding_rows
            },
            "sourceNotes": {"total": int(note_total["count"] if note_total else 0)},
        }

    def user_upload_summary(self) -> dict[str, int]:
        with self._lock:
            source_count = self._connection.execute(
                "SELECT COUNT(*) AS count FROM sources WHERE origin = 'user-upload'"
            ).fetchone()
            document_count = self._connection.execute(
                "SELECT COUNT(*) AS count FROM documents AS d JOIN sources AS s "
                "ON s.source_id = d.source_id WHERE s.origin = 'user-upload'"
            ).fetchone()
            chunk_count = self._connection.execute(
                "SELECT COUNT(*) AS count FROM chunks AS c JOIN documents AS d "
                "ON d.document_id = c.document_id JOIN sources AS s ON s.source_id = d.source_id "
                "WHERE s.origin = 'user-upload'"
            ).fetchone()
            note_count = self._connection.execute(
                "SELECT COUNT(*) AS count FROM source_notes AS n JOIN sources AS s "
                "ON s.source_id = n.source_id WHERE s.origin = 'user-upload'"
            ).fetchone()
            upload_count = self._connection.execute(
                "SELECT COUNT(*) AS count FROM uploads"
            ).fetchone()
        return {
            "userUploadSources": int(source_count["count"]),
            "userUploadDocuments": int(document_count["count"]),
            "userUploadChunks": int(chunk_count["count"]),
            "userUploadNotes": int(note_count["count"]),
            "uploads": int(upload_count["count"]),
        }
