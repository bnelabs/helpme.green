#!/usr/bin/env python3
"""Run a small, source-ID-based retrieval regression report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from helpme_green.knowledge_store import KnowledgeDatabase, SearchResult
from helpme_green.source_ingest import (
    embedding_provider_from_environment,
    reranker_from_environment,
)


def _metric(rows: list[dict[str, Any]], mode: str, k: int) -> dict[str, float]:
    eligible = [row for row in rows if mode in row["modes"] and row["expectedAvailableSourceIds"]]
    if not eligible:
        return {"queries": 0, "hitRate": 0.0, "recallAtK": 0.0, "mrr": 0.0}
    hits = 0
    recall_total = 0.0
    reciprocal_total = 0.0
    for row in eligible:
        expected = set(row["expectedAvailableSourceIds"])
        found = [item["sourceId"] for item in row["modes"][mode][:k]]
        found_set = set(found)
        hits += int(bool(expected.intersection(found_set)))
        recall_total += len(expected.intersection(found_set)) / len(expected)
        reciprocal_total += next(
            (1.0 / (index + 1) for index, source_id in enumerate(found) if source_id in expected),
            0.0,
        )
    count = len(eligible)
    return {
        "queries": count,
        "hitRate": hits / count,
        "recallAtK": recall_total / count,
        "mrr": reciprocal_total / count,
    }


def _serialize(items: list[SearchResult]) -> list[dict[str, Any]]:
    return [
        {
            "sourceId": item.source_id,
            "chunkId": item.chunk_id,
            "retrievalMode": item.retrieval_mode,
            "score": item.score,
        }
        for item in items
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--eval", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=6)
    args = parser.parse_args()
    if args.limit <= 0:
        raise SystemExit("--limit must be positive")
    raw = yaml.safe_load(args.eval.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("queries"), list):
        raise SystemExit("Evaluation file must contain a queries list")
    database = KnowledgeDatabase(args.db)
    available_source_ids = database.latest_extracted_source_ids()
    embedding_provider = embedding_provider_from_environment()
    reranker = reranker_from_environment()
    rows: list[dict[str, Any]] = []
    try:
        for item in raw["queries"]:
            if not isinstance(item, dict):
                continue
            query = str(item.get("query", "")).strip()
            expected = [str(value) for value in item.get("expected_source_ids", [])]
            if not query or not expected:
                continue
            modes: dict[str, list[dict[str, Any]]] = {
                "lexical": _serialize(database.search(query, limit=args.limit))
            }
            if embedding_provider is not None:
                vectors = embedding_provider.embed([query])
                query_vector = vectors[0] if vectors else []
                modes["hybrid"] = _serialize(
                    database.hybrid_search(
                        query,
                        query_embedding=query_vector,
                        model=embedding_provider.model,
                        limit=args.limit,
                        reranker=None,
                    )
                )
                if reranker is not None:
                    modes["hybrid+rerank"] = _serialize(
                        database.hybrid_search(
                            query,
                            query_embedding=query_vector,
                            limit=args.limit,
                            reranker=reranker.rerank,
                        )
                    )
            rows.append(
                {
                    "id": str(item.get("id", "")),
                    "query": query,
                    "expectedSourceIds": expected,
                    "expectedAvailableSourceIds": [
                        source_id for source_id in expected if source_id in available_source_ids
                    ],
                    "unavailableExpectedSourceIds": [
                        source_id for source_id in expected if source_id not in available_source_ids
                    ],
                    "modes": modes,
                }
            )
    finally:
        database.close()
    report = {
        "reportVersion": 1,
        "database": str(args.db.resolve()),
        "embeddingModel": embedding_provider.model if embedding_provider else None,
        "rerankerModel": getattr(reranker, "model", None) if reranker else None,
        "k": args.limit,
        "sourceCoverage": {
            "latestExtractedSources": len(available_source_ids),
            "expectedSources": sum(len(row["expectedSourceIds"]) for row in rows),
            "availableExpectedSources": sum(len(row["expectedAvailableSourceIds"]) for row in rows),
            "unavailableExpectedSources": sorted(
                {source_id for row in rows for source_id in row["unavailableExpectedSourceIds"]}
            ),
        },
        "metrics": {
            mode: _metric(rows, mode, args.limit) for mode in ("lexical", "hybrid", "hybrid+rerank")
        },
        "queries": rows,
    }
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
