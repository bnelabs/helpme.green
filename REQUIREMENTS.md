# helpme.green — Autonomous Circular-Economy Decision Platform
## Requirements & Plan (v3.0 — consolidated, codex goal brief)

## 0. Identity

- **Name:** helpme.green
- **One line:** *Describe any material stream. Get an honest, evidence-grounded, geography-aware answer: what it could become, what routes are actually applied, what evidence is missing, and what it is conservatively worth.*
- **Character:** advisory only. Deterministic engine + governed knowledge base + AI that interviews and explains but **never concludes**.
- **Scope for this phase:** the autonomous core + a **conversation-first local web surface**. The
  deterministic evaluator and compatibility command API remain available underneath; slash
  commands are not the primary user interaction. A broader public web product can be decided
  separately.

## 1. Vision

Anyone — a curious person, a small recycler, an upcycler, an investor — can describe a material stream and receive an honest assessment of its potential: which processing routes are real and applied (with sources), what evidence is missing before anyone should act, and what it is conservatively worth *here, in this economy*. The platform runs autonomously: every process is auto-fed, every issue is handled by AI agents with strict task contracts, and the knowledge base compounds — getting cheaper and smarter with use.

## 2. Problem statement

1. **The honesty gap** — general chat AIs confidently guess yields, prices, and process steps; non-experts can't tell. Real decisions need "I don't know, and here is what would prove it" as a first-class answer.
2. **The knowledge gap** — recycling knowledge is fragmented across regulations, standards, literature, local practice, and buyer specifications; no governed, source-linked, jurisdiction-scoped compilation exists.
3. **The access gap** — small recyclers and the public can't afford consultants; investors can't cheaply sanity-check streams. helpme.green makes professional-grade evaluation affordable, with **zero marginal cost for repeated questions**.

## 3. Audiences, tiers, and surfaces

- **Education tier** — curious public. Gets: broad, friendly, clearly labelled "for learning only — not a decision basis"; illustrative ranges only. Surface: **Public Web** (later phase).
- **Decision tier** — small recyclers, upcyclers, circular-economy professionals. Gets: fail-closed evaluation, route landscape, readiness per dimension, evidence checklists, comparison, value ranges with basis, next actions. Surface: **Pro Console (now)** + Web later.
- **Valuation tier** — investors, financers, platforms. Gets: conservative value records, sensitivity to missing evidence, VOI ranking. Surface: Pro Console + **API**.

Requirement: every output is labelled with its tier; no output may present education-tier content as decision-grade.

## 4. Core user journeys

**Conversation journey (now):** open the local surface → describe an object, material, situation, or
goal in ordinary language → the AI answers the actual question and asks at most one useful follow-up
when a missing detail changes the answer → the side rail quietly reflects the shared understanding
(object, condition, goal) → optional background context is available when relevant. The user never
has to learn slash commands, fill an evidence form, or provide a token when local auth is disabled.
The deterministic evaluator, snapshots, exports, and compatibility command API remain available to
controlled clients and advanced workflows.

**Web journey (later):** landing → pick material from catalog → guided wizard → same evaluation underneath.

## 5. Honesty & safety logic (invariant — R1–R12)

1. **R1 — Evidence ladder, no silent upgrades.** `hearsay → educated estimate → observed → screened → verified`. Nothing may upgrade a state automatically.
2. **R2 — Fail-closed.** Missing evidence on a mandatory requirement ⇒ `UNKNOWN` ⇒ blocks the affected conclusion. Unknown is never zero, assumption, or optimism.
3. **R3 — No auto-promotion.** User claims and dialogue content are never knowledge; only the review pipeline promotes, preserving the true evidence state.
4. **R4 — Hypothesis separation.** Unproven but plausible ideas are stored and shown separately, explicitly labelled unvalidated — never as established routes.
5. **R5 — Provenance.** Every claim shown traces to the source register (exact location, applicability, limitations). No source, no claim.
6. **R6 — Jurisdiction-aware.** Regulatory gates scoped to the user's geography; content per jurisdiction requires qualified review for that jurisdiction.
7. **R7 — Financial conservatism.** Ranges with basis (revenue floor, cost ceiling, currency, price year). **No financial figure on an incomplete basis — ever.**
8. **R8 — Bounded natural dialogue.** The AI may hold a natural conversation, answer the user’s
   actual question, translate ordinary language, and ask one useful follow-up; it cannot drift into
   deterministic conclusions, fabricated sources, or unsupported recommendations.
