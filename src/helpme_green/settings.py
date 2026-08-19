from __future__ import annotations

import json
import math
import os
import secrets
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .config import (
    SUPPORTED_PROVIDERS,
    ModelEnvironment,
    environment_secret,
    provider_api_key_environment_names,
)
from .persistence import SecretStore

_PROFILE_RESERVED_KEYS = {"model", "messages", "response_format", "stream"}
_PROFILE_SENSITIVE_KEYS = {"api_key", "authorization", "password", "secret", "token"}
_PROFILE_NUMERIC_RANGES = {
    "temperature": (0.0, 2.0),
    "top_p": (0.0, 1.0),
    "min_p": (0.0, 1.0),
    "frequency_penalty": (-2.0, 2.0),
    "presence_penalty": (-2.0, 2.0),
}
_PROFILE_INTEGER_LIMITS = {
    "top_k": (0, 1_000_000),
    "max_tokens": (1, 1_000_000),
    "context_window": (1, 10_000_000),
    "seed": (0, 2**31 - 1),
}
_CONFIG_KEYS = {
    "ai_enabled",
    "localai_base_url",
    "localai_tls_verify",
    "model_retries",
    "model_discovery_timeout",
    "max_model_timeout_seconds",
    "quality_judges",
}


class SettingsError(ValueError):
    """A user-editable runtime setting is invalid or cannot be saved safely."""

    code = "invalid_settings"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


def _split_identity(value: Any) -> tuple[str, str, str]:
    if not isinstance(value, str):
        raise SettingsError("Choose a supported AI provider and model.")
    raw = value.strip()
    if ":" not in raw:
        raise SettingsError("The model must use provider:model syntax.")
    provider, model = raw.split(":", 1)
    provider = provider.strip().casefold()
    model = model.strip()
    if provider not in SUPPORTED_PROVIDERS or not model or len(model) > 400:
        raise SettingsError("Choose a supported AI provider and a model name.")
    return provider, model, f"{provider}:{model}"


def _json_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SettingsError(f"{label} must be a JSON object.")
    try:
        encoded = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise SettingsError(f"{label} must contain JSON values only.") from exc
    if len(encoded) > 24_000:
        raise SettingsError(f"{label} is too large.")
    return dict(value)


def _reject_sensitive_profile_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in _PROFILE_SENSITIVE_KEYS:
                raise SettingsError("Model options cannot contain credential fields.")
            _reject_sensitive_profile_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_sensitive_profile_keys(child)


def _validate_profile(value: Any, *, max_timeout: float) -> dict[str, Any]:
    profile = _json_object(value, "Model options")
    forbidden = sorted(_PROFILE_RESERVED_KEYS.intersection(profile))
    if forbidden:
        raise SettingsError(
            "Model options cannot override protected request fields: " + ", ".join(forbidden)
        )
    _reject_sensitive_profile_keys(profile)
    for key, bounds in _PROFILE_NUMERIC_RANGES.items():
        if key not in profile:
            continue
        raw = profile[key]
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise SettingsError(f"{key} must be a number.")
        number = float(raw)
        if not math.isfinite(number) or number < bounds[0] or number > bounds[1]:
            raise SettingsError(f"{key} must be between {bounds[0]} and {bounds[1]}.")
    for key, bounds in _PROFILE_INTEGER_LIMITS.items():
        if key not in profile:
            continue
        raw = profile[key]
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise SettingsError(f"{key} must be an integer.")
        if raw < bounds[0] or raw > bounds[1]:
            raise SettingsError(f"{key} is outside the supported range.")
    for key in ("vision", "include_reasoning"):
        if key in profile and not isinstance(profile[key], bool):
            raise SettingsError(f"{key} must be true or false.")
    if "input_modalities" in profile:
        modalities = profile["input_modalities"]
        if not isinstance(modalities, list) or not all(
            isinstance(item, str) for item in modalities
        ):
            raise SettingsError("input_modalities must be a list of strings.")
    if "timeout_seconds" in profile:
        raw_timeout = profile["timeout_seconds"]
        if isinstance(raw_timeout, bool) or not isinstance(raw_timeout, (int, float)):
            raise SettingsError("timeout_seconds must be a number.")
        timeout = float(raw_timeout)
        if not math.isfinite(timeout) or timeout <= 0 or timeout > max_timeout:
            raise SettingsError("timeout_seconds must be positive and within the maximum timeout.")
    if "chat_template_kwargs" in profile:
        _json_object(profile["chat_template_kwargs"], "chat_template_kwargs")
    return profile


