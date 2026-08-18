# helpme.green Knowledge Base Management UI — Implementation Plan v2

Status: implementation baseline and roadmap

Verified against `main` at `7c4a970` on 2026-08-18. The core operator console, upload lifecycle,
approved-only retrieval policy, durable jobs, graph provenance fields, and filtered artifact path
now exist in the repository. The phase plan below remains useful for separating what is implemented
from remaining polish and future multi-user or distribution work; it is not a claim that every
future phase is complete.

This document replaces the original “Obsidian-grade” plan as the execution baseline. It keeps the useful ideas—an operator-facing knowledge library, safe user-reference uploads, provenance visibility, and optional graph navigation—but makes the trust, persistence, and delivery boundaries explicit.

## Executive decision

Build an operator-only knowledge-base management console with an Obsidian-inspired navigation view. Do not describe v1 as an Obsidian replacement and do not make the graph the primary workflow.

The public product remains the ordinary-language Lab Notebook/conversation surface. The KB console is a controlled maintenance surface for reviewing reference material, inspecting provenance, and deciding whether a user-supplied document may participate in assistant retrieval.

The first useful release is:

```text
operator authentication
  → upload a supported reference file
  → bounded extraction and provenance registration
  → review queue
  → explicit approve or quarantine
  → approved-only retrieval
  → auditable deletion and artifact exclusion
```

Graph exploration, embeddings, and AI-generated source notes are optional layers after this path is reliable.

## 1. Goals and success criteria

### 1.1 Goals

The console should let an authorized operator:

1. See which sources and documents exist, their origin, status, provenance, extraction health, and processing state.
2. Upload bounded local reference files without silently adding them to the manifest or release artifacts.
3. Inspect extracted text and metadata before activation.
4. Approve, quarantine, retry, or remove user-uploaded material with clear consequences.
5. Understand why a document is related to another document without treating a graph link as evidence.
6. Trigger optional embeddings or source-linked navigation notes only when the provider policy allows it.
7. Rebuild a clean, manifest-only artifact for controlled distribution.

### 1.2 Success criteria

The release is successful when all of the following are true:

- The public notebook remains conversation-first and does not expose internal KB mechanics.
- The KB route is unavailable to unauthenticated operators and is disabled by default unless explicitly enabled.
- A review-status user upload cannot affect assistant retrieval, source cards, or model context.
- An approved user upload is still labelled as user-supplied and unverified; it is never presented as proof for a particular batch, machine, site, legal position, safety decision, or business outcome.
- Imported text cannot become application instructions or silently alter the system prompt.
- Upload, review, approval, quarantine, processing, and deletion events are preserved in the append-only audit chain without logging secrets or raw content.
- A distributable artifact contains no user-uploaded source, document, chunk, note, embedding, raw file, or user-derived metadata.
- Restarting the service does not lose or silently duplicate a queued job.
- The full verification gate passes, including an actual browser path and a non-domain ordinary-language prompt.

## 2. Binding boundaries

The existing product requirements and agent instructions remain authoritative.

### 2.1 Product boundary

- The assistant answers the user’s actual message before asking for more information.
- The public surface does not become a form, terminal, workflow engine, or database browser.
- Skills, retrieval, ranking, graph state, jobs, and internal labels stay out of user-facing assistant replies.
- The KB console is an operator surface, not a new public conversation mode.

### 2.2 Knowledge boundary

- The knowledge base is reference infrastructure, not a single source of truth.
- Manifest sources, user uploads, extracted text, source notes, embeddings, and model output remain distinct records.
- Every passage and note retains source identity, URL or explicit local-reference status, scope, publisher, jurisdiction, scale, licence note, limitations, fetch/extraction status, and content hashes through its joins.
- Graph relationships support provenance and navigation only. Graph connectivity is never proof of a material, legal, safety, or economic conclusion.

### 2.3 Security boundary

- User files, imported records, webpages, and model output are untrusted content.
- Raw uploaded content never becomes trusted application instructions.
- No provider key, encryption key, raw private file, or uncleared downloaded source enters Git, browser history, logs, tests, or documentation.
- The application does not authorize or execute physical, legal, financial, purchasing, shipment, production, permit, or release actions.
- Optional external processing is disabled by policy unless the operator explicitly enables it and the UI identifies the destination provider.

## 3. Current-baseline facts

The following facts were revalidated against the committed baseline rather than carried forward from
the original proposal:

