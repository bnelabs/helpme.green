# Retrieval benchmark — 2026-08-11

This is a measured retrieval snapshot, not a claim that the knowledge base is complete or that a
retrieved passage is correct for a live material case.

## Corpus and coverage

- Registered sources: **153**
- Sources with a latest extracted document: **102**
- Latest searchable chunks: **6,069**
- Latest chunks embedded with `nvidia/nemotron-3-embed-1b:free`: **6,069**
- Expected source IDs in the benchmark: **28**
- Expected source IDs currently available to retrieve: **15**
- Expected source IDs unavailable because their latest content is not digested: **11**

The unavailable set is listed in the generated `.data/retrieval-evaluation.json` during local runs
and is represented by the manual-download queue. The benchmark excludes unavailable expected IDs
from quality scoring; it reports them as coverage instead of pretending they were searchable.

## Fixed query set results

The query set contains 12 ordinary-language questions spanning plastics, machinery, cable recovery,
HSE, policy, and waste controls. One query currently has no expected source available, so the scored
sample is 11 queries. `k = 6`; source diversity limits duplicate passages from one source.

| Mode | Queries scored | Hit rate | Recall@6 | MRR |
|---|---:|---:|---:|---:|
| Lexical FTS5 | 11 | 0.909 | 0.864 | 0.727 |
| Balanced hybrid RRF | 11 | 0.909 | 0.818 | **0.788** |
| Hybrid + free Nemotron VL reranker | 11 | 0.909 | **0.864** | 0.712 |

## Decision

1. Keep FTS5 because it is strong for exact regulation numbers, named polymers, machine families,
   and source-specific terminology.
2. Keep balanced hybrid retrieval as the semantic option because it produced the best first-hit
   ranking (MRR) in this small test. Do not claim that it increases overall recall yet.
3. Keep the free reranker opt-in. On this text-only corpus it restored Recall@6 but reduced MRR; the
   tested model is multimodal and may be more valuable after scanned diagrams, tables, or images
   are admitted into the corpus.
4. Do not couple a provider-specific model into the database contract. Embedding model identity is
   recorded, and a new model must pass this benchmark before replacing the current default.
5. After the manual downloads are imported, rerun the benchmark. The score should then include the
   legal, ECHA, and manufacturer sources currently missing from retrieval.

## Limitations

- The relevance set is small and human-maintained; it is not a gold answer set.
- Scores measure source retrieval, not factual accuracy, answer quality, safety, or legal validity.
- The source corpus has duplicate/overlapping vendor and legal references; source diversity limits
  reduce repetition but do not resolve source disagreement.
- The free endpoint’s provider behavior and availability may change. Public source text only should
  be sent to it; user case data remains outside this benchmark.
