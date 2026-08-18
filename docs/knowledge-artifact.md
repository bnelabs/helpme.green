# Knowledge artifact distribution

The digested SQLite database is the most useful runtime asset, but it is not the legal source
archive and it is not safe to put the current local copy in the normal Git tree. The current local
snapshot is 212.9 MB and contains extracted source text, chunks, embeddings, ingestion history, and
source metadata from a corpus whose reuse terms are mixed.

## Current state

The checked-in [`knowledge/artifact-manifest.json`](../knowledge/artifact-manifest.json) records the
current local snapshot's checksums and coverage:

- logical KB digest: `5eec432bd869fabcf55b942081d64c17fa90885b9d753b32311671e67acae740`
- database file size: 212,910,080 bytes
- proposed gzip release asset: 75,003,282 bytes (not uploaded)
- registered sources: 153
- extracted documents: 121; blocked documents: 10
- latest searchable chunks: 6,069; latest embedded chunks: 6,069
- embedding model: `nvidia/nemotron-3-embed-1b:free`

Its status is currently `pending-redistribution-review`, so a fresh clone receives the manifest and
the reproducible source queue, but not the full local database. That is deliberate: the current
database includes material that has not been cleared for public redistribution source by source.
The checked-in artifact is a database-version-3 snapshot; the current runtime schema is version 4
and migrates an installed v3 database forward idempotently when it opens.

Git cannot run an arbitrary post-clone downloader. Once a reviewed artifact is published, the
supported flow is an explicit bootstrap command. This is safer and makes the download, checksum,
version, and licensing boundary visible to the operator.

## Clone and install a published digest

After `artifact-manifest.json` has `status: "ready"`, a user can run:

```bash
git clone https://github.com/bnelabs/helpme.green.git
cd helpme.green
python3 scripts/bootstrap_knowledge.py
```

The bootstrapper downloads the HTTPS release asset, checks its size and SHA-256, decompresses it to
a temporary file, runs SQLite integrity verification, and atomically installs `.data/knowledge.db`.
It does not need an AI provider key or a browser access token.

Lexical retrieval works from the installed database without a provider. The current snapshot's
vectors were created with `nvidia/nemotron-3-embed-1b:free`; semantic or hybrid query-time retrieval still needs
an embedding endpoint configured with the same model (or a deliberate re-embedding run for a new
model). A database artifact does not contain or imply an API key.

To make Docker use that checked-out database, keep the normal named-volume deployment unchanged and
opt into the host-data override:

```bash
export HELPME_MASTER_KEY="$(python3 -c 'import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')"
docker compose -f docker-compose.yml -f docker-compose.host-data.yml up -d --build
```

The override mounts the local `.data/` directory, so the container and host use the same verified
database. The default Compose file continues to use the persistent `helpme_data` volume for
operators who want an isolated runtime store.

## Private or controlled artifact

For a reviewed private release, the operator can supply the URL and both checksums without editing
the repository manifest:

```bash
python3 scripts/bootstrap_knowledge.py \
  --url 'https://artifact-host.example/helpme-green-knowledge.sqlite.gz' \
  --artifact-sha256 '<compressed-file-sha256>' \
  --database-sha256 '<sqlite-file-sha256>' \
  --compression gzip
```

The values above are placeholders. Do not put provider API keys, signed URLs, or private artifact
credentials in Git, documentation, or the manifest.

## Publishing a reviewed artifact

The packaging tool creates a stable, checkpointed copy rather than copying a live WAL database:

```bash
python3 scripts/package_knowledge_artifact.py \
  --db .data/knowledge.db \
  --output dist/helpme-green-knowledge-2026-08-11.sqlite.gz \
  --allow-unreviewed
```

It intentionally refuses to package unless the operator passes `--allow-unreviewed`. That flag is
only an explicit acknowledgement for a private, controlled transfer; it is not a licence review and
does not authorize a public release.

For a public release, the maintainer must first remove uncleared source text and user-derived data,
then:

1. package the scrubbed database and record the resulting artifact and database checksums;
2. upload the compressed file as a GitHub Release asset;
3. fill `artifact.url`, `artifact.sha256`, and `artifact.sizeBytes` in the checked-in manifest;
4. change `status` to `ready` only after downloading the asset into a clean directory and running
   the bootstrapper successfully;
5. commit the manifest and release notes with the source attribution and reuse boundary.

GitHub blocks regular repository files above 100 MiB. Release assets are the appropriate GitHub
distribution channel for a reviewed 212.9 MB-class artifact, but the release channel does not waive
copyright, database-right, privacy, or attribution obligations. See [GitHub's large-file guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)
and [release documentation](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).
