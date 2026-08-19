from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_PROVIDERS = ("localai", "deepseek", "openrouter")
_DEFAULT_JSON_REQUEST_BYTES = 64_000
_DEFAULT_VISION_REQUEST_BYTES = 64 * 1024 * 1024
_DEFAULT_VISION_IMAGE_BYTES = 16 * 1024 * 1024
_DEFAULT_MODEL_DISCOVERY_TIMEOUT = 10.0
_DEFAULT_MAX_MODEL_TIMEOUT = 240.0
_DEFAULT_MODEL_RETRIES = 1


def _environment_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.casefold() in {"1", "true", "yes", "on"}


def _positive_environment_int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _optional_positive_environment_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _model_environment_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().casefold() not in {"", "0", "false", "no", "off"}


def _model_environment_number(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if math.isfinite(value) else default


def provider_api_key_environment_names(provider: str) -> tuple[str, ...]:
    names = {
        "localai": ("HELPME_LOCALAI_API_KEY", "LOCALAI_API_KEY"),
        "deepseek": ("DEEPSEEK_API_KEY",),
        "openrouter": ("OPENROUTER_API_KEY",),
    }
    try:
        return names[provider]
    except KeyError as exc:
        raise ValueError("Unsupported AI provider.") from exc


def environment_secret(*names: str) -> str:
    """Read the first configured secret without retaining it in shared configuration."""
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def _optional_environment_path(name: str) -> Path | None:
    raw = os.environ.get(name, "").strip()
    return Path(raw).expanduser() if raw else None


@dataclass(frozen=True)
class ModelEnvironment:
    """One typed snapshot of process-level model configuration.

    Secret values are deliberately not stored here. Provider key names remain centralized, while
    the secret store or the request boundary resolves values only when a provider call needs one.
    """

    model_identity: str
    provider: str
    ai_enabled: bool
    localai_base_url: str
    localai_tls_verify: bool
    model_retries: int
    model_discovery_timeout: float
    max_model_timeout_seconds: float
    quality_judges: bool
    model_profiles_json: str

    @classmethod
    def from_environment(cls) -> ModelEnvironment:
        return cls(
            model_identity=os.environ.get("HELPME_MODEL", "").strip(),
            provider=os.environ.get("HELPME_PROVIDER", "localai").strip().casefold() or "localai",
            ai_enabled=_model_environment_flag("HELPME_AI_ENABLED", False),
            localai_base_url=os.environ.get("HELPME_LOCALAI_BASE_URL", "").strip(),
            localai_tls_verify=_model_environment_flag("HELPME_LOCALAI_TLS_VERIFY", True),
            model_retries=int(
                _model_environment_number("HELPME_MODEL_RETRIES", _DEFAULT_MODEL_RETRIES)
            ),
            model_discovery_timeout=_model_environment_number(
                "HELPME_MODEL_DISCOVERY_TIMEOUT", _DEFAULT_MODEL_DISCOVERY_TIMEOUT
            ),
            max_model_timeout_seconds=_model_environment_number(
                "HELPME_MAX_MODEL_TIMEOUT_SECONDS", _DEFAULT_MAX_MODEL_TIMEOUT
            ),
            quality_judges=_model_environment_flag("HELPME_QUALITY_JUDGES", True),
            model_profiles_json=os.environ.get("HELPME_MODEL_PROFILES", "").strip(),
        )

    def default_identity(self) -> str:
        identity = self.model_identity
        if identity:
            if ":" in identity:
                provider, model = identity.split(":", 1)
                provider = provider.strip().casefold()
                if provider in SUPPORTED_PROVIDERS and model.strip():
                    return f"{provider}:{model.strip()}"
            elif self.provider in SUPPORTED_PROVIDERS:
                return f"{self.provider}:{identity}"
        provider = self.provider if self.provider in SUPPORTED_PROVIDERS else "localai"
        return f"{provider}:auto"


@dataclass(frozen=True)
class RetrievalEnvironment:
    """Typed non-secret settings for optional embedding and reranking adapters."""

    embedding_query_enabled: bool
    embedding_base_url: str
    embedding_model: str
    embedding_tls_verify: bool
    rerank_enabled: bool
    rerank_base_url: str
    rerank_model: str
    rerank_tls_verify: bool

    @classmethod
    def from_environment(cls) -> RetrievalEnvironment:
        return cls(
            embedding_query_enabled=_environment_flag("HELPME_EMBEDDING_QUERY_ENABLED", True),
            embedding_base_url=os.environ.get("HELPME_EMBEDDING_BASE_URL", "").strip(),
            embedding_model=os.environ.get("HELPME_EMBEDDING_MODEL", "").strip(),
            embedding_tls_verify=_model_environment_flag("HELPME_EMBEDDING_TLS_VERIFY", True),
            rerank_enabled=_model_environment_flag("HELPME_RERANK_ENABLED", True),
            rerank_base_url=os.environ.get("HELPME_RERANK_BASE_URL", "").strip(),
            rerank_model=os.environ.get("HELPME_RERANK_MODEL", "").strip(),
            rerank_tls_verify=_model_environment_flag("HELPME_RERANK_TLS_VERIFY", True),
        )


@dataclass(frozen=True)
class KbConfig:
    """Typed operator-console settings; the console remains disabled by default."""

    enabled: bool
    upload_dir: Path
    max_file_bytes: int
    max_request_bytes: int
    max_storage_bytes: int
    external_processing_enabled: bool

    @classmethod
    def from_environment(cls, data_dir: Path) -> KbConfig:
        return cls(
            enabled=_environment_flag("HELPME_KB_ENABLED"),
            upload_dir=Path(
                os.environ.get("HELPME_UPLOAD_DIR", str(data_dir / "uploads"))
            ).expanduser(),
            max_file_bytes=_optional_positive_environment_int(
                "HELPME_KB_MAX_FILE_BYTES", 20_971_520
            ),
            max_request_bytes=_optional_positive_environment_int(
                "HELPME_KB_MAX_REQUEST_BYTES", 84_000_000
            ),
            max_storage_bytes=_optional_positive_environment_int(
                "HELPME_KB_MAX_STORAGE_BYTES", 1_073_741_824
            ),
            external_processing_enabled=_environment_flag("HELPME_KB_EXTERNAL_PROCESSING"),
        )


@dataclass(frozen=True)
class RuntimePaths:
    """Non-secret process paths and read-only import allowlists."""

    root: Path | None
    data_dir: Path | None
    knowledge_db: Path | None
    source_download_dir: Path | None
    mcp_roots: tuple[Path, ...]
    mcp_hosts: tuple[str, ...]

    @classmethod
    def from_environment(cls) -> RuntimePaths:
        return cls(
            root=_optional_environment_path("HELPME_ROOT"),
            data_dir=_optional_environment_path("HELPME_DATA_DIR"),
            knowledge_db=_optional_environment_path("HELPME_KNOWLEDGE_DB"),
            source_download_dir=_optional_environment_path("HELPME_SOURCE_DOWNLOAD_DIR"),
            mcp_roots=tuple(
                Path(item).expanduser()
                for item in os.environ.get("HELPME_MCP_ROOTS", "").split(os.pathsep)
                if item
            ),
            mcp_hosts=tuple(
                item.strip()
                for item in os.environ.get("HELPME_MCP_HOSTS", "").split(",")
                if item.strip()
            ),
        )

    def database_path(self, data_dir: Path) -> Path:
        return self.knowledge_db or data_dir / "knowledge.db"

    def source_download_path(self, default: Path) -> Path:
        return self.source_download_dir or default


@dataclass(frozen=True)
class AccessEnvironment:
    """Access-gate policy without retaining bearer-token values in the snapshot."""

    access_token_name: str
    kb_access_token_name: str
    kb_loopback_dev_enabled: bool

    @classmethod
    def from_environment(cls) -> AccessEnvironment:
        return cls(
            access_token_name="HELPME_ACCESS_TOKEN",
            kb_access_token_name="HELPME_KB_ACCESS_TOKEN",
            kb_loopback_dev_enabled=_environment_flag("HELPME_KB_ALLOW_LOOPBACK_DEV"),
        )

    def resolve_access_token(self) -> str:
        return environment_secret(self.access_token_name)

    def resolve_kb_access_token(self) -> str:
        return environment_secret(self.kb_access_token_name)


@dataclass(frozen=True)
class HttpRuntimeConfig:
    """Typed configuration for the stdlib HTTP boundary.

    Provider and secret settings remain owned by RuntimeSettingsStore. This object only owns
    request-boundary values that must be fixed for the lifetime of a server instance.
    """

    metrics_enabled: bool
    max_json_request_bytes: int
    max_vision_request_bytes: int
    max_vision_image_bytes: int

    @classmethod
    def from_environment(cls) -> HttpRuntimeConfig:
        return cls(
            metrics_enabled=_environment_flag("HELPME_METRICS_ENABLED"),
            max_json_request_bytes=_positive_environment_int(
                "HELPME_MAX_JSON_REQUEST_BYTES", _DEFAULT_JSON_REQUEST_BYTES
            ),
            max_vision_request_bytes=_positive_environment_int(
                "HELPME_MAX_VISION_REQUEST_BYTES", _DEFAULT_VISION_REQUEST_BYTES
            ),
            max_vision_image_bytes=_positive_environment_int(
                "HELPME_MAX_VISION_IMAGE_BYTES", _DEFAULT_VISION_IMAGE_BYTES
            ),
        )
