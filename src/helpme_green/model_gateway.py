from __future__ import annotations

import json
import math
import ssl
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC
from email.utils import parsedate_to_datetime
from typing import Any

from .config import ModelEnvironment, environment_secret, provider_api_key_environment_names
from .observability import MetricsRegistry


class ProviderUnavailable(RuntimeError):
    """The configured model is unavailable or returned an unusable response."""

    code = "provider_unavailable"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


@dataclass(frozen=True)
class ModelSelection:
    provider: str
    model: str

    @property
    def identity(self) -> str:
        return f"{self.provider}:{self.model}"


_PROFILE_RESERVED_KEYS = {"model", "messages", "response_format", "stream"}
_AUTO_MODEL_NAMES = {"", "auto", "*"}
_RETRYABLE_HTTP_STATUS_CODES = {408, 429, 500, 502, 503, 504}
_MAX_RETRY_DELAY_SECONDS = 1.0


def _json_object(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProviderUnavailable(f"{label} must be a JSON object.")
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ProviderUnavailable(f"{label} must contain JSON values only.") from exc
    return dict(value)


def _looks_like_context_overflow(value: str) -> bool:
    text = value.casefold()
    return any(
        marker in text
        for marker in (
            "context length",
            "context window",
            "maximum context",
            "too many tokens",
            "prompt is too long",
            "max input",
        )
    )


def _is_timeout_error(exc: BaseException) -> bool:
    reason = getattr(exc, "reason", None)
    return isinstance(exc, TimeoutError) or isinstance(reason, TimeoutError)


def _http_failure_code(status: int) -> str:
    if status in {401, 403}:
        return "authentication"
    if status == 408:
        return "timeout"
    if status == 429:
        return "rate_limit"
    if status in {500, 502, 503, 504}:
        return "server_error"
    return "provider_configuration"


def _retry_delay(exc: urllib.error.HTTPError, attempt: int) -> tuple[float, bool]:
    fallback = min(_MAX_RETRY_DELAY_SECONDS, 0.25 * (2**attempt))
    headers = exc.headers
    raw = headers.get("Retry-After") if headers is not None else None
    if not raw:
        return fallback, False
    value = raw.strip()
    try:
        delay = float(int(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=UTC)
            delay = retry_at.timestamp() - time.time()
        except (TypeError, ValueError, OverflowError):
            return fallback, False
    if 0 <= delay <= fallback:
        return delay, True
    return fallback, False


class ModelRouter:
    """Provider and model selection is separate from retrieval and answer quality."""

    allowed = {"localai", "deepseek", "openrouter"}

    def __init__(
        self,
        selection: ModelSelection | None = None,
        *,
        key_provider: Callable[[str], str] | None = None,
        metrics: MetricsRegistry | None = None,
        environment: ModelEnvironment | None = None,
    ) -> None:
        self._environment = environment or ModelEnvironment.from_environment()
        self.selection = selection or self._default_selection(self._environment)
        self._key_provider = key_provider
        self._metrics = metrics or MetricsRegistry()
        self._tokens_in = 0
        self._tokens_out = 0
        self._calls = 0
        self._counter_lock = threading.Lock()
        self._runtime_settings: dict[str, Any] = {}

    def configure(self, settings: Mapping[str, Any]) -> None:
        """Apply validated local settings without changing process environment variables."""
        if not isinstance(settings, Mapping):
            raise ValueError("Runtime settings must be an object.")
        identity = settings.get("identity")
        if isinstance(identity, str) and identity.strip():
            self.selection = self.selection_for(identity)
        self._runtime_settings = dict(settings)

    @staticmethod
    def _default_selection(environment: ModelEnvironment | None = None) -> ModelSelection:
        configured = environment or ModelEnvironment.from_environment()
        identity = configured.model_identity
        if not identity:
            provider = configured.provider
            if provider not in ModelRouter.allowed:
                provider = "localai"
            return ModelSelection(provider, "auto")
        try:
            provider, model = identity.split(":", 1)
        except ValueError:
            provider = configured.provider
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

    def context_window(self, selection: ModelSelection | None = None) -> int | None:
        """Return an explicitly configured combined provider context window, if known."""
        selected = self._resolve_selection(selection or self.selection)
        profile = self._model_profile(selected.identity)
        raw = profile.get("context_window")
        if raw is None:
            return None
        if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
            raise ProviderUnavailable(
                f"Model profile {selected.identity} context_window must be a positive integer."
            )
        return raw

    def complete_json(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        system_contract: str,
        max_tokens: int | None = None,
        selection: ModelSelection | None = None,
        images: Sequence[Mapping[str, str]] | None = None,
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
        vision_enabled = self._profile_supports_vision(profile)
        timeout_seconds = self._timeout_seconds(profile)
        profile.pop("timeout_seconds", None)
        profile.pop("context_window", None)
        profile_max_tokens = profile.pop("max_tokens", None)
        profile.pop("vision", None)
        profile.pop("input_modalities", None)
        outgoing_messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_contract},
            *[dict(message) for message in messages],
        ]
        if images:
            if not vision_enabled:
                raise ProviderUnavailable(
                    "The selected model is not configured for image input; set vision=true in its model profile.",
                    code="vision_unavailable",
                )
            outgoing_messages = self._messages_with_images(outgoing_messages, images)
        payload = {
            "model": selected.model,
            "messages": outgoing_messages,
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
        self._metrics.counter("model_requests_total", labels={"provider": selected.provider})
        with self._metrics.track("model_request", labels={"provider": selected.provider}):
            for attempt in range(retries + 1):
                self._metrics.counter(
                    "model_attempts_total", labels={"provider": selected.provider}
                )
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
                    error_body = ""
                    try:
                        error_body = exc.read().decode("utf-8", errors="replace")
                    except OSError:
                        pass
                    if _looks_like_context_overflow(error_body):
                        raise ProviderUnavailable(
                            f"{selected.provider} rejected the request because it exceeds the context window.",
                            code="context_window_exceeded",
                        ) from exc
                    if exc.code not in _RETRYABLE_HTTP_STATUS_CODES or attempt >= retries:
                        raise ProviderUnavailable(
                            f"{selected.provider} request failed safely.",
                            code=_http_failure_code(exc.code),
                        ) from exc
                    self._metrics.counter(
                        "model_retries_total", labels={"provider": selected.provider}
                    )
                    delay, hint_honored = _retry_delay(exc, attempt)
                    if hint_honored:
                        self._metrics.counter(
                            "model_retry_hints_honored_total",
                            labels={"provider": selected.provider},
                        )
                    time.sleep(delay)
                except (OSError, urllib.error.URLError) as exc:
                    if attempt >= retries:
                        raise ProviderUnavailable(
                            f"{selected.provider} request failed safely.",
                            code="timeout" if _is_timeout_error(exc) else "transport_error",
                        ) from exc
                    self._metrics.counter(
                        "model_retries_total", labels={"provider": selected.provider}
                    )
                    time.sleep(min(_MAX_RETRY_DELAY_SECONDS, 0.25 * (2**attempt)))
                except json.JSONDecodeError as exc:
                    raise ProviderUnavailable(
                        f"{selected.provider} returned invalid JSON.", code="malformed_response"
                    ) from exc
        if raw is None:
            raise ProviderUnavailable(
                f"{selected.provider} request failed safely.", code="provider_unavailable"
            )
        if not isinstance(raw, Mapping):
            raise ProviderUnavailable(
                "Model response was not a JSON object.", code="malformed_response"
            )
        with self._counter_lock:
            self._calls += 1
        self._metrics.counter("model_calls_total", labels={"provider": selected.provider})
        message = self._message_text(raw)
        try:
            decoded = json.loads(self._strip_json_fence(message))
        except json.JSONDecodeError as exc:
            raise ProviderUnavailable(
                "Model returned non-JSON output.", code="malformed_response"
            ) from exc
        if not isinstance(decoded, Mapping):
            raise ProviderUnavailable(
                "Model returned an invalid JSON object.", code="malformed_response"
            )
        usage = raw.get("usage", {})
        with self._counter_lock:
            self._tokens_in += int(usage.get("prompt_tokens", 0) or 0)
            self._tokens_out += int(usage.get("completion_tokens", 0) or 0)
        self._metrics.counter(
            "model_tokens_in_total",
            int(usage.get("prompt_tokens", 0) or 0),
            labels={"provider": selected.provider},
        )
        self._metrics.counter(
            "model_tokens_out_total",
            int(usage.get("completion_tokens", 0) or 0),
            labels={"provider": selected.provider},
        )
        return decoded

    @staticmethod
    def _profile_supports_vision(profile: Mapping[str, Any]) -> bool:
        if profile.get("vision") is True:
            return True
        modalities = profile.get("input_modalities")
        return isinstance(modalities, list) and any(
            isinstance(item, str) and item.casefold() == "image" for item in modalities
        )

    @staticmethod
    def _messages_with_images(
        messages: Sequence[Mapping[str, Any]], images: Sequence[Mapping[str, str]]
    ) -> list[dict[str, Any]]:
        outgoing = [dict(message) for message in messages]
        user_index = next(
            (
                index
                for index in range(len(outgoing) - 1, -1, -1)
                if outgoing[index].get("role") == "user"
            ),
            None,
        )
        if user_index is None:
            raise ProviderUnavailable(
                "Image input requires a user message.", code="invalid_vision_request"
            )
        text = outgoing[user_index].get("content")
        if not isinstance(text, str):
            raise ProviderUnavailable(
                "Image input requires a text user message.", code="invalid_vision_request"
            )
        content: list[dict[str, Any]] = [{"type": "text", "text": text}]
        for image in images:
            mime_type = image.get("mime_type")
            data = image.get("data")
            if not isinstance(mime_type, str) or not mime_type.startswith("image/"):
                raise ProviderUnavailable(
                    "Image input has an invalid media type.", code="invalid_vision_request"
                )
            if not isinstance(data, str) or not data:
                raise ProviderUnavailable(
                    "Image input has no image data.", code="invalid_vision_request"
                )
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{data}"},
                }
            )
        outgoing[user_index]["content"] = content
        return outgoing

    def _timeout_seconds(self, profile: dict[str, Any]) -> float:
        raw = profile.get("timeout_seconds", 30)
        if isinstance(raw, bool):
            raise ProviderUnavailable("Model profile timeout_seconds must be positive.")
        try:
            timeout = float(raw)
        except (TypeError, ValueError) as exc:
            raise ProviderUnavailable("Model profile timeout_seconds must be positive.") from exc
        if not math.isfinite(timeout) or timeout <= 0:
            raise ProviderUnavailable("Model profile timeout_seconds must be positive.")
        maximum_value = self._runtime_settings.get("max_model_timeout_seconds")
        maximum_raw = (
            str(maximum_value)
            if maximum_value is not None
            else str(self._environment.max_model_timeout_seconds)
        )
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

    def _retry_count(self) -> int:
        configured = self._runtime_settings.get("model_retries")
        raw = str(configured) if configured is not None else str(self._environment.model_retries)
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
        configured_profiles = self._runtime_settings.get("profiles")
        if configured_profiles is not None:
            profiles = _json_object(configured_profiles, label="Runtime model profiles")
        else:
            raw = self._environment.model_profiles_json
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
        configured = self._runtime_settings.get("ai_enabled")
        if isinstance(configured, bool):
            return configured
        return self._environment.ai_enabled

    def quality_judges_enabled(self) -> bool:
        configured = self._runtime_settings.get("quality_judges")
        if isinstance(configured, bool):
            return configured
        return self._environment.quality_judges

    def _api_key(self, provider: str, env_name: str) -> str | None:
        del env_name
        api_key = environment_secret(*provider_api_key_environment_names(provider)) or None
        if not api_key and self._key_provider is not None:
            try:
                api_key = self._key_provider(provider)
            except (OSError, ValueError):
                api_key = None
        return api_key

    def _provider_base_url(self, provider: str) -> tuple[str, str]:
        if provider == "localai":
            configured = self._runtime_settings.get("localai_base_url")
            base_url = (
                str(configured).strip().rstrip("/")
                if configured is not None
                else self._environment.localai_base_url.rstrip("/")
            )
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
        headers = {"User-Agent": "helpme.green/0.1"}
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

    def _discovery_timeout(self) -> float:
        configured = self._runtime_settings.get("model_discovery_timeout")
        raw = (
            str(configured)
            if configured is not None
            else str(self._environment.model_discovery_timeout)
        )
        try:
            timeout = float(raw)
        except (TypeError, ValueError) as exc:
            raise ProviderUnavailable("HELPME_MODEL_DISCOVERY_TIMEOUT must be positive.") from exc
        if not math.isfinite(timeout) or timeout <= 0:
            raise ProviderUnavailable("HELPME_MODEL_DISCOVERY_TIMEOUT must be positive.")
        return timeout

    def _tls_context(self, endpoint: str, provider: str | None = None) -> ssl.SSLContext | None:
        if (provider or self.selection.provider) != "localai" or not endpoint.casefold().startswith(
            "https://"
        ):
            return None
        configured = self._runtime_settings.get("localai_tls_verify")
        tls_verify = (
            configured if isinstance(configured, bool) else self._environment.localai_tls_verify
        )
        if tls_verify:
            return None
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    @staticmethod
    def _message_text(raw: Mapping[str, Any]) -> str:
        choices = raw.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderUnavailable(
                "Model response did not contain a choice.", code="empty_response"
            )
        first = choices[0]
        if not isinstance(first, Mapping):
            raise ProviderUnavailable(
                "Model response contained an invalid choice.", code="malformed_response"
            )
        message = first.get("message")
        if not isinstance(message, Mapping):
            raise ProviderUnavailable(
                "Model response did not contain a message.", code="malformed_response"
            )
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
        raise ProviderUnavailable(
            "Model response did not contain text content.", code="empty_response"
        )

    @staticmethod
    def _strip_json_fence(value: str) -> str:
        text = value.strip()
        if text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
        return text