- `KnowledgeDatabase` already owns sources, documents, chunks, FTS, embeddings, source notes, ingestion runs, and a graph projection.
- The graph schema carries directed/origin/reason fields, and the rebuild path derives bounded
  provenance relationships deterministically. A richer operator graph UI and performance work remain
  roadmap items.
- The upload extractor covers PDF, HTML/XML, TXT, CSV, JSON, and bounded XLSX content. XLSX safety
  checks and the `openpyxl` dependency are part of the upload path; manifest URL validation remains
  separate from local user-upload metadata.
- `SourceSpec` keeps HTTPS validation for manifest sources while user-upload sources use an explicit
  local-reference/nullable-URL model.
- The HTTP surface includes a separate bounded multipart upload path alongside the JSON routes.
- `KbService` exposes targeted per-document digest and embedding jobs, with policy checks, durable
  leases, and bounded startup recovery. This is distinct from the bulk source digest pipeline.
- Retrieval applies the shared source-origin/status predicate: manifest `blocked` and user-upload
  `review`, `blocked`, or `deleted` content are excluded; approved user uploads remain labelled as
  unverified reference material.
- The artifact packager creates a filtered SQLite snapshot and asserts that user-upload rows and
  derived content do not survive into a distributable artifact.

Any future change should revalidate these facts against the target commit because the worktree may
contain unrelated user changes.

## 4. Product model and terminology

### 4.1 Core entities

| Entity | Meaning | User-visible role |
|---|---|---|
| Source | Stable provenance identity and metadata | Publisher, URL/local status, scope, family, jurisdiction, tier, limitations |
| Document | One extracted content revision for a source | Version, hash, extraction state, preview |
| Chunk | Bounded retrieval unit belonging to a document | Search result and provenance anchor |
| Upload | Original user-provided file and storage record | File name, raw hash, validation, lifecycle |
| Job | Durable asynchronous operation | Progress, retry state, error, target |
| Source note | Compact source-linked navigation aid | Summary, applicability, limitations |
| Graph edge | Declared or deterministically derived navigation relationship | Relationship type and reason |

### 4.2 Separate lifecycle states

Do not collapse upload, extraction, review, and retrieval into one status field.

`uploads.status`:

```text
received → validated → processing → ingested | failed | deleted
```

`sources.source_status`:

```text
review → active
review → blocked
review → deleted
```

Manifest sources retain their existing catalogued/active/blocked semantics. User-uploaded sources must not silently become manifest sources.

`register_source` currently validates exactly `{catalogued, active, blocked}`; the migration must extend that validation set for user-upload sources without weakening manifest validation. The `deleted` status and the `deleted_at` tombstone are one event: the status flip and the tombstone stamp happen in the same transaction.

`documents.extraction_status`:

```text
pending | extracted | blocked:<reason> | failed:<reason>
```

`jobs.status`:

```text
queued | running | done | failed | cancelled
```

The UI must show both source review status and document extraction status when they differ.

### 4.3 Retrieval policy

| Origin | Source status | Retrieval |
|---|---|---|
| manifest | catalogued/active | allowed according to existing relevance policy |
| manifest | blocked | excluded |
| user-upload | review | excluded |
| user-upload | active | allowed only when relevant, with unverified label |
| user-upload | blocked/deleted | excluded |

Do not change the existing manifest behaviour by globally excluding every `catalogued` source. The predicate must distinguish manifest origin from user-upload origin.

Because source-status exclusion is new behaviour (see §3), add a regression test proving that a manifest `blocked` source is excluded by the same predicate that excludes user-upload `review` sources.

## 5. Architecture

```text
operator browser
  → authenticated KB HTTP routes
  → bounded request parser / upload storage
  → SQLite knowledge store
  → durable job queue
      ├─ extraction worker
      ├─ embedding worker (optional, policy-gated)
      └─ source-note worker (optional, policy-gated)
  → retrieval policy
  → untrusted reference-data message to the model
```

Keep the following responsibilities separate:

- `server.py`: routing, authentication, body limits, response codes, security headers.
- `upload_ingest.py`: multipart parsing, file validation, atomic storage, extraction orchestration.
- `knowledge_store.py`: transactions, schema, source/document/chunk state, retrieval predicates, graph projection.
- `job_store.py` or an equivalent store service: job claiming, leases, retries, progress, recovery.
- `source_digest.py`: targeted source-note generation with bounded untrusted input.
- `conversation.py`: natural-language orchestration; it must not know how the KB UI stores files.
- `web.py`/static frontend: notebook view and operator KB view, sharing only visual tokens and safe request helpers.
- `package_knowledge_artifact.py`: filtered manifest-only snapshot creation and assertions.

