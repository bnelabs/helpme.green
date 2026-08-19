from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from .persistence import SecretStore, canonical_json

_ARTIFACT_SCHEMA_VERSION = 1
_DATA_KEY_NAME = "prompt_artifact_key_v1"
_SESSION_ID_PATTERN = re.compile(r"[0-9a-f-]{36}\Z")
_ARTIFACT_ID_PATTERN = re.compile(r"[0-9a-f-]{36}\Z")


class PromptArtifactError(RuntimeError):
    """A protected prompt artifact could not be created or verified."""


@dataclass(frozen=True)
class PromptArtifactReference:
    artifact_id: str
    envelope_sha256: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> PromptArtifactReference:
        if (
            value.get("schema_version") != _ARTIFACT_SCHEMA_VERSION
            or not isinstance(value.get("artifact_id"), str)
            or not isinstance(value.get("envelope_sha256"), str)
        ):
            raise PromptArtifactError("Prompt artifact reference is invalid.")
        return cls(str(value["artifact_id"]), str(value["envelope_sha256"]))

    def to_dict(self) -> dict[str, str | int]:
        return {
            "schema_version": _ARTIFACT_SCHEMA_VERSION,
            "artifact_id": self.artifact_id,
            "envelope_sha256": self.envelope_sha256,
        }


class PromptArtifactStore:
    """Encrypt and retain exact model prompt envelopes outside session/API projections.

    The data-encryption key is itself stored in the existing encrypted secret store, so rotating
    the master key re-encrypts the key without requiring prompt artifacts to be rewritten.
    """

    def __init__(self, root: Path, *, secret_store: SecretStore) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            self.root.chmod(0o700)
        except OSError:
            pass
        try:
            self._fernet = Fernet(self._data_key(secret_store))
        except ValueError as exc:
            raise PromptArtifactError("The prompt-artifact encryption key is invalid.") from exc

    @staticmethod
    def _data_key(secret_store: SecretStore) -> bytes:
        try:
            if _DATA_KEY_NAME in secret_store.names():
                return secret_store.get(_DATA_KEY_NAME).encode("ascii")
            key = Fernet.generate_key()
            secret_store.set(_DATA_KEY_NAME, key.decode("ascii"))
            return key
        except (OSError, ValueError) as exc:
            raise PromptArtifactError("The prompt-artifact encryption key is unavailable.") from exc

    def write(
        self,
        session_id: str,
        attempt: int,
        envelope: dict[str, Any],
    ) -> PromptArtifactReference:
        self._validate_session_id(session_id)
        if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt <= 0:
            raise PromptArtifactError("Prompt artifact attempt must be a positive integer.")
        if not isinstance(envelope, dict):
            raise PromptArtifactError("Prompt artifact envelope must be an object.")
        if (
            envelope.get("schema_version") != _ARTIFACT_SCHEMA_VERSION
            or envelope.get("kind") != "model_prompt_envelope"
            or envelope.get("session_id") != session_id
            or envelope.get("attempt") != attempt
        ):
            raise PromptArtifactError("Prompt artifact envelope metadata is invalid.")
        try:
            plaintext = canonical_json(envelope).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise PromptArtifactError("Prompt artifact envelope must contain JSON values.") from exc
        artifact_id = str(uuid.uuid4())
        envelope_sha256 = hashlib.sha256(plaintext).hexdigest()
        record = {
            "schema_version": _ARTIFACT_SCHEMA_VERSION,
            "artifact_id": artifact_id,
            "session_id": session_id,
            "attempt": attempt,
            "envelope_sha256": envelope_sha256,
            "ciphertext": self._fernet.encrypt(plaintext).decode("ascii"),
        }
        session_root = self.root / session_id
        session_root.mkdir(parents=True, exist_ok=True)
        try:
            session_root.chmod(0o700)
        except OSError:
            pass
        target = session_root / f"{artifact_id}.json"
        temporary = session_root / f".{artifact_id}.{secrets.token_hex(6)}.tmp"
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write(canonical_json(record) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            temporary.chmod(0o600)
            os.replace(temporary, target)
        except (OSError, TypeError, ValueError) as exc:
            try:
                temporary.unlink()
            except OSError:
                pass
            raise PromptArtifactError("Prompt artifact could not be stored safely.") from exc
        return PromptArtifactReference(artifact_id, envelope_sha256)

    def read(self, session_id: str, reference: PromptArtifactReference) -> dict[str, Any]:
        self._validate_session_id(session_id)
        if not _ARTIFACT_ID_PATTERN.fullmatch(reference.artifact_id):
            raise PromptArtifactError("Prompt artifact identifier is invalid.")
        path = self.root / session_id / f"{reference.artifact_id}.json"
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if (
                not isinstance(record, dict)
                or record.get("schema_version") != _ARTIFACT_SCHEMA_VERSION
                or record.get("artifact_id") != reference.artifact_id
                or record.get("session_id") != session_id
                or record.get("envelope_sha256") != reference.envelope_sha256
            ):
                raise PromptArtifactError("Prompt artifact metadata is invalid.")
            ciphertext = record.get("ciphertext")
            if not isinstance(ciphertext, str):
                raise PromptArtifactError("Prompt artifact ciphertext is invalid.")
            plaintext = self._fernet.decrypt(ciphertext.encode("ascii"))
            if hashlib.sha256(plaintext).hexdigest() != reference.envelope_sha256:
                raise PromptArtifactError("Prompt artifact digest verification failed.")
            envelope = json.loads(plaintext.decode("utf-8"))
        except PromptArtifactError:
            raise
        except (OSError, UnicodeError, ValueError, KeyError, TypeError, InvalidToken) as exc:
            raise PromptArtifactError("Prompt artifact could not be decrypted safely.") from exc
        if not isinstance(envelope, dict):
            raise PromptArtifactError("Prompt artifact envelope is invalid.")
        if (
            envelope.get("schema_version") != _ARTIFACT_SCHEMA_VERSION
            or envelope.get("kind") != "model_prompt_envelope"
            or envelope.get("session_id") != session_id
            or not isinstance(envelope.get("attempt"), int)
        ):
            raise PromptArtifactError("Prompt artifact envelope metadata is invalid.")
        return envelope

    @staticmethod
    def _validate_session_id(session_id: str) -> None:
        if not isinstance(session_id, str) or not _SESSION_ID_PATTERN.fullmatch(session_id):
            raise PromptArtifactError("Prompt artifact session identifier is invalid.")


def prompt_artifacts_enabled() -> bool:
    raw = os.environ.get("HELPME_PROMPT_ARTIFACTS_ENABLED", "")
    return raw.casefold() in {"1", "true", "yes", "on"}
