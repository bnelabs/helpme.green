# Knowledge retrieval and utilization

The knowledge base is a governed reference layer. It can make an answer more specific, expose
source disagreement, and point to the next verification step. It is never the sole source of truth:
current law, a laboratory result, a machine trial, a buyer specification, a permit, and the user's
actual material can all supersede a downloaded passage.

## Retrieval roles

The layers have different jobs:

1. **Lexical search (FTS5)** catches exact terms, regulation numbers, polymer names, machine model
   names, and unusual chemistry vocabulary.
2. **Embeddings** recover semantically related passages when the user describes a problem in
   ordinary language instead of the source's terminology.
3. **Hybrid search** is the default when a query embedding is enabled. It fuses lexical and semantic
   ranks with reciprocal-rank fusion so neither layer can silently replace the other.
4. **Reranking** is an optional second-stage precision step. It receives only the top hybrid
   candidates and reorders them; it is not the index and it is not a source-confidence judge.
5. **The graph projection** is for provenance and relationship questions: source → document →
   chunk, source → material family, and source/chunk → candidate claim. It is not a replacement for
   retrieval and it should not be used to infer a conclusion merely because two nodes are connected.
6. **GraphQL** is a read-only access surface over these capabilities. It is not the database, a
   vector index, or a truth authority. `search(mode: "lexical"|"semantic"|"hybrid")` is an API
   choice, while the SQLite store remains the local derived working store.

## Should a reranker be coupled?

Yes, as an optional adapter—not as a mandatory dependency in every conversation. The useful shape is:

```text
question
  ├─ FTS exact-term candidates ─┐
  └─ embedding candidates ──────┴─ RRF hybrid pool (about 24) ── optional reranker ── 3–6 passages
```

The reranker is worthwhile when the corpus grows, sources overlap, or precision matters more than a
small amount of latency. It is less useful for a tiny, clean corpus or an exact regulation-number
lookup. The implementation therefore fails back to hybrid/lexical results when the reranker is
missing, rate-limited, or returns an invalid response.

The current OpenRouter free reranker is an opt-in experiment. Free endpoints may have rate limits
and provider logging; only public source passages should be sent to them. User case details should
remain local unless the operator has deliberately accepted that data boundary.

## Embedding and reranker configuration

The embedding provider is OpenAI-compatible and provider-agnostic. For a public text-only corpus,
the current recommended test configuration is:

```bash
export HELPME_EMBEDDING_BASE_URL=https://openrouter.ai/api/v1
export HELPME_EMBEDDING_MODEL='nvidia/nemotron-3-embed-1b:free'
export HELPME_EMBEDDING_API_KEY='set-outside-the-repository'
export HELPME_EMBEDDING_TLS_VERIFY=1
```

Enable query-time semantic/hybrid retrieval only when the operator wants remote query embedding:

```bash
export HELPME_EMBEDDING_QUERY_ENABLED=1
```

Reranking is separately opt-in:

```bash
export HELPME_RERANK_ENABLED=1
export HELPME_RERANK_BASE_URL=https://openrouter.ai/api/v1
export HELPME_RERANK_MODEL='nvidia/llama-nemotron-rerank-vl-1b-v2:free'
export HELPME_RERANK_API_KEY='set-outside-the-repository'
export HELPME_RERANK_TLS_VERIFY=1
```

The exact model is configuration, not code. Changing provider or model creates a new embedding
model label in the health summary; chunks from different models are not mixed in semantic search.
Embedding refreshes are incremental and also repair an existing document whose chunks have no vector.

## Quality and source discipline

- Preserve source ID, URL, publisher, authority tier, jurisdiction, scale, limitations, and fetch
  hash with every passage.
- Keep candidate sources distinguishable from promoted governed knowledge.
- Use primary law and regulator material for legal gates; use peer-reviewed work for mechanism and
  process evidence; use manufacturers for declared machine capability; use community/low-tech
  material for orientation and failure modes.
- Never convert a vendor throughput into annual capacity, a policy statistic into project economics,
  or a review article into a batch acceptance decision.
- Treat a failed or challenge-blocked source as a coverage gap, not as a negative finding.
- Keep raw downloads and extracted SQLite local unless licensing, privacy, and redistribution rights
  have been reviewed. Commit the manifest, source register, catalog metadata, benchmark, and tooling.

## Evaluation

`knowledge/retrieval-eval.yml` is a small human-maintained query set. It is not a single source of
truth or a complete benchmark; it makes regressions visible. Run it against a local digest with:

```bash
PYTHONPATH=src .venv/bin/python scripts/evaluate_retrieval.py \
  --db .data/knowledge.db \
  --eval knowledge/retrieval-eval.yml \
  --output .data/retrieval-evaluation.json
```

The report compares lexical and, when an embedding provider is configured, hybrid and optional
reranked retrieval using hit rate, Recall@k, and reciprocal rank. It reports missing expected source
IDs instead of claiming answer quality from corpus size alone.

The latest checked-in interpretation is in
`knowledge/research/retrieval-benchmark-2026-08-11.md`. It records why the current free reranker is
not enabled by default and why model replacement must be benchmark-led.