Do not make the graph, upload handler, or digest worker a hidden extension of conversation orchestration.

## 6. Configuration and operator access

No new setting is required for the core conversation. The KB console should use explicit optional settings:

```text
HELPME_KB_ENABLED=0                         # safe default
HELPME_UPLOAD_DIR=.data/uploads             # optional location override
HELPME_KB_EXTERNAL_PROCESSING=0             # safe default; controls provider egress
HELPME_KB_MAX_FILE_BYTES=20971520           # optional bounded override
HELPME_KB_MAX_REQUEST_BYTES=...             # optional aggregate override
HELPME_KB_MAX_STORAGE_BYTES=...             # optional disk quota
```

Rules:

- Enabling the KB console requires the configured operator Bearer gate. Do not expose mutating KB routes merely because the global access token is absent.
- If the deployment intentionally permits loopback-only unauthenticated development, make that a separate explicit development setting and reject it when bound beyond loopback.
- The UI must not display provider keys or secret values.
- Embedding or digest options appear only when both the provider configuration and the external-processing policy permit them.
- When processing may leave the machine, show the provider identity and destination class before the operator confirms.

## 7. Schema and migration plan

### 7.1 Migration discipline

- Bump `store_meta.database_version` from its current value (`3`) and treat it as the single canonical schema key; stop relying on ad-hoc `ALTER TABLE` statements during open and drop any use of the legacy `schema_version` key.
- Add an explicit, idempotent migration runner; do not rely on a collection of untracked `ALTER TABLE` statements.
- Make a verified backup before migration when a local database exists.
- Test migration from an existing populated database, including old documents, blocked documents, embeddings, notes, FTS rows, graph rows, and ingestion history.
- Keep migrations forward-only and record the applied version in `store_meta`.

### 7.2 `sources` additions

Add or formalize:

```text
origin                  manifest | user-upload
source_status            existing manifest states plus review/deleted where applicable
url                     nullable only for user-upload local references
scope                   explicit source scope; never inferred from a material family
metadata_origin          declared | operator-supplied | system-default
reviewed_at             nullable timestamp
reviewed_by             nullable non-secret operator identifier
review_note              nullable operator rationale
deleted_at              nullable tombstone timestamp
```

Keep the raw source URL immutable for manifest sources. For user uploads, render “local upload; no public URL” rather than inventing a URL or using an empty string as a hidden sentinel.

### 7.3 `uploads`

```text
upload_id               UUID/text primary key
original_filename       display-only, sanitized at rendering time
storage_key              generated path/key; never derived from the raw filename
raw_sha256              full SHA-256 of uploaded bytes
size_bytes              bounded integer
declared_content_type   untrusted request metadata
detected_content_type   validator result
extension               normalized allowlisted extension
status                  received|validated|processing|ingested|failed|deleted
source_id               nullable until provenance registration
document_id             nullable until extraction
error_code              nullable stable error category
error_detail            nullable bounded human-readable detail
created_at              timestamp
updated_at              timestamp
deleted_at              nullable timestamp
```

Store the full raw hash. A short hash prefix may be used in a filename only after collision checking and must never be the only identity.

Keep raw file hash and extracted-text hash distinct. The document hash is the hash of normalized extracted content; it is not proof that two different files are the same source.

### 7.4 `jobs`

```text
job_id                  primary key
kind                    upload|extract|embed|digest|delete|graph-rebuild
target_id               upload/document/source identifier
status                  queued|running|done|failed|cancelled
step                    stable step code
progress_current       integer
progress_total         integer
detail                  bounded non-secret detail
error_code              nullable
error_detail            nullable bounded detail
attempts                integer
idempotency_key         nullable unique key
claimed_at              nullable timestamp
lease_until             nullable timestamp
created_at              timestamp
started_at              nullable timestamp
updated_at              timestamp
finished_at             nullable timestamp
```

On startup, recover expired `running` jobs according to a bounded retry policy. A completed job must be safe to retry without duplicating chunks, embeddings, notes, graph edges, or audit events.

### 7.5 Graph relations

Add fields that make graph semantics explicit:

