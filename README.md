# helpme.green

helpme.green is Circular Econ AI Backed R&D: a local-first assistant for understanding materials,
objects, processes, machines, risks, and circular-economy possibilities.

It is for the public as well as practitioners. Someone can write “I have rubber”, “what can I do
with this dirty film?”, “is this machine suitable?”, or ask a completely unrelated question. The
assistant starts from the user’s actual words, uses a relevant knowledge slice when one exists, and
responds like a capable collaborator. It does not force a fixed questionnaire or introduce a local
download, source, machine, or material that is not relevant to the question.

The knowledge base is valuable reference infrastructure, not a single source of truth. Current
measurements, product markings, machine trials, local rules, professional judgement, and the user’s
actual material can change the answer.

## What runs today

- Conversation-first web application at `http://localhost:8080`.
- AI-backed answers through any supported OpenAI-compatible provider.
- Automatic local-model discovery through `localai:auto`; no model name is embedded in the image.
- Domain skills that focus context internally without exposing forms, commands, or labels.
- Local SQLite retrieval using full-text search, optional embeddings, hybrid ranking, and optional
  second-stage reranking.
- Source-aware machinery and process references.
- A separate digest pipeline for scientific, engineering, chemical, HSE, regulatory, industry, and
  low-tech resources.
- Read-only source, capability, health, and GraphQL endpoints for inspection and integration.
- A separate operator-only knowledge-base console for bounded uploads, review, provenance, jobs, and
  retrieval eligibility; it is disabled by default and is not part of the public notebook.
- A static newcomer onboarding page in [`website/`](website/) with the material-handling framework,
  real notebook screenshots, and binary/Docker/source getting-started routes.

The assistant may explain uncertainty, limitations, and what would make an answer more specific. It
does not pretend that a source passage proves a particular batch, machine, site, product, or business
outcome.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'

export HELPME_AI_ENABLED=1
export HELPME_MODEL='localai:auto'
export HELPME_LOCALAI_BASE_URL='http://127.0.0.1:8090/v1'
export HELPME_LOCALAI_TLS_VERIFY=1

PYTHONPATH=src .venv/bin/python -m helpme_green --serve --host 127.0.0.1 --port 8080
```

Open [http://localhost:8080](http://localhost:8080). Type a normal sentence. Enter sends; Shift+Enter
adds a line break; New conversation starts a fresh thread.

LocalAI does not need a provider key by default. Open Settings in the app to choose a supported
provider, model, model options, and app safeguards. A provider key entered there is stored only in
the encrypted local store when `HELPME_MASTER_KEY` is configured; it is never returned to the
browser or added to a conversation. The browser access-token field is a separate gate that appears
only when `HELPME_ACCESS_TOKEN` is explicitly configured.

## Run the local Docker deployment

```bash
export HELPME_MASTER_KEY="$(python3 -c 'import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')"
export HELPME_AI_ENABLED=1
export HELPME_MODEL='localai:auto'
export HELPME_LOCALAI_BASE_URL='http://127.0.0.1:8090/v1'

