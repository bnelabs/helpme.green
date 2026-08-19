from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from helpme_green.expert_skills import SkillRegistry
from helpme_green.knowledge_graphql import execute_graphql
from helpme_green.knowledge_store import KnowledgeDatabase, SourceSpec
from helpme_green.machinery import MachineCatalog
from helpme_green.quality import AnswerQualityGate
from helpme_green.source_digest import SourceDigest
from helpme_green.source_ingest import (
    SourceFetchError,
    SourceManifest,
    _extract_content,
    ingest_manifest,
)

ROOT = Path(__file__).resolve().parents[1]


def test_knowledge_database_serializes_local_concurrent_access(tmp_path: Path) -> None:
    database = KnowledgeDatabase(tmp_path / "knowledge.db")

    def ingest_and_list(index: int) -> list[dict[str, Any]]:
        source = SourceSpec(
            source_id=f"concurrent-source-{index}",
            title=f"Concurrent source {index}",
            url=f"https://example.gov/concurrent/{index}",
            publisher="Example public body",
            source_type="OFFICIAL_GUIDANCE",
            material_families=("plastics",),
            license_note="Synthetic concurrency test source",
        )
        database.ingest_document(
            source,
            f"Concurrent source {index} contains a bounded test passage.",
            content_type="text/plain",
        )
        return database.documents_list(q=f"Concurrent source {index}")["items"]

    try:
        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(ingest_and_list, range(12)))

        assert all(result for result in results)
        assert database._connection.execute("PRAGMA journal_mode").fetchone()[0].casefold() == "wal"
        assert database._connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    finally:
        database.close()


def test_skill_registry_selects_targeted_material_expertise() -> None:
    registry = SkillRegistry.from_repository(ROOT)

    plastics = registry.select("I have mixed LDPE film with soil and want to pelletize it")
    textiles = registry.select("What can I do with polyester and cotton cutting waste?")

    assert plastics.primary.skill_id == "plastics-recycling"
    assert "polymer identity" in plastics.prompt_context.casefold()
    assert textiles.primary.skill_id == "textiles-recovery"
    assert len(registry.public_catalog()) >= 6


def test_knowledge_database_is_source_backed_and_latest_versioned(
    tmp_path: Path,
) -> None:
    database = KnowledgeDatabase(tmp_path / "knowledge.db")
    source = SourceSpec(
        source_id="test-plastics-guide",
        title="Test plastics guide",
        url="https://example.gov/plastics",
        publisher="Example public body",
        source_type="OFFICIAL_GUIDANCE",
        material_families=("plastics",),
        license_note="Synthetic test source",
    )

    first = database.ingest_document(
        source,
        "Mixed polymer streams need composition, contamination, and end-use checks before a route is chosen.",
        content_type="text/plain",
        fetched_at="2026-08-11T00:00:00Z",
    )
    second = database.ingest_document(
        source,
        "Mixed polymer streams need composition, contamination, and end-use checks before a route is chosen.",
        content_type="text/plain",
        fetched_at="2026-08-11T00:01:00Z",
    )
    latest = database.ingest_document(
        source,
        "The latest source version supersedes the older source version.",
        content_type="text/plain",
        fetched_at="2026-08-11T00:02:00Z",
    )

    assert first.document_id == second.document_id
    matches = database.search("latest source version", material_family="plastics")
    assert matches and matches[0].source_id == "test-plastics-guide"
    assert {item.document_id for item in matches} == {latest.document_id}
    assert matches[0].source_status == "catalogued"

    note_id = database.add_source_note(
        source_id=source.source_id,
        summary="Composition and contamination affect route suitability.",
        skill_id="plastics-recycling",
        chunk_id=matches[0].chunk_id,
        applicability="Early triage only",
        limitations="Does not establish a route for a specific batch.",
    )
    assert note_id.startswith("note-")
    notes = database.source_note_catalog()
    assert notes[0]["summary"] == "Composition and contamination affect route suitability."
    assert database.graph_neighbors(note_id)