```text
edge_type               relationship name
directed                boolean
edge_origin             declared | derived
reason_code             stable machine-readable code
reason_detail           deterministic human-readable explanation
projection_version      graph rebuild version
```

`supersedes` is directed. Undirected derived relationships use a canonical node ordering instead of two duplicate rows. Avoid materializing every same-publisher or same-jurisdiction pair by default.

### 7.6 Audit events

Reuse the append-only audit chain rather than creating a second informal log. Record events such as:

```text
kb.upload.accepted
kb.upload.rejected
kb.document.extracted
kb.source.approved
kb.source.quarantined
kb.job.started
kb.job.failed
kb.job.completed
kb.source.deleted
kb.artifact.filtered
```

Audit payloads may include IDs, hashes, status transitions, counts, and error codes. They must not include raw file content, prompt text, provider keys, or full user metadata when it could contain sensitive material.

The existing chain lives in the session store (`audit.jsonl`, hash-chained, keyed by session). KB events have no session, so the console must either inject the session store's appender into KB routes (with an empty session key) or run a KB-scoped chain with the identical format and verification. Pick one option, and verify chain integrity after KB mutations and after upload deletion.

## 8. Upload and ingestion pipeline

### 8.1 Request handling

1. Authenticate and authorize the KB route before reading the body.
2. Require `multipart/form-data` with a declared aggregate size, and reject unsupported transfer modes deliberately.
3. Stream each file to a private temporary file under the upload directory.
4. Enforce an exact maximum of 10 files per request, a per-file byte cap, an aggregate request cap, and a total storage quota.
5. Use a maintained streaming multipart parser or a separately reviewed/fuzz-tested standard-library parser. The “zero frontend dependency” preference must not weaken server-side parser safety.
6. Write atomically with exclusive file creation, restrictive permissions, and a generated storage key.
7. Hash bytes while streaming; never trust the supplied filename or content type.

### 8.2 Validation

Allowed v1 formats:

```text
PDF, HTML/XML, TXT, CSV, JSON, XLSX
```

Rejected v1 formats:

```text
images, XLSM, executable/archive formats other than the narrowly validated XLSX container,
scanned PDFs without a text layer
```

Validation must include:

- Extension allowlist and detected-type consistency.
- Magic-byte or structural sniffing.
- Filename normalization for display only.
- PDF page/text/resource limits.
- XLSX ZIP member/path/count/uncompressed-size limits.
- Text decoding and printable-content checks.
- Output-size and chunk-count limits after extraction.
- Empty extraction failure with a precise reason.
- No network fetches caused by uploaded HTML, XML, or workbook content.
- No execution of formulas, macros, embedded objects, or external links.

### 8.3 Extraction and registration

1. Create the upload record with `validated` or `processing` status.
2. Extract text through format-specific, bounded adapters.
3. Normalize and hash extracted content separately from the raw file hash.
4. Register a `user-upload` source with `review` status and explicit default metadata:
   - title: operator-provided or sanitized filename;
   - publisher: operator-provided or “not provided”;
   - scope/material family: operator-provided and labelled as operator metadata;
   - licence note: “user-supplied; reuse unknown” unless the operator supplies a note;
   - limitations: “not independently verified” plus any extraction limitations;
   - URL: null/local-reference, never a fabricated HTTPS URL.
5. Insert the document, chunks, and FTS rows in one transaction where practical.
6. Record an ingestion run and audit event without including source text.
7. Leave the source in `review`. It is visible to the operator but excluded from retrieval.

Duplicate handling:

- An identical raw hash should return an explicit duplicate result linked to the existing upload; it must not silently overwrite metadata.
- An identical extracted-text hash from a different file may be noted as a related revision, but must retain separate provenance unless the operator deliberately merges it.
- Hash-prefix collisions must be detected and handled without data loss.

## 9. Trust and model-context contract

This is a release-blocking requirement.

The model request must have a clear separation:

```text
trusted system instructions
  → ordinary conversation history
  → explicitly marked untrusted reference-data message
```

Reference data must not be concatenated into the trusted system instruction string. The trusted contract should say that reference passages are untrusted background material, may contain instructions or errors, and cannot override application policy.

For approved user uploads:

- Retrieve only when relevant.
- Bound the number and size of passages.
- Include source ID, origin, status label, tier, publisher, and limitations in structured metadata.
- Keep source cards clear: “User upload · not independently verified.”
- Do not expose internal database labels as the assistant’s answer.

