from __future__ import annotations

import json
import math
import os
import ssl
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


class ProviderUnavailable(RuntimeError):
    """The configured model is unavailable or returned an unusable response."""


@dataclass(frozen=True)
class ModelSelection:
    provider: str
    model: str

    @property
    def identity(self) -> str:
        return f"{self.provider}:{self.model}"


_PROFILE_RESERVED_KEYS = {"model", "messages", "response_format", "stream"}
_AUTO_MODEL_NAMES = {"", "auto", "*"}
_RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}


def _json_object(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProviderUnavailable(f"{label} must be a JSON object.")
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ProviderUnavailable(f"{label} must contain JSON values only.") from exc
    return value


class ModelRouter:
    """Provider and model selection is separate from retrieval and answer quality."""

    allowed = {"localai", "deepseek", "openrouter"}

    def __init__(
        self,
        selection: ModelSelection | None = None,
        *,
        key_provider: Callable[[str], str] | None = None,
    ) -> None:
        self.selection = selection or self._default_selection()
        self._key_provider = key_provider
        self._tokens_in = 0
        self._tokens_out = 0
        self._calls = 0
        self._counter_lock = threading.Lock()

    @staticmethod
    def _default_selection() -> ModelSelection:
        identity = os.environ.get("HELPME_MODEL", "").strip()
        if not identity:
            provider = os.environ.get("HELPME_PROVIDER", "localai").strip().casefold() or "localai"
            if provider not in ModelRouter.allowed:
                provider = "localai"
            return ModelSelection(provider, "auto")
        try:
            provider, model = identity.split(":", 1)
        except ValueError:
            provider = os.environ.get("HELPME_PROVIDER", "localai").strip().casefold() or "localai"
            if provider not in ModelRouter.allowed:
                provider = "localai"
            return ModelSelection(provider, identity)
        if not provider or not model.strip():
            return ModelSelection("localai", "auto")
        return ModelSelection(provider.casefold(), model)

    def select(self, identity: str) -> ModelSelection:
        self.selection = self.selection_for(identity)
        return self.selection

    def selection_for(self, identity: str) -> ModelSelection:
        try:
            provider, model = identity.split(":", 1)
        except ValueError as exc:
            raise ValueError("Model must use provider:model syntax.") from exc
        provider = provider.casefold()
        if provider not in self.allowed or not model.strip():
            raise ValueError("Supported model providers are localai, deepseek, and openrouter.")
        return ModelSelection(provider, model)

    def budget(self) -> dict[str, int | str]:
        return {
            "model": self.selection.identity,
            "calls": self._calls,
            "tokens_in": self._tokens_in,
            "tokens_out": self._tokens_out,
        }

    def complete_json(
        self,
        messages: list[Mapping[str, str]],
        *,
        system_contract: str,
        max_tokens: int | None = None,
        selection: ModelSelection | None = None,
    ) -> Mapping[str, Any]:
        """Call an OpenAI-compatible provider using the selected model profile."""
        if not self.ai_enabled():
            raise ProviderUnavailable(
                "AI interaction is disabled; set HELPME_AI_ENABLED=1 to enable the configured provider."
            )
        selected = self._resolve_selection(selection or self.selection)
        endpoint, env_name = self._endpoint_and_key_env(selected.provider)
        api_key = self._api_key(selected.provider, env_name)
        if not api_key and selected.provider != "localai":
            raise ProviderUnavailable(
                f"{selected.provider} key is not configured; local reference services remain available."
            )
        profile = self._model_profile(selected.identity)
        timeout_seconds = self._timeout_seconds(profile)
        profile.pop("timeout_seconds", None)
        profile_max_tokens = profile.pop("max_tokens", None)
        payload = {
            "model": selected.model,
            "messages": [
                {"role": "system", "content": system_contract},
                *messages,
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        requested_max_tokens = max_tokens if max_tokens is not None else profile_max_tokens
        if requested_max_tokens is not None:
            if (
                isinstance(requested_max_tokens, bool)
                or not isinstance(requested_max_tokens, int)
                or requested_max_tokens <= 0
            ):
                raise ProviderUnavailable("max_tokens must be a positive integer.")
            payload["max_tokens"] = requested_max_tokens
        payload.update(profile)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "helpme.green/0.1",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        raw: Any = None
        retries = self._retry_count()
        for attempt in range(retries + 1):
            try:
                context = self._tls_context(endpoint, selected.provider)
                if context is None:
                    response_context = urllib.request.urlopen(request, timeout=timeout_seconds)
                else:
                    response_context = urllib.request.urlopen(
                        request, timeout=timeout_seconds, context=context
                    )
                with response_context as response:
                    raw = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                if exc.code not in _RETRYABLE_HTTP_STATUS_CODES or attempt >= retries:
                    raise ProviderUnavailable(
                        f"{selected.provider} request failed safely."
                    ) from exc
                time.sleep(min(1.0, 0.25 * (2**attempt)))
            except (OSError, urllib.error.URLError) as exc:
                if attempt >= retries:
                    raise ProviderUnavailable(
                        f"{selected.provider} request failed safely."
                    ) from exc
                time.sleep(min(1.0, 0.25 * (2**attempt)))
            except json.JSONDecodeError as exc:
                raise ProviderUnavailable(f"{selected.provider} returned invalid JSON.") from exc
        if raw is None:
            raise ProviderUnavailable(f"{selected.provider} request failed safely.")
        if not isinstance(raw, Mapping):
            raise ProviderUnavailable("Model response was not a JSON object.")
        with self._counter_lock:
            self._calls += 1
        message = self._message_text(raw)
        try:
            decoded = json.loads(self._strip_json_fence(message))
        except json.JSONDecodeError as exc:
            raise ProviderUnavailable("Model returned non-JSON output.") from exc
        if not isinstance(decoded, Mapping):
            raise ProviderUnavailable("Model returned an invalid JSON object.")
        usage = raw.get("usage", {})
        with self._counter_lock:
            self._tokens_in += int(usage.get("prompt_tokens", 0) or 0)
            self._tokens_out += int(usage.get("completion_tokens", 0) or 0)
        return decoded

    @staticmethod
    def _timeout_seconds(profile: dict[str, Any]) -> float:
        raw = profile.get("timeout_seconds", 30)
        if isinstance(raw, bool):
            raise ProviderUnavailable("Model profile timeout_seconds must be positive.")
        try:
            timeout = float(raw)
        except (TypeError, ValueError) as exc:
            raise ProviderUnavailable("Model profile timeout_seconds must be positive.") from exc
        if not math.isfinite(timeout) or timeout <= 0:
            raise ProviderUnavailable("Model profile timeout_seconds must be positive.")
        maximum_raw = os.environ.get("HELPME_MAX_MODEL_TIMEOUT_SECONDS", "240")
        try:
            maximum = float(maximum_raw)
        except (TypeError, ValueError) as exc:
            raise ProviderUnavailable("HELPME_MAX_MODEL_TIMEOUT_SECONDS must be positive.") from exc
        if not math.isfinite(maximum) or maximum <= 0:
            raise ProviderUnavailable("HELPME_MAX_MODEL_TIMEOUT_SECONDS must be positive.")
        if timeout > maximum:
            raise ProviderUnavailable(
                "Model profile timeout_seconds exceeds HELPME_MAX_MODEL_TIMEOUT_SECONDS."
            )
        return timeout

    @staticmethod
    def _retry_count() -> int:
        raw = os.environ.get("HELPME_MODEL_RETRIES", "1")
        try:
            retries = int(raw)
        except (TypeError, ValueError) as exc:
            raise ProviderUnavailable(
                "HELPME_MODEL_RETRIES must be an integer from 0 to 3."
            ) from exc
        if retries < 0 or retries > 3:
            raise ProviderUnavailable("HELPME_MODEL_RETRIES must be an integer from 0 to 3.")
        return retries

    def _model_profile(self, identity: str | None = None) -> dict[str, Any]:
        """Return request options for the selected model, without changing other models."""
        raw = os.environ.get("HELPME_MODEL_PROFILES", "").strip()
        if not raw:
            return {}
        try:
            profiles = _json_object(json.loads(raw), label="HELPME_MODEL_PROFILES")
        except json.JSONDecodeError as exc:
            raise ProviderUnavailable("HELPME_MODEL_PROFILES must contain valid JSON.") from exc

        selected_identity = identity or self.selection.identity
        selected_provider = selected_identity.split(":", 1)[0]
        candidates = (selected_identity, f"{selected_provider}:*", "*")
        selected: Any = None
        for identity in candidates:
            if identity in profiles:
                selected = profiles[identity]
                break
        if selected is None:
            return {}
        options = _json_object(selected, label=f"Model profile {selected_identity}")
        forbidden = sorted(_PROFILE_RESERVED_KEYS.intersection(options))
        if forbidden:
            raise ProviderUnavailable(
                "Model profiles cannot override protected request fields: " + ", ".join(forbidden)
            )
        if "chat_template_kwargs" in options:
            _json_object(
                options["chat_template_kwargs"],
                label=f"Model profile {selected_identity}.chat_template_kwargs",
            )
        self._timeout_seconds(options)
        return options

    def resolve_selection(self, selection: ModelSelection | None = None) -> ModelSelection:
        return self._resolve_selection(selection or self.selection)

    def _resolve_selection(self, selection: ModelSelection | None = None) -> ModelSelection:
        selected = selection or self.selection
        if selected.model.casefold() not in _AUTO_MODEL_NAMES:
            return selected
        if selected.provider != "localai":
            raise ProviderUnavailable(
                "Automatic model discovery is supported for localai; set HELPME_MODEL to provider:model."
            )
        models = self._discover_localai_models()
        if not models:
            raise ProviderUnavailable(
                "The configured local model endpoint did not advertise a model."
            )
        if len(models) > 1:
            raise ProviderUnavailable(
                "The configured local model endpoint advertises multiple models; "
                "set HELPME_MODEL to localai:<model-id>."
            )
        return ModelSelection(selected.provider, models[0])

    def ai_enabled(self) -> bool:
        return self._env_flag("HELPME_AI_ENABLED", default=False)

    def _api_key(self, provider: str, env_name: str) -> str | None:
        api_key = os.environ.get(env_name)
        if provider == "localai" and not api_key:
            api_key = os.environ.get("LOCALAI_API_KEY")
        if not api_key and self._key_provider is not None:
            try:
                api_key = self._key_provider(provider)
            except (OSError, ValueError):
                api_key = None
        return api_key

    def _provider_base_url(self, provider: str) -> tuple[str, str]:
        if provider == "localai":
            base_url = os.environ.get("HELPME_LOCALAI_BASE_URL", "").strip().rstrip("/")
            if not base_url:
                raise ProviderUnavailable(
                    "Local model endpoint is not configured; set HELPME_LOCALAI_BASE_URL."
                )
            return base_url, "HELPME_LOCALAI_API_KEY"
        if provider == "deepseek":
            return "https://api.deepseek.com", "DEEPSEEK_API_KEY"
        return "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"

    def _endpoint_and_key_env(self, provider: str | None = None) -> tuple[str, str]:
        selected_provider = provider or self.selection.provider
        base_url, env_name = self._provider_base_url(selected_provider)
        if selected_provider == "localai":
            if base_url.endswith("/chat/completions"):
                return base_url, "HELPME_LOCALAI_API_KEY"
            if base_url.endswith("/v1"):
                return f"{base_url}/chat/completions", env_name
            return f"{base_url}/v1/chat/completions", env_name
        return f"{base_url}/chat/completions", env_name

    def _discover_localai_models(self) -> list[str]:
        base_url, env_name = self._provider_base_url("localai")
        if base_url.endswith("/models"):
            endpoint = base_url
        elif base_url.endswith("/v1"):
            endpoint = f"{base_url}/models"
        else:
            endpoint = f"{base_url}/v1/models"
        headers = {"User-Agent": "helpme.green/0.2"}
        api_key = self._api_key("localai", env_name)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(endpoint, headers=headers, method="GET")
        timeout = self._discovery_timeout()
        try:
            context = self._tls_context(endpoint, "localai")
            if context is None:
                response_context = urllib.request.urlopen(request, timeout=timeout)
            else:
                response_context = urllib.request.urlopen(request, timeout=timeout, context=context)
            with response_context as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise ProviderUnavailable("Local model discovery request failed safely.") from exc
        if not isinstance(raw, Mapping):
            raise ProviderUnavailable("Local model discovery returned an invalid response.")
        entries = raw.get("data")
        if not isinstance(entries, list):
            entries = raw.get("models")
        if not isinstance(entries, list):
            raise ProviderUnavailable("Local model discovery returned no model list.")
        models: list[str] = []
        for entry in entries:
            if isinstance(entry, Mapping):
                for key in ("id", "model", "name"):
                    candidate = entry.get(key)
                    if isinstance(candidate, str) and candidate.strip():
                        if candidate not in models:
                            models.append(candidate)
                        break
        return models

    @staticmethod
    def _discovery_timeout() -> float:
        raw = os.environ.get("HELPME_MODEL_DISCOVERY_TIMEOUT", "10")
        try:
            timeout = float(raw)
        except (TypeError, ValueError) as exc:
            raise ProviderUnavailable("HELPME_MODEL_DISCOVERY_TIMEOUT must be positive.") from exc
        if not math.isfinite(timeout) or timeout <= 0:
            raise ProviderUnavailable("HELPME_MODEL_DISCOVERY_TIMEOUT must be positive.")
        return timeout

    @staticmethod
    def _env_flag(name: str, *, default: bool) -> bool:
        raw = os.environ.get(name)
        if raw is None:
            return default
        return raw.strip().casefold() not in {"", "0", "false", "no", "off"}

    def _tls_context(self, endpoint: str, provider: str | None = None) -> ssl.SSLContext | None:
        if (provider or self.selection.provider) != "localai" or not endpoint.casefold().startswith(
            "https://"
        ):
            return None
        if self._env_flag("HELPME_LOCALAI_TLS_VERIFY", default=True):
            return None
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    @staticmethod
    def _message_text(raw: Mapping[str, Any]) -> str:
        choices = raw.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderUnavailable("Model response did not contain a choice.")
        first = choices[0]
        if not isinstance(first, Mapping):
            raise ProviderUnavailable("Model response contained an invalid choice.")
        message = first.get("message")
        if not isinstance(message, Mapping):
            raise ProviderUnavailable("Model response did not contain a message.")
        for key in ("content", "reasoning", "reasoning_content"):
            value = message.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, list):
                text = "".join(
                    str(item.get("text", "")) if isinstance(item, Mapping) else str(item)
                    for item in value
                )
                if text.strip():
                    return text
        raise ProviderUnavailable("Model response did not contain text content.")

    @staticmethod
    def _strip_json_fence(value: str) -> str:
        text = value.strip()
        if text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
        return text
