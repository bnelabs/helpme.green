from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import threading
import time
import uuid
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - the supported deployments are POSIX-based.
    fcntl = None  # type: ignore[assignment]

from cryptography.fernet import Fernet, InvalidToken


class SessionEventError(RuntimeError):
    """A session event log is invalid or cannot be durably updated."""


_SESSION_EVENT_TYPES = frozenset(
    {
        "session.created",
        "projection.imported",
        "conversation.turn",
        "message.user",
        "message.assistant",
        "understanding.updated",
        "context.compacted",
        "model.attempt",
        "model.completed",
        "model.failed",
    }
)


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
    working_context: list[dict[str, str]] = field(default_factory=list)
    understanding: dict[str, str] = field(default_factory=dict)
    event_seq: int = 0

    def __post_init__(self) -> None:
        if not self.working_context and self.conversation:
            self.working_context = [dict(item) for item in self.conversation]

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
            "working_context": self.working_context,
            "understanding": self.understanding,
            "event_seq": self.event_seq,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SessionState:
        raw_conversation = data.get("conversation", [])
        if not isinstance(raw_conversation, list):
            raise ValueError("Session conversation must be a list.")
        conversation = _parse_messages(raw_conversation, label="Session conversation")
        raw_working_context = data.get("working_context", conversation)
        working_context = _parse_messages(raw_working_context, label="Session working context")
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
            working_context=working_context,
            understanding=understanding,
            event_seq=_event_seq(data.get("event_seq", 0)),
        )


