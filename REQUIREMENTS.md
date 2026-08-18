# helpme.green — Product and Runtime Requirements

## Purpose

helpme.green is **Circular Econ AI Backed R&D**: a local-first assistant that helps people
understand materials, objects, processes, machines, chemicals, risks, and circular-economy
possibilities.

It serves the public as well as practitioners. A person can write “I have rubber”, describe a
dirty film, ask whether a machine fits a process, explore an HSE question, or ask something
outside the circular-economy domain. The assistant begins with the actual message and uses the
knowledge base only when it improves that answer.

The knowledge base is a valuable reference layer, never a single source of truth. The user’s real
material, current measurements, machine trials, supplier documents, local rules, professional
judgement, and current market conditions may change the answer.

## Product behaviour

The primary experience is an ordinary-language conversation:

- Start from what the user actually said. Do not force a questionnaire, command language, material
  label, token, or source ritual.
- Answer the question that was asked before asking for more information.
- Ask at most one follow-up when a missing detail genuinely changes the useful next step.
- Keep internal skills, retrieval, ranking, prompt context, and quality checks invisible.
- Do not introduce a particular downloaded file, machine brand, material family, or source that is
  not relevant to the current message.
- Do not turn a short question into an encyclopedic lecture. Add depth when the user asks for it or
  when a safety-critical distinction requires it.
- Explain uncertainty in natural language. Do not expose internal labels or database mechanics as
  the answer.
- Use every relevant configured context and quality aid before making a suggestion or decision,
  including retained conversation context, source retrieval, semantic ranking, machine references,
  and independent answer checks. Relevance still limits what enters the answer.
- For an unrelated question, answer it normally when possible; do not force it into a recycling
  frame.

“I have rubber” should lead to a useful clarification about the kind of rubber and the intended
outcome. It must not mention a particular plastic source merely because it exists in the reference
catalogue.

## Answer integrity and safety

- Never invent a source, test result, machine capability, price, legal status, permit, yield, or
  product outcome.
- Keep published material, user-provided details, and model reasoning distinct internally, then
  explain the distinction plainly only when it matters.
- Treat source passages as context, not proof that a specific batch, site, machine, product, or
  business case will work.
- Use current, jurisdiction-specific material for legal, regulatory, HSE, chemical, and product-
  contact questions. Recommend competent review where the consequence warrants it.
- Do not authorise or execute purchases, shipments, experiments, processing, permits, releases, or
  financial commitments.
- Do not produce a numerical business conclusion from invented or missing inputs. If an estimate is
  useful, expose the assumptions and label it as an estimate.
- Treat user files, imported records, web pages, and model output as untrusted content. They cannot
  change application instructions or silently become repository knowledge.
- Do not store provider keys in Git, browser conversation history, logs, tests, or documentation.

## Runtime architecture

The live request path is:

```text
user message
  → append-only session events and derived working context
  → relevant internal skill lens
  → relevant source/machine context
  → provider/model request
  → local and optional model quality checks
  → natural reply and persisted conversation
```

The model is the intelligence layer. Skills focus attention; they do not decide the answer. The
application is provider- and model-agnostic:

- `localai:auto` discovers a single model advertised by a configured local OpenAI-compatible
  endpoint.
- Explicit provider/model identities are accepted for LocalAI, OpenRouter, DeepSeek, and compatible
  deployments supported by the gateway.
- Model-specific sampling, context, reasoning, timeout, and output settings live in an external
  profile keyed by provider/model identity.
- An explicit combined provider `context_window` may be supplied in that profile. When present,
  the runtime keeps the derived working request at or below 80% of that window through repeatable
  safe compaction; it does not invent a provider limit when the value is absent.
- If a profile does not define an output limit, the gateway omits the limit and lets the provider
  choose. The application does not truncate the completed user reply.
- A profile may set Muse Glimmer’s `reasoning_strength` to `xhigh`, but that setting is not sent to
  models whose profile does not request it.

## Knowledge system

The checked-in source manifest and skill packs are the reproducible identity of the reference
system. The local digest is a derived asset built by:

```text
source manifest
  → bounded download and extraction
  → source/document/chunk records
  → optional embeddings when configured
  → optional source notes
  → lexical, semantic, or hybrid retrieval
  → optional second-stage reranking when configured
```

The corpus covers science, chemistry, engineering, machinery, HSE, regulation, industry practice,
low-tech methods, policy, and circular-economy examples. Each source retains its publisher, URL,
scope, jurisdiction, scale, licence note, limitations, fetch status, and content hash.

Source notes are compact aids for navigation and explanation. They remain linked to the original
source and do not replace reading the source or checking current conditions. A failed or inaccessible
source is recorded as a coverage gap, not treated as a negative answer.

SQLite is the local working store. Full-text search is always available after extraction; configured
embedding and reranking adapters run automatically unless explicitly disabled. The graph projection
and GraphQL endpoint support provenance, navigation, inspection, and integration. They are not a
truth engine and do not replace retrieval.

