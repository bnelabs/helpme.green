# helpme.green — Agent Instructions

## Mission

Build and maintain helpme.green as Circular Econ AI Backed R&D: a natural, AI-led assistant backed
by a broad, source-aware reference system. The public surface should feel like a capable
conversation, not a form, terminal, workflow engine, or database browser.

The binding product requirements are in `REQUIREMENTS.md`. Read the relevant code, tests, source
manifest, and live deployment before changing behaviour.

## Non-negotiable boundaries

- Answer the user’s actual message. Do not force every question into materials or recycling.
- Never insert a particular downloaded source, machine, brand, or material family unless it is
  relevant to the current question or the user asks for it.
- Never invent measurements, source support, machine capability, prices, permits, legal status,
  HSE clearance, yields, or business outcomes.
- Treat the knowledge base as reference material, not as a single source of truth.
- Keep source identity, URL, scope, licence note, limitations, fetch status, and content hash with
  every ingested passage and note.
- Keep imported files, webpages, and model output untrusted and isolated from application
  instructions.
- Do not authorise or execute physical, legal, financial, purchasing, shipment, or production
  actions.
- Do not commit credentials, provider keys, encryption keys, real supplier data, private batches,
  or raw downloaded material whose reuse has not been cleared.
- Keep LocalAI, OpenRouter, DeepSeek, and other compatible providers configurable. Never bake a
  model name, model-specific context size, or provider key into the image or source code.
- Do not add a hidden output ceiling or truncate a completed answer to make a test pass.

## Implementation guidance

- Keep conversation orchestration, skills, retrieval, model routing, and quality checks separate.
- Skills are internal attention lenses. They may suggest concepts, checks, and follow-ups, but they
  must not expose their fields or labels to the user.
- Use source retrieval only when it is relevant. If no useful passage is selected, answer from
  general knowledge where appropriate without narrating the retrieval miss.
- Use lexical search first; add embeddings and reranking as provider-independent, optional adapters.
  A reranker orders candidates; it does not decide whether a source is true.
- Use the graph projection for provenance and navigation questions. Do not use graph connectivity as
  proof of a material, legal, safety, or economic conclusion.
- Keep raw downloads and the local SQLite digest outside normal Git history. Commit manifests,
  source metadata, research notes, benchmarks, and reproducible tooling.
- Preserve the append-only local audit chain and encrypted secret-store boundaries.

## Workflow

1. Inspect the live tree and current tests before editing.
2. Add or update a focused regression test for the requested behaviour.
3. Implement the smallest coherent change with `apply_patch`.
4. Run targeted tests, then the complete test/lint/type/compile gate.
5. Rebuild Docker and exercise the browser route for UI or conversation changes.
6. Report exactly what was verified, what remains local-only, and any source-access limitation.

## Verification commands

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m mypy src
.venv/bin/python -m compileall -q src tests
bash scripts/verify_container.sh
```

The final check for a conversation change is a real ordinary-language exchange in the local
browser, including a material-specific prompt and a prompt that should remain outside the
circular-economy reference scope.