def _parse_messages(value: Any, *, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list.")
    messages: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError(f"{label} entries must be objects.")
        role = str(item.get("role", ""))
        content = item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            raise ValueError(f"{label} entries must contain a role and content.")
        messages.append({"role": role, "content": content})
    return messages


def _event_seq(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Session event_seq must be a non-negative integer.")
    return value


class SessionStore:
    def __init__(self, root: Path, *, knowledge_digest: str) -> None:
        self.root = root.resolve()
        self.knowledge_digest = knowledge_digest
        _mkdir_secure(self.root)
        _mkdir_secure(self.root / "sessions")
        _mkdir_secure(self.root / "snapshots")
        self.audit_path = self.root / "audit.jsonl"
        self._audit_lock = threading.RLock()
        self._audit_verification_signature: tuple[int, int, int] | None = None
        self._audit_verification_result: bool | None = None
        self._session_locks: dict[str, threading.RLock] = {}
        self._session_locks_guard = threading.Lock()
        if not self.audit_path.exists():
            self.audit_path.touch(mode=0o600)
        else:
            self.audit_path.chmod(0o600)

    def session_path(self, session_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f-]{36}", session_id):
            raise ValueError("Invalid session identifier.")
        return self.root / "sessions" / f"{session_id}.json"

    def session_events_path(self, session_id: str) -> Path:
        self.session_path(session_id)
        return self.root / "sessions" / f"{session_id}.events.jsonl"

    @contextmanager
    def session_lock(self, session_id: str) -> Iterator[None]:
        """Serialize a complete read-modify-write operation for one session in this process."""
        self.session_path(session_id)
        with self._session_locks_guard:
            lock = self._session_locks.setdefault(session_id, threading.RLock())
        with lock:
            yield

    @contextmanager
    def _session_events_handle(self, session_id: str, *, exclusive: bool) -> Iterator[Any]:
        path = self.session_events_path(session_id)
        with path.open("a+b") as handle:
            try:
                path.chmod(0o600)
            except OSError:
                pass
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
            try:
                yield handle
            finally:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def append_session_event(
        self, session_id: str, event_type: str, payload: Mapping[str, Any]
    ) -> int:
        """Append one durable, hash-linked semantic session event and return its sequence."""
        if event_type not in _SESSION_EVENT_TYPES:
            raise SessionEventError(f"Unknown session event type: {event_type!r}.")
        if not isinstance(payload, Mapping):
            raise SessionEventError("Session event payload must be an object.")
        try:
            canonical_json(payload)
        except (TypeError, ValueError) as exc:
            raise SessionEventError("Session event payload must contain JSON values.") from exc
        with self._session_events_handle(session_id, exclusive=True) as handle:
            records = self._read_session_event_records(handle, session_id)
            previous_hash = str(records[-1]["event_hash"]) if records else ""
            sequence = len(records) + 1
            event = {
                "schema_version": 1,
                "session_id": session_id,
                "seq": sequence,
                "event_type": event_type,
                "payload": dict(payload),
                "previous_hash": previous_hash,
            }
            event_hash = hashlib.sha256(canonical_json(event).encode("utf-8")).hexdigest()
            record = dict(event, event_hash=event_hash)
            handle.seek(0, os.SEEK_END)
            handle.write((canonical_json(record) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
            return sequence

    def load_session_events(self, session_id: str) -> list[dict[str, Any]]:
        path = self.session_events_path(session_id)
        if not path.exists():
            return []
        with self._session_events_handle(session_id, exclusive=False) as handle:
            return self._read_session_event_records(handle, session_id)

    @staticmethod
    def _read_session_event_records(handle: Any, session_id: str) -> list[dict[str, Any]]:
        handle.seek(0)
        raw = handle.read()
        if not raw:
            return []
        if not raw.endswith(b"\n"):
            raise SessionEventError("Session event log has an incomplete tail.")
        records: list[dict[str, Any]] = []
        previous_hash = ""
        try:
            lines = raw.decode("utf-8").splitlines()
            for expected_seq, line in enumerate(lines, start=1):
                record = json.loads(line)
                if not isinstance(record, Mapping):
                    raise SessionEventError("Session event record must be an object.")
                event = {
                    key: record[key]
                    for key in (
                        "schema_version",
                        "session_id",
                        "seq",
                        "event_type",
                        "payload",
                        "previous_hash",
                    )
                }
                if (
                    event["schema_version"] != 1
                    or event["session_id"] != session_id
                    or event["seq"] != expected_seq
                    or not isinstance(event["event_type"], str)
                    or event["event_type"] not in _SESSION_EVENT_TYPES
                    or not isinstance(event["payload"], Mapping)
                    or event["previous_hash"] != previous_hash
                ):
                    raise SessionEventError("Session event sequence or chain is invalid.")
                expected_hash = hashlib.sha256(canonical_json(event).encode("utf-8")).hexdigest()
                if record.get("event_hash") != expected_hash:
                    raise SessionEventError("Session event digest verification failed.")
                records.append(dict(record))
                previous_hash = expected_hash
        except (UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise SessionEventError("Session event log is not valid JSONL.") from exc
        return records

    def ensure_session_events(self, session: SessionState) -> None:
        """Create the initial event projection for a new or legacy session."""
        if self.load_session_events(session.session_id):
            return
        sequence = self.append_session_event(
            session.session_id,
            "session.created",
            {
                "topic": session.topic,
                "geography": session.geography,
                "model_identity": session.model_identity,
            },
        )
        session.event_seq = sequence
        if session.conversation or session.understanding:
            sequence = self.append_session_event(
                session.session_id,
                "projection.imported",
                {
                    "conversation": session.conversation,
                    "working_context": session.working_context,
                    "understanding": session.understanding,
                },
            )
            session.event_seq = sequence

    def save_session(self, session: SessionState) -> None:
        if not session.working_context and session.conversation:
            session.working_context = [dict(item) for item in session.conversation]
        self.ensure_session_events(session)
        records = self.load_session_events(session.session_id)
        projected = self._project_session(session, records)
        if not self._same_projection(projected, session):
            sequence = self.append_session_event(
                session.session_id,
                "projection.imported",
                {
                    "conversation": session.conversation,
                    "working_context": session.working_context,
                    "understanding": session.understanding,
                },
            )
            session.event_seq = sequence
        else:
            session.event_seq = len(records)
        target = self.session_path(session.session_id)
        temporary = target.with_suffix(f".json.{secrets.token_hex(6)}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write(canonical_json(session.to_dict()))
                handle.flush()
                os.fsync(handle.fileno())
            temporary.chmod(0o600)
            os.replace(temporary, target)
        except BaseException:
            try:
                temporary.unlink()
            except OSError:
                pass
            raise
        self.append_audit(
            session.session_id,
            "session.saved",
            {
                "conversation_turns": len(session.conversation),
                "working_context_messages": len(session.working_context),
                "event_seq": session.event_seq,
            },
        )

    def load_session(self, session_id: str) -> SessionState:
        session = SessionState.from_dict(
            json.loads(self.session_path(session_id).read_text(encoding="utf-8"))
        )
        if session.session_id != session_id:
            raise ValueError("Session identifier does not match its storage path.")
        records = self.load_session_events(session_id)
        return self._project_session(session, records) if records else session

    @staticmethod
    def _project_session(base: SessionState, records: Sequence[Mapping[str, Any]]) -> SessionState:
        conversation: list[dict[str, str]] = []
        working_context: list[dict[str, str]] = []
        understanding: dict[str, str] = {}
        topic = base.topic
        geography = base.geography
        model_identity = base.model_identity
        for record in records:
            event_type = str(record.get("event_type", ""))
            payload = record.get("payload", {})
            if not isinstance(payload, Mapping):
                raise SessionEventError("Session event payload must be an object.")
            if event_type == "session.created":
                topic = str(payload.get("topic", topic))
                geography = str(payload.get("geography", geography))
                model_identity = str(payload.get("model_identity", model_identity))
            elif event_type == "projection.imported":
                conversation = _parse_messages(
                    payload.get("conversation", []), label="Imported conversation"
                )
                working_context = _parse_messages(
                    payload.get("working_context", conversation), label="Imported working context"
                )
                raw_understanding = payload.get("understanding", {})
                if not isinstance(raw_understanding, Mapping):
                    raise SessionEventError("Imported understanding must be an object.")
                understanding = {
                    str(key): str(value)
                    for key, value in raw_understanding.items()
                    if isinstance(value, str)
                }
            elif event_type == "conversation.turn":
                user = payload.get("user")
                assistant = payload.get("assistant")
                if not isinstance(user, str) or not isinstance(assistant, str):
                    raise SessionEventError("Conversation turn messages must be strings.")
                turn = [
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": assistant},
                ]
                conversation.extend(turn)
                working_context.extend(dict(item) for item in turn)
                values = payload.get("understanding", {})
                if not isinstance(values, Mapping):
                    raise SessionEventError("Conversation understanding must be an object.")
                understanding.update(
                    {
                        str(key): str(value)
                        for key, value in values.items()
                        if isinstance(value, str) and value
                    }
                )
            elif event_type in {"message.user", "message.assistant"}:
                role = "user" if event_type == "message.user" else "assistant"
                content = payload.get("content")
                if not isinstance(content, str):
                    raise SessionEventError("Message event content must be a string.")
                message = {"role": role, "content": content}
                conversation.append(message)
                working_context.append(dict(message))
            elif event_type == "understanding.updated":
                values = payload.get("values", {})
                if not isinstance(values, Mapping):
                    raise SessionEventError("Understanding event values must be an object.")
                understanding.update(
                    {
                        str(key): str(value)
                        for key, value in values.items()
                        if isinstance(value, str) and value
                    }
                )
            elif event_type == "context.compacted":
                working_context = _parse_messages(
                    payload.get("working_context", []), label="Compacted working context"
                )
            elif event_type not in _SESSION_EVENT_TYPES:
                raise SessionEventError(f"Unknown session event type: {event_type!r}.")
        return SessionState(
            session_id=base.session_id,
            topic=topic,
            geography=geography,
            model_identity=model_identity,
            conversation=conversation,
            working_context=working_context or [dict(item) for item in conversation],
            understanding=understanding,
            event_seq=len(records),
        )

    @staticmethod
    def _same_projection(left: SessionState, right: SessionState) -> bool:
        return (
            left.topic == right.topic
            and left.geography == right.geography
            and left.model_identity == right.model_identity
            and left.conversation == right.conversation
            and left.working_context == right.working_context
            and left.understanding == right.understanding
        )

    def append_audit(self, session_id: str, event_type: str, payload: Mapping[str, Any]) -> str:
        with self._audit_lock:
            with self._audit_handle("a+b", exclusive=True) as handle:
                previous_hash = self._last_audit_hash(handle)
                event = {
                    "schema_version": 1,
                    "session_id": session_id,
                    "event_type": event_type,
                    "payload": self._audit_safe(payload),
                    "previous_hash": previous_hash,
                }
                event_hash = hashlib.sha256(canonical_json(event).encode("utf-8")).hexdigest()
                record = dict(event, event_hash=event_hash)
                handle.seek(0, os.SEEK_END)
                handle.write((canonical_json(record) + "\n").encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
                self._audit_verification_signature = None
                self._audit_verification_result = None
                return event_hash

    def verify_audit_chain(self) -> bool:
        with self._audit_lock:
            signature = self._audit_signature()
            if (
                signature is not None
                and signature == self._audit_verification_signature
                and self._audit_verification_result is not None
            ):
                return self._audit_verification_result
            previous_hash = ""
            valid = True
            try:
                with self._audit_handle("rb", exclusive=False) as handle:
                    raw_lines = handle.read().decode("utf-8").splitlines()
                for line in raw_lines:
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
                        valid = False
                        break
                    previous_hash = expected
            except (OSError, KeyError, TypeError, UnicodeError, ValueError, json.JSONDecodeError):
                valid = False
            self._audit_verification_signature = self._audit_signature()
            self._audit_verification_result = valid
            return valid

    def _audit_signature(self) -> tuple[int, int, int] | None:
        try:
            stat = self.audit_path.stat()
        except OSError:
            return None
        return (stat.st_ino, stat.st_size, stat.st_mtime_ns)

    @contextmanager
    def _audit_handle(self, mode: str, *, exclusive: bool) -> Iterator[Any]:
        with self.audit_path.open(mode) as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
            try:
                yield handle
            finally:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _last_audit_hash(handle: Any) -> str:
        handle.seek(0, os.SEEK_END)
        position = handle.tell()
        if position == 0:
            return ""
        buffer = b""
        while position:
            size = min(8192, position)
            position -= size
            handle.seek(position)
            buffer = handle.read(size) + buffer
            if b"\n" in buffer:
                break
        for line in reversed(buffer.splitlines()):
            if line.strip():
                record = json.loads(line.decode("utf-8"))
                return str(record["event_hash"])
        return ""

    def prune_empty_sessions(self, *, max_age_seconds: float = 7 * 24 * 60 * 60) -> int:
        """Remove only old, valid sessions that contain no conversation turns."""
        if not math.isfinite(max_age_seconds) or max_age_seconds <= 0:
            raise ValueError("Session retention must be positive.")
        cutoff = time.time() - max_age_seconds
        removed = 0
        for path in self.root.joinpath("sessions").glob("*.json"):
            try:
                session_id = path.stem
                self.session_path(session_id)
                with self.session_lock(session_id):
                    if path.stat().st_mtime >= cutoff:
                        continue
                    session = SessionState.from_dict(json.loads(path.read_text(encoding="utf-8")))
                    if session.conversation:
                        continue
                    path.unlink()
                    try:
                        self.session_events_path(session_id).unlink()
                    except FileNotFoundError:
                        pass
                    removed += 1
            except (FileNotFoundError, OSError, TypeError, ValueError, json.JSONDecodeError):
                continue
        return removed

    def prune_snapshots(self, session_id: str | None = None, *, max_per_session: int = 20) -> int:
        """Keep the newest snapshots while leaving the append-only audit history intact."""
        if max_per_session <= 0:
            raise ValueError("Snapshot retention must be positive.")
        if session_id is not None:
            self.session_path(session_id)
            directories: tuple[Path, ...] = (self.root / "snapshots" / session_id,)
        else:
            directories = tuple(
                path for path in (self.root / "snapshots").glob("*") if path.is_dir()
            )
        removed = 0
        for directory in directories:
            snapshots: list[tuple[float, Path]] = []
            for path in directory.glob("*.json"):
                try:
                    snapshots.append((path.stat().st_mtime, path))
                except FileNotFoundError:
                    continue
            snapshots.sort(key=lambda item: item[0], reverse=True)
            for _mtime, path in snapshots[max_per_session:]:
                try:
                    path.unlink()
                    removed += 1
                except FileNotFoundError:
                    pass
        return removed

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
        self.prune_snapshots(session.session_id)
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
        self._lock = threading.RLock()
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
        with self._lock:
            self._write_secret(name, secret, self._fernet)

    def get(self, name: str) -> str:
        with self._lock:
            try:
                record = json.loads(self._path(name).read_text(encoding="utf-8"))
                return self._fernet.decrypt(str(record["ciphertext"]).encode("ascii")).decode(
                    "utf-8"
                )
            except (OSError, KeyError, ValueError, InvalidToken) as exc:
                raise ValueError("Unable to decrypt requested key.") from exc

    def rotate_master_key(self, master_key: bytes | str) -> None:
        """Re-encrypt all stored provider keys under a new Fernet master key."""
        new_fernet = Fernet(
            master_key if isinstance(master_key, bytes) else master_key.encode("ascii")
        )
        with self._lock:
            secrets_to_rotate = [
                (path.stem, self.get(path.stem)) for path in self.root.glob("*.json")
            ]
            for name, secret in secrets_to_rotate:
                self._write_secret(name, secret, new_fernet)
            self._fernet = new_fernet

    def names(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(path.stem for path in self.root.glob("*.json")))

    def _write_secret(self, name: str, secret: str, fernet: Fernet) -> None:
        ciphertext = fernet.encrypt(secret.encode("utf-8")).decode("ascii")
        target = self._path(name)
        temporary = target.with_suffix(f".json.{secrets.token_hex(6)}.tmp")
        temporary.write_text(
            canonical_json({"name": name, "ciphertext": ciphertext}), encoding="utf-8"
        )
        temporary.chmod(0o600)
        os.replace(temporary, target)
