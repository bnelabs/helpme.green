# Knowledge pipeline and storage boundary

The knowledge base is a governed reference layer, not a single source of truth. It is designed to
make an answer more useful while preserving uncertainty, source disagreement, jurisdiction limits,
and the difference between a vendor description and an independently verified specification.

## What is tracked

- `knowledge/source-manifest.yml` registers candidate sources with publisher, URL, material family,
  jurisdiction, authority tier, scale, access mode, licence note, and limitations.
- `knowledge/machine-catalog.yml` records structured vendor-reference profiles for recycling,
  sorting, washing, granulation, extrusion, textile, paper, metals, cable, and sensor equipment.
  Every profile points back to one or more registered sources.
- `knowledge/catalog.snapshot.json` contains the database schema version, digest, source metadata,
  content hashes, extracted-document metadata, claim counts, and ingestion failures. It contains no
  source passages.
- `knowledge/artifact-manifest.json` records the digest file checksum, logical digest, coverage,
  and whether a reviewed runtime artifact is available for download.

The manifest deliberately mixes primary public bodies and regulators, peer-reviewed research,
industry specifications, manufacturer technical pages, community practice, and low-tech resources.
The tier is visible to the retrieval and review layers; it is not a confidence shortcut.

## What stays local

The default runtime locations are:

```text
.data/knowledge.db
.data/source-downloads/
```

The SQLite database contains extracted text, chunks, embeddings when configured, candidate claims,
reviews, graph projections, and ingestion history. The download directory contains bounded raw
copies plus hash metadata. Both are intentionally outside Git: source reuse terms vary, and the DB
is a derived working store rather than the legal source archive.

To rebuild or refresh them:

```bash
PYTHONPATH=src .venv/bin/python -m helpme_green.knowledge_loop \
  --manifest knowledge/source-manifest.yml \
  --db .data/knowledge.db \
  --downloads .data/source-downloads \
  --export-catalog knowledge/catalog.snapshot.json
```

The operation is bounded to explicit HTTPS hosts and a per-source byte limit. A failed fetch,
empty extraction, access challenge, or unsupported format is recorded as a failed run; it is never
silently converted into a usable passage. Blocked documents remain in the audit trail but are
excluded from search and curation.

## AI-assisted digesting

`--curate` sends bounded passages to the configured model and stores only narrow candidate claims.
The curator cannot promote claims, change evidence state, resolve conflicts, or make a case
decision. Promotion requires independent reviews under the repository contract. Embeddings are
optional and provider-independent; use `--embed` only with an explicitly configured
OpenAI-compatible endpoint. Existing extracted documents are repaired incrementally: a digest run
does not need to redownload a document merely because its chunks lack vectors. Search can fuse FTS
and embeddings, while an opt-in reranker only reorders a bounded candidate pool. See
`docs/knowledge-retrieval.md` for the retrieval contract and benchmark.

## Why the current DB is not committed

Uploading the current raw SQLite file to the normal Git tree would make extracted text, embeddings,
and potentially future user-derived candidate material part of repository history. At 212.9 MB it
also exceeds GitHub's regular per-file limit. It would make source licence review, takedown, and
database-right analysis difficult.

The checked-in artifact manifest gives GitHub the reproducible identity and health of the local
digest without copying its passages. The supported distribution path is a versioned, compressed
GitHub Release asset or controlled private artifact, installed by
[`scripts/bootstrap_knowledge.py`](../scripts/bootstrap_knowledge.py) only after checksum and
SQLite-integrity verification. See [`docs/knowledge-artifact.md`](knowledge-artifact.md).

The current snapshot remains `pending-redistribution-review` because the 153-source corpus has mixed
reuse terms. A public artifact must be scrubbed and cleared source by source before the manifest can
be changed to `ready`.