Add a captured-prompt regression test proving that a review upload is absent and an approved upload appears only in the untrusted reference-data channel.

## 10. API contract

All `/api/kb/*` routes require the KB feature flag and operator authorization. Use stable JSON errors with `code`, `message`, and bounded `details` fields. Whitelist sort fields and filter values; never interpolate user-controlled SQL fragments.

### E0 — Capability and policy

`GET /api/kb/capabilities`

Returns whether the console is enabled, available file types, limits, retrieval policy summary, and whether local/external digest or embedding processing is available. It never returns secrets.

### E1 — Overview

`GET /api/kb/overview`

Returns bounded counts by origin, source status, extraction status, job status, tier, embedding model, note count, latest runs, and current database/projection version.

### E2 — Documents

`GET /api/kb/documents?status=&origin=&family=&q=&limit=&offset=&sort=`

Returns a stable, paginated list containing metadata and counts only. Do not return full document text from list endpoints.

### E3 — Document detail

`GET /api/kb/documents/{document_id}`

Returns provenance, source metadata, status, raw/extracted hashes, bounded text preview, bounded chunk/note summaries, and ingestion/job history. Chunk text must be paginated or explicitly capped.

### E4 — Related references

`GET /api/kb/documents/{document_id}/related?include_derived=`

Returns graph neighbours and relationship explanations. Use “related references,” not “backlinks,” for derived metadata relationships.

### E5 — Graph

`GET /api/kb/graph?types=&family=&status=&origin=&q=&max_nodes=&selected=`

Returns bounded nodes and edges, a `truncated` flag, `total_nodes`, projection version, and deterministic reason fields. Chunk nodes are excluded by default. Selected-document expansion is explicit and bounded.

### E6 — Upload

`POST /api/kb/uploads`

Streaming multipart request. Return `202 Accepted` with per-file `upload_id`, validation status, and `job_id` where processing is queued. Return `400/401/403/413/415/422/409` with stable error codes for malformed, unauthorized, oversized, unsupported, invalid, or duplicate requests.

### E7 — Jobs

`GET /api/kb/jobs?status=&limit=` and `GET /api/kb/jobs/{job_id}`

Return bounded progress and last error. Do not expose prompt text, raw content, provider keys, or stack traces.

### E8 — Review transitions

`POST /api/kb/uploads/{upload_id}/approve`

Atomically transitions the upload's registered source `review → active` after validating that the upload and latest document are usable, then appends an audit event. `uploads.status` remains `ingested` and never becomes `active`; the status change, retrieval-eligibility flip, and audit append happen in one transaction.

`POST /api/kb/uploads/{upload_id}/quarantine`

Transitions `review → blocked`, records a bounded reason, excludes retrieval, and appends an audit event.

`POST /api/kb/uploads/{upload_id}/retry`

Permitted only for retryable failures and idempotently creates a new job.

### E9 — Optional source notes

`POST /api/kb/documents/{document_id}/digest`

Queues a targeted source-note job. It is not “summarize for the assistant”; the UI should call it “Create source-linked navigation notes.” It may run on review material only when external-processing policy and operator confirmation allow it. Notes inherit the source’s review status for retrieval purposes.

### E10 — Optional embeddings

`POST /api/kb/documents/{document_id}/embed`

Queues an idempotent embedding job only when an embedding provider is configured and policy permits sending this content to that provider. The response and UI must identify whether the provider is local or external.

### E11 — Upload deletion

`DELETE /api/kb/uploads/{upload_id}`

User-upload only. Prefer a tombstone plus a bounded cleanup job so raw files, chunks, FTS rows, notes, graph nodes, and jobs are removed consistently. Preserve the audit event and non-sensitive hash/status record. Manifest sources return `403`.

## 11. Frontend information architecture

### 11.1 Public and operator views

Keep the notebook as the default route. The KB view may share the shell, theme, and safe request helper, but it must be capability-gated and visually distinct as an operator console.

Recommended navigation:

```text
Lab Notebook
Knowledge base
  ├─ Documents
  ├─ Review queue
  ├─ Jobs
  └─ Graph
```

Do not expose a KB link that opens an empty or unauthorized internal database view. Support `#kb`, reload, and back/forward only after authorization state is known.

### 11.2 Documents-first layout

The default KB view should prioritize the action operators perform most often:

