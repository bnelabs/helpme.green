from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class KnowledgeStoreError(ValueError):
    """Raised when a knowledge store operation would violate its contract."""


_AUTHORITY_TIERS = {"primary", "secondary", "industry", "low-tech", "community"}
_ACCESS_MODES = {"web", "pdf", "api", "local-reference"}


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


class KnowledgeDatabase:
    """SQLite knowledge-management store with a rebuildable graph and FTS index.

    Downloaded documents and candidate claims live here at runtime. The checked-in YAML packs
    remain the authoritative static evaluator input; this store never silently promotes a fetch.
    """

    schema_version = 2

    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.path.parent.chmod(0o700)
        except OSError:
            pass
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(str(self.path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._initialize()

    def _initialize(self) -> None:
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS store_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sources (
                    source_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    publisher TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    material_families TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    license_note TEXT NOT NULL,
                    limitations TEXT NOT NULL,
                    source_status TEXT NOT NULL DEFAULT 'candidate',
                    content_sha256 TEXT,
                    content_type TEXT,
                    fetched_at TEXT,
                    authority_tier TEXT NOT NULL DEFAULT 'secondary',
                    scale TEXT NOT NULL DEFAULT '',
                    access_mode TEXT NOT NULL DEFAULT 'web',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS documents (
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
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL REFERENCES documents(document_id),
                    ordinal INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    embedding_json TEXT,
                    embedding_model TEXT,
                    UNIQUE(document_id, ordinal)
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
                    chunk_id UNINDEXED,
                    source_id UNINDEXED,
                    material_families,
                    text
                );
                CREATE TABLE IF NOT EXISTS claims (
                    claim_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL REFERENCES sources(source_id),
                    document_id TEXT NOT NULL REFERENCES documents(document_id),
                    chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),
                    skill_id TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    evidence_state TEXT NOT NULL DEFAULT 'candidate',
                    status TEXT NOT NULL DEFAULT 'candidate',
                    applicability TEXT NOT NULL,
                    limitations TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    promoted_at TEXT
                );
                CREATE TABLE IF NOT EXISTS claim_reviews (
                    review_id TEXT PRIMARY KEY,
                    claim_id TEXT NOT NULL REFERENCES claims(claim_id),
                    reviewer_id TEXT NOT NULL,
                    reviewer_role TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reasoning TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(claim_id, reviewer_id)
                );
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    node_id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    label TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS graph_edges (
                    edge_id TEXT PRIMARY KEY,
                    from_node TEXT NOT NULL REFERENCES graph_nodes(node_id),
                    to_node TEXT NOT NULL REFERENCES graph_nodes(node_id),
                    edge_type TEXT NOT NULL,
                    UNIQUE(from_node, to_node, edge_type)
                );
                CREATE TABLE IF NOT EXISTS ingestion_runs (
                    run_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(source_status);
                CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source_id, version);
                CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);
                CREATE INDEX IF NOT EXISTS idx_reviews_claim ON claim_reviews(claim_id);
                """
            )
            self._connection.execute(
                "INSERT OR REPLACE INTO store_meta(key, value) VALUES ('schema_version', ?)",
                (str(self.schema_version),),
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

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def register_source(self, source: SourceSpec, *, status: str = "candidate") -> None:
        """Register source metadata without downloading or promoting its content."""
        if status not in {"candidate", "active", "blocked"}:
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
                    content_type, fetched_at, authority_tier, scale, access_mode,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate', ?, ?, ?, ?, ?, ?, ?, ?)
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
            existing = self._connection.execute(
                "SELECT document_id FROM documents WHERE source_id = ? AND content_sha256 = ?",
                (source.source_id, digest),
            ).fetchone()
            if existing is not None:
                return IngestResult(source.source_id, str(existing["document_id"]), 0, digest, True)
            row = self._connection.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 AS next_version FROM documents WHERE source_id = ?",
                (source.source_id,),
            ).fetchone()
            version = int(row["next_version"])
            document_id = f"doc-{source.source_id}-{version}-{digest[:12]}"
            self._connection.execute(
                """
                INSERT INTO documents(
                    document_id, source_id, version, content, content_sha256, content_type,
                    fetched_at, extraction_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    source.source_id,
                    version,
                    normalized,
                    digest,
                    content_type,
                    timestamp,
                    extraction_status,
                ),
            )
            chunks = _chunks(normalized)
            for ordinal, chunk in enumerate(chunks):
                chunk_id = f"chunk-{document_id}-{ordinal}"
                self._connection.execute(
                    "INSERT INTO chunks(chunk_id, document_id, ordinal, text) VALUES (?, ?, ?, ?)",
                    (chunk_id, document_id, ordinal, chunk),
                )
                self._connection.execute(
                    "INSERT INTO chunk_fts(chunk_id, source_id, material_families, text) VALUES (?, ?, ?, ?)",
                    (chunk_id, source.source_id, " ".join(source.material_families), chunk),
                )
            self._graph_node(f"source:{source.source_id}", "source", source.title)
            self._graph_node(document_id, "document", f"{source.title} v{version}")
            self._graph_edge(f"source:{source.source_id}", document_id, "has_document")
            for family in source.material_families:
                family_id = f"material:{family}"
                self._graph_node(family_id, "material_family", family)
                self._graph_edge(f"source:{source.source_id}", family_id, "covers")
            for ordinal in range(len(chunks)):
                chunk_id = f"chunk-{document_id}-{ordinal}"
                self._graph_node(chunk_id, "chunk", f"{source.title} passage {ordinal + 1}")
                self._graph_edge(document_id, chunk_id, "contains")
            return IngestResult(source.source_id, document_id, len(chunks), digest, False)

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

    def documents_for_curating(self, *, limit: int = 20) -> list[dict[str, Any]]:
        """Return downloaded source passages for an explicit, candidate-only curator run."""
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

    def search(
        self,
        query: str,
        *,
        material_family: str | None = None,
        limit: int = 6,
        include_candidate: bool = True,
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
                           s.authority_tier, s.scale,
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
            except sqlite3.OperationalError:
                rows = self._connection.execute(
                    """
                    SELECT c.chunk_id, s.source_id, c.text, c.document_id,
                           s.title, s.url, s.publisher, s.material_families, s.source_status,
                           s.authority_tier, s.scale,
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
        for row in rows:
            families = tuple(json.loads(str(row["material_families"])))
            if material_family and material_family not in families:
                continue
            status = str(row["source_status"])
            if not include_candidate and status != "active":
                continue
            result.append(
                SearchResult(
                    chunk_id=str(row["chunk_id"]),
                    document_id=str(row["document_id"]),
                    source_id=str(row["source_id"]),
                    title=str(row["title"]),
                    url=str(row["url"]),
                    publisher=str(row["publisher"]),
                    material_families=families,
                    source_status=status,
                    authority_tier=str(row["authority_tier"]),
                    scale=str(row["scale"]),
                    text=str(row["text"]),
                    score=float(row["rank"]),
                )
            )
            if len(result) >= limit:
                break
        return result

    def context_for_query(
        self, query: str, *, material_family: str | None = None, limit: int = 4
    ) -> tuple[str, list[dict[str, str]]]:
        results = self.search(query, material_family=material_family, limit=limit)
        if not results:
            return (
                "No downloaded source passage matched this question. Do not imply that the source catalog covers it.",
                [],
            )
        passages: list[str] = []
        cards: list[dict[str, str]] = []
        for item in results:
            status_note = (
                "candidate background only; not promoted knowledge"
                if item.source_status != "active"
                else "source linked to promoted knowledge"
            )
            tier_note = "; ".join(item for item in (item.authority_tier, item.scale) if item)
            passages.append(f"[{item.source_id}; {status_note}; {tier_note}] {item.text[:900]}")
            cards.append(
                {
                    "label": item.title,
                    "detail": f"{item.publisher} · {status_note}",
                }
            )
        context = (
            "Downloaded source passages (untrusted reference context; never treat a candidate as a conclusion):\n"
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
                    "url": str(row["url"]),
                    "publisher": str(row["publisher"]),
                    "sourceType": str(row["source_type"]),
                    "jurisdiction": str(row["jurisdiction"]),
                    "licenseNote": str(row["license_note"]),
                    "limitations": str(row["limitations"]),
                    "materialFamilies": list(families),
                    "status": str(row["source_status"]),
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
            "schemaVersion": self.schema_version,
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
        """Return source, extraction, retrieval, claim, and run health without source text."""
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
            claim_rows = self._connection.execute(
                "SELECT status, COUNT(*) AS count FROM claims GROUP BY status"
            ).fetchall()
            claim_total = self._connection.execute(
                "SELECT COUNT(*) AS count FROM claims"
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
            },
            "chunks": {
                "total": int((chunk_row["total"] or 0) if chunk_row else 0),
                "searchable": int((chunk_row["searchable"] or 0) if chunk_row else 0),
                "embedded": int((chunk_row["embedded"] or 0) if chunk_row else 0),
            },
            "claims": {
                "total": int(claim_total["count"] if claim_total else 0),
                "byStatus": {str(row["status"]): int(row["count"]) for row in claim_rows},
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

    def add_candidate_claim(
        self,
        *,
        source_id: str,
        statement: str,
        skill_id: str,
        chunk_id: str,
        applicability: str,
        limitations: str,
    ) -> str:
        if not statement.strip() or not applicability.strip() or not limitations.strip():
            raise KnowledgeStoreError(
                "Candidate claims require statement, applicability, and limitations."
            )
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT document_id FROM chunks WHERE chunk_id = ?", (chunk_id,)
            ).fetchone()
            if row is None:
                raise KnowledgeStoreError("Candidate claim chunk is not present in the store.")
            source_row = self._connection.execute(
                "SELECT source_id FROM sources WHERE source_id = ?", (source_id,)
            ).fetchone()
            if source_row is None:
                raise KnowledgeStoreError("Candidate claim source is not present in the store.")
            claim_id = (
                "claim-"
                + hashlib.sha256(
                    _canonical([source_id, chunk_id, skill_id, statement]).encode("utf-8")
                ).hexdigest()[:24]
            )
            self._connection.execute(
                """
                INSERT OR IGNORE INTO claims(
                    claim_id, source_id, document_id, chunk_id, skill_id, statement,
                    evidence_state, status, applicability, limitations, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'candidate', 'candidate', ?, ?, ?)
                """,
                (
                    claim_id,
                    source_id,
                    str(row["document_id"]),
                    chunk_id,
                    skill_id,
                    statement.strip(),
                    applicability.strip(),
                    limitations.strip(),
                    _now(),
                ),
            )
            self._graph_node(claim_id, "claim", statement.strip()[:180])
            self._graph_edge(f"source:{source_id}", claim_id, "supports")
            self._graph_edge(chunk_id, claim_id, "proposes")
            return claim_id

    def review_claim(
        self,
        claim_id: str,
        *,
        reviewer_id: str,
        reviewer_role: str,
        decision: str,
        reasoning: str,
    ) -> None:
        allowed = {"approve", "reject", "request_more_evidence"}
        if decision not in allowed:
            raise KnowledgeStoreError("Claim review decision is not allowed.")
        if not reviewer_id.strip() or not reviewer_role.strip() or not reasoning.strip():
            raise KnowledgeStoreError(
                "Claim reviews require reviewer identity, role, and reasoning."
            )
        with self._lock, self._connection:
            if (
                self._connection.execute(
                    "SELECT claim_id FROM claims WHERE claim_id = ?", (claim_id,)
                ).fetchone()
                is None
            ):
                raise KnowledgeStoreError("Claim does not exist.")
            self._connection.execute(
                """
                INSERT INTO claim_reviews(
                    review_id, claim_id, reviewer_id, reviewer_role, decision, reasoning, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(claim_id, reviewer_id) DO UPDATE SET
                    reviewer_role=excluded.reviewer_role, decision=excluded.decision,
                    reasoning=excluded.reasoning, created_at=excluded.created_at
                """,
                (
                    f"review-{uuid.uuid4()}",
                    claim_id,
                    reviewer_id.strip(),
                    reviewer_role.strip(),
                    decision,
                    reasoning.strip(),
                    _now(),
                ),
            )

    def promote_claim(self, claim_id: str) -> bool:
        with self._lock, self._connection:
            claim = self._connection.execute(
                "SELECT status, source_id FROM claims WHERE claim_id = ?", (claim_id,)
            ).fetchone()
            if claim is None:
                raise KnowledgeStoreError("Claim does not exist.")
            if str(claim["status"]) == "active":
                return True
            reviews = self._connection.execute(
                "SELECT reviewer_id, reviewer_role, decision FROM claim_reviews WHERE claim_id = ?",
                (claim_id,),
            ).fetchall()
            if any(str(row["decision"]) != "approve" for row in reviews):
                return False
            approved = {(str(row["reviewer_id"]), str(row["reviewer_role"])) for row in reviews}
            roles = {role for _reviewer, role in approved}
            reviewers = {reviewer for reviewer, _role in approved}
            if len(reviewers) < 2 or len(roles) < 2:
                return False
            self._connection.execute(
                "UPDATE claims SET status = 'active', evidence_state = 'reviewed', promoted_at = ? WHERE claim_id = ?",
                (_now(), claim_id),
            )
            self._graph_node(claim_id, "claim", claim_id)
            return True

    def claim_status(self, claim_id: str) -> str:
        with self._lock:
            row = self._connection.execute(
                "SELECT status FROM claims WHERE claim_id = ?", (claim_id,)
            ).fetchone()
        if row is None:
            raise KnowledgeStoreError("Claim does not exist.")
        return str(row["status"])

    def claim_catalog(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            if status:
                rows = self._connection.execute(
                    "SELECT * FROM claims WHERE status = ? ORDER BY created_at LIMIT ?",
                    (status, max(1, min(limit, 500))),
                ).fetchall()
            else:
                rows = self._connection.execute(
                    "SELECT * FROM claims ORDER BY created_at LIMIT ?",
                    (max(1, min(limit, 500)),),
                ).fetchall()
        return [
            {
                "id": str(row["claim_id"]),
                "sourceId": str(row["source_id"]),
                "documentId": str(row["document_id"]),
                "chunkId": str(row["chunk_id"]),
                "skillId": str(row["skill_id"]),
                "statement": str(row["statement"]),
                "status": str(row["status"]),
                "evidenceState": str(row["evidence_state"]),
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
            rows = self._connection.execute(
                """
                SELECT source_id, content_sha256, source_status FROM sources ORDER BY source_id;
                """
            ).fetchall()
            claims = self._connection.execute(
                "SELECT claim_id, status, statement FROM claims ORDER BY claim_id"
            ).fetchall()
        body = [dict(row) for row in rows] + [dict(row) for row in claims]
        return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()

    def _graph_node(self, node_id: str, node_type: str, label: str) -> None:
        self._connection.execute(
            "INSERT INTO graph_nodes(node_id, node_type, label) VALUES (?, ?, ?) ON CONFLICT(node_id) DO UPDATE SET label=excluded.label",
            (node_id, node_type, label),
        )

    def _graph_edge(self, from_node: str, to_node: str, edge_type: str) -> None:
        self._connection.execute(
            "INSERT OR IGNORE INTO graph_edges(edge_id, from_node, to_node, edge_type) VALUES (?, ?, ?, ?)",
            (f"edge-{uuid.uuid4()}", from_node, to_node, edge_type),
        )
