# helpme.green

helpme.green is a local-first, advisory circular-economy assistant. A person describes a material,
object, problem, or idea in ordinary language; the assistant responds conversationally, uses focused
domain skills and a governed reference corpus, and makes uncertainty visible.

It is deliberately not an approval engine. It does not decide that a batch is recyclable, safe,
legal, permitted, economically viable, or ready for sale. Those decisions require current facts,
qualified review, measurements, and accountable operators.

## What the project is now

The repository combines five cooperating layers:

- A conversation-first local web surface backed by a configurable OpenAI-compatible model. LocalAI
  can run without a user-entered API key; a browser token appears only when
  `HELPME_CONSOLE_TOKEN` is explicitly configured.
- A deterministic, reviewable evaluator for the governed case workflow. AI may understand, ask,
  translate, and explain; it cannot overwrite deterministic blocks or promote knowledge.
- A governed knowledge pipeline that registers source provenance, downloads bounded public sources,
  extracts text into a local SQLite working store, records candidate claims, and exposes health and
  hashes through a portable catalog snapshot.
- A provider-independent retrieval layer: exact lexical search, optional embeddings, hybrid rank
  fusion, and an opt-in second-stage reranker. Graph relationships support provenance and
  navigation; they are not a substitute for search or source review.
- Read-only compatibility surfaces for capability inspection, source catalog access, sessions, and
  GraphQL queries. The browser conversation remains the primary user experience.

## Start locally

Install the package and development tools:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

Point the app at a running LocalAI/llama-server-compatible endpoint. The model identity is
configuration, so do not copy Muse settings to another model:

```bash
export HELPME_AI_ENABLED=1
export HELPME_MODEL='localai:muse-glimmer-30B'
export HELPME_LOCALAI_BASE_URL='http://192.168.68.57:8090/v1'
export HELPME_LOCALAI_TLS_VERIFY=1
export HELPME_MODEL_PROFILES='{"localai:muse-glimmer-30B":{"temperature":1.0,"top_p":0.95,"top_k":64,"max_tokens":16384,"timeout_seconds":240,"chat_template_kwargs":{"reasoning_strength":"xhigh"}}}'

PYTHONPATH=src .venv/bin/python -m helpme_green --serve --host 127.0.0.1 --port 8080
```

