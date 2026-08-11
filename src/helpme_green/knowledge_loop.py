from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from .curator import KnowledgeCurator
from .expert_skills import SkillRegistry
from .knowledge_store import KnowledgeDatabase
from .model_gateway import ModelRouter
from .source_ingest import (
    OfficialSourceFetcher,
    SourceManifest,
    embedding_provider_from_environment,
    ingest_manifest,
)


def run_once(
    *,
    manifest_path: Path,
    database_path: Path,
    download_dir: Path,
    export_catalog: Path | None = None,
    embed: bool = False,
    curate: bool = False,
    max_bytes: int = 32_000_000,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    manifest = SourceManifest.from_path(manifest_path)
    database = KnowledgeDatabase(database_path)
    try:
        for source in manifest.sources:
            database.register_source(source, status="candidate")
        provider = embedding_provider_from_environment() if embed else None
        results = ingest_manifest(
            manifest,
            database,
            fetcher=OfficialSourceFetcher(
                allowed_hosts=manifest.allowed_hosts,
                max_bytes=max_bytes,
                download_dir=download_dir,
            ),
            embedding_provider=provider,
        )
        curator_data: dict[str, Any] = {}
        if curate:
            root = repository_root or manifest_path.parent.parent
            curator_data = (
                KnowledgeCurator(
                    ModelRouter(),
                    SkillRegistry.from_repository(root),
                )
                .run(database)
                .to_dict()
            )
        if export_catalog:
            database.export_catalog(export_catalog)
        return {
            "database": str(database.path),
            "downloadDir": str(download_dir.expanduser().resolve()),
            "ingested": [result.__dict__ for result in results],
            "sourceCount": len(database.source_catalog()),
            "ingestion": database.ingestion_summary(),
            "digest": database.digest(),
            "catalog": str(export_catalog.resolve()) if export_catalog else "",
            "curator": curator_data,
        }
    finally:
        database.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch, digest, and optionally curate the allowlisted knowledge manifest."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--downloads", type=Path, default=None)
    parser.add_argument("--export-catalog", type=Path, default=None)
    parser.add_argument("--embed", action="store_true")
    parser.add_argument("--curate", action="store_true")
    parser.add_argument("--max-bytes", type=int, default=32_000_000)
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=0,
        help="repeat after this interval; zero performs one run and exits",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.interval_seconds < 0:
        raise SystemExit("--interval-seconds must not be negative")
    data_dir = Path(os.environ.get("HELPME_DATA_DIR", ".data"))
    database_path = args.db or data_dir / "knowledge.db"
    download_dir = args.downloads or Path(
        os.environ.get("HELPME_SOURCE_DOWNLOAD_DIR", str(data_dir / "source-downloads"))
    )
    while True:
        print(
            json.dumps(
                run_once(
                    manifest_path=args.manifest,
                    database_path=database_path,
                    download_dir=download_dir,
                    export_catalog=args.export_catalog,
                    embed=args.embed,
                    curate=args.curate,
                    max_bytes=args.max_bytes,
                ),
                ensure_ascii=False,
            )
        )
        if args.interval_seconds == 0:
            return 0
        time.sleep(args.interval_seconds)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
