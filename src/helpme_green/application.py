from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .conversation import ConversationAgent
from .expert_skills import SkillRegistry
from .knowledge import KnowledgeBase
from .knowledge_store import KnowledgeDatabase, SourceSpec
from .machinery import MachineCatalog
from .mcp import ReadOnlyMCP
from .model_gateway import ModelRouter, ProviderUnavailable
from .persistence import SecretStore, SessionState, SessionStore
from .source_ingest import (
    SourceManifest,
    embedding_provider_from_environment,
    reranker_from_environment,
)


def _environment_enabled(name: str) -> bool:
    return os.environ.get(name, "").casefold() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ApplicationResponse:
    text: str
    data: dict[str, Any] | None = None
    error: str | None = None


class ApplicationProcessor:
    """Conversation and reference services for the local application.

    The public runtime contains conversation and reference services. Source provenance, retrieval
    metadata, and quality flags remain internal service data; they are not a user workflow.
    """

    def __init__(
        self,
        knowledge: KnowledgeBase,
        store: SessionStore,
        *,
        mcp: ReadOnlyMCP | None = None,
        secret_store: SecretStore | None = None,
    ) -> None:
        self.knowledge = knowledge
        self.store = store
        key_provider = secret_store.get if secret_store is not None else None
        self.model_router = ModelRouter(key_provider=key_provider)
        self.skill_registry = SkillRegistry.from_repository(knowledge.root)
        self.machine_catalog = MachineCatalog.from_path(
            knowledge.root / "knowledge/machine-catalog.yml"
        )
        database_path = Path(
            os.environ.get("HELPME_KNOWLEDGE_DB", str(store.root / "knowledge.db"))
        )
        self.knowledge_db = KnowledgeDatabase(database_path)
        self._register_source_catalog(knowledge)
        self.store.knowledge_digest = self._runtime_knowledge_digest()
        self.query_embedding_provider = (
            embedding_provider_from_environment()
            if _environment_enabled("HELPME_EMBEDDING_QUERY_ENABLED")
            else None
        )
        self.reranker = reranker_from_environment()
        self.conversation = ConversationAgent(
            self.model_router,
            store,
            skill_registry=self.skill_registry,
            knowledge_db=self.knowledge_db,
            machine_catalog=self.machine_catalog,
            embedding_provider=self.query_embedding_provider,
            reranker=self.reranker,
        )
        self.mcp = mcp or ReadOnlyMCP(file_roots=(knowledge.root, store.root))

    def _runtime_knowledge_digest(self) -> str:
        return f"{self.knowledge.digest}:{self.knowledge_db.digest()}"

    def _register_source_catalog(self, knowledge: KnowledgeBase) -> None:
        for record in knowledge.source_registry.values():
            try:
                self.knowledge_db.register_source(
                    SourceSpec(
                        source_id=record.source_id,
                        title=record.title,
                        url=record.url,
                        publisher=record.publisher,
                        source_type=record.source_type or "REFERENCE",
                        material_families=record.material_families,
                        jurisdiction=record.jurisdiction,
                        license_note=record.license_note,
                        limitations=record.limitations,
                        authority_tier=record.authority_tier,
                        scale=record.scale,
                    ),
                    status="catalogued",
                )
            except ValueError:
                continue

        manifest_path = knowledge.root / "knowledge/source-manifest.yml"
        if not manifest_path.exists():
            return
        manifest = SourceManifest.from_path(manifest_path)
        missing = self.machine_catalog.missing_source_ids(
            source.source_id for source in manifest.sources
        )
        if missing:
            raise ValueError(
                "Machine catalog references sources missing from the source manifest: "
                + ", ".join(missing)
            )
        for source in manifest.sources:
            self.knowledge_db.register_source(source, status="catalogued")

    def respond_to_message(self, session: SessionState, message: str) -> ApplicationResponse:
        self.store.knowledge_digest = self._runtime_knowledge_digest()
        try:
            session_selection = self.model_router.selection_for(session.model_identity)
            model_selection = (
                session_selection
                if session_selection.identity != self.model_router.selection.identity
                else None
            )
            result = self.conversation.respond(session, message, model_selection=model_selection)
        except (ProviderUnavailable, ValueError) as exc:
            return ApplicationResponse(
                text="I couldn’t answer that right now. Please try again when the local assistant is available.",
                data={"model": session.model_identity, "ai_used": False},
                error=str(exc),
            )
        return ApplicationResponse(result.text, result.to_data())