docker compose up -d --build
curl http://127.0.0.1:8080/healthz
```

Compose binds the service to loopback and persists sessions, audit history, the runtime database, and
source downloads in `helpme_data`. No particular local download is mounted into the conversation
runtime. Sources enter the answer only through the same relevance-ranked knowledge path used for any
other registered reference.

Model settings belong in `HELPME_MODEL_PROFILES` and are keyed by the advertised provider/model ID:

```bash
export HELPME_MODEL='localai:<model-id>'
export HELPME_MODEL_PROFILES='{"localai:<model-id>":{"temperature":1.0,"top_p":0.95,"top_k":64,"max_tokens":16384,"timeout_seconds":240,"chat_template_kwargs":{"reasoning_strength":"xhigh"}}}'
```

For image-assisted notebook comparisons, use a vision-capable model and mark that capability in its
external profile. The browser sends the original selected photos, selected library example images,
the saved page details, and labels to the configured provider when the user compares; raw image
bytes remain outside the server knowledge base and session ledger:

```bash
export HELPME_MODEL='openrouter:dots-studio/dots-3-note-preview:free'
export OPENROUTER_API_KEY='set-in-your-shell-or-secret-manager'
export HELPME_MODEL_PROFILES='{"openrouter:dots-studio/dots-3-note-preview:free":{"vision":true,"include_reasoning":false,"max_tokens":8192,"timeout_seconds":180,"context_window":512000}}'
export HELPME_MAX_VISION_IMAGE_BYTES=16777216
export HELPME_MAX_VISION_REQUEST_BYTES=67108864
```

Provider keys must stay outside the repository and conversation history. Settings accepts them only
through encrypted local storage. If the selected profile is not marked vision-capable, an image
request fails honestly instead of silently falling back to text-only analysis.

These settings are deployment configuration, not hardcoded model behavior. If a profile does not
specify `max_tokens`, the application omits it and lets the provider/model choose. The application
does not truncate the completed user-facing answer. Auxiliary quality checks may use smaller
requests; they never replace or shorten the main answer. Local quality checks run in every runtime;
configured AI critic calls default on in direct local settings, while the Docker Compose example
defaults to `HELPME_QUALITY_JUDGES=0`. Set it to `1` when the extra provider-backed review pass is
desired.

The gateway retries one transient provider failure by default. Set `HELPME_MODEL_RETRIES=0` to
disable retries, or choose a value from 0 to 3. `HELPME_MAX_MODEL_TIMEOUT_SECONDS` caps the
per-provider wait at 240 seconds by default, even when a profile requests a longer timeout.

Sessions, snapshots, and browser note history are retained indefinitely by default. No startup or
snapshot-creation pruning runs automatically. The explicit `SessionStore.prune_empty_sessions` and
`SessionStore.prune_snapshots` maintenance methods remain available when an operator deliberately
chooses cleanup. The read-only import boundary supports explicitly allowed JSON, CSV, XLSX, and
HTTPS reads for internal or CLI integrations, but the browser API does not expose arbitrary import.

## Knowledge digest

The checked-in [source manifest](knowledge/source-manifest.yml) is a broad, expandable queue covering
science, chemistry, engineering, machinery, HSE, regulation, industry practice, low-tech methods,
packaging, and circular-economy policy. Each source carries publisher, URL, material scope,
jurisdiction, scale, access mode, reuse note, and limitations.

Build or refresh the local working database:

```bash
PYTHONPATH=src .venv/bin/python -m helpme_green.knowledge_loop \
  --manifest knowledge/source-manifest.yml \
  --db .data/knowledge.db \
  --downloads .data/source-downloads \
  --export-catalog knowledge/catalog.snapshot.json
```

Configure embeddings with either an OpenRouter endpoint or a local OpenAI-compatible LocalAI
endpoint. When configured and enabled, query-time semantic/hybrid retrieval is used automatically.
Direct local runtime configuration defaults to enabled; the Docker Compose example defaults to
disabled until `HELPME_EMBEDDING_QUERY_ENABLED=1` is supplied:

```bash
export HELPME_EMBEDDING_BASE_URL='https://openrouter.ai/api/v1'
export HELPME_EMBEDDING_MODEL='nvidia/nemotron-3-embed-1b:free'
export HELPME_EMBEDDING_API_KEY='set-in-your-shell-or-secret-manager'
export HELPME_EMBEDDING_QUERY_ENABLED=1

PYTHONPATH=src .venv/bin/python -m helpme_green.knowledge_loop \
  --manifest knowledge/source-manifest.yml \
  --db .data/knowledge.db \
  --downloads .data/source-downloads \
  --export-catalog knowledge/catalog.snapshot.json \
  --embed
```

Reranking is an optional adapter. It is useful when the corpus grows or several sources use similar
language, but it is not required for lexical search and is never treated as a source-authority
judge. A configured reranker is used automatically when enabled. Direct local runtime configuration
defaults to enabled; the Docker Compose example defaults to disabled until
`HELPME_RERANK_ENABLED=1` is supplied.

The full SQLite digest and raw downloads remain outside the normal Git tree because they contain
extracted text and sources with mixed reuse terms. [knowledge/artifact-manifest.json](knowledge/artifact-manifest.json)
records the digest identity, checksums, coverage, and publication status. A reviewed release asset
can be installed explicitly with:

```bash
python3 scripts/bootstrap_knowledge.py
```

See [docs/knowledge-artifact.md](docs/knowledge-artifact.md) for the distribution boundary.

## How retrieval is used

```text
user message → relevant context selection → lexical/semantic retrieval
             → optional reranking → model answer → quality pass → natural reply
