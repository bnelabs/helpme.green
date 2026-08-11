# helpme.green

Autonomous, advisory decision support for the circular economy.

Write what you are dealing with in ordinary language. The assistant asks only
the next useful question, keeps a plain-language summary of what it heard, and
is candid when the available background cannot answer something.

- **Advisory only.** The system never approves or executes purchases, shipments,
  processes, experiments, legal classifications, or product releases.
- **Deterministic engine + governed knowledge base.** The AI can converse,
  translate, and explain, but it cannot write or override deterministic
  conclusions.
- **Conversation first.** The browser surface is a calm conversation, not a
  terminal, wizard, schema viewer, or evidence checklist.

## Status

Phase A implementation is now present as a Python package: the conversation-first local web
surface, LocalAI/OpenAI-compatible model routing, deterministic copper-cable evaluation,
immutable snapshots, append-only audit history, encrypted BYOK storage, and the reference
knowledge-pack provenance gate. The deterministic evaluator and compatibility command API remain
available underneath for controlled workflows; they are not the primary user experience. The full
requirements and plan are in
[REQUIREMENTS.md](REQUIREMENTS.md) — the binding contract for implementation.
`AGENTS.md` governs how coding agents (e.g. Codex) must operate in this repo.

## Documents

- `REQUIREMENTS.md` — consolidated v3.0 requirements & plan (codex goal brief).
- `AGENTS.md` — repository instructions and invariant rules for coding agents.
- `knowledge/` — governed reference packs plus the tiered multi-material source manifest,
  machinery catalog, and portable digest snapshot.
- `vendor/reference/knowledge-manifest.json` — reference commit and pack hashes.
- vendor/candidates/precious-plastic-kit-v4.1.json — candidate-only local kit provenance; excluded from Phase A.
- docs/open-source-reuse.md — point-in-time license and reuse register for external circular-economy projects.
- docs/open-source-integration.md — clean-room integration boundaries and invariant mapping.
- `docs/deployment.md` — dedicated-VPS container deployment and secret-boundary instructions.
- `docs/phase-a-verification.md` — requirement-to-control matrix and current verification record.
- `knowledge/source-manifest.yml` — the registered, tiered source queue across materials, science,
  chemistry, machinery, industry, low-tech practice, HSE, and regulation.
- `knowledge/machine-catalog.yml` — vendor-reference machine profiles linked back to registered
  technical sources; it is not a fitness guarantee or purchasing recommendation.
- `knowledge/catalog.snapshot.json` — versionable metadata, hashes, extraction health, and source
  status; it intentionally contains no downloaded source passages.

## Build the local knowledge store

Raw downloads and the extracted SQLite database live outside the tracked knowledge packs:

```bash
PYTHONPATH=src .venv/bin/python -m helpme_green.knowledge_loop \
  --manifest knowledge/source-manifest.yml \
  --db .data/knowledge.db \
  --downloads .data/source-downloads \
  --export-catalog knowledge/catalog.snapshot.json
```

The run is candidate-only. Failed or blocked sources stay registered with their reason; they are
not silently treated as evidence. `.data/knowledge.db` and `.data/source-downloads/` are ignored by
Git because the database contains extracted source text and downloaded documents may have
publisher-specific reuse terms. The checked-in snapshot is the portable audit/digest asset. Rebuild
the database from the manifest when the snapshot or source set changes. Use `--curate` only when an
AI provider is deliberately configured; it creates candidate claims and cannot promote them.

## Run locally

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
PYTHONPATH=src .venv/bin/python -m helpme_green
```

The local conversation surface is available with:

```bash
PYTHONPATH=src .venv/bin/python -m helpme_green --serve --host 127.0.0.1 --port 8080
```

Then open [http://localhost:8080](http://localhost:8080). Start with a sentence such as:

> I found a dusty light bulb in my workshop and want to understand what useful options I have.

The default provider is LocalAI at `HELPME_LOCALAI_BASE_URL`; LocalAI does not need a user-entered
API key. The browser only shows a token gate when `HELPME_CONSOLE_TOKEN` is explicitly configured.
Use **New conversation** in the header to clear the current thread without reloading. **Enter**
sends a message; **Shift+Enter** inserts a line break.

## Run in Docker

```bash
HELPME_MASTER_KEY="$(python3 -c 'import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')" \
  docker compose up -d --build
```

Open [http://localhost:8080](http://localhost:8080). The Precious Plastic Download Kit can be
mounted read-only with the default `HELPME_KIT_HOST_PATH`; it is used as candidate orientation
context only, not as safety, legal, engineering, or financial approval.

Compose keeps its runtime database and raw downloads in the `helpme_data` volume. Populate that
volume when you want the Docker instance to search the downloaded source passages:

```bash
env HELPME_MASTER_KEY="$(python3 -c 'import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')" \
  docker compose run --rm helpme-green \
  python -m helpme_green.knowledge_loop \
  --manifest /app/knowledge/source-manifest.yml \
  --db /app/.data/knowledge.db \
  --downloads /app/.data/source-downloads
```

The host command above is faster for rebuilding the checked-in digest snapshot; the Docker
command maintains a separate runtime copy for the container.

Configure additional read-only `/load` roots with repeated `--mcp-root` options or the
`HELPME_MCP_ROOTS` environment variable. HTTPS imports require explicit `--mcp-host` or
`HELPME_MCP_HOSTS` configuration.

The app remains advisory-only. `/value` remains blocked until the knowledge pack contains a
complete, source-backed economic basis; the compatibility command endpoint is not exposed as
instructions in the primary browser surface.

## Verification

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m mypy src
PYTHONPATH=src .venv/bin/python scripts/verify_phase_a.py
bash scripts/verify_container.sh
```

## Reference

The deterministic evaluation logic (navigator/compliance/economics evaluators)
has a reference implementation in the private `bnelabs/konverta-material-intelligence`
repository; reuse that logic where REQUIREMENTS.md calls for it, subject to the
boundaries in REQUIREMENTS.md §16.
