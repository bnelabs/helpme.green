#!/usr/bin/env python3
"""Download and install a verified, versioned knowledge SQLite artifact."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

_CHUNK_SIZE = 1024 * 1024
_DEFAULT_TIMEOUT = 120
_DEFAULT_MAX_ARTIFACT_BYTES = 4 * 1024 * 1024 * 1024
_SHA256_LENGTH = 64


class KnowledgeBootstrapError(RuntimeError):
    """Raised when a knowledge artifact cannot be safely installed."""


@dataclass(frozen=True)
class ArtifactSpec:
    status: str
    url: str
    compression: str
    artifact_sha256: str
    artifact_size_bytes: int
    database_sha256: str
    database_size_bytes: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(_CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_sha256(value: Any, field: str, *, required: bool) -> str:
    if not isinstance(value, str):
        if required or value not in (None, ""):
            raise KnowledgeBootstrapError(f"{field} must be a SHA-256 hex string.")
        return ""
    normalized = value.strip().lower()
    if not normalized and not required:
        return ""
    if len(normalized) != _SHA256_LENGTH or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise KnowledgeBootstrapError(f"{field} must be a SHA-256 hex string.")
    return normalized


def _require_nonnegative_int(value: Any, field: str, *, required: bool) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise KnowledgeBootstrapError(f"{field} must be a non-negative integer.")
    if required and value == 0:
        raise KnowledgeBootstrapError(f"{field} must be greater than zero for a ready artifact.")
    return value


def load_artifact_spec(path: Path) -> ArtifactSpec:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KnowledgeBootstrapError(f"Cannot read artifact manifest {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise KnowledgeBootstrapError("Artifact manifest must contain a JSON object.")

    status = payload.get("status")
    if status not in {"ready", "pending-redistribution-review", "local-only"}:
        raise KnowledgeBootstrapError("Artifact manifest has an unsupported status.")
    artifact = payload.get("artifact")
    database = payload.get("database")
    if not isinstance(artifact, dict) or not isinstance(database, dict):
        raise KnowledgeBootstrapError(
            "Artifact manifest must contain artifact and database objects."
        )

    url = artifact.get("url", "")
    if not isinstance(url, str):
        raise KnowledgeBootstrapError("artifact.url must be a string.")
    if url and urlparse(url).scheme != "https":
        raise KnowledgeBootstrapError("artifact.url must use HTTPS.")
    compression = artifact.get("compression")
    if compression not in {"none", "gzip"}:
        raise KnowledgeBootstrapError("artifact.compression must be 'none' or 'gzip'.")
    ready = status == "ready"
    return ArtifactSpec(
        status=status,
        url=url,
        compression=compression,
        artifact_sha256=_require_sha256(
            artifact.get("sha256", ""), "artifact.sha256", required=ready
        ),
        artifact_size_bytes=_require_nonnegative_int(
            artifact.get("sizeBytes", 0), "artifact.sizeBytes", required=ready
        ),
        database_sha256=_require_sha256(
            database.get("sha256", ""), "database.sha256", required=ready
        ),
        database_size_bytes=_require_nonnegative_int(
            database.get("sizeBytes", 0), "database.sizeBytes", required=ready
        ),
    )


def _validate_sqlite(path: Path) -> None:
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            result = connection.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise KnowledgeBootstrapError(f"SQLite integrity check failed for {path}: {result}")
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise KnowledgeBootstrapError(
            f"Downloaded artifact is not a readable SQLite database: {exc}"
        ) from exc


def _download(
    url: str, destination: Path, *, expected_size: int, max_bytes: int, timeout: int
) -> None:
    request = Request(url, headers={"User-Agent": "helpme.green knowledge bootstrap"})
    try:
        with urlopen(request, timeout=timeout) as response, destination.open("wb") as target:
            final_url = response.geturl() if hasattr(response, "geturl") else url
            if urlparse(final_url).scheme != "https":
                raise KnowledgeBootstrapError("Artifact download redirected away from HTTPS.")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_bytes:
                raise KnowledgeBootstrapError("Artifact exceeds the configured download limit.")
            total = 0
            while True:
                block = response.read(_CHUNK_SIZE)
                if not block:
                    break
                total += len(block)
                if total > max_bytes:
                    raise KnowledgeBootstrapError("Artifact exceeds the configured download limit.")
                target.write(block)
    except KnowledgeBootstrapError:
        raise
    except (OSError, ValueError) as exc:
        raise KnowledgeBootstrapError(f"Artifact download failed: {exc}") from exc
    if expected_size and destination.stat().st_size != expected_size:
        raise KnowledgeBootstrapError(
            f"Artifact size mismatch: expected {expected_size}, got {destination.stat().st_size}."
        )


def _unpack(artifact_path: Path, destination: Path, compression: str) -> None:
    source = gzip.open(artifact_path, "rb") if compression == "gzip" else artifact_path.open("rb")
    try:
        with source, destination.open("wb") as target:
            shutil.copyfileobj(source, target, length=_CHUNK_SIZE)
    except (OSError, gzip.BadGzipFile) as exc:
        raise KnowledgeBootstrapError(f"Artifact decompression failed: {exc}") from exc


def bootstrap(
    *,
    manifest_path: Path,
    database_path: Path,
    force: bool = False,
    url_override: str = "",
    artifact_sha256_override: str = "",
    database_sha256_override: str = "",
    compression_override: str = "",
    max_artifact_bytes: int = _DEFAULT_MAX_ARTIFACT_BYTES,
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    spec = load_artifact_spec(manifest_path)
    url = url_override or spec.url
    if not url:
        raise KnowledgeBootstrapError(
            "No public knowledge artifact is configured. The current digest is local-only until "
            "a scrubbed, licence-cleared release asset is published."
        )
    if urlparse(url).scheme != "https":
        raise KnowledgeBootstrapError("The knowledge artifact URL must use HTTPS.")
    if spec.status != "ready" and not url_override:
        raise KnowledgeBootstrapError(
            f"Artifact manifest status is {spec.status!r}; refusing an unpublished artifact. "
            "Use an explicit --url and checksum for a separately reviewed private artifact."
        )
    artifact_sha256 = _require_sha256(
        artifact_sha256_override or spec.artifact_sha256,
        "artifact SHA-256",
        required=True,
    )
    database_sha256 = database_sha256_override or spec.database_sha256
    if database_sha256:
        database_sha256 = _require_sha256(database_sha256, "database SHA-256", required=True)
    compression = compression_override or spec.compression
    if compression not in {"none", "gzip"}:
        raise KnowledgeBootstrapError("Compression must be 'none' or 'gzip'.")
    if max_artifact_bytes <= 0 or timeout <= 0:
        raise KnowledgeBootstrapError("Download limit and timeout must be positive.")

    database_path = database_path.expanduser().resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists() and not force:
        if database_sha256 and _sha256(database_path) == database_sha256:
            _validate_sqlite(database_path)
            return {
                "status": "already-present",
                "database": str(database_path),
                "databaseSha256": database_sha256,
            }
        raise KnowledgeBootstrapError(
            f"Database already exists at {database_path}; use --force only to replace it."
        )
    if force:
        sidecars = [Path(f"{database_path}-wal"), Path(f"{database_path}-shm")]
        if any(sidecar.exists() for sidecar in sidecars):
            raise KnowledgeBootstrapError(
                f"Refusing to replace {database_path} while SQLite sidecar files exist; stop the "
                "runtime and checkpoint or remove the sidecars first."
            )

    artifact_path: Path | None = None
    unpacked_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=database_path.parent,
            prefix=".knowledge-artifact-",
            suffix=".download",
            delete=False,
        ) as temporary:
            artifact_path = Path(temporary.name)
        _download(
            url,
            artifact_path,
            expected_size=spec.artifact_size_bytes if not url_override else 0,
            max_bytes=max_artifact_bytes,
            timeout=timeout,
        )
        actual_artifact_sha256 = _sha256(artifact_path)
        if actual_artifact_sha256 != artifact_sha256:
            raise KnowledgeBootstrapError(
                "Artifact checksum mismatch: "
                f"expected {artifact_sha256}, got {actual_artifact_sha256}."
            )
        with tempfile.NamedTemporaryFile(
            dir=database_path.parent, prefix=".knowledge-db-", suffix=".partial", delete=False
        ) as temporary:
            unpacked_path = Path(temporary.name)
        _unpack(artifact_path, unpacked_path, compression)
        actual_database_sha256 = _sha256(unpacked_path)
        if database_sha256 and actual_database_sha256 != database_sha256:
            raise KnowledgeBootstrapError(
                "Database checksum mismatch: "
                f"expected {database_sha256}, got {actual_database_sha256}."
            )
        if spec.database_size_bytes and not database_sha256_override:
            if unpacked_path.stat().st_size != spec.database_size_bytes:
                raise KnowledgeBootstrapError("Database size does not match the artifact manifest.")
        _validate_sqlite(unpacked_path)
        os.replace(unpacked_path, database_path)
        unpacked_path = None
        return {
            "status": "installed",
            "database": str(database_path),
            "databaseSha256": actual_database_sha256,
            "artifactSha256": actual_artifact_sha256,
            "artifactUrl": url,
        }
    finally:
        for temporary in (artifact_path, unpacked_path):
            if temporary is not None:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download and verify the versioned helpme.green knowledge SQLite artifact."
    )
    parser.add_argument("--manifest", type=Path, default=Path("knowledge/artifact-manifest.json"))
    parser.add_argument("--db", type=Path, default=Path(".data/knowledge.db"))
    parser.add_argument("--force", action="store_true", help="replace an existing database")
    parser.add_argument(
        "--url", default="", help="explicit HTTPS URL for a reviewed private artifact"
    )
    parser.add_argument("--artifact-sha256", default="")
    parser.add_argument("--database-sha256", default="")
    parser.add_argument("--compression", choices=("none", "gzip"), default="")
    parser.add_argument("--max-artifact-bytes", type=int, default=_DEFAULT_MAX_ARTIFACT_BYTES)
    parser.add_argument("--timeout", type=int, default=_DEFAULT_TIMEOUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = bootstrap(
            manifest_path=args.manifest,
            database_path=args.db,
            force=args.force,
            url_override=args.url,
            artifact_sha256_override=args.artifact_sha256,
            database_sha256_override=args.database_sha256,
            compression_override=args.compression,
            max_artifact_bytes=args.max_artifact_bytes,
            timeout=args.timeout,
        )
    except KnowledgeBootstrapError as exc:
        print(f"knowledge bootstrap failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
