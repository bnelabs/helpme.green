# Open-Source Integration Strategy

How external open-source circular-economy projects are ingested into the
helpme.green architecture. This document aligns with REQUIREMENTS.md (v3.0)
and the license register in `open-source-reuse.md`.

## Principle

External software is treated as **clean-room inspiration, structural
blueprints, or governed data sources** — never as raw code dependencies. This
preserves complete governance over the deterministic core and avoids license
contamination. The contamination vectors to respect are **AGPL** (Fleetbase),
**EUPL** (CIRCULOOS platform), and **CC BY-SA** (Precious Plastic content);
permissive licenses (BSD-3, MIT, Apache-2.0) carry only attribution and
no-endorsement obligations. Invariants R1–R12 (§5 of REQUIREMENTS.md) and the
never-list (§16) bind every ingestion below.

## 1. Precious Plastic (CC BY-SA content, MIT/GPL code)

- **Role:** Basis for **Plastic Route Cards** (Phase E) and community
  micro-processing knowledge.
- **Architectural mapping:** process logic (shredding, extruding, washing
  yields) is extracted into the Knowledge Register via the Sourcer and Curator
  Agents; machine scale and capital cost data inform the Economics Agent's
  baseline assumptions.
- **Invariant & IP enforcement:**
  - **R5 (Provenance):** every plastic route card explicitly links to the
    specific Precious Plastic blueprint/manual version used as its basis.
  - **CC BY-SA attribution:** content is re-expressed in helpme.green's
    internal structured schema (`CandidateClaims`) with clean attribution and
    no code dependency. **Share-alike precision:** re-expressing *facts* is
    free; reproducing *substantial content* makes the derived pack BY-SA
    (per register rules). Keep derived packs BY-SA or obtain separate
    permission before any substantial reproduction.

## 2. Plastic Odyssey (No Public License)

- **Role:** Contextual framework for **Geography & Income-Tier Framing**.
- **Architectural mapping:** informs the Evaluator Core and Economics Agent
  when evaluating low-infrastructure, regional, or decentralized recycling
  options (electrical requirements, repairability constraints, small-scale
  feasibility in non-industrialized regions).
- **Invariant & IP enforcement:**
  - **Boundary (§16):** reading/study-only permission. **Zero reproduction**
    of their CAD files, machinery plans, or instruction guides; no bulk
    harvesting of their content.
  - **R6 (Jurisdiction & Locale):** used purely to set realistic operational
    parameters — facts only, always attributed as concepts.

## 3. Deep Waste (BSD-3)

- **Role:** Blueprint for **Catalog Taxonomy & Photo-Intake Pipeline**
  (Phase 3 / Public Web).
- **Architectural mapping:** taxonomy structures material streams into
  recognizable visual classes during user intake; informs the prompt and
  validation schema for the photo-intake tool in the Intake Agent.
- **Invariant & IP enforcement:**
  - **Clean-room build:** we build our own inference/classifier pipeline
    (BSD-3 also permits direct use with attribution; clean-room is the
    cautious default). Model granularity is surfaced honestly (Deep Waste's
    shipped model distinguishes ~6 broad classes, not specific polymers).
  - **R1 & R10 (Evidence Ladder & Contamination):** photo classification
    outputs are treated strictly as `hearsay`/`educated estimate`. Visual
    classification can *never* clear a stream or override a contamination
    check.

## 4. Fleetbase (AGPL-3.0)

- **Role:** Architectural design pattern for **Agent Contracts & Pipeline
  Event Loops**.
- **Architectural mapping:** informs the event-driven core architecture
  (publish/subscribe event bus between agents, state machines for case
  transitions, modular plugin contracts). These are generic design patterns;
  no Fleetbase expression is used.
- **Invariant & IP enforcement:**
  - **Zero AGPL code:** absolute clean-room implementation — no imported
    modules, libraries, or snippets from Fleetbase. **Process records**
    (independent design docs, our own tests, our own schemas) are the
    guarantee that clean-room holds.
  - **§16 Boundary:** complete isolation ensures AGPL terms never touch the
    helpme.green proprietary engine or client interfaces.

## 5. CIRCULOOS / FIWARE

- **Role:** Methodology for **Sustainability Metrics & Catalog Naming**.
- **Architectural mapping:** EU Product Environmental Footprint (PEF) and
  Environmental Footprint (EF 3.1) methodologies inform the environmental
  readiness dimensions rendered by the Explainer Agent; naming conventions
  align the material catalog with international standards.
- **Invariant & IP enforcement:**
  - **Custom schema:** we do **not** adopt the NGSI-LD API framework or
    FIWARE context-broker overhead. All data lives in our native, immutable,
    version-controlled store.
  - **R2 & R12 (Fail-Closed & Explainability):** sustainability scores require
    complete EF 3.1 parameters. If a parameter is missing, the score renders
    as `UNKNOWN` rather than estimating a value. The CIRCULOOS data-model
    repo has no license file — reference the methodology (facts, indicators);
    do not ingest that repo's content.

## 6. PV ICE (BSD-3)

- **Role:** Algorithmic model for **Mass/Energy-Flow & Material Degradation**.
- **Architectural mapping:** direct inspiration (and potential BSD-3 module
  reuse) for deterministic yield calculations in the Evaluator Core; powers
  mass-closure verification (input mass = output products + residual waste).
- **Invariant & IP enforcement:**
  - **R7 (Financial & Yield Conservatism):** the **basis-completeness check is
    engine-owned** — the kernel is called only after the Evaluator Core has
    verified the basis (mass closure, price basis, units, currency-year).
    Never delegate the fail-closed check to a kernel's own error handling.
  - **R11 (AI Never Concludes):** kernel execution happens strictly inside the
    deterministic Evaluator Core runtime, fully separated from LLM generation.
  - **Domain scope:** PV ICE is solar-specific. The pattern generalizes; each
    future kernel (batteries, WEEE, textiles) requires its own license
    verification and basis-gate before integration.

## System Architecture Summary

| Source Domain | Type of Asset | Target System Component | Primary Invariant / Boundary |
| --- | --- | --- | --- |
| Precious Plastic | Knowledge / Logic | Route Cards & Knowledge Register | R5 (Provenance & Attribution; BY-SA share-alike if substantial) |
| Plastic Odyssey | Concepts | Income-Tier & Regional Logic | Read-Only (No Plan Reproduction; R6) |
| Deep Waste | Taxonomy | Intake Classifier & Catalog Schema | R1 & R10 (Visuals = Hearsay Only) |
| Fleetbase | Design Pattern | Event Loop & Agent Bus | 0% Code Reuse (Clean-Room, Recorded) |
| CIRCULOOS / FIWARE | Indicators | Sustainability Metrics | Custom Schema (No NGSI-LD; R2/R12 UNKNOWN) |
| PV ICE | Algorithms | Deterministic Mass-Flow Kernel | R7 & R11 (Engine-Owned Basis Gate) |

---

*See `open-source-reuse.md` for verified licenses, attribution strings, and
the binding reuse rules. This document is a factual summary, not legal advice;
derivative-work boundaries are fact-dependent and should be reviewed by
counsel before shipping ingested content.*
