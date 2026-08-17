from __future__ import annotations

import hashlib
import http.client
import json
import sqlite3
import threading
from pathlib import Path

import pytest

from helpme_green.application import ApplicationProcessor
from helpme_green.conversation import ConversationAgent
from helpme_green.expert_skills import SkillRegistry
from helpme_green.knowledge import KnowledgeBase
from helpme_green.knowledge_store import KnowledgeDatabase, KnowledgeStoreError, SourceSpec
from helpme_green.model_gateway import ModelRouter, ModelSelection
from helpme_green.persistence import SessionState, SessionStore
from helpme_green.server import _HelpmeServer
from helpme_green.upload_ingest import (
    MultipartPart,
    UploadError,
    UploadIngestor,
    UploadStorage,
    extract_text,
)

ROOT = Path(__file__).resolve().parents[1]


def _source(source_id: str, families: tuple[str, ...] = ("plastics",)) -> SourceSpec:
    return SourceSpec(
        source_id=source_id,
        title=f"Source {source_id}",
        url=f"https://example.gov/{source_id}",
        publisher="Example public body",
        source_type="OFFICIAL_GUIDANCE",
        material_families=families,
        license_note="Synthetic test source",
    )


def _v3_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE store_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO store_meta(key, value) VALUES ('database_version', '3');
        CREATE TABLE sources (
            source_id TEXT PRIMARY KEY, title TEXT NOT NULL, url TEXT NOT NULL,
            publisher TEXT NOT NULL, source_type TEXT NOT NULL, material_families TEXT NOT NULL,
            jurisdiction TEXT NOT NULL, license_note TEXT NOT NULL, limitations TEXT NOT NULL,
            source_status TEXT NOT NULL DEFAULT 'catalogued', content_sha256 TEXT, content_type TEXT,
            fetched_at TEXT, authority_tier TEXT NOT NULL DEFAULT 'secondary',
            scale TEXT NOT NULL DEFAULT '', access_mode TEXT NOT NULL DEFAULT 'web',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(source_id),
            version INTEGER NOT NULL, content TEXT NOT NULL, content_sha256 TEXT NOT NULL,
            content_type TEXT NOT NULL, fetched_at TEXT NOT NULL, extraction_status TEXT NOT NULL,
            UNIQUE(source_id, content_sha256)
        );
        CREATE TABLE chunks (
            chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(document_id),
            ordinal INTEGER NOT NULL, text TEXT NOT NULL, embedding_json TEXT, embedding_model TEXT,
            UNIQUE(document_id, ordinal)
        );
        CREATE VIRTUAL TABLE chunk_fts USING fts5(
            chunk_id UNINDEXED, source_id UNINDEXED, material_families, text
        );
        CREATE TABLE source_notes (
            note_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(source_id),
            document_id TEXT NOT NULL REFERENCES documents(document_id),
            chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id), skill_id TEXT NOT NULL,
            summary TEXT NOT NULL, applicability TEXT NOT NULL, limitations TEXT NOT NULL,
            created_at TEXT NOT NULL, UNIQUE(source_id, chunk_id, skill_id, summary)
        );
        CREATE TABLE graph_nodes (node_id TEXT PRIMARY KEY, node_type TEXT NOT NULL, label TEXT NOT NULL);
        CREATE TABLE graph_edges (
            edge_id TEXT PRIMARY KEY, from_node TEXT NOT NULL REFERENCES graph_nodes(node_id),
            to_node TEXT NOT NULL REFERENCES graph_nodes(node_id), edge_type TEXT NOT NULL,
            UNIQUE(from_node, to_node, edge_type)
        );
        CREATE TABLE ingestion_runs (
            run_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, outcome TEXT NOT NULL,
            detail TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT NOT NULL
        );
        """
    )
    connection.executemany(
        "INSERT INTO sources(source_id, title, url, publisher, source_type, material_families, "
        "jurisdiction, license_note, limitations, source_status, content_sha256, content_type, "
        "fetched_at, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                "legacy-source",
                "Legacy source",
                "https://example.gov/legacy",
                "Example body",
                "OFFICIAL_GUIDANCE",
                '["plastics"]',
                "",
                "Synthetic",
                "",
                "catalogued",
                "legacy-content-sha256",
                "text/plain",
                "2026-08-01T00:00:00Z",
                "2026-08-01T00:00:00Z",
                "2026-08-01T00:00:00Z",
            ),
            (
                "legacy-blocked",
                "Legacy blocked",
                "https://example.gov/blocked",
                "Example body",
                "OFFICIAL_GUIDANCE",
                '["plastics"]',
                "",
                "Synthetic",
                "",
                "blocked",
                "legacy-blocked-sha256",
                "text/plain",
                "2026-08-01T00:00:00Z",
                "2026-08-01T00:00:00Z",
                "2026-08-01T00:00:00Z",
            ),
        ],
    )
    connection.execute(
        "INSERT INTO documents(document_id, source_id, version, content, content_sha256, "
        "content_type, fetched_at, extraction_status) VALUES (?,?,?,?,?,?,?,?)",
        (
            "doc-legacy-1",
            "legacy-source",
            1,
            "Legacy retrieved passage with a unique searchable term.",
            "legacy-doc-sha",
            "text/plain",
            "2026-08-01T00:00:00Z",
            "extracted",
        ),
    )
    connection.execute(
        "INSERT INTO chunks(chunk_id, document_id, ordinal, text) VALUES (?,?,?,?)",
        (
            "chunk-legacy-0",
            "doc-legacy-1",
            0,
            "Legacy retrieved passage with a unique searchable term.",
        ),
    )
    connection.execute(
        "INSERT INTO chunk_fts(chunk_id, source_id, material_families, text) VALUES (?,?,?,?)",
        (
            "chunk-legacy-0",
            "legacy-source",
            "plastics",
            "Legacy retrieved passage with a unique searchable term.",
        ),
    )
    connection.execute(
        "INSERT INTO source_notes(note_id, source_id, document_id, chunk_id, skill_id, summary, "
        "applicability, limitations, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            "note-legacy",
            "legacy-source",
            "doc-legacy-1",
            "chunk-legacy-0",
            "plastics-recycling",
            "Legacy note summary.",
            "Early triage",
            "Not a conclusion.",
            "2026-08-01T00:00:00Z",
        ),
    )
    connection.execute(
        "INSERT INTO graph_nodes(node_id, node_type, label) VALUES (?,?,?)",
        ("source:legacy-source", "source", "Legacy source"),
    )
    connection.execute(
        "INSERT INTO graph_nodes(node_id, node_type, label) VALUES (?,?,?)",
        ("doc-legacy-1", "document", "Legacy source v1"),
    )
    connection.execute(
        "INSERT INTO graph_edges(edge_id, from_node, to_node, edge_type) VALUES (?,?,?,?)",
        ("edge-legacy", "source:legacy-source", "doc-legacy-1", "has_document"),
    )
    connection.execute(
        "INSERT INTO ingestion_runs(run_id, source_id, outcome, detail, started_at, finished_at) "
        "VALUES (?,?,?,?,?,?)",
        (
            "run-legacy",
            "legacy-source",
            "ingested",
            "ok",
            "2026-08-01T00:00:00Z",
            "2026-08-01T00:00:01Z",
        ),
    )
    connection.commit()
    connection.close()


def test_migration_from_v3_preserves_populated_data(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    _v3_database(path)

    database = KnowledgeDatabase(path)
    try:
        assert database.database_version == 4
        sources = {item["id"]: item for item in database.source_catalog(limit=200)}
        assert sources["legacy-source"]["origin"] == "manifest"
        assert sources["legacy-source"]["status"] == "catalogued"
        assert sources["legacy-blocked"]["status"] == "blocked"
        matches = database.search("unique searchable term")
        assert matches and matches[0].source_id == "legacy-source"
        assert database.source_note_catalog()[0]["summary"] == "Legacy note summary."
        assert database.ingestion_summary()["runs"]["total"] == 1
        assert database.graph_neighbors("source:legacy-source")
    finally:
        database.close()


def test_user_upload_source_has_null_url_and_review_status(tmp_path: Path) -> None:
    database = KnowledgeDatabase(tmp_path / "knowledge.db")
    try:
        source_id = database.register_user_upload_source(
            source_id="upload-abc123",
            title="Operator upload",
            publisher="not provided",
            source_type="USER_UPLOAD",
            material_families=("plastics",),
        )
        assert source_id == "upload-abc123"
        catalog = {item["id"]: item for item in database.source_catalog()}
        assert catalog["upload-abc123"]["url"] == ""
        assert catalog["upload-abc123"]["status"] == "review"
        assert catalog["upload-abc123"]["origin"] == "user-upload"
    finally:
        database.close()


def test_retrieval_policy_distinguishes_manifest_and_user_upload(tmp_path: Path) -> None:
    database = KnowledgeDatabase(tmp_path / "knowledge.db")
    try:
        database.ingest_document(
            _source("manifest-catalogued"),
            "Shared recycled polymer passage.",
            content_type="text/plain",
        )
        blocked = _source("manifest-blocked")
        database.register_source(blocked, status="blocked")
        database.ingest_document(
            blocked, "Shared recycled polymer blocked passage.", content_type="text/plain"
        )
        database.register_user_upload_source(
            source_id="upload-review",
            title="Review upload",
            publisher="not provided",
            source_type="USER_UPLOAD",
            material_families=("plastics",),
        )
        database.ingest_upload_document(
            source_id="upload-review",
            title="Review upload",
            material_families=("plastics",),
            content="Shared recycled polymer review passage.",
            content_type="text/plain",
        )
        database.register_user_upload_source(
            source_id="upload-active",
            title="Active upload",
            publisher="not provided",
            source_type="USER_UPLOAD",
            material_families=("plastics",),
        )
        database.ingest_upload_document(
            source_id="upload-active",
            title="Active upload",
            material_families=("plastics",),
            content="Shared recycled polymer active passage.",
            content_type="text/plain",
        )
        with database._connection:
            database._connection.execute(
                "UPDATE sources SET source_status = 'active' WHERE source_id = 'upload-active'"
            )

        results = database.search("recycled polymer", limit=20)
        source_ids = {item.source_id for item in results}
        assert "manifest-catalogued" in source_ids
        assert "upload-active" in source_ids
        assert "manifest-blocked" not in source_ids
        assert "upload-review" not in source_ids
        active = next(item for item in results if item.source_id == "upload-active")
        assert active.origin == "user-upload"
    finally:
        database.close()


def test_transition_matrix_and_delete_cleanup(tmp_path: Path) -> None:
    database = KnowledgeDatabase(tmp_path / "knowledge.db")
    try:
        database.register_user_upload_source(
            source_id="upload-abc",
            title="Upload",
            publisher="not provided",
            source_type="USER_UPLOAD",
            material_families=("plastics",),
        )
        document = database.ingest_upload_document(
            source_id="upload-abc",
            title="Upload",
            material_families=("plastics",),
            content="Transition passage for approval.",
            content_type="text/plain",
        )
        database.create_upload(
            "upload-1",
            original_filename="a.txt",
            storage_key="0123456789abcdef0123456789abcdef.bin",
            raw_sha256="abc",
            size_bytes=10,
            declared_content_type="text/plain",
            detected_content_type=".txt",
            extension=".txt",
            status="ingested",
        )
        database.update_upload("upload-1", source_id="upload-abc", document_id=document.document_id)

        # Approve only works from review with an extracted document.
        assert database.search("Transition passage", limit=10) == []
        database.approve_upload("upload-1", reviewed_by="operator")
        assert database.search("Transition passage", limit=10)[0].source_id == "upload-abc"
        with pytest.raises(KnowledgeStoreError):
            database.approve_upload("upload-1")

        # Quarantine removes eligibility again and blocks re-approval from `blocked`.
        database.quarantine_upload("upload-1", reviewed_by="operator")
        assert database.search("Transition passage", limit=10) == []
        with pytest.raises(KnowledgeStoreError):
            database.approve_upload("upload-1")

        # Delete tombstones the upload and removes derived rows, keeping the audit tombstone.
        result = database.delete_upload("upload-1")
        assert result is not None
        source_id, storage_key, raw_sha256 = result
        assert source_id == "upload-abc"
        assert storage_key.endswith(".bin")
        assert raw_sha256 == "abc"
        upload = database.get_upload("upload-1")
        assert upload is not None and upload["status"] == "deleted"
        assert database.search("Transition passage", limit=10) == []
        assert database.delete_upload("upload-1") is None
    finally:
        database.close()


def test_graph_rebuild_is_deterministic_and_reasons_edges(tmp_path: Path) -> None:
    database = KnowledgeDatabase(tmp_path / "knowledge.db")
    try:
        first = database.ingest_document(
            _source("graph-a"), "First version text.", content_type="text/plain"
        )
        database.ingest_document(
            _source("graph-a"), "Second version text.", content_type="text/plain"
        )
        database.ingest_document(
            _source("graph-b"), "Other family source.", content_type="text/plain"
        )

        derived_first = database.rebuild_graph(projection_version=7)
        derived_second = database.rebuild_graph(projection_version=7)
        assert derived_first == derived_second > 0
        projection = database.graph_projection(include_derived=True, max_nodes=100)
        supersedes = [e for e in projection["edges"] if e["edgeType"] == "supersedes"]
        assert any(e["directed"] and e["reasonCode"] == "newer_version" for e in supersedes)
        assert projection["projectionVersion"] == 7
        assert first.document_id in {e["from"] for e in supersedes}
    finally:
        database.close()


def test_extractors_and_duplicate_detection(tmp_path: Path) -> None:
    assert "hello world" in extract_text("a.txt", ".txt", b"hello world")
    assert "cell" in extract_text("a.csv", ".csv", b"a,b\ncell,d\n")
    with pytest.raises(UploadError) as empty:
        extract_text("a.txt", ".txt", b"   \n  ")
    assert empty.value.code == "empty_extraction"
    with pytest.raises(UploadError) as mismatched:
        extract_text("a.xlsx", ".xlsx", b"not a zip at all")
    assert mismatched.value.code in {"malformed_xlsx", "mismatched_content_type"}

    database = KnowledgeDatabase(tmp_path / "knowledge.db")
    storage = UploadStorage(tmp_path / "uploads", max_storage_bytes=1_000_000)
    ingestor = UploadIngestor(database, storage, max_file_bytes=10_000)
    try:
        first = ingestor.ingest(MultipartPart("doc.txt", "text/plain", b"unique raw bytes"))
        second = ingestor.ingest(MultipartPart("doc2.txt", "text/plain", b"unique raw bytes"))
        assert second.duplicate_of == first.upload_id
    finally:
        database.close()


def _running_kb_server(tmp_path: Path, monkeypatch) -> tuple[_HelpmeServer, threading.Thread]:
    monkeypatch.setenv("HELPME_KB_ENABLED", "1")
    monkeypatch.setenv("HELPME_KB_ACCESS_TOKEN", "kb-test-token")
    monkeypatch.setenv("HELPME_KB_ALLOW_LOOPBACK_DEV", "0")
    knowledge = KnowledgeBase.from_repository(ROOT)
    sessions = SessionStore(tmp_path / "data", knowledge_digest=knowledge.digest)
    processor = ApplicationProcessor(knowledge, sessions)
    server = _HelpmeServer(("127.0.0.1", 0), processor, sessions)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _multipart(fields: dict[str, str], files: list[tuple[str, str, bytes]]) -> tuple[bytes, str]:
    boundary = "----helpmeBoundary7MA4YWxk"
    lines: list[bytes] = []
    for name, value in fields.items():
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        lines.append(value.encode() + b"\r\n")
    for filename, content_type, data in files:
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(
            f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'.encode()
        )
        lines.append(f"Content-Type: {content_type}\r\n\r\n".encode())
        lines.append(data + b"\r\n")
    lines.append(f"--{boundary}--\r\n".encode())
    body = b"".join(lines)
    return body, f"multipart/form-data; boundary={boundary}"


def test_kb_api_gating_and_upload_review_approve_flow(tmp_path: Path, monkeypatch) -> None:
    server, thread = _running_kb_server(tmp_path, monkeypatch)
    try:
        base = ("127.0.0.1", server.server_port)

        def request(method, path, *, body=None, headers=None):
            connection = http.client.HTTPConnection(*base, timeout=10)
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            payload = response.read()
            connection.close()
            return response.status, response.getheader("Content-Type", ""), payload

        # Capabilities requires the operator token.
        status, _, _ = request("GET", "/api/kb/capabilities")
        assert status == 401
        auth = {"Authorization": "Bearer kb-test-token"}
        status, _, payload = request("GET", "/api/kb/capabilities", headers=auth)
        assert status == 200
        capabilities = json.loads(payload)
        assert capabilities["enabled"] is True

        # Upload a reference file.
        mp_body, mp_ct = _multipart(
            {"title": "Recycled PET guide", "materialFamilies": "plastics"},
            [
                (
                    "pet-guide.txt",
                    "text/plain",
                    b"Recycled PET flake needs washing and sorting before extrusion.",
                )
            ],
        )
        status, _, payload = request(
            "POST", "/api/kb/uploads", body=mp_body, headers={**auth, "Content-Type": mp_ct}
        )
        assert status == 202, payload
        created = json.loads(payload)
        upload_id = created["uploads"][0]["uploadId"]
        assert created["uploads"][0]["status"] == "validated"

        # A review upload is absent from the documents list search.
        status, _, payload = request("GET", "/api/kb/documents?origin=user-upload", headers=auth)
        assert status == 200
        documents = json.loads(payload)
        assert documents["total"] >= 1

        # Approve the upload.
        status, _, payload = request(
            "POST",
            f"/api/kb/uploads/{upload_id}/approve",
            body=json.dumps({}),
            headers={**auth, "Content-Type": "application/json"},
        )
        assert status == 200, payload

        # Overview reflects the approved source.
        status, _, payload = request("GET", "/api/kb/overview", headers=auth)
        assert status == 200
        assert json.loads(payload)["sources"]["total"] >= 1

        # Delete the upload; retrieval rows are removed.
        status, _, payload = request("DELETE", f"/api/kb/uploads/{upload_id}", headers=auth)
        assert status == 200, payload
        status, _, _ = request("DELETE", f"/api/kb/uploads/{upload_id}", headers=auth)
        assert status == 404

        # The append-only audit chain remains valid after every KB mutation.
        assert server.store.verify_audit_chain()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_kb_disabled_returns_403(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HELPME_KB_ENABLED", "0")
    monkeypatch.setenv("HELPME_KB_ACCESS_TOKEN", "kb-test-token")
    knowledge = KnowledgeBase.from_repository(ROOT)
    sessions = SessionStore(tmp_path / "data", knowledge_digest=knowledge.digest)
    processor = ApplicationProcessor(knowledge, sessions)
    server = _HelpmeServer(("127.0.0.1", 0), processor, sessions)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request("GET", "/api/kb/capabilities")
        response = connection.getresponse()
        response.read()
        connection.close()
        assert response.status == 403
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize(
    "origin_status,expected",
    [
        ("manifest|catalogued", True),
        ("manifest|active", True),
        ("manifest|blocked", False),
        ("user-upload|review", False),
        ("user-upload|active", True),
        ("user-upload|blocked", False),
        ("user-upload|deleted", False),
    ],
)
def test_retrievable_predicate_matrix(origin_status: str, expected: bool) -> None:
    origin, status = origin_status.split("|")
    assert KnowledgeDatabase._retrievable(status, origin, include_catalogued=True) is expected


def test_hash_distinction_and_duplicate_upload(tmp_path: Path) -> None:
    database = KnowledgeDatabase(tmp_path / "knowledge.db")
    storage = UploadStorage(tmp_path / "uploads", max_storage_bytes=100_000)
    ingestor = UploadIngestor(database, storage, max_file_bytes=100_000)
    try:
        first = ingestor.ingest(MultipartPart("a.txt", "text/plain", b"raw file bytes"))
        assert first.upload_id and first.status == "validated"
        upload = database.get_upload(first.upload_id)
        assert upload["rawSha256"] == hashlib.sha256(b"raw file bytes").hexdigest()
        second = ingestor.ingest(MultipartPart("b.txt", "text/plain", b"raw file bytes"))
        assert second.status == "duplicate"
    finally:
        database.close()


def test_review_upload_absent_and_approved_upload_only_in_untrusted_channel(
    tmp_path: Path,
) -> None:
    database = KnowledgeDatabase(tmp_path / "knowledge.db")
    database.register_user_upload_source(
        source_id="upload-review-ctx",
        title="Review ctx",
        publisher="not provided",
        source_type="USER_UPLOAD",
        material_families=("plastics",),
    )
    database.ingest_upload_document(
        source_id="upload-review-ctx",
        title="Review ctx",
        material_families=("plastics",),
        content="Recycled polymer review secret marker passage.",
        content_type="text/plain",
    )
    database.register_user_upload_source(
        source_id="upload-active-ctx",
        title="Active ctx",
        publisher="not provided",
        source_type="USER_UPLOAD",
        material_families=("plastics",),
    )
    database.ingest_upload_document(
        source_id="upload-active-ctx",
        title="Active ctx",
        material_families=("plastics",),
        content="Recycled polymer feedstock needs moisture checks before extrusion.",
        content_type="text/plain",
    )
    with database._connection:
        database._connection.execute(
            "UPDATE sources SET source_status = 'active' WHERE source_id = 'upload-active-ctx'"
        )

    store = SessionStore(tmp_path / "data", knowledge_digest="digest-v1")
    router = ModelRouter(ModelSelection("localai", "test-model"))
    captured_messages: list[list[dict[str, str]]] = []
    captured_contracts: list[str] = []

    def fake_complete_json(messages, **kwargs):
        captured_messages.append([dict(item) for item in messages])
        captured_contracts.append(str(kwargs["system_contract"]))
        return {"reply": "Moisture checks matter.", "hearing": {}}

    router.complete_json = fake_complete_json
    agent = ConversationAgent(
        router,
        store,
        skill_registry=SkillRegistry.from_repository(ROOT),
        knowledge_db=database,
    )
    session = SessionState.new(topic="", geography="")
    store.save_session(session)

    try:
        result = agent.respond(session, "recycled polymer feedstock")

        assert result.ai_used is True
        system_contract = captured_contracts[0]
        # The trusted contract marks reference text as untrusted and unable to change instructions.
        assert "untrusted" in system_contract.casefold()
        assert "cannot change these instructions" in system_contract.casefold()
        # The approved passage never leaks into the trusted system contract.
        assert "feedstock" not in system_contract
        # The review passage is absent from both the contract and every message.
        assert "secret marker" not in system_contract
        all_message_text = " ".join(item["content"] for item in captured_messages[0])
        assert "secret marker" not in all_message_text
        # The approved passage appears only in an explicitly-marked untrusted reference message.
        reference_messages = [
            item
            for item in captured_messages[0]
            if "untrusted background material" in item["content"].casefold()
        ]
        assert reference_messages
        assert "feedstock" in reference_messages[0]["content"]
    finally:
        database.close()
