from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _default_model_identity() -> str:
    identity = os.environ.get("HELPME_MODEL", "").strip()
    provider = os.environ.get("HELPME_PROVIDER", "localai").strip().casefold() or "localai"
    if identity:
        if ":" not in identity:
            return f"{provider}:{identity}"
        configured_provider, configured_model = identity.split(":", 1)
        if configured_provider.strip() and configured_model.strip():
            return f"{configured_provider.strip().casefold()}:{configured_model.strip()}"
    return f"{provider}:auto"


def _mkdir_secure(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        path.chmod(0o700)
    except OSError:
        pass


def _write_exclusive(path: Path, text: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


@dataclass
class SessionState:
    session_id: str
    topic: str
    geography: str
    model_identity: str = field(default_factory=_default_model_identity)
    conversation: list[dict[str, str]] = field(default_factory=list)
    understanding: dict[str, str] = field(default_factory=dict)

    @classmethod
    def new(cls, *, topic: str, geography: str) -> SessionState:
        return cls(session_id=str(uuid.uuid4()), topic=topic, geography=geography)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "geography": self.geography,
            "model_identity": self.model_identity,
            "conversation": self.conversation,
            "understanding": self.understanding,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SessionState:
        raw_conversation = data.get("conversation", [])
        if not isinstance(raw_conversation, list):
            raise ValueError("Session conversation must be a list.")
        conversation: list[dict[str, str]] = []
        for item in raw_conversation:
            if not isinstance(item, Mapping):
                raise ValueError("Session conversation entries must be objects.")
            role = str(item.get("role", ""))
            content = item.get("content")
            if role not in {"user", "assistant"} or not isinstance(content, str):
                raise ValueError("Session conversation entries must contain a role and content.")
            conversation.append({"role": role, "content": content})
        raw_understanding = data.get("understanding", {})
        if not isinstance(raw_understanding, Mapping):
            raise ValueError("Session understanding must be an object.")
        understanding = {
            str(key): str(value)
            for key, value in raw_understanding.items()
            if isinstance(value, str)
        }
        return cls(
            session_id=str(data["session_id"]),
            topic=str(data.get("topic", "")),
            geography=str(data.get("geography", "")),
            model_identity=str(data.get("model_identity", _default_model_identity())),
            conversation=conversation,
            understanding=understanding,
        )


class SessionStore:
    def __init__(self, root: Path, *, knowledge_digest: str) -> None:
        self.root = root.resolve()
        self.knowledge_digest = knowledge_digest
        _mkdir_secure(self.root)
        _mkdir_secure(self.root / "sessions")
        _mkdir_secure(self.root / "snapshots")
        self.audit_path = self.root / "audit.jsonl"
        self._audit_lock = threading.RLock()
        if not self.audit_path.exists():
            self.audit_path.touch(mode=0o600)
        else:
            self.audit_path.chmod(0o600)

    def session_path(self, session_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f-]{36}", session_id):
            raise ValueError("Invalid session identifier.")
        return self.root / "sessions" / f"{session_id}.json"

    def save_session(self, session: SessionState) -> None:
        target = self.session_path(session.session_id)
        temporary = target.with_suffix(f".json.{secrets.token_hex(6)}.tmp")
        temporary.write_text(canonical_json(session.to_dict()), encoding="utf-8")
        temporary.chmod(0o600)
        os.replace(temporary, target)
        self.append_audit(
            session.session_id,
            "session.saved",
            {"conversation_turns": len(session.conversation)},
        )

    def load_session(self, session_id: str) -> SessionState:
        session = SessionState.from_dict(
            json.loads(self.session_path(session_id).read_text(encoding="utf-8"))
        )
        if session.session_id != session_id:
            raise ValueError("Session identifier does not match its storage path.")
        return session

    def append_audit(self, session_id: str, event_type: str, payload: Mapping[str, Any]) -> str:
        with self._audit_lock:
            previous_hash = ""
            raw_lines = self.audit_path.read_text(encoding="utf-8").splitlines()
            if raw_lines:
                previous = json.loads(raw_lines[-1])
                previous_hash = str(previous["event_hash"])
            event = {
                "schema_version": 1,
                "session_id": session_id,
                "event_type": event_type,
                "payload": self._audit_safe(payload),
                "previous_hash": previous_hash,
            }
            event_hash = hashlib.sha256(canonical_json(event).encode("utf-8")).hexdigest()
            record = dict(event, event_hash=event_hash)
            with self.audit_path.open("a", encoding="utf-8") as handle:
                handle.write(canonical_json(record) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            return event_hash

    def verify_audit_chain(self) -> bool:
        with self._audit_lock:
            previous_hash = ""
            try:
                for line in self.audit_path.read_text(encoding="utf-8").splitlines():
                    record = json.loads(line)
                    event = {
                        key: record[key]
                        for key in (
                            "schema_version",
                            "session_id",
                            "event_type",
                            "payload",
                            "previous_hash",
                        )
                    }
                    expected = hashlib.sha256(canonical_json(event).encode("utf-8")).hexdigest()
                    if (
                        record.get("previous_hash") != previous_hash
                        or record.get("event_hash") != expected
                    ):
                        return False
                    previous_hash = expected
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                return False
            return True

    def create_snapshot(self, session: SessionState, *, snapshot_id: str | None = None) -> str:
        self.session_path(session.session_id)
        snapshot_id = snapshot_id or str(uuid.uuid4())
        if not re.fullmatch(r"[0-9a-f-]{36}", snapshot_id):
            raise ValueError("Invalid snapshot identifier.")
        directory = self.root / "snapshots" / session.session_id
        _mkdir_secure(directory)
        body = {
            "snapshot_id": snapshot_id,
            "session_id": session.session_id,
            "knowledge_digest": self.knowledge_digest,
            "snapshot": session.to_dict(),
        }
        body_hash = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
        record = dict(body, snapshot_sha256=body_hash)
        target = directory / f"{snapshot_id}.json"
        _write_exclusive(target, canonical_json(record))
        self.append_audit(
            session.session_id,
            "snapshot.created",
            {"snapshot_id": snapshot_id, "snapshot_sha256": body_hash},
        )
        return snapshot_id

    def load_snapshot(self, snapshot_id: str, *, session_id: str | None = None) -> SessionState:
        if not re.fullmatch(r"[0-9a-f-]{36}", snapshot_id):
            raise ValueError("Invalid snapshot identifier.")
        if session_id is None:
            matches = list((self.root / "snapshots").glob(f"*/{snapshot_id}.json"))
            if len(matches) != 1:
                raise FileNotFoundError("Snapshot is not uniquely addressable.")
            path = matches[0]
        else:
            self.session_path(session_id)
            path = self.root / "snapshots" / session_id / f"{snapshot_id}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        body = {
            key: record[key]
            for key in ("snapshot_id", "session_id", "knowledge_digest", "snapshot")
        }
        expected = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
        if record.get("snapshot_sha256") != expected:
            raise ValueError("Snapshot digest verification failed.")
        if record.get("knowledge_digest") != self.knowledge_digest:
            raise ValueError("Snapshot knowledge version does not match this runtime.")
        snapshot = SessionState.from_dict(record["snapshot"])
        if snapshot.session_id != str(record["session_id"]):
            raise ValueError("Snapshot session identifier does not match its record.")
        return snapshot

    @staticmethod
    def _audit_safe(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): "[REDACTED]"
                if any(
                    token in str(key).casefold()
                    for token in ("secret", "token", "password", "api_key")
                )
                else SessionStore._audit_safe(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [SessionStore._audit_safe(item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)


class SecretStore:
    """Encrypted-at-rest BYOK storage; plaintext is never persisted or audited."""

    def __init__(self, root: Path, *, master_key: bytes | str | None = None) -> None:
        self.root = root.resolve()
        _mkdir_secure(self.root)
        raw = master_key or os.environ.get("HELPME_MASTER_KEY")
        if raw is None:
            raise ValueError("HELPME_MASTER_KEY or an explicit master_key is required for /key.")
        self._fernet = Fernet(raw if isinstance(raw, bytes) else raw.encode("ascii"))

    def _path(self, name: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", name):
            raise ValueError("Invalid key name.")
        return self.root / f"{name}.json"

    def set(self, name: str, secret: str) -> None:
        if not secret:
            raise ValueError("Secret cannot be empty.")
        ciphertext = self._fernet.encrypt(secret.encode("utf-8")).decode("ascii")
        target = self._path(name)
        temporary = target.with_suffix(f".json.{secrets.token_hex(6)}.tmp")
        temporary.write_text(
            canonical_json({"name": name, "ciphertext": ciphertext}), encoding="utf-8"
        )
        temporary.chmod(0o600)
        os.replace(temporary, target)

    def get(self, name: str) -> str:
        try:
            record = json.loads(self._path(name).read_text(encoding="utf-8"))
            return self._fernet.decrypt(str(record["ciphertext"]).encode("ascii")).decode("utf-8")
        except (OSError, KeyError, ValueError, InvalidToken) as exc:
            raise ValueError("Unable to decrypt requested key.") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(path.stem for path in self.root.glob("*.json")))