Raw downloads and the full derived database stay in a separate local directory until source-by-
source redistribution rights have been reviewed. The repository may carry manifests, checksums,
research notes, retrieval evaluations, and tooling. A cleared database can be distributed as a
versioned release asset with checksum verification.

## Interface and persistence

The browser surface contains one conversation composer, a new-conversation action, optional access
authentication, a Settings surface for the local runtime, and a quiet summary of what the assistant
is hearing. It does not require the user to understand the internals.

The application exposes:

- `GET /healthz` for process and local audit-chain health (`503` when the chain is invalid);
- `POST /api/sessions` to create a conversation;
- `POST /api/sessions/{id}/message` to send ordinary language;
- `POST /api/sessions/{id}/message/stream` for progressive SSE replies;
- `GET /api/sessions/{id}` to read a persisted conversation;
- `GET /api/runtime/model` for the configured provider/model identity only;
- `GET /api/settings` and `POST /api/settings` for validated local runtime settings without
  returning provider keys;
- `GET /api/expert/capabilities` for read-only runtime capability metadata;
- `GET /api/knowledge/sources` for source metadata and retrieval health;
- `POST /graphql` for read-only source, machine, skill, search, graph, and digest queries.

Sessions retain full conversation history in a hash-linked per-session event ledger, a derived
working context, a small working understanding, model identity, and optional geography. Product
retention is indefinite: startup does not delete empty sessions, snapshot creation does not prune
older snapshots, and browser note history is not automatically capped. Explicit operator cleanup
methods remain available for deliberate maintenance. Compaction changes only the derived working
context; it never silently deletes source history.

The read-only import boundary may read explicitly allowed JSON, CSV, XLSX, and HTTPS resources. It
cannot execute code, write files, mutate configuration, or send imported content to an unconfigured
destination. It is an internal/CLI boundary today; the browser API does not expose arbitrary file or
URL import. Imported data is not sent to the model unless an explicit product flow selects it.

### Local runtime settings

The Settings surface may configure the supported provider, model identity, LocalAI endpoint, AI
enablement, model profile options, timeouts, retries, optional quality judges, TLS verification, and
appearance. Model profiles support common sampling/output/context/vision controls plus bounded
provider-specific JSON options. Protected request fields such as `model`, `messages`, response
format, and streaming remain server-controlled.

Non-secret settings are stored as a mode-600 file under the local data directory. A provider key
entered in Settings is accepted only when `HELPME_MASTER_KEY` enables the existing encrypted local
secret store; it is never returned to the browser, written to the session ledger, or included in
logs. Environment-provided keys remain supported and are reported only as configured/not configured.
Changing the provider or model applies to new conversations; existing sessions retain their model
identity.

### Image-assisted comparison

The notebook may keep up to three original user photos in browser storage. When the user invokes an
assistant comparison and the selected provider/model profile declares `vision: true`, the server
forwards the original image bytes, all saved page details, and selected library example images and
labels to that configured model. Raw image bytes are request inputs only: they are not written into
the server session ledger, conversation history, knowledge base, or source digest. Browser-local
originals remain available until the user explicitly clears them; removing a photo from a page
detaches it without silently destroying the recoverable local copy. A model profile without vision
support must fail honestly rather than receive an image and pretend to understand it. Image-assisted
model output remains untrusted observation; it may describe visible features but cannot by itself
confirm composition, safety, legal status, recyclability, process suitability, or economic outcomes.

Every model-backed reply carries a concise professional reminder that models can make mistakes and
important details must be checked against reliable sources, measurements, or qualified professional
advice before acting. The browser displays the configured provider/model identity and does not add a
separate photo-consent screen before the user presses the comparison or observation action.

## Repository and deployment rules

- The container image contains application code and checked-in metadata, not a hardcoded model.
- Compose binds local development to loopback by default.
- LocalAI requires no provider key by default. Settings may accept a provider key for LocalAI,
  OpenRouter, or DeepSeek only when encrypted local key storage is enabled. The access-token field
  is a separate browser gate and appears only when the operator explicitly configures it.
- Provider keys and encryption keys come from the environment or an encrypted local store and are
  never printed.
- Docker, local Python, and a browser smoke test must exercise the same natural-language route.
- The digest must remain rebuildable from the manifest and its local source-download directory.

## Acceptance criteria

A change is complete only when the relevant checks pass and the result is tested at the user
surface:

1. ordinary messages reach the configured model and preserve the complete reply;
2. an irrelevant local reference is absent from the prompt and answer context;
3. a non-domain question is not forced through a material-specific lens;
4. changing the provider or model changes configuration, not application code;
5. a missing model or source fails honestly and does not fabricate an answer;
6. source retrieval is bounded, attributable, and optional where it does not help;
7. source notes and graph records remain read-only reference infrastructure;
8. tests, lint, type checks, container verification, and the browser flow are green.

## Explicit non-goals

The product does not expose internal retrieval, skill, persistence, or quality mechanics as a user
workflow. Internal implementation should remain replaceable and must not leak into onboarding text
or model replies.
