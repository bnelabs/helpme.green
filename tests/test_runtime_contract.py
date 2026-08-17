from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from helpme_green.application import ApplicationProcessor
from helpme_green.conversation import ConversationAgent
from helpme_green.expert_skills import SkillRegistry
from helpme_green.knowledge import KnowledgeBase
from helpme_green.mcp import ReadOnlyMCP, ReadOnlyViolation
from helpme_green.model_gateway import ModelRouter, ModelSelection, ProviderUnavailable
from helpme_green.persistence import SecretStore, SessionState, SessionStore

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
    router.complete_json([], system_contract="Return JSON.")
    router.select("localai:other-model")
    router.complete_json([], system_contract="Return JSON.")

    assert captured[0]["max_tokens"] == 16384
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
