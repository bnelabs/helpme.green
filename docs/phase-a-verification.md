# Verification record: application and knowledge runtime

This record maps the current implementation to the binding contract in
[`REQUIREMENTS.md`](../REQUIREMENTS.md). It is an implementation verification record, not a
material-knowledge source or a substitute for qualified external review. The deterministic copper
workflow remains governed separately from the broader candidate reference corpus used by the
conversation surface.

## Governed inputs

- The copper-cable v0.2 and discovery v0.3 packs are copied verbatim from the reference commit
  recorded in [`vendor/reference/knowledge-manifest.json`](../vendor/reference/knowledge-manifest.json).
- The runtime verifies every manifest SHA-256 before loading a pack.
- Claims and route references are resolved through the copied source register; unregistered
  source IDs fail the knowledge load or deterministic evaluation.
- The multi-material candidate manifest is independently provenance-tagged and does not promote a
  downloaded passage into a deterministic conclusion.
- `knowledge/catalog.snapshot.json` is the checked-in digest health artifact; `.data/knowledge.db`
  and `.data/source-downloads/` remain local derived state.

## Candidate-only external material

The local Precious Plastic Download Kit V4.1 is recorded in
[vendor/candidates/precious-plastic-kit-v4.1.json](../vendor/candidates/precious-plastic-kit-v4.1.json).
It is not part of the Phase A knowledge manifest and cannot affect copper-cable evaluation.
Its license, disclaimer, and future plastic-family use boundaries are governed by
[docs/open-source-reuse.md](open-source-reuse.md) and
[docs/open-source-integration.md](open-source-integration.md). The open-source register is
provenance and policy documentation, not an active claim pack.

## Invariant coverage

| Invariant | Deterministic control | Evidence |
| --- | --- | --- |
| R1 | User/MCP labels map only to hearsay, estimate, or unknown; elevated evidence requires qualified-review provenance and source IDs. | `domain.py`, `engine.py`, intake tests |
| R2 | Missing or weak mandatory requirements remain `UNKNOWN`/`WEAK_EVIDENCE` and route policy determines a block. | `engine.py`, empty-case test |
| R3 | User and MCP facts cannot become reviewed facts or knowledge claims automatically. | `domain.py`, `mcp.py`, provenance tests |
| R4 | Research-supported routes remain `RESEARCH_STAGE`; they are not presented as established financial routes. | `engine.py`, copied route cards |
| R5 | Claims and route outputs require registered source references with locations and limitations. | `knowledge.py`, provenance test |
| R6 | Unsupported geography produces `R6_JURISDICTION_NOT_COVERED` and blocks routes. | `invariants.py`, jurisdiction test |
| R7 | Phase A always returns `value: null`; incomplete economics remain explicit blockers. | `engine.py`, 100-case gate |
| R8 | Intake and explainer contracts are bounded; the console routes commands to deterministic operations. | `intake.py`, `explainer.py`, `console.py` |
| R9 | The deterministic evaluator remains limited to the loaded copper-cable family and covered geography; the conversation reference catalog may cover more families but cannot create a deterministic conclusion outside the governed evaluator. | `knowledge.py`, `engine.py`, `knowledge_store.py` |
| R10 | Missing or merely declared contamination evidence produces an R10 block and a screening action. | `invariants.py`, contamination tests |
| R11 | The evaluator consumes facts and governed packs only; model selection cannot write a conclusion. | `engine.py`, `model_gateway.py`, cross-model gate |
| R12 | Results expose rules, evidence states, claims, source references, blocks, and next actions. | `engine.py`, `explainer.py` |

## Executed gates

From the repository root:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m mypy src
PYTHONPATH=src .venv/bin/python scripts/verify_phase_a.py
bash scripts/verify_container.sh
```

The verification script currently reports 100 representative evaluations, zero fabricated source
references, zero financial outputs, and identical deterministic output across DeepSeek/OpenRouter
selections.

The container image has also been built and exercised locally with a bearer token. A session was
created, an `unknown` contamination fact and immutable snapshot were recorded, the container was
restarted against the same data volume, and the session was read back with a valid audit chain.

## Knowledge and retrieval gates

The source pipeline is checked separately from the deterministic evaluator:

```bash
PYTHONPATH=src .venv/bin/python -m helpme_green.knowledge_loop \
  --manifest knowledge/source-manifest.yml \
  --db .data/knowledge.db \
  --downloads .data/source-downloads \
  --export-catalog knowledge/catalog.snapshot.json

PYTHONPATH=src .venv/bin/python scripts/evaluate_retrieval.py \
  --db .data/knowledge.db \
  --eval knowledge/retrieval-eval.yml \
  --output .data/retrieval-evaluation.json
```

The catalog reports registered sources, extracted documents, searchable chunks, embedding models,
candidate claims, graph projection health, and latest failed sources. A larger count is not a
quality claim. Retrieval evaluation is a regression instrument; source IDs in the small benchmark
are human-maintained relevance judgments, not a gold-standard truth set. Semantic and reranked
metrics are present only when the corresponding provider is deliberately configured.

## VPS status

[`deploy/vps/deploy.sh`](../deploy/vps/deploy.sh) is prepared for a dedicated VPS and requires
`HELPME_VPS_HOST`, `HELPME_VPS_USER`, `HELPME_VPS_APP_DIR`, and `HELPME_VPS_ENV_FILE`. A dedicated
helpme.green target and pre-provisioned env-file were not available in the current environment, so
the remote deployment itself remains pending; the local Docker rehearsal does not claim to be a
VPS deployment.