```text
Header: title, counts, upload, search, filters
Review queue / documents table
Selected-document drawer or detail route
Optional graph tab
```

The table should show title, origin, status, extraction state, family, chunks, notes, updated time, and actions. Use textual status labels; color is supplementary.

The detail view should show:

- Source identity and provenance.
- Raw and extracted hashes.
- Declared versus operator-supplied metadata.
- Review status and clear transition actions.
- Bounded text preview.
- Extraction/job history.
- Related references with deterministic reasons.
- A plain explanation of what approval changes: “This document may become eligible for relevant assistant context.”

### 11.3 Upload flow

Use a dedicated panel or route rather than a small modal for long-running multi-file work.

```text
1. Select and validate files
2. Extract and show per-file progress
3. Review text preview and metadata
4. Choose optional local/external processing with disclosure
5. Ready for explicit approval
```

Approval is a separate deliberate action from upload completion. Do not auto-activate at the end of the wizard.

Metadata editing must preserve immutable original filename, raw hash, detected type, upload time, and extraction results. Editable fields are labelled as operator annotations, not verified publisher facts.

Error states must include:

- Missing operator authorization.
- Unsupported type or mismatched magic bytes.
- File/request/storage limit exceeded.
- Duplicate raw file.
- Empty or unreadable extraction.
- Malformed XLSX/PDF.
- Provider disabled or external processing disallowed.
- Job retryable versus permanently failed.
- Approval blocked because extraction or provenance is incomplete.

### 11.4 Accessibility and frontend safety

- Use native headings, tables, buttons, lists, and live regions.
- Keep dynamic text in DOM text nodes; never inject upload data with `innerHTML`.
- Use a real focus model for panels and dialogs; restore focus after close.
- Announce job state changes through `aria-live` without repeatedly stealing focus.
- Support keyboard access to every action, including review transitions.
- Keep reduced-motion behavior deterministic.
- Do not make graph interaction depend on hover or double-click.
- If using SVG, make nodes focusable and provide accessible labels plus a DOM list fallback. Do not describe “canvas keyboard navigation” while implementing SVG.
- Provide a related-reference table fallback for screen readers and users who do not use graph navigation.
- Test dark mode, high contrast, zoom, narrow mobile widths, and long filenames/error messages.

## 12. Graph design

The graph is a navigation aid, not the default management surface.

### 12.1 Default graph contents

Include source, document, material-family, and source-note nodes as useful. Exclude chunk nodes by default. Expand selected document neighbours on demand.

### 12.2 Relationship semantics

Always include existing structural relations such as `has_document`, `covers`, `contains`, and `has_note` where useful.

Add these cross-document relations only after defining their semantics:

- `supersedes`: directed version relationship within a source.
- `shares_family`: derived overlap, hidden by default when it would create noise.
- `same_publisher`: derived metadata relation, not an evidence relationship.
- `same_jurisdiction`: derived metadata relation, not an evidence relationship.

Each edge must expose:

```text
relationship type
declared or derived origin
reason code
plain reason text
source fields used to derive it
```

Generate the projection deterministically and support a full rebuild. Do not make graph correctness depend on incremental ingest order.

### 12.3 Performance

- Enforce server-side node and edge caps.
- Return `truncated` and total counts.
- Use lazy expansion for selected documents.
- Measure the current corpus and a deliberately dense synthetic graph.
- Record response size and render time in a smoke test; do not claim graph performance from a single small fixture.

## 13. Optional background processing

### 13.1 Worker rules

Worker execution model: v1 workers run as threads inside the server process and share the existing single-connection `KnowledgeDatabase` lock, so queue durability is the only new persistence requirement and the current concurrency model is preserved. If a separate worker process is ever introduced, enable WAL mode and a busy timeout first and re-run the concurrent upload/conversation tests under that mode.

- The HTTP request only validates, stores, and queues.
- Workers claim jobs with a lease and update progress transactionally.
- Extraction, embedding, digest, and cleanup jobs are idempotent.
- AI jobs have their own bounded concurrency so they do not starve ordinary conversation requests.
- Provider errors become stable job failures; stack traces stay in local diagnostics, not API responses.
- Stale jobs are recovered on startup.
- Shutdown stops new claims and allows bounded cleanup.

### 13.2 Digest rules

Source notes remain compact navigation aids linked to exact chunks. The digest contract must:

