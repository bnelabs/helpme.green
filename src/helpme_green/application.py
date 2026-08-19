from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .config import RetrievalEnvironment, RuntimePaths
from .conversation import ConversationAgent
from .expert_skills import SkillRegistry
from .kb_service import KbService, kb_config_from_environment
from .knowledge import KnowledgeBase
from .knowledge_store import KnowledgeDatabase, SourceSpec
from .machinery import MachineCatalog
from .mcp import ReadOnlyMCP
from .model_gateway import ModelRouter, ProviderUnavailable
from .observability import MetricsRegistry
from .persistence import SecretStore, SessionState, SessionStore
from .prompt_artifacts import PromptArtifactStore, prompt_artifacts_enabled
from .settings import RuntimeSettingsStore
from .source_ingest import (
    SourceManifest,
    embedding_provider_from_environment,
    reranker_from_environment,
)


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
        self.runtime_paths = RuntimePaths.from_environment()
        self.settings = RuntimeSettingsStore(store.root, secret_store=secret_store)
        if prompt_artifacts_enabled() and secret_store is None:
            raise ValueError(
                "HELPME_PROMPT_ARTIFACTS_ENABLED requires HELPME_MASTER_KEY for encrypted storage."
            )
        self.prompt_artifacts = (
            PromptArtifactStore(store.root / "prompt-artifacts", secret_store=secret_store)
            if prompt_artifacts_enabled() and secret_store is not None
            else None
        )
        self.metrics = MetricsRegistry.from_environment()
        self.model_router = ModelRouter(
            key_provider=self.settings.get_api_key,
            metrics=self.metrics,
            environment=self.settings.environment,
        )
        self.model_router.configure(self.settings.runtime())
        self.skill_registry = SkillRegistry.from_repository(knowledge.root)
        self.machine_catalog = MachineCatalog.from_path(
            knowledge.root / "knowledge/machine-catalog.yml"
        )
        database_path = self.runtime_paths.database_path(store.root)
        self.knowledge_db = KnowledgeDatabase(database_path)
        self._register_source_catalog(knowledge)
        self.store.knowledge_digest = self._runtime_knowledge_digest()
        self.retrieval_environment = RetrievalEnvironment.from_environment()
        self.query_embedding_provider = (
            embedding_provider_from_environment(self.retrieval_environment)
            if self.retrieval_environment.embedding_query_enabled
            else None
        )
        self.reranker = reranker_from_environment(self.retrieval_environment)
        self.kb_service = KbService(
            self.knowledge_db,
            store,
            config=kb_config_from_environment(store.root),
            embedding_provider=self.query_embedding_provider,
            digest_router=self.model_router,
            digest_skills=self.skill_registry,
        )
        self.conversation = ConversationAgent(
            self.model_router,
            store,
            prompt_artifacts=self.prompt_artifacts,
            skill_registry=self.skill_registry,
            knowledge_db=self.knowledge_db,
            machine_catalog=self.machine_catalog,
            embedding_provider=self.query_embedding_provider,
            reranker=self.reranker,
        )
        self.mcp = mcp or ReadOnlyMCP(file_roots=(knowledge.root, store.root))

    def runtime_settings(self) -> dict[str, Any]:
        return self.settings.public()

    def update_runtime_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.settings.update(payload)
        self.model_router.configure(self.settings.runtime())
        return result

    def current_model_identity(self) -> str:
        return self.model_router.selection.identity

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

    def respond_to_message(
        self,
        session: SessionState,
        message: str,
        *,
        images: Sequence[Mapping[str, str]] | None = None,
    ) -> ApplicationResponse:
        self.store.knowledge_digest = self._runtime_knowledge_digest()
        try:
            session_selection = self.model_router.selection_for(session.model_identity)
            model_selection = (
                session_selection
                if session_selection.identity != self.model_router.selection.identity
                else None
            )
            result = self.conversation.respond(
                session,
                message,
                model_selection=model_selection,
                images=images,
            )
        except (ProviderUnavailable, ValueError) as exc:
            return ApplicationResponse(
                text="I couldn’t answer that right now. Please try again when the local assistant is available.",
                data={"model": session.model_identity, "ai_used": False},
                error=str(exc),
            )
        return ApplicationResponse(result.text, result.to_data())