9. **R9 — Coverage honesty.** "Not yet covered" is an acceptable, required answer; never improvise beyond vetted knowledge.
10. **R10 — Contamination presumption.** The AI actively probes contamination and condition even if the user asserts cleanliness; non-expert "none" = hearsay, never clearance.
11. **R11 — The AI never writes the conclusion.** The engine evaluates; the AI interviews, translates, explains.
12. **R12 — Explainability.** Every status and block is explainable: rule → claim → source → evidence state → what's missing.

## 6. Autonomous operation & agent organization

The system runs unattended. No human in the operational loop. Humans only (a) set policy outside the runtime, and (b) receive formal escalation requests. **"Requires qualified external review" is an output state, not a human process step** — the machine correctly refusing to exceed its authority.

Every agent is **code + prompt + bounded tools** with a five-part contract: **Mission / Inputs → Outputs / Autonomy scope / Forbidden actions / Escalation**, plus a mandatory anti-myopia clause.

- **Intake Agent** — interviews, produces labelled `CaseFacts`. Forbidden: conclusions, over-crediting evidence, skipping confirmation. Escalates contradictions → Conflict.
- **Evaluator Core** — *not an agent*; the deterministic engine; enforces R1–R12; agents cannot change it.
- **Explainer Agent** — renders engine output in plain language with sources and tier labels. Forbidden: adding claims, softening blocks, omitting unknowns.
- **Sourcer Agent** — discovers authoritative sources; produces candidate source-register entries (exact location, applicability, limitations). Forbidden: creating claims, non-authoritative sources for legal gates.
- **Knowledge Curator Agent** — composes candidate claims from sources + consented dialogue candidates; assigns evidence states. Forbidden: promoting, upgrading states, inventing units/currency context.
- **Domain Reviewer Agents** (materials, safety/EHS, legal, product/buyer, commercial/financial) — approve / reject / request-more-evidence with recorded reasoning. Forbidden: self-review, cross-domain decisions, waiving evidence minimums.
- **Conflict Agent** — detects contradictions; blocks conflicting promotions; surfaces conflicts. Forbidden: silently picking a winner.
- **Market Data Agent** — scheduled fetch/validation/expiry of prices, FX, energy. Forbidden: deriving data from dialogue, extrapolation, stale backfill.
- **Economics Agent** — composes value records under conservative rules. Forbidden: incomplete-basis computation, single-point estimates, unit/currency mismatches.
- **QA Auditor Agent** — audits: source verification, hallucination detection, evidence-state audits, re-review triggers, pipeline pauses. Forbidden: rewriting knowledge, overriding invariants.
- **Ops Agent** — health, cache invalidation, token budgets, retries, backups, incidents. Forbidden: changing logic/invariants, masking failures.
- **Policy Agent** (top) — enforces the invariant layer, resolves cross-domain conflicts, decides when an external authority is required. Forbidden: modifying invariants, overriding fail-closed blocks, reversing a review rejection. Escalates anything unresolvable within invariants → owner, as a formal decision request.

**Anti-myopia mechanisms:** invariants are code, not policy; separation of duties (propose ≠ review ≠ promote; two independent domain reviews required for promotion); the global-objective clause in every contract ("if completing your task degrades another pipeline's guarantee, stop and escalate"); cross-check pairs; the escalation contract (never punished); fail-closed operation (invariant violation pauses the pipeline); full audit of every agent decision; budget discipline enforced by Ops.

## 7. Auto-fed pipelines

- **Intake** — input → Intake Agent → confirmed labelled facts → Evaluator Core.
- **Evaluation** — facts → landscape + readiness + next actions → Explainer → answer + value record (if eligible) → caches updated.
- **Knowledge** — Sourcer → Curator → Conflict check → two independent domain reviews → Policy promotion → active knowledge → cache invalidation. Dialogue candidates enter via the same gate.
- **Market** — scheduled fetches → validation → normalization → expiry windows.
- **QA** — scheduled audits, source verification, invariant checks → flags / re-reviews / incidents.
- **Ops** — health, backups, cache, budgets, incidents → self-healing or owner flag.
- **Moderation** — user content triaged automatically; ambiguous edge cases escalate to owner.

## 8. Knowledge base & governance logic (agentic)

Sources register → candidate claims (evidence state + provenance) → dedupe + conflict check → two independent domain reviews → promotion with logged decision → active knowledge with review due-dates and expiry → versioned immutability (published content changes only via new version + re-review). Conflicts surfaced, never silently resolved. Jurisdiction-scoped. Dialogue-derived candidates always tagged with their true state.

