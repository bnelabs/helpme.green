# Knowledge Base Operator Runbook

The knowledge-base console is an operator-only maintenance surface for reviewing reference
material, inspecting provenance, and deciding whether a user-supplied document may participate in
assistant retrieval. It is disabled by default and never part of the public conversation.

## Enable the console

The console is fail-closed:

```text
HELPME_KB_ENABLED=1                 # default 0
HELPME_KB_ACCESS_TOKEN=<secret>     # required operator bearer gate
HELPME_UPLOAD_DIR=.data/uploads     # optional location override
HELPME_KB_MAX_FILE_BYTES=20971520   # optional per-file cap
HELPME_KB_MAX_REQUEST_BYTES=84000000  # optional aggregate request cap
HELPME_KB_MAX_STORAGE_BYTES=1073741824  # optional on-disk quota
HELPME_KB_EXTERNAL_PROCESSING=0     # default 0; controls provider egress
```

Rules:

- If `HELPME_KB_ENABLED` is off, every `/api/kb/*` route returns `403`.
- If the console is on but no operator token is configured, mutating and read routes return `403`
  (`kb_operator_unconfigured`). A correct token is required for access.
- Optional loopback-only development can use `HELPME_KB_ALLOW_LOOPBACK_DEV=1`, but it is refused
  when the server is bound beyond loopback.

The browser console is reached at `#kb` after authorizing with the operator key. The public
notebook remains the default route.

## Lifecycle

Uploads follow `received → validated → processing → ingested | failed | deleted`. A user-uploaded
source is registered in `review` and is **never** eligible for retrieval until an operator
explicitly approves it. Approval is a separate, deliberate action from upload completion.

- **Approve** — transitions `review → active`. The document becomes eligible for relevant
  assistant context, always labelled “User upload · not independently verified”.
- **Quarantine** — transitions `review|active → blocked` and removes retrieval eligibility.
- **Delete** — tombstones the upload and source and removes derived chunks, FTS rows, notes, graph
  nodes, and jobs. The raw file is removed; the audit event and a non-sensitive hash record remain.
- **Retry** — creates a new extraction job for a retryable failure.

Manifest sources cannot be approved, quarantined, deleted, or overwritten by the upload routes.

## Retrieval policy

| Origin | Status | Retrieval |
|---|---|---|
| manifest | catalogued / active | allowed by the existing relevance policy |
| manifest | blocked | excluded |
| user-upload | review | excluded |
| user-upload | active | allowed only when relevant, with the unverified label |
| user-upload | blocked / deleted | excluded |

The retrieval predicate is shared by lexical, semantic, and hybrid search, so a manifest `blocked`
source and a user-upload `review` source are excluded by the same rule.

## Trust boundary

Retrieved passages are sent to the model in a separate, explicitly marked **untrusted
reference-data message**, never concatenated into the trusted system instructions. The trusted
contract states that reference text is untrusted and cannot change application instructions.
Prompt-injection text in an uploaded file cannot become application instructions.

## Optional external processing

Embedding and source-note (digest) jobs are policy-gated. When `HELPME_KB_EXTERNAL_PROCESSING=0`,
queueing them returns `403` and no content leaves the machine, even if provider variables are
present. The UI identifies that processing may leave the machine before it is confirmed.

## Jobs and recovery

Jobs are durable rows with leases. On startup, expired `running` jobs are requeued within a bounded
retry budget (3 attempts) or marked failed. Completed jobs are safe to retry without duplicating
chunks, embeddings, notes, graph edges, or audit events.

## Database migration

The store uses a single canonical `store_meta.database_version` key. Opening an existing v3
database migrates it forward to v4 idempotently (sources gain `origin`, `metadata_origin`,
`reviewed_at`, `reviewed_by`, `review_note`, `deleted_at`, and a nullable URL; `uploads` and
`jobs` tables are created; graph edges gain reason fields). Make a verified backup before
upgrading a populated local database.

## Distribution hygiene

`scripts/package_knowledge_artifact.py` always scrubs user uploads from the packaged snapshot:
user-upload sources, documents, chunks, FTS rows, notes, graph nodes/edges, `uploads`, and `jobs`
are removed, and the packager asserts that no user-upload content survives. The artifact is a
manifest-only snapshot.

## Audit events

KB mutations are appended to the same hash-chained `audit.jsonl` (with an empty session key) used
by the conversation surface. Payloads contain IDs, hashes, status transitions, counts, and error
codes — never raw file content, prompt text, or provider keys. `GET /healthz` reports `degraded`
whenever the chain fails verification.
