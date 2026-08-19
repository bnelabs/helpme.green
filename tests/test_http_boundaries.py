from __future__ import annotations

import os
from pathlib import Path

import pytest

from helpme_green.config import (
    AccessEnvironment,
    HttpRuntimeConfig,
    KbConfig,
    ModelEnvironment,
    RetrievalEnvironment,
    RuntimePaths,
    environment_secret,
    provider_api_key_environment_names,
)
from helpme_green.model_gateway import ModelRouter
from helpme_green.observability import MetricsRegistry
from helpme_green.routing import SessionRoute, match_session_route, path_parts
from helpme_green.server import _Handler
from helpme_green.settings import RuntimeSettingsStore


def test_session_routes_are_decoded_and_parameterized() -> None:
    assert path_parts("/api/sessions/example%2Fid/message") == (
        "api",
        "sessions",
        "example/id",
        "message",
    )
    assert match_session_route("/api/sessions/abc") == SessionRoute("read", "abc")
    assert match_session_route("/api/sessions/abc/message") == SessionRoute("message", "abc")
    assert match_session_route("/api/sessions/abc/message/stream") == SessionRoute(
        "message_stream", "abc"
    )
    assert match_session_route("/api/sessions/abc/other") is None


def test_http_metric_routes_do_not_capture_arbitrary_paths() -> None:
    assert _Handler._metric_route("/api/sessions") == "/api/sessions"
    assert (
        _Handler._metric_route("/api/sessions/abc/message/stream")
        == "/api/sessions/:id/message_stream"
    )
    assert _Handler._metric_route("/anything/a-user-could-type") == "/other"


def test_http_runtime_config_validates_request_limits(monkeypatch) -> None:
    monkeypatch.setenv("HELPME_MAX_JSON_REQUEST_BYTES", "1234")
    monkeypatch.setenv("HELPME_MAX_VISION_REQUEST_BYTES", "5678")
    monkeypatch.setenv("HELPME_MAX_VISION_IMAGE_BYTES", "9012")
    monkeypatch.setenv("HELPME_METRICS_ENABLED", "true")

    config = HttpRuntimeConfig.from_environment()

    assert config.max_json_request_bytes == 1234
    assert config.max_vision_request_bytes == 5678
    assert config.max_vision_image_bytes == 9012
    assert config.metrics_enabled is True


def test_http_runtime_config_rejects_non_positive_limits(monkeypatch) -> None:
    monkeypatch.setenv("HELPME_MAX_JSON_REQUEST_BYTES", "0")

    with pytest.raises(ValueError, match="HELPME_MAX_JSON_REQUEST_BYTES"):
        HttpRuntimeConfig.from_environment()


def test_model_environment_snapshots_shared_runtime_settings(monkeypatch) -> None:
    monkeypatch.setenv("HELPME_MODEL", "example/model")
    monkeypatch.setenv("HELPME_PROVIDER", "openrouter")
    monkeypatch.setenv("HELPME_AI_ENABLED", "true")
    monkeypatch.setenv("HELPME_MODEL_RETRIES", "2.5")
    monkeypatch.setenv("HELPME_MODEL_PROFILES", '{"openrouter:example/model":{"max_tokens":10}}')
    monkeypatch.setenv("HELPME_MAX_MODEL_TIMEOUT_SECONDS", "not-a-number")

    environment = ModelEnvironment.from_environment()

    assert environment.default_identity() == "openrouter:example/model"
    assert environment.ai_enabled is True
    assert environment.model_retries == 2
    assert environment.max_model_timeout_seconds == 240.0
    assert environment.model_profiles_json == '{"openrouter:example/model":{"max_tokens":10}}'
    assert provider_api_key_environment_names("localai") == (
        "HELPME_LOCALAI_API_KEY",
        "LOCALAI_API_KEY",
    )
    with pytest.raises(ValueError, match="Unsupported AI provider"):
        provider_api_key_environment_names("unknown")