## 9. Value & economics logic

Three layers, never conflated: **governed economics knowledge** (typed, source-linked, review-gated cost/yield/output data), **market data** (time-stamped, externally refreshed, never from dialogue), **value records / cache** (composed, digested snapshots: profile + geography + route + ranges + price basis + currency + date + sources). Value record computed only on complete basis (R7); conservative (revenue floor, cost ceiling); range-shaped; sensitivity shown; the evidence that would change the number shown. **VOI:** rank next evidence actions by expected value gain minus cost — the platform tells users whether testing is worth paying for. **Geography & income context:** jurisdiction gates, local prices, income-level feasibility framing, locale. Politics/regulation surface as gated requirements, never editorial.

## 10. Reuse & cost logic

Deterministic evaluation ⇒ same facts + same knowledge version = same result forever. Cache keys: knowledge digests + normalized fact sets + geography + locale; invalidate only on knowledge change. Pattern-level caching only (never per-user transcripts). First novel question pays for extraction/rendering; repeats are free; tier budgets; BYOK controls own spend.

## 11. AI & token logic

Provider-agnostic interface (swap models without behavior change — verified by asserting identical engine outputs across models). **DeepSeek primary for testing (cheap), OpenRouter free models selectable.** BYOK: user tokens encrypted at rest, never in browser/logs, metered and audited. Platform default tier: cost-capped, model identity shown. AI roles hard-constrained (interviewer/translator/explainer). Fallback: engine still answers from cache when a model fails; clearly says the interview cannot continue. No training on user data without explicit consent.

## 12. Interface strategy — conversation-first local surface

**Primary surface:** a local web conversation with a calm editorial layout. It has one message box,
one natural-language send action, and a quiet “What I’m hearing” summary. It does not expose slash
commands, internal schemas, evidence-state labels, or a required token prompt. The user can begin
with an incomplete sentence, a question, or frustration; the assistant meets that message at its
level and continues from there.

**Compatibility surface:** the existing command endpoint and CLI remain available for deterministic
engine tests, snapshots, exports, and controlled professional workflows. They are implementation
interfaces, not onboarding instructions for the conversation surface.

**Session model:** case-oriented sessions; state = labelled fact set + knowledge version + geography; resume by snapshot; every decision appended to the audit chain. Sessions persist, cases resume.

**Read-only MCP contract:** allowed tools = read files/CSV/XLSX, fetch whitelisted URLs, query the user's configured data sources. **Forbidden = execute code, write anywhere, send data outside, mutate knowledge or config.** MCP/user-supplied content is **untrusted input**: enters as `CaseFacts` with evidence states and provenance ("from user's file, unverified"), is **prompt-injection-isolated** from agent instructions (same treatment as user text), can never promote itself into knowledge, and every tool call is logged. The console **never executes anything** — slash commands run against the engine, never against the user's machine.

**Public Web (later phase):** landing + education tier + mobile-first guided wizard, same engine underneath. Separate build, separate budget.

## 13. Public platform logic (applies to both surfaces)

Accounts: optional for education, required for decision/valuation (snapshots, BYOK, history). Privacy: data minimization, GDPR-default for EU, deletion on request, explicit consent for knowledge-pipeline use. Moderation: automated triage; ambiguous cases escalate to owner. Licensing: users grant the platform license to use anonymized contributions in the governed knowledge pipeline.

## 14. Business model

Free education tier (funnel/public good) · Decision tier subscription/credits (console + snapshots + BYOK) · Valuation tier / API (investors, bulk evaluation, value records) · Enterprise (private catalogs, private knowledge packs). **Never monetized: fabricated confidence; converting `UNKNOWN` into a number.**

## 15. Legal & compliance posture

Advisory-only on every surface; "not legal/regulatory/safety/investment advice" framing; GDPR-default; content liability = governed publisher, not open wiki; jurisdiction expansion requires qualified review per jurisdiction before offering content there.

## 16. Boundaries — the final never-list

