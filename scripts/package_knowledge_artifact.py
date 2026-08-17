#!/usr/bin/env python3
"""Create a stable gzip-compressed SQLite snapshot for a reviewed release."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

_CHUNK_SIZE = 1024 * 1024


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(_CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def _stable_copy(source_path: Path, destination_path: Path) -> None:
    source = sqlite3.connect(source_path)
    try:
        result = source.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise RuntimeError(f"source database failed integrity check: {result}")
        destination = sqlite3.connect(destination_path)
        try:
            source.backup(destination)
            result = destination.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise RuntimeError(f"stable copy failed integrity check: {result}")
        finally:
            destination.close()
    finally:
        source.close()


def _gzip(source_path: Path, destination_path: Path) -> None:
    with source_path.open("rb") as source, destination_path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0, compresslevel=9) as target:
            shutil.copyfileobj(source, target, length=_CHUNK_SIZE)


def _scrub_user_uploads(path: Path) -> dict[str, int]:
    """Remove user-uploaded sources and all derived rows from a distributable snapshot."""
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        table_row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'sources'"
        ).fetchone()
        if table_row is None:
            return {
                "userUploadSources": 0,
                "userUploadDocuments": 0,
                "userUploadChunks": 0,
                "userUploadNotes": 0,
                "uploads": 0,
                "jobs": 0,
            }
        source_ids = [
            str(row[0])
            for row in connection.execute(
                "SELECT source_id FROM sources WHERE origin = 'user-upload'"
            ).fetchall()
        ]
        counts: dict[str, int] = {
            "userUploadSources": len(source_ids),
            "userUploadDocuments": 0,
            "userUploadChunks": 0,
            "userUploadNotes": 0,
            "uploads": 0,
            "jobs": 0,
        }
        document_ids: list[str] = []
        chunk_ids: list[str] = []
        if source_ids:
            placeholders = ",".join("?" for _ in source_ids)
            document_ids = [
                str(row[0])
                for row in connection.execute(
                    f"SELECT document_id FROM documents WHERE source_id IN ({placeholders})",
                    source_ids,
                ).fetchall()
            ]
            counts["userUploadDocuments"] = len(document_ids)
            if document_ids:
                document_placeholders = ",".join("?" for _ in document_ids)
                chunk_ids = [
                    str(row[0])
                    for row in connection.execute(
                        f"SELECT chunk_id FROM chunks WHERE document_id IN ({document_placeholders})",
                        document_ids,
                    ).fetchall()
                ]
                counts["userUploadChunks"] = len(chunk_ids)
                if chunk_ids:
                    chunk_placeholders = ",".join("?" for _ in chunk_ids)
                    connection.execute(
                        f"DELETE FROM chunk_fts WHERE chunk_id IN ({chunk_placeholders})", chunk_ids
                    )
                    connection.execute(
                        f"DELETE FROM chunks WHERE chunk_id IN ({chunk_placeholders})", chunk_ids
                    )
                node_ids = [f"source:{item}" for item in source_ids] + document_ids + chunk_ids
                node_placeholders = ",".join("?" for _ in node_ids)
                connection.execute(
                    f"DELETE FROM graph_edges WHERE from_node IN ({node_placeholders}) "
                    f"OR to_node IN ({node_placeholders})",
                    (*node_ids, *node_ids),
                )
                connection.execute(
                    f"DELETE FROM graph_nodes WHERE node_id IN ({node_placeholders})", node_ids
                )
                connection.execute(
                    f"DELETE FROM documents WHERE document_id IN ({document_placeholders})",
                    document_ids,
                )
            counts["userUploadNotes"] = connection.execute(
                f"DELETE FROM source_notes WHERE source_id IN ({placeholders})", source_ids
            ).rowcount
        counts["uploads"] = connection.execute("DELETE FROM uploads").rowcount
        counts["jobs"] = connection.execute("DELETE FROM jobs").rowcount
        connection.execute("DELETE FROM sources WHERE origin = 'user-upload'")
        connection.commit()
        remaining_sources = connection.execute(
            "SELECT COUNT(*) FROM sources WHERE origin = 'user-upload'"
        ).fetchone()[0]
        remaining_uploads = connection.execute("SELECT COUNT(*) FROM uploads").fetchone()[0]
        if source_ids:
            remaining_fts = connection.execute(
                f"SELECT COUNT(*) FROM chunk_fts WHERE source_id IN "
                f"({','.join('?' for _ in source_ids)})",
                source_ids,
            ).fetchone()[0]
        else:
            remaining_fts = 0
        if remaining_sources or remaining_uploads or remaining_fts:
            raise RuntimeError("user-upload content survived artifact scrubbing")
        return counts
    finally:
        connection.close()


def package(source_path: Path, output_path: Path, *, allow_unreviewed: bool) -> dict[str, Any]:
    if not allow_unreviewed:
        raise RuntimeError(
            "Refusing to package an artifact without an explicit redistribution review. "
            "Pass --allow-unreviewed only for a private, controlled transfer."
        )
    source_path = source_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    if not source_path.is_file():
        raise RuntimeError(f"Source database does not exist: {source_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stable_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output_path.parent, prefix=".knowledge-stable-", suffix=".db", delete=False
        ) as temporary:
            stable_path = Path(temporary.name)
        _stable_copy(source_path, stable_path)
        scrubbed = _scrub_user_uploads(stable_path)
        _gzip(stable_path, output_path)
        return {
            "artifact": str(output_path),
            "artifactSha256": _sha256(output_path),
            "artifactSizeBytes": output_path.stat().st_size,
            "databaseSha256": _sha256(stable_path),
            "databaseSizeBytes": stable_path.stat().st_size,
            "compression": "gzip",
            "userUploadsScrubbed": scrubbed,
        }
    finally:
        if stable_path is not None:
            try:
                stable_path.unlink()
            except FileNotFoundError:
                pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a stable gzip knowledge database artifact after a redistribution review."
    )
    parser.add_argument("--db", type=Path, default=Path(".data/knowledge.db"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist/helpme-green-knowledge.sqlite.gz"),
    )
    parser.add_argument(
        "--allow-unreviewed",
        action="store_true",
        help="explicitly permit packaging for a private controlled transfer",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        print(json.dumps(package(args.db, args.output, allow_unreviewed=args.allow_unreviewed)))
    except (OSError, RuntimeError, sqlite3.Error) as exc:
        print(f"knowledge packaging failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
