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

LocalAI does not need a user-entered API key. A browser access-token field appears only when
`HELPME_ACCESS_TOKEN` is explicitly configured. `HELPME_MASTER_KEY` protects optional encrypted
local provider-key storage; it is not a browser login token.

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

These settings are deployment configuration, not hardcoded model behavior. If a profile does not
specify `max_tokens`, the application omits it and lets the provider/model choose. The application
does not truncate the completed user-facing answer. Auxiliary quality checks may use smaller requests;
they never replace or shorten the main answer. Local quality checks are on by default; optional AI
critic calls are opt-in with `HELPME_QUALITY_JUDGES=1` because they add extra model requests and
latency on smaller local deployments.

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

Add embeddings only when an endpoint is intentionally configured:

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
judge.

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

The model receives a small relevant context, not the entire database. Registered source metadata and
retrieval determine what is relevant; there is no special prompt path for a particular download.
Graph relationships are useful for provenance and navigation; GraphQL is a read-only access surface,
not a replacement for retrieval or a truth authority.

## HTTP surfaces

- `GET /healthz` — process and audit-chain health.
- `POST /api/sessions` — create a conversation session.
- `POST /api/sessions/{id}/message` — send ordinary language.
- `GET /api/sessions/{id}` — read a persisted session.
- `GET /api/expert/capabilities` — skills, machinery, reference health, and read-only capabilities.
- `GET /api/knowledge/sources` — source metadata, hashes, status, and limitations.
- `POST /graphql` — read-only source, machine, skill, search, graph, and digest queries.

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
- `src/helpme_green/knowledge_store.py` — SQLite source, chunk, vector, and graph projection.
- `src/helpme_green/source_ingest.py` — bounded downloads, extraction, embeddings, and reranking.
- `src/helpme_green/knowledge.py` — source-catalog identity and digest.
- `src/helpme_green/machinery.py` — machine-reference catalog.
- `knowledge/` — source manifest, machine profiles, research register, retrieval benchmark, and
  distribution metadata.
- `docs/` — deployment, retrieval, pipeline, source reuse, and artifact boundaries.

The project is advisory and educational. It helps people think, research, compare, and ask better
questions; it does not authorize physical, legal, financial, or operational action.
