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
        _gzip(stable_path, output_path)
        return {
            "artifact": str(output_path),
            "artifactSha256": _sha256(output_path),
            "artifactSizeBytes": output_path.stat().st_size,
            "databaseSha256": _sha256(stable_path),
            "databaseSizeBytes": stable_path.stat().st_size,
            "compression": "gzip",
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
