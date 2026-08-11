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
OpenAI-compatible endpoint.

## Why the DB is not committed

Uploading the raw SQLite file to GitHub would make extracted text, embeddings, and potentially
future user-derived candidate material part of repository history. It would also make source
licence review and deletion difficult. The portable snapshot plus the manifest gives GitHub the
reproducible identity and health of the KB without copying the underlying documents. If a governed
deployment later requires a DB artifact, publish an explicitly licensed, scrubbed export through a
private artifact store or release process after a licence and privacy review; do not add it to the
normal source tree by accident.