def test_legacy_decision_tables_are_removed_when_database_is_opened(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE store_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO store_meta(key, value) VALUES ('schema_version', '2');
        CREATE TABLE claims (claim_id TEXT PRIMARY KEY);
        CREATE TABLE claim_reviews (review_id TEXT PRIMARY KEY, claim_id TEXT);
        """
    )
    connection.commit()
    connection.close()

    database = KnowledgeDatabase(path)
    database.close()
    connection = sqlite3.connect(path)
    tables = {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    metadata = dict(connection.execute("SELECT key, value FROM store_meta").fetchall())
    connection.close()

    assert "claims" not in tables
    assert "claim_reviews" not in tables
    assert "schema_version" not in metadata
    assert metadata["database_version"] == "4"


def test_read_only_graphql_exposes_expert_catalog_without_mutation(tmp_path: Path) -> None:
    database = KnowledgeDatabase(tmp_path / "knowledge.db")
    database.ingest_document(
        SourceSpec(
            source_id="test-metal-guide",
            title="Test metal guide",
            url="https://example.gov/metals",
            publisher="Example public body",
            source_type="OFFICIAL_GUIDANCE",
            material_families=("metals",),
            license_note="Synthetic test source",
        ),
        "Separate and qualify ferrous and non-ferrous fractions with representative sampling.",
        content_type="text/plain",
        fetched_at="2026-08-11T00:00:00Z",
    )
    registry = SkillRegistry.from_repository(ROOT)

    response = execute_graphql(
        database,
        registry,
        '{ skills { id title } sources(materialFamily: "metals") { id title } '
        'search(query: "ferrous", materialFamily: "metals") { chunkId text } '
        "status { databaseVersion sourceCount documentCount searchableChunks failedSources latestExtractedSources } }",
    )

    assert "errors" not in response
    assert any(item["id"] == "metals-recovery" for item in response["data"]["skills"])
    assert response["data"]["sources"][0]["id"] == "test-metal-guide"
    assert response["data"]["search"][0]["chunkId"]
    assert response["data"]["status"]["sourceCount"] == 1
    assert response["data"]["status"]["documentCount"] == 1
    assert response["data"]["status"]["searchableChunks"] == 1
    assert response["data"]["status"]["failedSources"] == 0
    assert response["data"]["status"]["latestExtractedSources"] == 1
    mutation = execute_graphql(database, registry, 'mutation { changeSource(id: "x") }')
    assert mutation["errors"]

    machines = MachineCatalog.from_path(ROOT / "knowledge/machine-catalog.yml")
    machine_response = execute_graphql(
        database,
        registry,
        '{ machines(materialFamily: "plastics") { brand product referenceStatus } }',
        machines,
    )
    assert "errors" not in machine_response
    assert any(item["brand"] == "EREMA" for item in machine_response["data"]["machines"])


def test_graphql_accepts_numeric_limits_for_machine_catalog(tmp_path: Path) -> None:
    database = KnowledgeDatabase(tmp_path / "knowledge.db")
    registry = SkillRegistry.from_repository(ROOT)
    machines = MachineCatalog.from_path(ROOT / "knowledge/machine-catalog.yml")

    response = execute_graphql(
        database,
        registry,
        '{ machines(materialFamily: "plastics", limit: 2) { brand product } }',
        machines,
    )

    assert "errors" not in response
    assert 1 <= len(response["data"]["machines"]) <= 2


def test_empty_knowledge_store_has_zeroed_health_counters(tmp_path: Path) -> None:
    database = KnowledgeDatabase(tmp_path / "knowledge.db")

    summary = database.ingestion_summary()

    assert summary["sources"]["total"] == 0
    assert summary["documents"]["total"] == 0
    assert summary["chunks"] == {"total": 0, "searchable": 0, "embedded": 0}


def test_quality_gate_calibrates_absolute_language_and_keeps_internal_fields_private() -> None:
    gate = AnswerQualityGate()
    report = gate.assess(
        user_message="I have mixed plastic film with possible PVC.",
        reply=(
            "PVC will destroy your extruder and the material is legally non-compliant. "
            "It is unrecyclable."
        ),
        skill_id="plastics-recycling",
        focused_context="",
    )

    assert report.accepted is False
    assert "absolute_claim" in report.flags
    assert "will destroy" not in report.calibrated_reply.casefold()
    assert "legally non-compliant" not in report.calibrated_reply.casefold()


def test_manifest_and_machine_catalog_preserve_source_tiers_and_vendor_limits() -> None:
    manifest = SourceManifest.from_path(ROOT / "knowledge/source-manifest.yml")
    catalog = MachineCatalog.from_path(ROOT / "knowledge/machine-catalog.yml")

    epa = next(
        item for item in manifest.sources if item.source_id == "us-epa-plastics-advanced-recycling"
    )
    assert epa.authority_tier == "primary"
    assert epa.access_mode == "web"
    europe_pmc = next(
        item for item in manifest.sources if item.source_id == "pmc-paper-recycling-review"
    )
    assert europe_pmc.access_mode == "api"
    assert any(item.source_id == "eu-clp-regulation-1272-2008" for item in manifest.sources)
    assert any(item.brand == "EREMA" for item in catalog.profiles)
    context, cards = catalog.context_for_query("wet LDPE film extrusion pelletizing")
    assert "vendor-reported" in context.casefold()
    assert cards


def test_xml_full_text_sources_are_extractable_without_raw_markup() -> None:
    text, content_type = _extract_content(
        b"<article><title>Polymer recovery</title><p>Separate by composition.</p></article>",
        "application/xml",
        "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC123/fullTextXML",
    )

    assert content_type == "application/xml"
    assert "Polymer recovery" in text
    assert "Separate by composition." in text
    assert "<article>" not in text


def test_knowledge_catalog_export_contains_hashes_not_raw_source_text(tmp_path: Path) -> None:
    database = KnowledgeDatabase(tmp_path / "knowledge.db")
    source = SourceSpec(
        source_id="test-export",
        title="Export test",
        url="https://example.gov/export",
        publisher="Example public body",
        source_type="OFFICIAL_GUIDANCE",
        material_families=("plastics",),
        authority_tier="primary",
    )
    database.ingest_document(
        source,
        "A private source passage must not be copied into the portable catalog.",
        content_type="text/plain",
    )
    output = tmp_path / "catalog.json"
    database.export_catalog(output)
    exported = json.loads(output.read_text(encoding="utf-8"))
    assert exported["digest"] == database.digest()
    assert "chunks" not in exported["documents"][0]
    assert "private source passage" not in output.read_text(encoding="utf-8")


def test_catalog_records_ingestion_health_without_exporting_source_text(tmp_path: Path) -> None:
    database = KnowledgeDatabase(tmp_path / "knowledge.db")
    source = SourceSpec(
        source_id="test-health",
        title="Health test source",
        url="https://example.gov/health",
        publisher="Example public body",
        source_type="OFFICIAL_GUIDANCE",
        material_families=("plastics",),
        authority_tier="primary",
    )
    result = database.ingest_document(source, "Searchable passage.", content_type="text/plain")
    database.quarantine_documents((result.document_id,), reason="access-challenge")
    database.record_run(
        source.source_id,
        "failed",
        "Source returned an access challenge instead of its content.",
        "2026-08-11T00:00:00Z",
        "2026-08-11T00:00:01Z",
    )

    summary = database.ingestion_summary()
    assert summary["documents"]["byExtractionStatus"] == {"blocked:access-challenge": 1}
    assert summary["chunks"]["total"] == 1
    assert summary["chunks"]["searchable"] == 0
    assert summary["retrieval"]["latestExtractedSources"] == 0
    assert summary["retrieval"]["sourcesWithBlockedLatestDocument"] == 1
    assert summary["retrieval"]["sourcesWithoutLatestDocument"] == 0
    assert summary["runs"]["byOutcome"] == {"failed": 1}
    assert summary["runs"]["failures"][0]["sourceId"] == source.source_id

    database.record_run(
        source.source_id,
        "ingested",
        "recovered-content-sha256",
        "2026-08-11T00:01:00Z",
        "2026-08-11T00:01:01Z",
    )
    assert database.ingestion_summary()["runs"]["failures"] == []

    output = tmp_path / "catalog.json"
    summary = database.ingestion_summary()
    database.export_catalog(output)
    exported = json.loads(output.read_text(encoding="utf-8"))
    assert exported["ingestion"] == summary
    assert "Searchable passage" not in output.read_text(encoding="utf-8")
    assert exported["documents"][0]["extractionStatus"] == "blocked:access-challenge"
    assert exported["documents"][0]["contentSha256"]


def test_source_digest_adds_linked_notes_without_rewriting_sources(tmp_path: Path) -> None:
    class FakeRouter:
        def complete_json(self, messages: list[dict[str, str]], **_: Any) -> dict[str, Any]:
            assert "<source_passage>" in messages[0]["content"]
            return {
                "notes": [
                    {
                        "summary": "The source describes a conditional route.",
                        "applicability": "Only within the source's stated process conditions.",
                        "limitations": "It does not establish a route for an unknown local batch.",
                    }
                ]
            }

    database = KnowledgeDatabase(tmp_path / "knowledge.db")
    source = SourceSpec(
        source_id="test-source-digest",
        title="Source digest test source",
        url="https://example.gov/source-digest",
        publisher="Example public body",
        source_type="OFFICIAL_GUIDANCE",
        material_families=("plastics",),
        authority_tier="primary",
    )
    database.ingest_document(
        source,
        "A conditional route is described only for a defined process condition.",
        content_type="text/plain",
    )
    run = SourceDigest(FakeRouter(), SkillRegistry.from_repository(ROOT)).run(database)
    assert run.notes_added == 1
    notes = database.source_note_catalog()
    assert len(notes) == 1
    assert notes[0]["summary"] == "The source describes a conditional route."


def test_hybrid_search_fuses_semantic_results_and_reports_mode(tmp_path: Path) -> None:
    database = KnowledgeDatabase(tmp_path / "knowledge.db")
    plastic = SourceSpec(
        source_id="test-hybrid-plastics",
        title="Hybrid plastics guide",
        url="https://example.gov/hybrid-plastics",
        publisher="Example public body",
        source_type="OFFICIAL_GUIDANCE",
        material_families=("plastics",),
        license_note="Synthetic test source",
    )
    metal = SourceSpec(
        source_id="test-hybrid-metals",
        title="Hybrid metals guide",
        url="https://example.gov/hybrid-metals",
        publisher="Example public body",
        source_type="OFFICIAL_GUIDANCE",
        material_families=("metals",),
        license_note="Synthetic test source",
    )
    plastic_doc = database.ingest_document(
        plastic,
        "Polymer film needs moisture and contamination checks before reprocessing.",
        content_type="text/plain",
    )
    metal_doc = database.ingest_document(
        metal,
        "Copper cable needs representative sampling and output qualification.",
        content_type="text/plain",
    )
    database.set_embeddings(plastic_doc.document_id, [[1.0, 0.0]], "test-embed")
    database.set_embeddings(metal_doc.document_id, [[0.0, 1.0]], "test-embed")

    results = database.hybrid_search(
        "feedstock wetness",
        query_embedding=[1.0, 0.0],
        limit=1,
    )

    assert results[0].source_id == plastic.source_id
    assert results[0].retrieval_mode == "hybrid"
    assert results[0].to_dict()["retrievalMode"] == "hybrid"


def test_embedding_repair_runs_for_existing_document_when_fetch_fails(tmp_path: Path) -> None:
    database = KnowledgeDatabase(tmp_path / "knowledge.db")
    source = SourceSpec(
        source_id="test-embedding-repair",
        title="Embedding repair source",
        url="https://example.gov/repair",
        publisher="Example public body",
        source_type="OFFICIAL_GUIDANCE",
        material_families=("plastics",),
        license_note="Synthetic test source",
    )
    document = database.ingest_document(
        source,
        "An existing extracted passage can be embedded without another download.",
        content_type="text/plain",
    )

    class FakeProvider:
        model = "fake-embedding"

        def embed(self, texts: list[str]) -> list[list[float]]:
            return [[float(len(text)), 1.0] for text in texts]

    class FailingFetcher:
        def fetch(self, _source: SourceSpec) -> tuple[str, str, str]:
            raise SourceFetchError("manual test fetch failure")

    manifest = SourceManifest((source,), frozenset({"example.gov"}))
    ingest_manifest(
        manifest,
        database,
        fetcher=FailingFetcher(),
        embedding_provider=FakeProvider(),
    )

    assert database.chunks_missing_embeddings(document.document_id, "fake-embedding") == []
    assert database.ingestion_summary()["retrieval"]["latestEmbeddedChunks"] == 1