def test_settings_store_and_router_share_the_model_environment_snapshot(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("HELPME_MODEL", "localai:sample-model")
    environment = ModelEnvironment.from_environment()

    settings = RuntimeSettingsStore(tmp_path / "data", environment=environment)
    router = ModelRouter(environment=environment)

    assert settings.environment is environment
    assert router.selection.identity == "localai:sample-model"


def test_retrieval_environment_snapshots_non_secret_adapter_settings(monkeypatch) -> None:
    monkeypatch.setenv("HELPME_EMBEDDING_QUERY_ENABLED", "0")
    monkeypatch.setenv("HELPME_EMBEDDING_BASE_URL", "http://127.0.0.1:8090/v1")
    monkeypatch.setenv("HELPME_EMBEDDING_MODEL", "local-embedding-model")
    monkeypatch.setenv("HELPME_EMBEDDING_TLS_VERIFY", "0")
    monkeypatch.setenv("HELPME_RERANK_ENABLED", "false")
    monkeypatch.setenv("HELPME_RERANK_BASE_URL", "http://127.0.0.1:8091/v1")
    monkeypatch.setenv("HELPME_RERANK_MODEL", "local-reranker")
    monkeypatch.setenv("HELPME_RERANK_TLS_VERIFY", "no")
    monkeypatch.setenv("HELPME_EMBEDDING_API_KEY", "embedding-test-secret")

    environment = RetrievalEnvironment.from_environment()

    assert environment.embedding_query_enabled is False
    assert environment.embedding_base_url == "http://127.0.0.1:8090/v1"
    assert environment.embedding_model == "local-embedding-model"
    assert environment.embedding_tls_verify is False
    assert environment.rerank_enabled is False
    assert environment.rerank_base_url == "http://127.0.0.1:8091/v1"
    assert environment.rerank_model == "local-reranker"
    assert environment.rerank_tls_verify is False
    assert environment_secret("HELPME_EMBEDDING_API_KEY") == "embedding-test-secret"
    assert "embedding-test-secret" not in repr(environment)


def test_kb_config_snapshots_safe_limits_and_defaults(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HELPME_KB_ENABLED", "true")
    monkeypatch.setenv("HELPME_UPLOAD_DIR", "~/helpme-test-uploads")
    monkeypatch.setenv("HELPME_KB_MAX_FILE_BYTES", "not-a-number")
    monkeypatch.setenv("HELPME_KB_MAX_REQUEST_BYTES", "0")
    monkeypatch.setenv("HELPME_KB_MAX_STORAGE_BYTES", "123456")
    monkeypatch.setenv("HELPME_KB_EXTERNAL_PROCESSING", "on")

    config = KbConfig.from_environment(tmp_path)

    assert config.enabled is True
    assert config.upload_dir == Path("~/helpme-test-uploads").expanduser()
    assert config.max_file_bytes == 20_971_520
    assert config.max_request_bytes == 84_000_000
    assert config.max_storage_bytes == 123456
    assert config.external_processing_enabled is True


def test_runtime_paths_snapshot_non_secret_overrides(monkeypatch) -> None:
    monkeypatch.setenv("HELPME_ROOT", "~/helpme-root")
    monkeypatch.setenv("HELPME_DATA_DIR", "~/helpme-data")
    monkeypatch.setenv("HELPME_KNOWLEDGE_DB", "~/helpme-data/knowledge.db")
    monkeypatch.setenv("HELPME_SOURCE_DOWNLOAD_DIR", "~/helpme-data/downloads")
    monkeypatch.setenv("HELPME_MCP_ROOTS", f"~/imports{os.pathsep}/tmp/second-import")
    monkeypatch.setenv("HELPME_MCP_HOSTS", " example.test, second.example.test ")

    paths = RuntimePaths.from_environment()

    assert paths.root == Path("~/helpme-root").expanduser()
    assert paths.data_dir == Path("~/helpme-data").expanduser()
    assert paths.knowledge_db == Path("~/helpme-data/knowledge.db").expanduser()
    assert paths.source_download_dir == Path("~/helpme-data/downloads").expanduser()
    assert paths.mcp_roots == (
        Path("~/imports").expanduser(),
        Path("/tmp/second-import"),
    )
    assert paths.mcp_hosts == ("example.test", "second.example.test")
    assert paths.database_path(Path("/fallback")) == paths.knowledge_db
    assert paths.source_download_path(Path("/fallback-downloads")) == paths.source_download_dir


def test_access_environment_resolves_tokens_without_snapshotting_values(monkeypatch) -> None:
    monkeypatch.setenv("HELPME_ACCESS_TOKEN", "main-test-secret")
    monkeypatch.setenv("HELPME_KB_ACCESS_TOKEN", "kb-test-secret")
    monkeypatch.setenv("HELPME_KB_ALLOW_LOOPBACK_DEV", "yes")

    access = AccessEnvironment.from_environment()

    assert access.kb_loopback_dev_enabled is True
    assert access.resolve_access_token() == "main-test-secret"
    assert access.resolve_kb_access_token() == "kb-test-secret"
    assert "main-test-secret" not in repr(access)
    assert "kb-test-secret" not in repr(access)


def test_metrics_registry_renders_bounded_labels_and_timings() -> None:
    metrics = MetricsRegistry(enabled=True)
    metrics.counter("http_requests_total", labels={"route": "/api/sessions", "status": 201})
    with metrics.track("model_request", labels={"provider": "localai"}):
        metrics.counter("model_calls_total", labels={"provider": "localai"})

    rendered = metrics.prometheus()

    assert "helpme_http_requests_total" in rendered
    assert 'route="/api/sessions"' in rendered
    assert "helpme_model_request_duration_seconds_count" in rendered
    assert "helpme_model_calls_total" in rendered