- Treat passages as untrusted reference data.
- Preserve conditional, vendor-reported, study-specific, and jurisdiction-specific wording.
- Never resolve source disagreement or generate a user-specific conclusion.
- Store applicability and limitations with every note.
- Report per-document/per-chunk failure counts without retaining raw prompts in job detail.

## 14. Verification plan

### 14.1 Schema and store tests

- Migration from the existing database version with populated data.
- URL validation: HTTPS required for manifest sources; nullable local reference only for user uploads.
- Origin/status validation and legal transition matrix.
- Raw-hash versus extracted-hash behavior.
- Duplicate upload handling and prefix collision handling.
- FTS and semantic retrieval policy for every origin/status combination.
- Graph rebuild determinism, directed supersedes, canonical derived edges, reason fields, and bounds.
- Tombstone/delete cleanup without breaking the audit chain.

### 14.2 Upload and parser tests

- One file, ten files, eleven files.
- Exact size limits and aggregate body limits.
- Missing filename, Unicode filename, path traversal, duplicate filename, malformed boundaries, binary boundary content, and truncated body.
- Content-type spoofing and magic-byte mismatch.
- Valid/invalid PDF, textless PDF, malformed XLSX, XLSX zip bomb limits, CSV/JSON decoding, empty extraction, and output-size limits.
- Atomic storage and cleanup after worker failure.

### 14.3 Security and trust tests

- All KB routes return `401` when the operator gate is required and `403` when the feature is disabled or the action is not permitted.
- Manifest sources cannot be approved, deleted, or overwritten by upload routes.
- Review/blocked/deleted uploads do not reach search or conversation context, and a manifest `blocked` source is excluded by the same status predicate.
- Approved user material appears only in the untrusted reference-data channel.
- Prompt-injection text cannot change application instructions.
- Raw user content is absent from audit payloads, logs, catalog exports, and release snapshots.
- External processing is impossible when policy is disabled, even if provider variables are present.

### 14.4 API and job tests

- Response shapes and stable error codes for E0–E11.
- Pagination, sorting allowlist, query bounds, and graph truncation.
- Idempotency, duplicate action submission, retry, lease expiry, restart recovery, and cancellation.
- `202`, `204`, `401`, `403`, `404`, `409`, `413`, `415`, and `422` behavior.
- Concurrent upload and conversation requests do not corrupt SQLite or starve ordinary messages.

### 14.5 Frontend and browser tests

- `node --check` on the actual static JavaScript file or extracted script, whichever is shipped.
- Functional DOM tests for review actions, errors, job progress, focus restoration, and route state.
- No untrusted value reaches `innerHTML`, unsafe URLs, or executable attributes.
- Keyboard-only upload/review flow.
- Reduced motion, dark mode, high contrast, zoom, mobile reflow, and long-content rendering.
- Browser flow against the live local server:
  1. authorize the operator;
  2. upload a small reference file;
  3. observe review status;
  4. verify it is absent from retrieval;
  5. approve it;
  6. send a relevant message and capture the untrusted reference context;
  7. quarantine/delete it and verify it disappears from retrieval;
  8. send a non-domain prompt and confirm it is not forced through the KB.

