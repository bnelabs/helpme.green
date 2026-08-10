# helpme.green

Autonomous, advisory decision support for the circular economy.

Describe any material stream. Get an honest, evidence-grounded, geography-aware
answer: what it could become, what processing routes are actually applied (with
sources), what evidence is missing before anyone should act, and what it is
conservatively worth — here, in this economy.

- **Advisory only.** The system never approves or executes purchases, shipments,
  processes, experiments, legal classifications, or product releases.
- **Deterministic engine + governed knowledge base.** An AI interviews and
  explains, but never writes the conclusion.
- **Autonomous operation.** Every process is auto-fed; every issue is handled by
  AI agents with strict task contracts.

## Status

Early-stage. The full requirements and plan are in
[REQUIREMENTS.md](REQUIREMENTS.md) — the binding contract for implementation.
`AGENTS.md` governs how coding agents (e.g. Codex) must operate in this repo.

## Documents

- `REQUIREMENTS.md` — consolidated v3.0 requirements & plan (codex goal brief).
- `AGENTS.md` — repository instructions and invariant rules for coding agents.
- `docs/open-source-reuse.md` — license register for external open-source circular-economy projects (reuse rules + per-project verdicts, binding on the Sourcer Agent).

## Reference

The deterministic evaluation logic (navigator/compliance/economics evaluators)
has a reference implementation in the private `bnelabs/konverta-material-intelligence`
repository; reuse that logic where REQUIREMENTS.md calls for it, subject to the
boundaries in REQUIREMENTS.md §16.
