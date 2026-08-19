from __future__ import annotations

import io
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from helpme_green.application import ApplicationProcessor
from helpme_green.compaction import (
    ContextCompactionError,
    compact_until_fit,
    estimate_request_tokens,
)
from helpme_green.conversation import ConversationAgent
from helpme_green.expert_skills import SkillRegistry
from helpme_green.knowledge import KnowledgeBase
from helpme_green.mcp import ReadOnlyMCP, ReadOnlyViolation
from helpme_green.model_gateway import ModelRouter, ModelSelection, ProviderUnavailable
from helpme_green.persistence import SecretStore, SessionEventError, SessionState, SessionStore
from helpme_green.prompt_artifacts import PromptArtifactReference, PromptArtifactStore
from helpme_green.settings import RuntimeSettingsStore, SettingsError
from helpme_green.source_ingest import embedding_provider_from_environment

ROOT = Path(__file__).resolve().parents[1]


def test_source_catalog_is_the_runtime_knowledge_identity() -> None:
    knowledge = KnowledgeBase.from_repository(ROOT)

    assert len(knowledge.source_registry) > 20
    assert knowledge.digest
    assert knowledge.source_registry["us-epa-plastics-data"].material_families == ("plastics",)


def test_session_persistence_and_snapshots_store_conversation_not_internal_records(
    tmp_path: Path,
) -> None:
    store = SessionStore(tmp_path / "data", knowledge_digest="digest-v1")
    session = SessionState.new(topic="rubber", geography="EU")
    session.conversation.append({"role": "user", "content": "I have rubber"})
    store.save_session(session)

    snapshot_id = store.create_snapshot(session)
    resumed = store.load_session(session.session_id)
    restored = store.load_snapshot(snapshot_id, session_id=session.session_id)

    assert resumed.to_dict() == session.to_dict()
    assert restored.to_dict() == session.to_dict()
    assert "material" not in resumed.to_dict()
    assert store.verify_audit_chain()


def test_session_events_retain_full_history_and_rebuild_projection(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "data", knowledge_digest="digest-v1")
    session = SessionState.new(topic="rubber", geography="EU")
    store.save_session(session)

    for index in range(30):
        user = f"Observation {index}"
        assistant = f"Response {index}"
        session.event_seq = store.append_session_event(
            session.session_id,
            "conversation.turn",
            {"user": user, "assistant": assistant, "understanding": {}},
        )
        session.conversation.extend(
            [{"role": "user", "content": user}, {"role": "assistant", "content": assistant}]
        )
        session.working_context.extend(
            [{"role": "user", "content": user}, {"role": "assistant", "content": assistant}]
        )
    store.save_session(session)

    resumed = store.load_session(session.session_id)

    assert len(resumed.conversation) == 60
    assert len(resumed.working_context) == 60
    assert resumed.event_seq == 31
    assert len(store.load_session_events(session.session_id)) == 31


def test_session_event_log_rejects_unknown_events_and_torn_tails(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "data", knowledge_digest="digest-v1")
    session = SessionState.new(topic="", geography="")
    store.save_session(session)

    with pytest.raises(SessionEventError):
        store.append_session_event(session.session_id, "unknown.required", {})

    events_path = store.session_events_path(session.session_id)
    with events_path.open("ab") as handle:
        handle.write(b'{"incomplete":')
    with pytest.raises(SessionEventError):
        store.load_session_events(session.session_id)


def test_compaction_repeats_to_ceiling_without_mutating_source_messages() -> None:
    messages = [
        {
            "role": "user" if index % 2 == 0 else "assistant",
            "content": f"Turn {index}: " + ("detail " * 35),
        }
        for index in range(20)
    ]

    def staged_measure(_system: str, messages: Sequence[Mapping[str, str]]) -> int:
        summary_count = sum(
            item.get("content", "").count("Earlier conversation") for item in messages
        )
        return 900 if summary_count == 0 else 800 if summary_count == 1 else 600

    compacted, passes = compact_until_fit(
        messages,
        "What should I check next?",
        system_contract="Answer clearly.",
        ceiling=700,
        minimum_tail_messages=2,
        measure=staged_measure,
    )

    assert len(passes) >= 2
    assert (
        staged_measure(
            "Answer clearly.",
            [*compacted, {"role": "user", "content": "What should I check next?"}],
        )
        <= 700
    )
    assert len(messages) == 20
    assert any("Earlier conversation" in item["content"] for item in compacted)

    with pytest.raises(ContextCompactionError):
        compact_until_fit(
            [],
            "x" * 5000,
            system_contract="Answer clearly.",
            ceiling=700,
        )


