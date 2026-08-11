from __future__ import annotations

import json
import os
import ssl
import threading
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


class ProviderUnavailable(RuntimeError):
    """The model is unavailable; deterministic evaluation remains usable."""


@dataclass(frozen=True)
class ModelSelection:
    provider: str
    model: str

    @property
    def identity(self) -> str:
        return f"{self.provider}:{self.model}"


class ModelRouter:
    """Provider selection is separate from the deterministic engine."""

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
        identity = os.environ.get("HELPME_MODEL", "localai:Qwen3.6-27B")
        try:
            provider, model = identity.split(":", 1)
        except ValueError:
            return ModelSelection("localai", "Qwen3.6-27B")
        if not provider or not model.strip():
            return ModelSelection("localai", "Qwen3.6-27B")
        return ModelSelection(provider.casefold(), model)

    def select(self, identity: str) -> ModelSelection:
        try:
            provider, model = identity.split(":", 1)
        except ValueError as exc:
            raise ValueError("Model must use provider:model syntax.") from exc
        provider = provider.casefold()
        if provider not in self.allowed or not model.strip():
            raise ValueError("Supported model providers are localai, deepseek, and openrouter.")
        self.selection = ModelSelection(provider, model)
        return self.selection

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
        max_tokens: int = 1200,
    ) -> Mapping[str, Any]:
        """Call an OpenAI-compatible provider without giving it evaluator authority."""
        if not self._env_flag("HELPME_AI_ENABLED", default=False):
            raise ProviderUnavailable(
                "AI interaction is disabled; set HELPME_AI_ENABLED=1 to enable the configured provider."
            )
        endpoint, env_name = self._endpoint_and_key_env()
        api_key = os.environ.get(env_name)
        if self.selection.provider == "localai" and not api_key:
            api_key = os.environ.get("LOCALAI_API_KEY")
        if not api_key and self._key_provider is not None:
            try:
                api_key = self._key_provider(self.selection.provider)
            except (OSError, ValueError):
                api_key = None
        if not api_key and self.selection.provider != "localai":
            raise ProviderUnavailable(
                f"{self.selection.provider} key is not configured; the deterministic engine can continue from cache."
            )
        payload = {
            "model": self.selection.model,
            "messages": [
                {"role": "system", "content": system_contract},
                *messages,
            ],
            "temperature": 0,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
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
        try:
            context = self._tls_context(endpoint)
            if context is None:
                response_context = urllib.request.urlopen(request, timeout=30)
            else:
                response_context = urllib.request.urlopen(request, timeout=30, context=context)
            with response_context as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise ProviderUnavailable(f"{self.selection.provider} request failed safely.") from exc
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

    def _endpoint_and_key_env(self) -> tuple[str, str]:
        if self.selection.provider == "localai":
            base_url = os.environ.get("HELPME_LOCALAI_BASE_URL", "http://127.0.0.1:8080/v1").rstrip(
                "/"
            )
            if base_url.endswith("/chat/completions"):
                return base_url, "HELPME_LOCALAI_API_KEY"
            if base_url.endswith("/v1"):
                return f"{base_url}/chat/completions", "HELPME_LOCALAI_API_KEY"
            return f"{base_url}/v1/chat/completions", "HELPME_LOCALAI_API_KEY"
        if self.selection.provider == "deepseek":
            return "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY"
        return "https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY"

    @staticmethod
    def _env_flag(name: str, *, default: bool) -> bool:
        raw = os.environ.get(name)
        if raw is None:
            return default
        return raw.strip().casefold() not in {"", "0", "false", "no", "off"}

    def _tls_context(self, endpoint: str) -> ssl.SSLContext | None:
        if self.selection.provider != "localai" or not endpoint.casefold().startswith("https://"):
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
