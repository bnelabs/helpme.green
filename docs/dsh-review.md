# DSH cross-review and implementation plan

## How to read this document

- **Part I — Cross-review (updated 2026-08-17):** what DeepSeek Harness does, what helpme.green
  can take from it, and what it must not take. Refreshed for DSH `dsh-0.1.0-rc.7` and for the
  current helpme.green tree (PR #11/#12 merged 2026-08-17 14:34 +0300).
- **Part II — Implementation plan (verbatim, revised 2026-08-17):** the actionable decisions
  derived from the review. Part II supersedes Part I wherever they differ (see §7
  Reconciliation).

---

# Part I — Cross-review

## 1. Revision history

| Date | Artifact | State |
| --- | --- | --- |
| 2026-08-17 (early) | Original review | DSH commit `47f9438`; helpme.green tree before PR #11/#12 |
| 2026-08-17 (evening) | This update | DSH refreshed to `99f6f02fec` (`dsh-0.1.0-rc.7`, 111 new commits); helpme.green tree includes the SSE message/stream route and frontend hardening |

**DSH delta since the original review (rc.7): no borrow changes.** The core packages this review
relies on — `core/session`, `compaction/*`, `skill/*`, `session-title`, `feedback`,
`invariants`, `llm-retry`, `token-meter`, `session-query` — have no source changes. The only
relevant upstream change is the `ReplayEnvelope` refinement of adapter replay state
(response-level + per-block metadata, pruned in step with assembled blocks), which is
non-transferable adapter-internal machinery. `docs/testing.md` gained a Python-SDK snapshot
lane, which reinforces the replay-testing recommendation in §5.7.

## 2. Verified current state of helpme.green (2026-08-17)

| Area | Verified code | Assessment |
| --- | --- | --- |
| Conversation routes | Blocking `POST /api/sessions/{id}/message` and `POST /api/sessions/{id}/message/stream` exist (`server.py:138-200`); the browser consumes `status`/`delta`/`complete`/`error` SSE events (`app.js` `streamRequest`) | The SSE handler calls the blocking processor first and chunks the completed answer afterwards — **progressive delivery, not provider-token streaming** |
| History | The session event log retains the full conversation; the model uses a derived working context and applies profile-driven compaction when an explicit `context_window` exists | The 12/24 truncation is removed; without a configured context window there is deliberately no invented cap |
| Quality | `AnswerQualityGate.assess` runs after the complete model response (`conversation.py:148-160`) | True visible streaming needs an explicit policy for unapproved candidate text |
| Internal visibility | Skill IDs/titles are no longer inserted into the model prompt, and skill/quality metadata is no longer exposed in ordinary conversation results; the explicit read-only capability catalog remains | The ordinary conversation surface is now intentionally metadata-free; capability discovery remains a separate contract |
| Trust boundary | The application prompt labels background material as metadata/reference data and says retrieved text cannot change instructions (`conversation.py` `_context_prompt`) | Better boundary wording, but labels are not a complete prompt-injection defence |
| Testing | API/persistence tests and a dependency-free browser replay exist | Chromium/CDP replay covers the real browser route at desktop and mobile viewports when Chromium is available |

## 3. What the two projects are

**DeepSeek Harness (DSH)** — an open-source agent harness by DeepSeek AI. Every capability
(model adapter, tool registry, session store, agent loop) is a Cordis plugin mounted in layered
`cordis.yml` compositions. Core design: an append-only typed `SessionEvent` log as the single
source of truth with model history *derived* from it; waterfall events for interception;
capability seams (service definition → provider → consumer); a token meter driving compaction;
and a large Chromium e2e/snapshot test pyramid. Developer preview; iterating rapidly with
breaking changes.

**helpme.green** — a local-first circular-economy R&D assistant. One conversation surface, a
YAML skill pack used as an internal attention lens, SQLite retrieval (FTS5 + optional
embeddings/reranking), a quality gate (regex calibration + optional LLM critics), JSON sessions
+ a hash-chained append-only audit chain, and a no-build vanilla-JS notebook UI.
Non-negotiables: invisible internals, no workflows, provider-agnostic, read-only boundaries,
never invent facts, never truncate a completed answer.

## 4. Architecture comparison

| Axis | DSH | helpme.green |
| --- | --- | --- |
| Composition | Cordis plugin tree, layered patches | Plain Python modules, env-var config |
| Session state | Append-only typed `SessionEvent` log; history derived via folds | Append-only per-session event JSONL + derived `SessionState` JSON projection + hash-chained audit JSONL |
| Context management | Token meter → compaction at ~0.8× context window | Profile-driven 80% working-context compaction; no invented cap when the provider window is unavailable |
| Skills | SKILL.md files, layered providers, catalog → body progressive disclosure | One YAML pack, keyword-scored selection, full lens injected |
| Failure handling | `LlmFailure` canonical codes, per-route retry policy, idle-timeout watchdog | Stable provider, quality-rejection, and persistence-failure codes with bounded backoff and bounded `Retry-After` hints |
| Titles / feedback | Log-folded titles; CAS feedback sidecar | None (client-side note title only) |
| Search | FTS5 across sessions with inert-phrase quoting, cursors | No server-side session search |
| QA | Invariants registry, replay e2e, browser snapshots, "verify the world" | pytest tests + dependency-free browser replay + verified manual browser acceptance; no browser matrix |
| Docs | Generated catalogs (config/tools/persistence) verified in CI | Hand-maintained README + docs |

## 5. What applies — Tier 1

### 5.1 Streaming: progressive delivery shipped; true provider streaming deferred

**DSH:** adapters emit a closed `StreamChunk` union — `block-start`, `text-delta`,
`reasoning-delta`, `block-end`, `usage`, `finish` — the loop logs every raw chunk as an
`assistant/chunk` event and folds them with one shared `BlockAssembler`. The UI accumulates
chunks, swaps partial → final on `assistant/message`, and freezes interrupted streams with a
"stopped" marker. Transport is `text/event-stream` over `fetch` + `ReadableStream`, with a
`: connected` heartbeat and a mid-stream error frame. Cancellation propagates into the provider
request and normalizes to a terminal `aborted` frame; an idle provider stall maps to `TIMEOUT`.

**helpme.green today:** the SSE wrapper delivers the completed answer in chunks after the
blocking call finishes. This is already the right browser contract; what remains is the
*provider-side* work, which Part II §5 defers until measured latency justifies it (quality runs
after the complete response, so true token streaming needs a policy for unapproved candidate
text — buffered, marked, or withheld).

**Apply when justified:** typed provider streams + cancellation; persist only the
quality-approved authoritative answer; test disconnects, partial output, late errors,
backpressure, cancellation, fallback.

### 5.2 Event-sourced sessions with derived folds

**DSH:** a `Session` is an append-only log of typed events; `seq = log.length`; lossless JSON,
deep-frozen at acceptance; only three "surface" event types produce model messages, each
carrying `surfaceOp` + `sourceEventSeqs`, so **"model-visible means logged"** is enforced at
the source. `deriveMessages()` is a cached fold over surface nodes. Unknown *required* events
make replay refuse loudly rather than silently drop. Fork/resume is seeding a log prefix.
Projections are pure `{init(), apply(state, event), view(state)}` units with per-session
watermarks and a `stateVersion` for invalidation.

**Apply (the flagship idea):** versioned, sequenced, hash-linked session events (Part II §3);
derive the visible conversation and `understanding` as folds; treat a server title as a later
feature; add the "model-visible means logged" invariant; reject malformed or
unknown-required events on load. A torn tail must fail closed or be quarantined; any future
`interrupted` marker must be appended as a new event after integrity checks, never used to
rewrite valid history.

### 5.3 Compaction instead of hard truncation

**DSH:** `compaction-basic` triggers at pressure when measured tokens ≥ 0.8× context window and
on the canonical `CONTEXT_WINDOW_EXCEEDED` error. It prunes oversized results model-free,
selects a head-anchored range retaining a priced recent tail (~16% of the window) without
splitting paired events, then runs a logged bracket (`compaction/start` lock → summary →
replacement with `surfaceOp: replace` + shadowed seqs → `compaction/end`). The replacement must
be *smaller*; stability is re-checked; everything rides the log, so compaction is replayable.
The token meter is a per-session replay fold (provider `usage` trusted only when the request
envelope matches and its total ≥ the heuristic price; otherwise 4 chars/token +4/block +4/role).

**Apply (sharpened by Part II §4):** hard input ceiling of 80% of the configured or
adapter-discovered context window; remeasure and repeat with no fixed pass count; progress
guards (no-progress summaries, oversized indivisible events, state fingerprint against
infinite loops); append a versioned event with source range, summary, before/after
measurements, profile, provenance; never silently delete source history. This is an input
ceiling, not an output limit.

### 5.4 Structured failure taxonomy and retry policy

**DSH:** one serializable `LlmFailure` (`code`, `status`, `providerRetryAfterMs`, `requestId`)
with canonical codes — `EMPTY_RESPONSE`, `RATE_LIMIT`, `SERVER`, `TIMEOUT`, `TRANSPORT`,
`CONTEXT_WINDOW_EXCEEDED` — and regex classifiers for provider wording. Retry only on the code
allowlist (never `CONTEXT_WINDOW_EXCEEDED`), exponential backoff with symmetric jitter,
`Retry-After` honored only when ≤ max delay, empty completion retryable, one adapter call = one
provider attempt, idle-stream watchdog, atomic per-request endpoint+key resolution.

**Apply (with one correction from Part II §1):** stable failure codes for provider unavailable,
timeout, authentication/configuration, rate limit, context overflow, malformed or empty
response, quality rejection, persistence failure. Record **explicit model attempts and provider
retry hints**; the hash-chained audit file is not a lossless session log and must not be used as
a model-attempt counter (this corrects an earlier draft suggestion to derive retry budgets by
counting audit records). On context overflow: compact again with progress guards; never
silently truncate.

The runtime records a quality-gate rejection as `model.failed` with the stable
`quality_rejected` code and does not append a completed or conversation-turn event for that
draft. Durable response-write errors are classified as `persistence_failed`; the user receives a
plain retry message and the underlying storage error remains internal. The failure event is best
effort when the storage path itself is unavailable.

### 5.5 Skills: progressive disclosure, ordered sections, hard invisibility

**DSH:** skills are Markdown files with YAML frontmatter; the prompt gets a catalog of
summaries, the full body loads on demand; the catalog republishes only when a content digest
changes; prompt assembly is a registry of ordered sections and strict `{{variable}}`
interpolation where unknown names throw; runtime context is emitted only when the rendered text
changed; actionable material is injected last.

**Apply now for ordinary-surface invisibility; defer progressive disclosure until prompt-size
measurements justify it:** split each skill into a short lens
(injected) and a longer body (on demand); keep trigger matching host-side; formalize the system
prompt as ordered named sections pinned by a test; and use strict template interpolation.
Escaping should prevent renderer delimiter collisions, not be presented as a prompt-injection
defence. Remove skill IDs/titles from the ordinary conversation response and model prompt
(the current `"Expert lens: {title} ({skill_id})"` is removed); keep the intentional
read-only capability-metadata endpoint separate.

### 5.6 Titles, feedback, search, headless — deferred

DSH's log-folded titles with a deterministic fallback (never blocking the reply), CAS feedback
sidecars keyed by immutable message/event IDs, FTS5 session search with inert-phrase quoting,
and a headless one-shot mode are all sound mechanisms. Part II §6 defers them until product and
retention requirements exist. The mechanisms remain in the backlog, not abandoned.

### 5.7 Record/replay testing

**DSH:** web e2e boots the real composition over real HTTP and drives real Chromium; a replay
provider serves recorded fixtures — a model call without a declared fixture fails loudly, and
teardown asserts full fixture consumption. "Verify the world, not the self-report"; test the
real entry path; mock only the model adapter.

**Apply (refined by Part II §2):** an **injected test-only fake provider/model boundary**, not a
shipped developer-only HTTP endpoint. Exercise ordinary prompts, material prompts,
irrelevant-reference rejection, provider failures, SSE framing, blocking fallback, session
reload, and audit integrity. Add browser-path coverage when a browser harness is available,
asserting visible behaviour and persistence.

## 6. Explicit non-borrows

| DSH feature | Why not |
| --- | --- |
| Cordis plugin tree / `cordis.yml` layering / profiles/bundles | The composition needs are a dozen env vars; a plugin framework would make the implementation itself the product |
| Tools: bash, fs, terminal, web-fetch, LSP, code-runtime, E2B sandbox | Contradicts "do not authorise or execute physical, legal, financial, or operational actions" and the read-only MCP boundary |
| Approval/permission presets, sandbox policy | No execution surface to gate; `ReadOnlyMCP` already fails closed — that is the approval seam |
| Goals, todo, plan mode, subagents, workflow/Ralph, jobs/schedule | Workflow engines — the explicit non-goal is "the product does not expose internal mechanics as a user workflow" |
| ACP / hook bridges / JSON-RPC mux / typert RPC / projection registry change-feed | Multi-client host infrastructure for a single local browser |
| React + Vite + CSS Modules + ui-theme token system | The no-build vanilla page is a feature (zero deps, easy audit); port behaviours, not the stack |
| Multi-backend storage hub, spill, zstd packing, replay-state ownership (`ReplayEnvelope`) | Enterprise scale not needed; the fold and token-meter *ideas* are what matter |

Meta-lesson: DSH's seam discipline — "adding a capability means designing the service
definition, a provider, and a consumer" — is worth keeping. helpme.green already practices it
for models, embeddings, and rerankers; make it explicit for retrieval backends and quality
critics in a doc.

## 7. Reconciliation with the implementation plan (Part II)

The plan and this review agree on the decisions that matter: append-only events and
"model-visible means logged" (yes, required), compaction with a hard 80% input ceiling and
progress guards (yes), failure taxonomy, replay tests, and bounded retry hints (yes, now), and no
DSH runtime/plugin/workflow stack (no).

The plan corrects or sharpens this review in three places, and those corrections are accepted:

1. **Retry budgets must not be inferred by counting audit records.** The audit chain is a
   governance log, not an attempt ledger; record explicit model attempts once the session event
   log exists (§5.4).
2. **True provider streaming is deferred until latency evidence justifies its provider,
   quality-gate, and cancellation complexity.** The shipped SSE wrapper is progressive delivery
   and must not be called true streaming (Part II §5, bottom line).
3. **Replay tests use an injected test-only fake provider boundary**, not a shipped
   developer-only HTTP endpoint (§5.7).

Open items carried by the plan: provider-token streaming and cancellation only after latency
evidence; broader browser and alternate-engine matrix coverage; and product/retention
requirements before titles, feedback, search, or headless ask.

---

# Part II — Implementation plan

Status: revised 2026-08-17

## Decision

Borrow selected DSH mechanisms; do not adopt its runtime, plugin stack, tools,
workflows, goals, subagents, ACP surface, or React architecture.

Implement reliability hardening first, then an append-only session log, then
compaction. Consider true provider streaming only if measured latency warrants
its provider, quality-gate, and cancellation complexity.

The intended compaction rule is:

- the assembled model input has a hard ceiling of 80% of the configured or
  adapter-discovered context window;
- there is no hard cap on retained turns, compaction events, or safe summary
  passes;
- completed answers are never truncated by the application.

## Requirements audit

REQUIREMENTS.md is mostly accurate as a product contract, but not completely
accurate as a current implementation snapshot.

| Area | Current code | Assessment |
| --- | --- | --- |
| Conversation routes | Blocking message and SSE message routes exist; the browser consumes delta and complete events. | The SSE handler calls the blocking processor first and chunks the completed answer afterward. This is progressive delivery, not provider-token streaming. |
| History | The session event log retains the full conversation; the model uses a derived working context and profile-driven compaction when `context_window` is explicit. | The 12/24 truncation is removed; a provider window is required before enforcing an 80% working-context ceiling. |
| Provider profiles | Provider/model/timeout/sampling/output settings are external and model-agnostic; `context_window` is accepted as local routing metadata and is not forwarded to providers. | The boundary is correct and pre-measurement/compaction is implemented when the window is configured; provider-token streaming remains absent. |
| Quality | Quality processing runs after the complete model response. | True visible streaming needs an explicit policy for unapproved candidate text. |
| Knowledge | Manifests, source metadata, hashes, ingestion state, retrieval metadata, and read-only GraphQL/MCP boundaries exist. | Broadly matches the requirements. |
| Trust boundary | Background material is labelled application metadata/reference data and explicitly cannot change the instructions. | Better wording, but this remains a boundary aid rather than a complete prompt-injection defence. |
| Internal visibility | Skill IDs/titles are removed from the ordinary model prompt and conversation result; the separate capability catalog remains available. | The ordinary conversation surface is now metadata-free. |
| Testing | API/persistence tests and a dependency-free browser replay exist. | Chromium/CDP replay covers the real route at desktop and mobile viewports when Chromium is available; manual browser acceptance remains verified. |

The requirements reflect the intended boundaries and most public routes. The
runtime now has an append-only session event ledger, full retained source
history, explicit model-attempt/failure events, and profile-driven 80%
compaction. Remaining gaps are provider-token streaming, broader browser and
alternate-engine matrix coverage, and optional feature families.

## Compaction contract

For every request, measure the complete provider-visible input envelope:
instructions, selected conversation, retrieved/machine context,
response-format/protocol overhead, and all other input fields.

Let context_window be the provider's combined input-plus-completion limit,
supplied by configuration or the provider adapter. Do not invent it. The hard
input ceiling is:

    input_ceiling = floor(0.80 * context_window)

Compact until the assembled input is at or below that ceiling. The remaining
20% is headroom for completion and protocol behavior. A profile may choose a
lower budget, but the implementation must not silently exceed 80%. This is an
input ceiling, not an output limit. If a completion still cannot fit, return a
classified failure or use an explicit continuation design; never truncate the
completed answer.

After every safe compaction, remeasure and repeat. There is no fixed maximum
pass count. Stop only when the request is below 80% or a real safety boundary
is reached: no safe range remains, an indivisible event is too large, the
summary makes no reduction, the same state repeats, the context limit is
unavailable, the provider rejects a valid request, or durable persistence/
locking fails. A state fingerprint is required to prevent an infinite loop.

Compaction must append a versioned event containing the source range,
summary/protected reference, before/after measurements, profile, and
provenance. It may update a derived working projection, but must not silently
delete source history. The current hash-chained audit file is not a lossless
session log and must not be used as a model-attempt counter.

## Implementation roadmap

### 1. Contract and hardening

- Record the migration status and post-completion SSE behavior as implementation
  limitations; the 12/24 history truncation has been removed.
- Define the provider context-window contract and prompt-artifact
  retention/protection policy.
- Keep stable failure codes for provider unavailable, timeout,
  authentication/configuration, rate limit, context overflow, malformed or
  empty response, quality rejection, and persistence failure covered by focused
  regression tests.
- Define explicit model-attempt records and provider retry hints as part of the
  event-ledger contract; do not infer retry budgets by counting audit records.
- Load shared model/provider, retrieval, KB, and non-secret runtime path/access
  policy through typed snapshots; keep bearer/provider/master-key values out of
  them and resolve credentials only at their adapter boundaries.
- Classify context overflow now; enable recovery compaction only after the
  repeatable compactor is active. Never silently truncate.
- Remove skill IDs/titles and unnecessary internal metadata from model/API
  surfaces.
- Keep retrieved/imported text explicitly untrusted.
- Add the browser IME composition guard, consistent User-Agent metadata, and
  focused regression tests.

### 2. Replay the actual route

Use an injected test-only fake provider/model boundary, not a shipped
developer-only HTTP endpoint. Exercise ordinary prompts, material prompts,
irrelevant-reference rejection, provider failures, SSE framing, blocking
fallback, session reload, and audit integrity. The repository now includes
`scripts/browser_replay.mjs` and `tests/test_browser_replay.py`: an isolated
headless Chromium/CDP runner drives the real HTTP/SSE path at explicit desktop
and mobile viewports, records material and unrelated observations, checks the
visible assistant response, asserts no horizontal overflow and usable core
controls, reloads the page, checks console/framework health, and writes an
optional temporary screenshot. The pytest case skips only when no
Chromium-compatible executable is available.

### 3. Append-only session events

Add versioned, sequenced, hash-linked events for user/assistant messages,
model attempts, provider/model/profile identity, prompt-builder and schema
versions, selected skills and source IDs/hashes, quality decisions, and
compaction source ranges.

The target replay unit is the model-visible request envelope plus the durable
references explaining how it was assembled, not merely visible messages. When
`HELPME_PROMPT_ARTIFACTS_ENABLED=1`, the runtime now stores that envelope in a
separate mode-700 directory encrypted with a data key held by the existing
master-key-backed secret store. The session event retains only the artifact
identifier and digests; the artifact is not exposed through the browser/API.
The feature is disabled by default, fails closed without `HELPME_MASTER_KEY`,
retains no raw image bytes, and remains until an operator explicitly removes
the local prompt-artifact directory. The migration has removed the 12-entry and
24-entry truncation. A bounded derived projection may still be added later for
performance, but it must not replace the source event history.

### 4. Repeatable 80% compaction

Measure actual requests rather than using a universal token estimate. Select
safe ranges, preserve recent tail, paired/structured units, unknowns,
constraints, user intent, source identity, and provenance. Append
transactionally, remeasure, and repeat with no fixed pass count. Reject
non-shrinking or structurally/provenance-invalid summaries. Serialize or
version concurrent compaction. Return "cannot safely compact" rather than
dropping content.

Test one and repeated compaction, long histories, no-progress summaries,
oversized indivisible messages, context-overflow recovery, reload, migration,
and concurrent requests.

### 5. True provider streaming, only if justified

The current provider interface returns complete JSON and quality runs
afterward, so streaming is not a drop-in change. If latency evidence warrants
it, add typed provider streams and cancellation, preserve the browser SSE
contract, persist only the quality-approved authoritative answer, and decide
whether candidate text is buffered, marked, or withheld. Test disconnects,
partial output, late errors, backpressure, cancellation, and fallback.

### 6. Defer optional features

Defer server titles, session search, feedback sidecars keyed by immutable
message/event IDs, headless ask, and configuration catalogs. Do not add web
search, execution, workflows, goals, subagents, branching, skill shadowing,
or projection caches without separate product and security decisions.

## Verdict

| Idea | Decision |
| --- | --- |
| Append-only events and "model-visible means logged" | Yes; required for replay and trustworthy compaction. |
| Compaction | Yes; hard 80% input ceiling, unlimited safe passes, progress guards. |
| Failure taxonomy/retry and replay tests | Yes, now. |
| Typed provider streaming/cancellation | Later, only if latency evidence supports it. |
| Titles, feedback, session search, headless ask | Later, after product and retention requirements. |
| DSH runtime/plugin/workflow stack | No; outside helpme.green's scope. |

## Acceptance gates

Full event history must be replayable; every model request must be attributable
to its profile, prompt, sources, and quality decision; compaction must reach
the hard 80% input ceiling without a fixed pass limit or silent deletion;
no-progress cases must fail honestly; answers must remain uncut; irrelevant
references and unrelated prompts must remain correctly scoped; provider swaps
must remain configuration-only; and API, lint, type, compile, container, and
real browser checks must pass.

## Bottom line

Implement the reliability foundations, event model, and 80%-ceiling
compaction. Do not implement the broader DSH roadmap wholesale, and do not
call the current post-completion SSE wrapper true provider streaming.
