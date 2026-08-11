from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .knowledge_store import KnowledgeDatabase
from .source_ingest import (
    OfficialSourceFetcher,
    SourceManifest,
    embedding_provider_from_environment,
    ingest_manifest,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest whitelisted circular-economy source pages."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument(
        "--downloads",
        type=Path,
        default=None,
        help="separate local folder for raw source copies; never committed by default",
    )
    parser.add_argument(
        "--export-catalog",
        type=Path,
        default=None,
        help="write metadata and hashes (not source text) to a portable catalog JSON",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=32_000_000,
        help="maximum bytes per source download",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="download and extract the manifest pages; without this flag only metadata is registered",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="send extracted chunks to the configured OpenAI-compatible embedding endpoint",
    )
    parser.add_argument(
        "--embedding-batch-size",
        type=int,
        default=32,
        help="number of chunks per embedding request",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    manifest = SourceManifest.from_path(args.manifest)
    db_path = args.db or Path(os.environ.get("HELPME_DATA_DIR", ".data")) / "knowledge.db"
    download_dir = args.downloads or Path(
        os.environ.get("HELPME_SOURCE_DOWNLOAD_DIR", ".data/source-downloads")
    )
    database = KnowledgeDatabase(db_path)
    for source in manifest.sources:
        database.register_source(source, status="candidate")
    if args.fetch:
        provider = embedding_provider_from_environment() if args.embed else None
        results = ingest_manifest(
            manifest,
            database,
            fetcher=OfficialSourceFetcher(
                allowed_hosts=manifest.allowed_hosts,
                max_bytes=args.max_bytes,
                download_dir=download_dir,
            ),
            embedding_provider=provider,
            embedding_batch_size=args.embedding_batch_size,
        )
        exported = database.export_catalog(args.export_catalog) if args.export_catalog else None
        print(
            json.dumps(
                {
                    "database": str(database.path),
                    "ingested": [result.__dict__ for result in results],
                    "source_count": len(database.source_catalog()),
                    "ingestion": database.ingestion_summary(),
                    "digest": database.digest(),
                    "download_dir": str(download_dir),
                    "catalog": str(args.export_catalog) if exported else "",
                },
                ensure_ascii=False,
            )
        )
    else:
        exported = database.export_catalog(args.export_catalog) if args.export_catalog else None
        print(
            json.dumps(
                {
                    "database": str(database.path),
                    "registered": len(manifest.sources),
                    "fetch_required": True,
                    "source_count": len(database.source_catalog()),
                    "ingestion": database.ingestion_summary(),
                    "catalog": str(args.export_catalog) if exported else "",
                },
                ensure_ascii=False,
            )
        )
    database.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