1. Never approves, executes, or recommends execution of purchases, shipments, processes, experiments, legal classifications, or product releases.
2. Never presents itself as legal, regulatory, safety, or investment advice.
3. Never lets the AI write a conclusion or improvise out-of-coverage answers.
4. Never promotes user claims or dialogue content into facts without the two-review pipeline.
5. Never upgrades an evidence state automatically.
6. Never computes a financial figure on an incomplete basis; never replaces unknown with zero.
7. Never presents unproven science as established.
8. Never derives market prices from user chatter.
9. Never mixes helpme.green data with Konverta's operational data (separate systems).
10. Never trains on user data without explicit consent; never stores API tokens in plaintext.
11. **No human in the operational loop** — humans set policy outside the runtime and receive escalation requests only.
12. No agent deviates from its contract, decides outside its autonomy scope, modifies invariants or the engine, or spends outside budget.
13. No single agent promotes knowledge (two independent reviews required).
14. **The console never executes anything; MCP is read-only; MCP/user content is untrusted, injection-isolated, and never becomes knowledge.**
15. The console serves the pro tier only; education tier waits for the public web.
16. No matchmaking, brokerage, or marketplace execution (separate future decision).
17. Frontend design (public web) is out of scope until a separate decision.

## 17. Plan & roadmap

- **Phase 0 — Decisions** (owner): pricing skeleton; launch jurisdictions; initial domain-review agent configuration; trademark/domain check on helpme.green. *Exit:* decisions recorded.
- **Phase A — Honest spine + conversation surface:** engine wiring, bounded natural conversation on
  LocalAI/OpenAI-compatible providers, sessions, snapshots, read-only MCP, compatibility API, one
  material family (copper cable), and local Docker deployment. *Exit:* 100 evaluations, 0 fabricated
  sources, identical engine outputs across models, conversational sessions persist and resume.
- **Phase B — Knowledge pipeline:** Sourcer + Curator + Domain Reviewers + Conflict + Policy promotion; dialogue candidate intake. *Exit:* autonomous knowledge growth; two-review promotion only; zero single-agent promotions in audit.
- **Phase C — Value generation:** Market Data + Economics agents, value records, VOI. *Exit:* zero incomplete-basis numbers in QA audits.
- **Phase D — Autonomy hardening:** QA Auditor, Ops Agent, incidents, budgets, fail-closed pauses, escalation contract. *Exit:* 72-hour unattended run, no invariant violations, no human steps.
- **Phase E — Breadth:** catalog expansion, more material families, more jurisdictions, public API. *Exit:* coverage KPIs met.
- **Phase F — Public Web (separate work stream):** landing, education tier, mobile wizard. *Exit:* live education tier, funnel to console.

## 18. Success metrics

Honesty: 0 fabricated sources in audits; 100% of decision outputs show `BLOCKED`/`UNKNOWN` when applicable. Cost: cache hit >80%; marginal cost of repeat answer ≈ €0. Adoption: evaluations/week, returning users, coverage growth, time-to-first-landscape < 1 min. Compounding: candidates → reviewed → promoted per month; catalog coverage growth. Trust: acted-on-output rate, complaint rate, reviewer/pipeline error metrics.

## 19. Risks & mitigations

1. **Extractor soft spot** → confirmation step, unlabelled-fact rejection, strict translation schema, QA audits.
2. **Breadth gap vs ChatGPT** → coverage honesty (R9), phased breadth, decision-tier value (determinism, audit, fail-closed) where ChatGPT cannot follow.
3. **Knowledge poisoning via dialogue/community** → candidate-only intake, two-review promotion, conflict gates, expiry.
4. **Regulatory exposure** → tier labelling, advisory framing, jurisdiction gates.
5. **Token cost blowout** → deterministic cache, templated question agenda, budgets, BYOK.
6. **Agent myopia / drift** → contracts, separation of duties, cross-check pairs, fail-closed pauses, audit.
7. **Conversation drift or model failure** → keep the model bounded, preserve the deterministic
   evaluator, state when the provider is unavailable, and never turn a missing answer into a guess.
8. **Scope creep toward execution/marketplace** → boundary §16.16, explicit separate decision.

## 20. Open decisions

1. Pricing skeleton and launch paid tiers.
2. Launch jurisdictions and expansion order.
3. Default free-tier model budget per user/month.
4. Community contribution model: open to all users or verified recyclers only.
5. Whether the console is permanently the pro surface or a bridge to a web-based pro dashboard.
6. Marketplace/matchmaking future: yes/no/never (explicit decision, not drift).

## 21. Handoff note for Codex

This document is the **contract**. Invariants (R1–R12) and the never-list (§16) outrank implementation convenience. Agent contracts (§6) are binding specifications — turn them into prompts + tool scopes + validation, not suggestions. Every pipeline maps to a produced asset; every agent to its five-part contract. The engine is deterministic; the AI never concludes; MCP is read-only; the console never executes. Surface any conflict between this document and an implementation constraint — never resolve it silently.