def _environment_profiles(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return dict(parsed)


def _public_profile(value: Any) -> Any:
    if isinstance(value, dict):
        public: dict[str, Any] = {}
        for key, child in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if (
                normalized in _PROFILE_SENSITIVE_KEYS
                or normalized.endswith("_key")
                or normalized.endswith("_token")
            ):
                continue
            public[str(key)] = _public_profile(child)
        return public
    if isinstance(value, list):
        return [_public_profile(child) for child in value]
    return value


class RuntimeSettingsStore:
    """Persist non-secret runtime settings and keep provider keys in SecretStore only."""

    def __init__(
        self,
        root: Path,
        *,
        secret_store: SecretStore | None = None,
        environment: ModelEnvironment | None = None,
    ) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            self.root.chmod(0o700)
        except OSError:
            pass
        self.path = self.root / "settings.json"
        self.secret_store = secret_store
        self.environment = environment or ModelEnvironment.from_environment()
        self._lock = threading.RLock()
        self._stored = self._read()

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SettingsError("Saved runtime settings could not be read safely.") from exc
        if not isinstance(value, dict) or value.get("version", 1) != 1:
            raise SettingsError("Saved runtime settings use an unsupported format.")
        return dict(value)

    def _effective(self) -> dict[str, Any]:
        stored = self._stored
        profile_map = _environment_profiles(self.environment.model_profiles_json)
        stored_profiles = stored.get("profiles")
        if isinstance(stored_profiles, dict):
            profile_map.update(stored_profiles)
        values: dict[str, Any] = {
            "identity": stored.get("identity", self.environment.default_identity()),
            "ai_enabled": stored.get("ai_enabled", self.environment.ai_enabled),
            "localai_base_url": stored.get("localai_base_url", self.environment.localai_base_url),
            "localai_tls_verify": stored.get(
                "localai_tls_verify", self.environment.localai_tls_verify
            ),
            "model_retries": stored.get("model_retries", self.environment.model_retries),
            "model_discovery_timeout": stored.get(
                "model_discovery_timeout", self.environment.model_discovery_timeout
            ),
            "max_model_timeout_seconds": stored.get(
                "max_model_timeout_seconds", self.environment.max_model_timeout_seconds
            ),
            "quality_judges": stored.get("quality_judges", self.environment.quality_judges),
            "profiles": profile_map,
        }
        return values

    def runtime(self) -> dict[str, Any]:
        """Return the settings consumed by the live model router without any secrets."""
        with self._lock:
            effective = self._effective()
            runtime = {"identity": effective["identity"]}
            for key in _CONFIG_KEYS:
                if key in self._stored:
                    runtime[key] = effective[key]
            if "profiles" in self._stored:
                runtime["profiles"] = effective["profiles"]
            return runtime

    def public(self) -> dict[str, Any]:
        with self._lock:
            effective = self._effective()
            provider, model, identity = _split_identity(effective["identity"])
            profiles = effective["profiles"]
            profile = profiles.get(identity, {}) if isinstance(profiles, dict) else {}
            if not isinstance(profile, dict):
                profile = {}
            return {
                "provider": provider,
                "model": model,
                "identity": identity,
                "ai_enabled": bool(effective["ai_enabled"]),
                "localai_base_url": str(effective["localai_base_url"] or ""),
                "localai_tls_verify": bool(effective["localai_tls_verify"]),
                "model_retries": effective["model_retries"],
                "model_discovery_timeout": effective["model_discovery_timeout"],
                "max_model_timeout_seconds": effective["max_model_timeout_seconds"],
                "quality_judges": bool(effective["quality_judges"]),
                "profile": _public_profile(profile),
                "api_key_storage_available": self.secret_store is not None,
                "api_keys": {name: self._key_status(name) for name in SUPPORTED_PROVIDERS},
                "apply_scope": "New conversations use provider and model changes; saved conversations keep their model identity.",
            }

    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise SettingsError("Settings must be a JSON object.")
        with self._lock:
            current = self._effective()
            provider = payload.get("provider", _split_identity(current["identity"])[0])
            model = payload.get("model", _split_identity(current["identity"])[1])
            if not isinstance(provider, str) or not isinstance(model, str):
                raise SettingsError("Choose a supported AI provider and model.")
            _, _, identity = _split_identity(f"{provider}:{model}")
            next_values: dict[str, Any] = {"version": 1, "identity": identity}
            for key in _CONFIG_KEYS:
                value = payload[key] if key in payload else current[key]
                next_values[key] = self._validate_config_value(key, value)

            profiles = current["profiles"] if isinstance(current["profiles"], dict) else {}
            profiles = dict(profiles)
            profile_value = payload.get("profile", profiles.get(identity, {}))
            profiles[identity] = _validate_profile(
                profile_value, max_timeout=float(next_values["max_model_timeout_seconds"])
            )
            next_values["profiles"] = profiles

            api_key = payload.get("api_key")
            if api_key is not None:
                if not isinstance(api_key, str) or len(api_key) > 4_096:
                    raise SettingsError("The provider key is invalid or too long.")
                if api_key and payload.get("clear_api_key") is True:
                    raise SettingsError(
                        "Choose either a new provider key or clearing the saved key."
                    )
                if api_key:
                    if self.secret_store is None:
                        raise SettingsError(
                            "Encrypted provider-key storage is unavailable. Configure HELPME_MASTER_KEY before saving a key.",
                            code="secret_store_unavailable",
                        )
                    self.secret_store.set(self._secret_name(provider), api_key)
            if payload.get("clear_api_key") is True and self.secret_store is not None:
                self.secret_store.delete(self._secret_name(provider))

            self._write(next_values)
            self._stored = next_values
            return self.public()

    def get_api_key(self, provider: str) -> str:
        if self.secret_store is None:
            return ""
        try:
            return self.secret_store.get(self._secret_name(provider))
        except (OSError, ValueError):
            return ""

    def api_key_configured(self, provider: str) -> bool:
        return bool(self.get_api_key(provider)) or bool(self._environment_key(provider))

    def _key_status(self, provider: str) -> dict[str, Any]:
        stored = bool(self.get_api_key(provider))
        environment = bool(self._environment_key(provider))
        return {
            "configured": stored or environment,
            "source": "encrypted" if stored else "environment" if environment else "none",
        }

    @staticmethod
    def _secret_name(provider: str) -> str:
        if provider not in SUPPORTED_PROVIDERS:
            raise SettingsError("Unsupported AI provider.")
        return f"provider_api_key_{provider}"

    @staticmethod
    def _environment_key(provider: str) -> str:
        names = provider_api_key_environment_names(provider)
        return environment_secret(*names)

    @staticmethod
    def _validate_config_value(key: str, value: Any) -> Any:
        if key in {"ai_enabled", "localai_tls_verify", "quality_judges"}:
            if not isinstance(value, bool):
                raise SettingsError(f"{key} must be true or false.")
            return value
        if key == "localai_base_url":
            if not isinstance(value, str) or len(value) > 2_048:
                raise SettingsError("The LocalAI endpoint is invalid or too long.")
            endpoint = value.strip()
            if endpoint:
                try:
                    parsed = urlsplit(endpoint)
                except ValueError as exc:
                    raise SettingsError(
                        "The LocalAI endpoint must be a valid HTTP(S) URL."
                    ) from exc
                if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username:
                    raise SettingsError(
                        "The LocalAI endpoint must be an HTTP(S) URL without credentials."
                    )
            return endpoint.rstrip("/")
        if key == "model_retries":
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 3:
                raise SettingsError("Model retries must be an integer from 0 to 3.")
            return value
        if key in {"model_discovery_timeout", "max_model_timeout_seconds"}:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise SettingsError(f"{key} must be a positive number.")
            number = float(value)
            upper = 120.0 if key == "model_discovery_timeout" else 3_600.0
            if not math.isfinite(number) or number <= 0 or number > upper:
                raise SettingsError(f"{key} must be between 0 and {upper} seconds.")
            return number
        raise SettingsError(f"Unknown runtime setting: {key}")

    def _write(self, value: dict[str, Any]) -> None:
        try:
            encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
        except (TypeError, ValueError) as exc:
            raise SettingsError("Runtime settings contain unsupported values.") from exc
        temporary = self.path.with_name(f".settings.{secrets.token_hex(6)}.tmp")
        try:
            temporary.write_text(encoded + "\n", encoding="utf-8")
            temporary.chmod(0o600)
            os.replace(temporary, self.path)
            try:
                self.path.chmod(0o600)
            except OSError:
                pass
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