```

The model receives a small relevant context, not the entire database. When configured and enabled,
semantic embeddings, hybrid ranking, reranking, machine references, and independent quality critics
are used automatically to improve the answer; each remains bounded and relevance-filtered. Registered
source metadata and retrieval determine what is relevant; there is no special prompt path for a
particular download.
Graph relationships are useful for provenance and navigation; GraphQL is a read-only access surface,
not a replacement for retrieval or a truth authority.

## HTTP surfaces

- `GET /healthz` — process and audit-chain health; returns `503` when the local audit chain is invalid.
- `POST /api/sessions` — create a conversation session.
- `POST /api/sessions/{id}/message` — send ordinary language.
- `POST /api/sessions/{id}/message/stream` — stream progress and reply deltas as SSE.
- `GET /api/runtime/model` — return the configured provider/model identity without secrets.
- `GET /api/settings` and `POST /api/settings` — read or update validated local runtime settings;
  provider keys are write-only and never returned.
- `GET /api/sessions/{id}` — read a persisted session.
- `GET /api/expert/capabilities` — skills, machinery, reference health, and read-only capabilities.
- `GET /api/knowledge/sources` — source metadata, hashes, status, and limitations.
- `POST /graphql` — read-only source, machine, skill, search, graph, and digest queries.
- `/api/kb/*` — capability-gated operator routes for knowledge-base uploads, review, jobs, and
  provenance; see [the operator runbook](docs/kb-operator-runbook.md).

The browser conversation is the application’s primary user surface; its retrieval and digest
services remain available through read-only integration endpoints.

## Verification

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m mypy src
bash scripts/verify_container.sh
```

Retrieval regression evaluation:

```bash
PYTHONPATH=src .venv/bin/python scripts/evaluate_retrieval.py \
  --db .data/knowledge.db \
  --eval knowledge/retrieval-eval.yml \
  --output .data/retrieval-evaluation.json
```

## Repository map

- `src/helpme_green/application.py` — runtime assembly and conversation service.
- `src/helpme_green/conversation.py` — natural-language orchestration.
- `src/helpme_green/model_gateway.py` — provider/model routing and profiles.
- `src/helpme_green/settings.py` — validated runtime settings and encrypted BYOK integration.
- `src/helpme_green/knowledge_store.py` — SQLite source, chunk, vector, and graph projection.
- `src/helpme_green/kb_service.py` and `src/helpme_green/upload_ingest.py` — operator KB lifecycle,
  bounded uploads, review transitions, and jobs.
- `src/helpme_green/source_ingest.py` — bounded downloads, extraction, embeddings, and reranking.
- `src/helpme_green/knowledge.py` — source-catalog identity and digest.
- `src/helpme_green/machinery.py` — machine-reference catalog.
- `knowledge/` — source manifest, machine profiles, research register, retrieval benchmark, and
  distribution metadata.
- `docs/` — deployment, retrieval, pipeline, source reuse, artifact boundaries, and the
  [material-handling framework](docs/material-handling-framework.md).
- `website/` — static GitHub-ready onboarding page and visual evidence for the public surface.
- `docs/documentation-audit-2026-08-18.md` — current branch, release, and documentation consistency
  audit.

The project is advisory and educational. It helps people think, research, compare, and ask better
questions; it does not authorize physical, legal, financial, or operational action.

## Releases

Release policy, supported delivery targets, native bundle instructions, checksums, signing, and the
knowledge-artifact boundary are documented in [docs/release-process.md](docs/release-process.md).
The intended container release is a multi-platform Linux image; macOS and Windows hosts use the
Linux container through Docker Desktop. Native bundles are target-specific for Linux amd64/arm64,
macOS arm64/amd64, and Windows amd64/arm64, and require the release verification and signing gates
described there. The current source version is `0.1.0-rc.6`. The checked-in GitHub Actions release
workflow has built and smoke-tested six native bundles for the draft candidate, plus Python
distributions and a multi-platform container image. [Open the GitHub Releases page](https://github.com/bnelabs/helpme.green/releases)
for the current candidate and checksums; stable publication remains a maintainer decision because
macOS and Windows signing/notarization are still required. This is an early release candidate:
automated checks reduce risk, but occasional breakage, rough edges, and behavior changes are still
possible between candidates. The draft was built from tagged commit `955d8ed`; `main` has since
advanced to `95e137e`, so a future candidate is needed to package later main-branch changes.