def test_conversation_keeps_full_history_and_hides_internal_result_metadata(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HELPME_AI_ENABLED", "1")
    monkeypatch.setenv("HELPME_QUALITY_JUDGES", "0")
    monkeypatch.delenv("HELPME_MODEL_PROFILES", raising=False)
    store = SessionStore(tmp_path / "data", knowledge_digest="digest-v1")
    router = ModelRouter(ModelSelection("localai", "test-model"))
    router.complete_json = lambda messages, **kwargs: {
        "reply": "A careful next step is to inspect the sample.",
        "hearing": {"subject": "sample", "situation": "", "aim": ""},
    }
    agent = ConversationAgent(
        router,
        store,
        skill_registry=SkillRegistry.from_repository(ROOT),
    )
    session = SessionState.new(topic="", geography="")
    store.save_session(session)

    for index in range(15):
        result = agent.respond(session, f"I have observation {index}")

    resumed = store.load_session(session.session_id)
    event_types = [
        str(item["event_type"]) for item in store.load_session_events(session.session_id)
    ]

    assert len(resumed.conversation) == 30
    assert event_types.count("model.attempt") == 15
    assert event_types.count("conversation.turn") == 15
    assert "Models can make mistakes" in result.text
    assert result.to_data().keys() == {"hearing", "sources", "model", "ai_used"}


def test_conversation_compacts_working_context_at_profile_ceiling(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HELPME_AI_ENABLED", "1")
    monkeypatch.setenv("HELPME_QUALITY_JUDGES", "0")
    monkeypatch.setenv(
        "HELPME_MODEL_PROFILES",
        json.dumps({"localai:test-model": {"context_window": 1800}}),
    )
    store = SessionStore(tmp_path / "data", knowledge_digest="digest-v1")
    router = ModelRouter(ModelSelection("localai", "test-model"))
    captured_messages: list[dict[str, str]] = []
    captured_system: list[str] = []

    def fake_complete_json(messages, **kwargs):
        captured_messages.extend(dict(item) for item in messages)
        captured_system.append(str(kwargs["system_contract"]))
        return {"reply": "A short answer.", "hearing": {}}

    router.complete_json = fake_complete_json
    agent = ConversationAgent(
        router,
        store,
        skill_registry=SkillRegistry.from_repository(ROOT),
    )
    session = SessionState.new(topic="", geography="")
    store.save_session(session)
    for index in range(12):
        user = f"Old user turn {index} " + ("detail " * 50)
        assistant = f"Old assistant turn {index} " + ("answer " * 50)
        session.event_seq = store.append_session_event(
            session.session_id,
            "conversation.turn",
            {"user": user, "assistant": assistant, "understanding": {}},
        )
        session.conversation.extend(
            [{"role": "user", "content": user}, {"role": "assistant", "content": assistant}]
        )
        session.working_context.extend(
            [
                {"role": "user", "content": user},
                {"role": "assistant", "content": assistant},
            ]
        )
    store.save_session(session)

    agent.respond(session, "What should I inspect next?")

    events = store.load_session_events(session.session_id)
    resumed = store.load_session(session.session_id)
    assert any(item["event_type"] == "context.compacted" for item in events)
    assert estimate_request_tokens(captured_system[0], captured_messages) <= 1440
    assert len(resumed.conversation) == 26
    assert len(resumed.working_context) < len(resumed.conversation)


def test_context_overflow_retries_after_an_additional_safe_compaction(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HELPME_AI_ENABLED", "1")
    monkeypatch.setenv("HELPME_QUALITY_JUDGES", "0")
    monkeypatch.setenv(
        "HELPME_MODEL_PROFILES",
        json.dumps({"localai:test-model": {"context_window": 2200}}),
    )
    store = SessionStore(tmp_path / "data", knowledge_digest="digest-v1")
    router = ModelRouter(ModelSelection("localai", "test-model"))
    calls = 0
    captured: list[list[dict[str, str]]] = []

    def fake_complete_json(messages, **kwargs):
        nonlocal calls
        del kwargs
        calls += 1
        captured.append([dict(item) for item in messages])
        if calls == 1:
            raise ProviderUnavailable("context overflow", code="context_window_exceeded")
        return {"reply": "A shorter context now fits.", "hearing": {}}

    router.complete_json = fake_complete_json
    agent = ConversationAgent(
        router,
        store,
        skill_registry=SkillRegistry.from_repository(ROOT),
    )
    session = SessionState.new(topic="", geography="")
    store.save_session(session)
    for index in range(12):
        user = f"Old user turn {index} " + ("detail " * 50)
        assistant = f"Old assistant turn {index} " + ("answer " * 50)
        session.event_seq = store.append_session_event(
            session.session_id,
            "conversation.turn",
            {"user": user, "assistant": assistant, "understanding": {}},
        )
        session.conversation.extend(
            [{"role": "user", "content": user}, {"role": "assistant", "content": assistant}]
        )
        session.working_context.extend(
            [
                {"role": "user", "content": user},
                {"role": "assistant", "content": assistant},
            ]
        )
    store.save_session(session)

    result = agent.respond(session, "What should I inspect next?")

    events = store.load_session_events(session.session_id)
    assert result.text.startswith("A shorter context now fits.")
    assert "Models can make mistakes" in result.text
    assert calls == 2
    assert sum(item["event_type"] == "model.attempt" for item in events) == 2
    assert sum(item["event_type"] == "context.compacted" for item in events) >= 2
    assert len(captured[-1]) < len(captured[0])


def test_read_only_import_returns_untrusted_records_without_execution(tmp_path: Path) -> None:
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps({"material": "rubber"}), encoding="utf-8")
    mcp = ReadOnlyMCP(file_roots=(tmp_path,))

    records = mcp.load(input_path)

    assert records[0].key == "material"
    assert records[0].value == "rubber"
    assert records[0].untrusted
    try:
        mcp.execute("anything")
    except ReadOnlyViolation:
        pass
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("read-only imports must not execute commands")


def test_byok_is_encrypted_and_not_present_as_plaintext(tmp_path: Path) -> None:
    secret = "provider-secret-that-must-not-be-logged"
    store = SecretStore(tmp_path / "secrets", master_key=Fernet.generate_key())

    store.set("provider", secret)
    raw = (tmp_path / "secrets" / "provider.json").read_text(encoding="utf-8")

    assert secret not in raw
    assert store.get("provider") == secret


def test_prompt_artifacts_are_encrypted_and_survive_master_key_rotation(tmp_path: Path) -> None:
    old_key = Fernet.generate_key()
    new_key = Fernet.generate_key()
    secrets = SecretStore(tmp_path / "secrets", master_key=old_key)
    artifacts = PromptArtifactStore(tmp_path / "prompt-artifacts", secret_store=secrets)
    session_id = str(uuid.uuid4())
    envelope = {
        "schema_version": 1,
        "kind": "model_prompt_envelope",
        "session_id": session_id,
        "attempt": 1,
        "system_contract": "PRIVATE_PROMPT_MARKER",
        "messages": [{"role": "user", "content": "I have rubber."}],
        "images": [],
        "raw_image_bytes_stored": False,
    }

    reference = artifacts.write(session_id, 1, envelope)
    stored_bytes = b"".join(
        path.read_bytes() for path in (tmp_path / "prompt-artifacts").rglob("*.json")
    )
    assert b"PRIVATE_PROMPT_MARKER" not in stored_bytes
    assert artifacts.read(session_id, reference) == envelope

    secrets.rotate_master_key(new_key)
    rotated = SecretStore(tmp_path / "secrets", master_key=new_key)
    assert (
        PromptArtifactStore(tmp_path / "prompt-artifacts", secret_store=rotated).read(
            session_id, reference
        )
        == envelope
    )


def test_prompt_artifact_capture_is_opt_in_and_kept_out_of_session_events(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HELPME_PROMPT_ARTIFACTS_ENABLED", "1")
    monkeypatch.setenv("HELPME_AI_ENABLED", "1")
    monkeypatch.setenv("HELPME_QUALITY_JUDGES", "0")
    monkeypatch.setenv("HELPME_MODEL", "localai:test-model")
    knowledge = KnowledgeBase.from_repository(ROOT)
    store = SessionStore(tmp_path / "data", knowledge_digest=knowledge.digest)
    secrets = SecretStore(tmp_path / "secrets", master_key=Fernet.generate_key())
    processor = ApplicationProcessor(knowledge, store, secret_store=secrets)
    processor.model_router.complete_json = lambda messages, **kwargs: {
        "reply": "The sample needs one more detail.",
        "hearing": {"subject": "rubber", "situation": "", "aim": ""},
    }
    session = SessionState.new(topic="", geography="")
    store.save_session(session)

    result = processor.respond_to_message(
        session,
        "PRIVATE_PROMPT_MARKER: I have rubber.",
        images=[{"mime_type": "image/png", "data": "PRIVATE_IMAGE_BYTES"}],
    )

    events = store.load_session_events(session.session_id)
    attempt = next(item for item in events if item["event_type"] == "model.attempt")
    reference = attempt["payload"]["prompt_artifact"]
    assert "PRIVATE_PROMPT_MARKER" not in json.dumps(attempt)
    assert "prompt_artifact" not in json.dumps(result.data or {})
    assert processor.prompt_artifacts is not None
    envelope = processor.prompt_artifacts.read(
        session.session_id,
        PromptArtifactReference.from_dict(reference),
    )
    assert envelope["kind"] == "model_prompt_envelope"
    assert "PRIVATE_PROMPT_MARKER" in envelope["messages"][-1]["content"]
    assert "PRIVATE_IMAGE_BYTES" not in json.dumps(envelope)
    assert envelope["images"][0]["encoded_length"] == len("PRIVATE_IMAGE_BYTES")
    assert envelope["raw_image_bytes_stored"] is False


def test_prompt_artifacts_require_encrypted_storage(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HELPME_PROMPT_ARTIFACTS_ENABLED", "1")
    monkeypatch.delenv("HELPME_MASTER_KEY", raising=False)
    knowledge = KnowledgeBase.from_repository(ROOT)
    store = SessionStore(tmp_path / "data", knowledge_digest=knowledge.digest)

    with pytest.raises(ValueError, match="HELPME_MASTER_KEY"):
        ApplicationProcessor(knowledge, store)


def test_audit_chain_detects_tampering(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "data", knowledge_digest="digest-v1")
    session = SessionState.new(topic="", geography="")
    store.save_session(session)

    record = json.loads(store.audit_path.read_text(encoding="utf-8").splitlines()[0])
    record["event_type"] = "tampered"
    store.audit_path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    assert not store.verify_audit_chain()


def test_empty_session_retention_keeps_nonempty_sessions(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "data", knowledge_digest="digest-v1")
    empty = SessionState.new(topic="", geography="")
    nonempty = SessionState.new(topic="", geography="")
    nonempty.conversation.append({"role": "user", "content": "Keep this"})
    store.save_session(empty)
    store.save_session(nonempty)
    old = 1.0
    os.utime(store.session_path(empty.session_id), (old, old))
    os.utime(store.session_path(nonempty.session_id), (old, old))

    assert store.prune_empty_sessions(max_age_seconds=60) == 1
    assert not store.session_path(empty.session_id).exists()
    assert store.load_session(nonempty.session_id).conversation[0]["content"] == "Keep this"


def test_snapshot_retention_keeps_newest_snapshots(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "data", knowledge_digest="digest-v1")
    session = SessionState.new(topic="", geography="")
    session.conversation.append({"role": "user", "content": "Keep snapshots"})
    store.save_session(session)
    snapshot_ids = [str(uuid.uuid4()) for _ in range(3)]
    for index, snapshot_id in enumerate(snapshot_ids):
        store.create_snapshot(session, snapshot_id=snapshot_id)
        snapshot_path = store.root / "snapshots" / session.session_id / f"{snapshot_id}.json"
        os.utime(snapshot_path, (100 + index, 100 + index))

    assert store.prune_snapshots(session.session_id, max_per_session=2) == 1
    assert not (store.root / "snapshots" / session.session_id / f"{snapshot_ids[0]}.json").exists()
    assert store.load_snapshot(snapshot_ids[2], session_id=session.session_id).conversation


def test_snapshot_creation_does_not_prune_by_default(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "data", knowledge_digest="digest-v1")
    session = SessionState.new(topic="", geography="")
    store.save_session(session)
    snapshot_ids = [str(uuid.uuid4()) for _ in range(21)]

    for snapshot_id in snapshot_ids:
        store.create_snapshot(session, snapshot_id=snapshot_id)

    snapshot_dir = store.root / "snapshots" / session.session_id
    assert len(list(snapshot_dir.glob("*.json"))) == len(snapshot_ids)


def test_byok_master_key_rotation_reencrypts_existing_keys(tmp_path: Path) -> None:
    old_key = Fernet.generate_key()
    new_key = Fernet.generate_key()
    store = SecretStore(tmp_path / "secrets", master_key=old_key)
    store.set("provider", "secret-value")

    store.rotate_master_key(new_key)

    assert store.get("provider") == "secret-value"
    assert SecretStore(tmp_path / "secrets", master_key=new_key).get("provider") == "secret-value"
    with pytest.raises(ValueError):
        SecretStore(tmp_path / "secrets", master_key=old_key).get("provider")


def test_runtime_settings_keep_api_keys_encrypted_and_restore_model_profile(
    tmp_path: Path, monkeypatch
) -> None:
    for name in (
        "HELPME_MODEL",
        "HELPME_PROVIDER",
        "HELPME_MODEL_PROFILES",
        "HELPME_AI_ENABLED",
        "HELPME_LOCALAI_BASE_URL",
        "OPENROUTER_API_KEY",
        "DEEPSEEK_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    secret = "openrouter-secret-that-must-not-leak"
    secrets = SecretStore(tmp_path / "secrets", master_key=Fernet.generate_key())
    settings = RuntimeSettingsStore(tmp_path / "data", secret_store=secrets)

    public = settings.update(
        {
            "provider": "openrouter",
            "model": "example/model",
            "ai_enabled": True,
            "model_retries": 0,
            "profile": {
                "vision": True,
                "temperature": 0.4,
                "max_tokens": 1200,
                "chat_template_kwargs": {"reasoning_strength": "high"},
            },
            "api_key": secret,
        }
    )

    raw_settings = (tmp_path / "data" / "settings.json").read_text(encoding="utf-8")
    raw_secret = (tmp_path / "secrets" / "provider_api_key_openrouter.json").read_text(
        encoding="utf-8"
    )
    assert public["identity"] == "openrouter:example/model"
    assert public["profile"]["vision"] is True
    assert public["api_keys"]["openrouter"] == {"configured": True, "source": "encrypted"}
    assert secret not in raw_settings
    assert secret not in raw_secret
    assert secret not in json.dumps(public)

    restored = RuntimeSettingsStore(tmp_path / "data", secret_store=secrets)
    assert restored.get_api_key("openrouter") == secret
    assert restored.public()["profile"]["max_tokens"] == 1200

    with pytest.raises(SettingsError, match="protected request fields"):
        settings.update({"profile": {"messages": "not allowed"}})


def test_model_router_applies_saved_runtime_options_without_environment_mutation(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("HELPME_MODEL_PROFILES", raising=False)
    captured: list[dict[str, object]] = []

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            del args

        def read(self) -> bytes:
            return json.dumps(
                {"choices": [{"message": {"content": '{"reply":"Configured."}'}}], "usage": {}}
            ).encode("utf-8")

    def fake_urlopen(request, timeout, context=None):
        del timeout, context
        captured.append(json.loads(request.data.decode("utf-8")))
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    router = ModelRouter(ModelSelection("localai", "old-model"))
    router.configure(
        {
            "identity": "openrouter:configured/model",
            "ai_enabled": True,
            "model_retries": 0,
            "max_model_timeout_seconds": 42,
            "profiles": {
                "openrouter:configured/model": {
                    "temperature": 0.4,
                    "top_p": 0.8,
                    "max_tokens": 1200,
                    "vision": True,
                }
            },
        }
    )

    assert router.complete_json([], system_contract="Return JSON.") == {"reply": "Configured."}
    assert router.selection.identity == "openrouter:configured/model"
    assert captured[0]["model"] == "configured/model"
    assert captured[0]["temperature"] == 0.4
    assert captured[0]["top_p"] == 0.8
    assert captured[0]["max_tokens"] == 1200


def test_auto_model_resolution_does_not_mutate_shared_selection(monkeypatch) -> None:
    router = ModelRouter(ModelSelection("localai", "auto"))
    monkeypatch.setattr(router, "_discover_localai_models", lambda: ["resolved-model"])

    resolved = router.resolve_selection()

    assert resolved.identity == "localai:resolved-model"
    assert router.selection.identity == "localai:auto"


def test_localai_gateway_omits_output_cap_without_a_model_profile(monkeypatch) -> None:
    monkeypatch.setenv("HELPME_AI_ENABLED", "1")
    monkeypatch.setenv("HELPME_LOCALAI_BASE_URL", "http://127.0.0.1:8090/v1")
    monkeypatch.delenv("HELPME_MODEL_PROFILES", raising=False)
    captured: list[dict[str, object]] = []

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            del args

        def read(self) -> bytes:
            return json.dumps(
                {"choices": [{"message": {"content": '{"reply":"Noted."}'}}], "usage": {}}
            ).encode("utf-8")

    def fake_urlopen(request, timeout, context=None):
        del timeout, context
        captured.append(json.loads(request.data.decode("utf-8")))
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    router = ModelRouter(ModelSelection("localai", "unprofiled-model"))

    assert router.complete_json([], system_contract="Return JSON.") == {"reply": "Noted."}
    assert "max_tokens" not in captured[0]


def test_model_gateway_attaches_configured_vision_images(monkeypatch) -> None:
    monkeypatch.setenv("HELPME_AI_ENABLED", "1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv(
        "HELPME_MODEL_PROFILES",
        json.dumps({"openrouter:vision-model": {"vision": True, "max_tokens": 900}}),
    )
    captured: list[dict[str, object]] = []

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            del args

        def read(self) -> bytes:
            return json.dumps(
                {"choices": [{"message": {"content": '{"reply":"I can see it."}'}}], "usage": {}}
            ).encode("utf-8")

    def fake_urlopen(request, timeout, context=None):
        del timeout, context
        captured.append(json.loads(request.data.decode("utf-8")))
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    router = ModelRouter(ModelSelection("openrouter", "vision-model"))

    assert router.complete_json(
        [{"role": "user", "content": "Describe this image."}],
        system_contract="Return JSON.",
        images=[{"mime_type": "image/png", "data": "aGVsbG8="}],
    ) == {"reply": "I can see it."}

    user_content = captured[0]["messages"][-1]["content"]
    assert isinstance(user_content, list)
    assert user_content[0] == {"type": "text", "text": "Describe this image."}
    assert user_content[1] == {
        "type": "image_url",
        "image_url": {"url": "data:image/png;base64,aGVsbG8="},
    }
    assert "vision" not in captured[0]
    assert captured[0]["max_tokens"] == 900


def test_model_gateway_rejects_images_without_vision_profile(monkeypatch) -> None:
    monkeypatch.setenv("HELPME_AI_ENABLED", "1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("HELPME_MODEL_PROFILES", raising=False)
    router = ModelRouter(ModelSelection("openrouter", "text-model"))

    with pytest.raises(ProviderUnavailable, match="not configured for image input"):
        router.complete_json(
            [{"role": "user", "content": "Describe this image."}],
            system_contract="Return JSON.",
            images=[{"mime_type": "image/png", "data": "aGVsbG8="}],
        )


def test_loopback_embedding_provider_can_run_without_a_provider_key(monkeypatch) -> None:
    monkeypatch.setenv("HELPME_EMBEDDING_BASE_URL", "http://127.0.0.1:8090/v1")
    monkeypatch.setenv("HELPME_EMBEDDING_MODEL", "local-embedding-model")
    monkeypatch.delenv("HELPME_EMBEDDING_API_KEY", raising=False)

    provider = embedding_provider_from_environment()

    assert provider is not None
    assert provider.model == "local-embedding-model"


def test_model_gateway_retries_one_transient_failure(monkeypatch) -> None:
    monkeypatch.setenv("HELPME_AI_ENABLED", "1")
    monkeypatch.setenv("HELPME_MODEL_RETRIES", "1")
    monkeypatch.setenv("HELPME_LOCALAI_BASE_URL", "http://127.0.0.1:8090/v1")
    calls = 0

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            del args

        def read(self) -> bytes:
            return json.dumps(
                {"choices": [{"message": {"content": '{"reply":"Recovered."}'}}], "usage": {}}
            ).encode("utf-8")

    def fake_urlopen(request, timeout, context=None):
        nonlocal calls
        del request, timeout, context
        calls += 1
        if calls == 1:
            raise urllib.error.URLError("temporary")
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    router = ModelRouter(ModelSelection("localai", "retry-model"))

    assert router.complete_json([], system_contract="Return JSON.") == {"reply": "Recovered."}
    assert calls == 2


def test_model_gateway_classifies_authentication_failures_without_retry(monkeypatch) -> None:
    monkeypatch.setenv("HELPME_AI_ENABLED", "1")
    monkeypatch.setenv("HELPME_MODEL_RETRIES", "3")
    monkeypatch.setenv("HELPME_LOCALAI_BASE_URL", "http://127.0.0.1:8090/v1")
    calls = 0

    def fake_urlopen(request, timeout, context=None):
        nonlocal calls
        del request, timeout, context
        calls += 1
        raise urllib.error.HTTPError(
            "http://127.0.0.1:8090/v1/chat/completions",
            401,
            "unauthorized",
            {},
            io.BytesIO(b"{}"),
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    router = ModelRouter(ModelSelection("localai", "auth-model"))

    with pytest.raises(ProviderUnavailable) as failure:
        router.complete_json([], system_contract="Return JSON.")

    assert failure.value.code == "authentication"
    assert calls == 1


@pytest.mark.parametrize(("retry_after", "expected_delay"), [("0", 0.0), ("2", 0.25)])
def test_model_gateway_honors_only_bounded_retry_after_hints(
    monkeypatch, retry_after: str, expected_delay: float
) -> None:
    monkeypatch.setenv("HELPME_AI_ENABLED", "1")
    monkeypatch.setenv("HELPME_MODEL_RETRIES", "1")
    monkeypatch.setenv("HELPME_LOCALAI_BASE_URL", "http://127.0.0.1:8090/v1")
    sleeps: list[float] = []

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            del args

        def read(self) -> bytes:
            return json.dumps(
                {"choices": [{"message": {"content": '{"reply":"Recovered."}'}}]}
            ).encode("utf-8")

    def fake_urlopen(request, timeout, context=None):
        del request, timeout, context
        if not sleeps:
            raise urllib.error.HTTPError(
                "http://127.0.0.1:8090/v1/chat/completions",
                503,
                "temporary",
                {"Retry-After": retry_after},
                io.BytesIO(b"{}"),
            )
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(time, "sleep", sleeps.append)
    router = ModelRouter(ModelSelection("localai", "retry-hint-model"))

    assert router.complete_json([], system_contract="Return JSON.") == {"reply": "Recovered."}
    assert sleeps == [expected_delay]


def test_model_gateway_classifies_timeout_and_empty_responses(monkeypatch) -> None:
    monkeypatch.setenv("HELPME_AI_ENABLED", "1")
    monkeypatch.setenv("HELPME_MODEL_RETRIES", "0")
    monkeypatch.setenv("HELPME_LOCALAI_BASE_URL", "http://127.0.0.1:8090/v1")
    calls = 0

    class EmptyResponse:
        def __enter__(self) -> EmptyResponse:
            return self

        def __exit__(self, *args: object) -> None:
            del args

        def read(self) -> bytes:
            return b'{"choices": []}'

    def fake_urlopen(request, timeout, context=None):
        nonlocal calls
        del request, timeout, context
        calls += 1
        if calls == 1:
            raise urllib.error.URLError(TimeoutError("timed out"))
        return EmptyResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    router = ModelRouter(ModelSelection("localai", "failure-model"))

    with pytest.raises(ProviderUnavailable) as failure:
        router.complete_json([], system_contract="Return JSON.")
    assert failure.value.code == "timeout"

    monkeypatch.setenv("HELPME_MODEL_RETRIES", "0")
    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: EmptyResponse())
    with pytest.raises(ProviderUnavailable) as empty:
        router.complete_json([], system_contract="Return JSON.")
    assert empty.value.code == "empty_response"


def test_model_profile_is_scoped_to_the_selected_model(monkeypatch) -> None:
    monkeypatch.setenv("HELPME_AI_ENABLED", "1")
    monkeypatch.setenv("HELPME_LOCALAI_BASE_URL", "http://127.0.0.1:8090/v1")
    monkeypatch.setenv(
        "HELPME_MODEL_PROFILES",
        json.dumps(
            {
                "localai:profiled-model": {
                    "temperature": 1.0,
                    "top_p": 0.95,
                    "top_k": 64,
                    "max_tokens": 16384,
                    "context_window": 32768,
                    "chat_template_kwargs": {"reasoning_strength": "xhigh"},
                }
            }
        ),
    )
    captured: list[dict[str, object]] = []

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            del args

        def read(self) -> bytes:
            return json.dumps(
                {"choices": [{"message": {"content": '{"reply":"Noted."}'}}], "usage": {}}
            ).encode("utf-8")

    def fake_urlopen(request, timeout, context=None):
        del timeout, context
        captured.append(json.loads(request.data.decode("utf-8")))
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    router = ModelRouter(ModelSelection("localai", "profiled-model"))
    assert router.context_window() == 32768
    router.complete_json([], system_contract="Return JSON.")
    router.select("localai:other-model")
    router.complete_json([], system_contract="Return JSON.")

    assert captured[0]["max_tokens"] == 16384
    assert "context_window" not in captured[0]
    assert captured[0]["chat_template_kwargs"] == {"reasoning_strength": "xhigh"}
    assert "max_tokens" not in captured[1]
    assert "chat_template_kwargs" not in captured[1]


def test_user_facing_reply_is_not_truncated() -> None:
    assert ConversationAgent._reply({"reply": "A" * 7000}) == "A" * 7000


def test_model_failure_has_a_plain_user_facing_fallback(tmp_path: Path) -> None:
    knowledge = KnowledgeBase.from_repository(ROOT)
    store = SessionStore(tmp_path / "data", knowledge_digest=knowledge.digest)
    router = ModelRouter(ModelSelection("localai", "test-model"))

    def fail_to_complete(*args, **kwargs):
        del args, kwargs
        raise ProviderUnavailable("test provider failure")

    router.complete_json = fail_to_complete
    agent = ConversationAgent(
        router,
        store,
        skill_registry=SkillRegistry.from_repository(ROOT),
    )

    result = agent.respond(SessionState.new(topic="", geography=""), "glass")

    assert (
        result.text == "I couldn’t get a response from the local model just now. Please try again."
    )
    assert "recommendation" not in result.text.casefold()
    assert "evidence" not in result.text.casefold()


def test_quality_rejection_is_classified_without_persisting_the_rejected_reply(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HELPME_AI_ENABLED", "1")
    monkeypatch.setenv("HELPME_QUALITY_JUDGES", "0")
    store = SessionStore(tmp_path / "data", knowledge_digest="digest-v1")
    router = ModelRouter(ModelSelection("localai", "test-model"))
    router.complete_json = lambda messages, **kwargs: {
        "reply": "This is guaranteed to be safe and always works.",
        "hearing": {"subject": "sample", "situation": "", "aim": ""},
    }
    agent = ConversationAgent(
        router,
        store,
        skill_registry=SkillRegistry.from_repository(ROOT),
    )
    session = SessionState.new(topic="", geography="")
    store.save_session(session)

    result = agent.respond(session, "I have a sample")

    events = store.load_session_events(session.session_id)
    failed = [item for item in events if item["event_type"] == "model.failed"]
    assert result.text == (
        "I couldn’t make that answer reliable enough to give you as written. "
        "Please try again with one more concrete detail."
    )
    assert result.ai_used is False
    assert failed[-1]["payload"]["code"] == "quality_rejected"
    assert "absolute_claim" in failed[-1]["payload"]["quality_flags"]
    assert not any(item["event_type"] == "model.completed" for item in events)
    assert not any(item["event_type"] == "conversation.turn" for item in events)
    assert session.conversation == []


@pytest.mark.parametrize("failure_path", ["save_session", "append_audit"])
def test_persistence_failure_is_classified_and_kept_out_of_the_user_surface(
    tmp_path: Path, monkeypatch, failure_path: str
) -> None:
    monkeypatch.setenv("HELPME_AI_ENABLED", "1")
    monkeypatch.setenv("HELPME_QUALITY_JUDGES", "0")
    store = SessionStore(tmp_path / "data", knowledge_digest="digest-v1")
    router = ModelRouter(ModelSelection("localai", "test-model"))
    router.complete_json = lambda messages, **kwargs: {
        "reply": "A careful next step is to inspect the sample.",
        "hearing": {"subject": "sample", "situation": "", "aim": ""},
    }
    agent = ConversationAgent(
        router,
        store,
        skill_registry=SkillRegistry.from_repository(ROOT),
    )
    session = SessionState.new(topic="", geography="")
    store.save_session(session)

    if failure_path == "save_session":

        def fail_save(_session: SessionState) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(store, "save_session", fail_save)
    else:
        original_append_audit = store.append_audit
        append_calls = 0

        def fail_append_audit(session_id, event_type, payload):
            nonlocal append_calls
            append_calls += 1
            if append_calls >= 2:
                raise OSError("audit unavailable")
            return original_append_audit(session_id, event_type, payload)

        monkeypatch.setattr(store, "append_audit", fail_append_audit)

    result = agent.respond(session, "I have a sample")

    events = store.load_session_events(session.session_id)
    failed = [item for item in events if item["event_type"] == "model.failed"]
    assert result.text == "I couldn’t save that response safely. Please try again."
    assert "disk full" not in result.text
    assert "audit unavailable" not in result.text
    assert failed[-1]["payload"]["code"] == "persistence_failed"


def test_unrelated_local_reference_is_not_sent_to_the_model(tmp_path: Path, monkeypatch) -> None:
    local_reference = tmp_path / "unrelated-reference"
    local_reference.mkdir()
    (local_reference / "README.txt").write_text(
        "PRIVATE_UNRELATED_REFERENCE_MARKER", encoding="utf-8"
    )
    monkeypatch.delenv("HELPME_AI_ENABLED", raising=False)

    knowledge = KnowledgeBase.from_repository(ROOT)
    store = SessionStore(tmp_path / "data", knowledge_digest=knowledge.digest)
    processor = ApplicationProcessor(knowledge, store)
    captured: dict[str, str] = {}

    def fake_complete_json(messages, *, system_contract, max_tokens):
        del messages, max_tokens
        captured["contract"] = system_contract
        return {
            "reply": "Rubber can mean several different materials. What kind is it, and what do you want to do with it?",
            "hearing": {"subject": "rubber", "situation": "", "aim": ""},
        }

    processor.model_router.complete_json = fake_complete_json
    session = SessionState.new(topic="", geography="")
    store.save_session(session)

    result = processor.respond_to_message(session, "I have rubber")

    assert "unrelated-reference" not in captured["contract"]
    assert "PRIVATE_UNRELATED_REFERENCE_MARKER" not in captured["contract"]
    assert "No source passage" not in captured["contract"]
    assert result.data is not None and result.data["sources"] == []