### 14.6 Full repository gate

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m mypy src
.venv/bin/python -m compileall -q src tests
bash scripts/verify_container.sh
```

Extend `scripts/verify_container.sh` only after the focused tests are stable. The Docker gate must exercise the same natural-language route as the local process and must include a restart during or after a queued job.

## 15. Delivery phases and exit gates

### P0 — Contract and migration design — complete

Deliver:

- State model and retrieval policy.
- Threat model and external-processing policy.
- Schema migration design.
- Auth/feature-flag behavior.
- Prompt-channel contract.
- Filtered-artifact design.

Exit gate: requirements review, migration fixture, and captured model-request contract approved.

### P1 — Safe upload to review queue — implemented baseline

Deliver:

- Schema migration to the current database version.
- Operator authentication/feature gate.
- Streaming upload parser and storage.
- Format validation and extractors, including bounded XLSX support.
- Upload/source/document/job records.
- Durable job records with startup recovery of interrupted `running` jobs and idempotent retry; lease expiry and concurrency tuning are P4.
- Review-only list/detail API.
- Audit events.

Exit gate: a valid upload reaches `review`; malformed, oversized, unsupported, and prompt-injection fixtures fail safely; no uploaded content reaches retrieval.

### P2 — Review and lifecycle controls — implemented baseline

Deliver:

- Approve, quarantine, retry, and upload deletion.
- Retrieval policy enforcement.
- Detail view with provenance and extraction history.
- Tombstone/cleanup behavior.
- Filtered artifact packaging and assertions.

Exit gate: review→active changes retrieval eligibility only after explicit approval; quarantine/delete removes eligibility and preserves audit integrity; a manifest `blocked` source is excluded by the same status predicate (regression-tested).

### P3 — Documents-first operator UI — implemented baseline

Deliver:

- Authenticated KB route.
- Overview, documents table, review queue, detail panel, filters, search, and jobs view.
- Accessible upload flow with progress and clear provider disclosure.
- Responsive, dark-mode, high-contrast, and reduced-motion support.

Exit gate: keyboard and browser flow passes on the live server; no public notebook regression.

### P4 — Optional processing jobs — implemented baseline; polish remains

Deliver:

- Targeted source-note jobs.
- Optional embedding jobs.
- Provider policy checks and disclosure.
- Worker lease expiry, concurrency bounds, progress reporting, and cancellation polish remain
  follow-up work; durability, startup recovery, and idempotent retry are implemented.

Exit gate: local/external provider behavior is tested separately; disabled policy prevents egress; jobs are idempotent.

### P5 — Graph navigation — implemented baseline; UI/performance polish remains

Deliver:

- Deterministic graph rebuild and bounded graph API.
- Related-reference panel with reason fields.
- SVG graph with DOM fallback and keyboard support.
- Lazy expansion, filters, reduced-motion layout, and performance measurements.

Exit gate: graph is useful for navigation on the current corpus and a dense synthetic fixture without being presented as evidence or truth.

### P6 — Documentation and release hygiene — in progress

Remaining roadmap items:

- `docs/knowledge-pipeline.md` update.
- Operator runbook for approval, quarantine, deletion, backup, migration, and provider policy.
- Artifact scrubbing documentation.
- API contract and threat-model documentation.
- Final Docker/browser verification.

Exit gate: clean verification report states what was tested, what remains local-only, and any source/provider-access limitation.

## 16. Risks and mitigations

| Risk | Mitigation |
|---|---|
| KB mutations exposed publicly | Feature flag plus fail-closed operator authentication |
| Prompt injection through uploaded text | Separate untrusted reference-data channel; captured-prompt tests |
| Multipart parser vulnerability | Streaming parser with limits, fuzz tests, and security review |
| ZIP/PDF resource exhaustion | Structural validation, decompression quotas, parser limits |
| Disk exhaustion | Aggregate request cap, total storage quota, retention and cleanup |
| Job loss after restart | Durable status, leases, recovery, retry limits, idempotency |
| User data in release artifact | Filtered SQLite snapshot plus content and origin assertions |
| Dense or misleading graph | Documents-first UI, derived-edge labels, lazy expansion, deterministic rebuild |
| External provider disclosure | Policy gate, provider identity, explicit per-action confirmation |
| Provenance overwritten by editing | Immutable upload facts plus separate operator annotations |
| Manifest regression | Migration tests and manifest-only registration tests |
| Public UX becomes a database browser | Keep KB operator-only and conversation surface unchanged |

## 17. Explicit v1 non-goals

- OCR or scanned-PDF recovery.
- Image/photo ingestion into the KB; notebook photos may be sent transiently to a configured vision model for assistant comparison but remain outside the KB.
- In-app editing of source documents.
- Citation parsing or automatic legal/source-quality adjudication.
- Automatic source merging across different uploads.
- Multi-user roles beyond the existing operator gate.
- Public sharing of user-uploaded material.
- Automatic upload activation.
- Model-generated graph relationships.
- Using graph connectivity as proof.
- Exporting user uploads into the checked-in manifest, `knowledge/`, or release assets.

## 18. Definition of done

The feature is complete only when:

1. The approved-only retrieval policy is enforced in code and tested.
2. The untrusted reference-data boundary is visible in captured provider requests.
3. Operator authentication, audit events, migrations, job recovery, and deletion semantics are complete.
4. The artifact packager proves that user uploads cannot be distributed.
5. The documents-first UI is usable without the graph.
6. The graph, if enabled, is bounded, accessible, deterministic, and labelled as navigation.
7. Targeted tests, full repository gates, Docker verification, and the live browser flow pass.
8. The handoff explicitly reports local-only data, provider configuration, source-access limitations, and any remaining operational risk.