Open [http://localhost:8080](http://localhost:8080). The useful first action is simply to write a
sentence, for example:

> I have mixed LDPE film from a greenhouse, with soil, moisture, labels, and some unknown clips. I
> want to know whether a small recycler should process it or sell it as a separated stream.

In the conversation surface, **Enter** sends and **Shift+Enter** adds a line break. **New
conversation** clears the current thread. The user should not need to learn slash commands,
schemas, evidence labels, or a token when local auth is disabled.

## Run the local Docker deployment

Docker is the reproducible local deployment. `HELPME_MASTER_KEY` is required by the encrypted local
storage layer; it is not the same thing as the optional browser console token.

```bash
export HELPME_MASTER_KEY="$(python3 -c 'import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')"
export HELPME_AI_ENABLED=1
export HELPME_MODEL='localai:muse-glimmer-30B'
export HELPME_LOCALAI_BASE_URL='http://192.168.68.57:8090/v1'
docker compose up -d --build
curl http://127.0.0.1:8080/healthz
```

Open [http://localhost:8080](http://localhost:8080). Leave `HELPME_CONSOLE_TOKEN` unset for a
local no-token browser. If it is set, the page will correctly show a token gate and use that token
for protected API calls.

The Compose volume `helpme_data` holds sessions, audit history, the runtime SQLite database, and
raw source downloads. The Precious Plastic kit is mounted read-only from
`HELPME_KIT_HOST_PATH` (default: `/Users/barisnacierzeren/Downloads/precious-plastic-kit`) and is
candidate orientation material, not a safety, legal, engineering, or financial approval.

## Build and digest the knowledge base

The checked-in manifest is the source queue. It covers scientific and chemical literature, official
law and regulator material, HSE, industry statistics, machinery pages and technical sheets, low-tech
practice, packaging guidance, and circular-economy policy. Every source retains publisher, URL,
jurisdiction, authority tier, scale, limitations, and access mode.

Build the host working store and portable metadata snapshot:

```bash
PYTHONPATH=src .venv/bin/python -m helpme_green.knowledge_loop \
  --manifest knowledge/source-manifest.yml \
  --db .data/knowledge.db \
  --downloads .data/source-downloads \
  --export-catalog knowledge/catalog.snapshot.json
```

Add `--embed` only when an embedding provider is deliberately configured. The operation is
incremental: an existing extracted document whose chunks have no vector will be embedded without
being downloaded again.

```bash
export HELPME_EMBEDDING_BASE_URL='https://openrouter.ai/api/v1'
export HELPME_EMBEDDING_MODEL='nvidia/nemotron-3-embed-1b:free'
export HELPME_EMBEDDING_API_KEY='set-in-your-shell-or-secret-manager'
export HELPME_EMBEDDING_TLS_VERIFY=1

PYTHONPATH=src .venv/bin/python -m helpme_green.knowledge_loop \
  --manifest knowledge/source-manifest.yml \
  --db .data/knowledge.db \
  --downloads .data/source-downloads \
  --export-catalog knowledge/catalog.snapshot.json \
  --embed
```

Populate the separate Docker runtime store when the running container should search the digest:

```bash
docker compose run --rm helpme-green \
  python -m helpme_green.knowledge_loop \
  --manifest /app/knowledge/source-manifest.yml \
  --db /app/.data/knowledge.db \
  --downloads /app/.data/source-downloads
```

To embed the Docker store, pass the embedding variables transiently through the command or a
Git-ignored environment file. Never put the key in `docker-compose.yml`, the manifest, a shell
script, a commit, or a catalog snapshot.

The raw downloads and `.data/knowledge.db` are intentionally untracked. They can contain extracted
copyrighted text, provider-generated vectors, and future candidate material. GitHub receives the
reproducible source queue, source research register, health/hash snapshot, retrieval benchmark,
and tooling—not an uncontrolled redistribution of the source archive.

If a source is blocked by a 403, challenge page, dynamic legal portal, 404, or unsupported format,
the run records the failure and excludes that content from usable retrieval. See the current
[manual-download queue](knowledge/research/manual-download-queue.md) for resources that can be
downloaded manually and added through a reviewed local import.

## Retrieval design

The recommended path is:

```text
user question → relevant skill → focused source context → lexical + semantic retrieval
             → optional reranker → model answer → quality gate → natural reply
```

- FTS5 catches exact polymer, regulation, chemistry, and machine terminology.
- Embeddings recover related passages expressed in different language.
- Hybrid retrieval fuses both rank lists and preserves source metadata.
- The reranker is optional and only sees a bounded candidate pool; it fails back safely.
- The graph projection preserves source/document/chunk/claim relationships and is useful for
  provenance and multi-hop navigation.
- GraphQL is a read-only access surface, not the truth layer or a replacement for the SQLite
  working store.

Query-time semantic/hybrid retrieval is separately opt-in:

```bash
export HELPME_EMBEDDING_QUERY_ENABLED=1
```

Reranking is separately opt-in:

```bash
export HELPME_RERANK_ENABLED=1
export HELPME_RERANK_BASE_URL='https://openrouter.ai/api/v1'
export HELPME_RERANK_MODEL='nvidia/llama-nemotron-rerank-vl-1b-v2:free'
export HELPME_RERANK_API_KEY='set-outside-the-repository'
```

Free remote endpoints should receive only public source text unless the operator has explicitly
accepted the privacy and logging boundary. See [docs/knowledge-retrieval.md](docs/knowledge-retrieval.md)
for the full process and [knowledge/retrieval-eval.yml](knowledge/retrieval-eval.yml) for the
human-maintained retrieval regression set.

## HTTP and GraphQL surfaces

With local authorization disabled, `/healthz` is public. Protected endpoints use the configured
bearer token when one is set:

- `GET /healthz` — process and audit-chain health.
- `POST /api/sessions` — create a case session.
- `POST /api/sessions/{id}/message` — send a natural-language message.
- `POST /api/sessions/{id}/command` — compatibility command API for controlled workflows.
- `GET /api/expert/capabilities` — skills, machines, MCP capabilities, and KB health.
- `GET /api/knowledge/sources` — source metadata, hashes, status, and limitations.
- `POST /graphql` — read-only skills, machines, sources, lexical/semantic/hybrid search, graph
  neighbors, and digest status.

Example read-only GraphQL query:

```graphql
{
  search(query: "mixed LDPE film moisture contamination", mode: "hybrid", limit: 4) {
    sourceId title authorityTier retrievalMode text score
  }
  status { sourceCount documentCount searchableChunks embeddedChunks failedSources }
}
```

## Verification

Run the repository checks:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m mypy src
PYTHONPATH=src .venv/bin/python scripts/verify_phase_a.py
bash scripts/verify_container.sh
```

Run retrieval evaluation against a local digest:

```bash
PYTHONPATH=src .venv/bin/python scripts/evaluate_retrieval.py \
  --db .data/knowledge.db \
  --eval knowledge/retrieval-eval.yml \
  --output .data/retrieval-evaluation.json
```

The benchmark reports hit rate, Recall@k, and reciprocal rank by retrieval mode. It is a regression
instrument, not a claim that the KB is complete or that a retrieved passage is correct for a live
case.

## Repository map

- `src/helpme_green/` — application, deterministic engine, conversation surface, source ingestion,
  SQLite store, retrieval, GraphQL projection, and model adapters.
- `knowledge/source-manifest.yml` — candidate source queue and provenance metadata.
- `knowledge/machine-catalog.yml` — vendor-reference machine profiles linked to source IDs.
- `knowledge/retrieval-eval.yml` — retrieval regression queries and expected source IDs.
- `knowledge/research/` — research registers, manual-download queue, and limitations.
- `knowledge/catalog.snapshot.json` — versioned metadata, hashes, extraction/retrieval health; no
  raw passages.
- `docs/knowledge-pipeline.md` — source lifecycle and storage boundary.
- `docs/knowledge-retrieval.md` — lexical/semantic/hybrid/reranker/graph utilization.
- `docs/deployment.md` — local Docker and dedicated deployment boundaries.
- `docs/phase-a-verification.md` — requirement-to-control and verification record.
- `REQUIREMENTS.md` — binding product/invariant contract.
- `AGENTS.md` — repository rules for coding agents.

The application remains advisory-only. It never fabricates a price, turns a user statement into
verified evidence, silently promotes a candidate source, or treats a graph edge as proof.
