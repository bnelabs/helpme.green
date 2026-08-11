from __future__ import annotations

import json
import urllib.request
from pathlib import Path

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
