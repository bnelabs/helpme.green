# helpme.green — Agent Instructions

## Mission

Build the helpme.green platform per REQUIREMENTS.md (the binding contract). The
system supports human decisions; it never executes them. It runs autonomously,
but every agent operates within a strict task contract and never deviates into
other concerns.

## Non-negotiable boundaries (REQUIREMENTS.md §16 — the never-list)

- Never approve or execute a purchase, shipment, process, experiment, legal
  classification, safety procedure, or product release.
- Never let an AI write a conclusion or improvise out-of-coverage answers. The
  deterministic engine evaluates; the AI only interviews, translates, and
  explains.
- Never promote user claims or dialogue content into facts without the
  two-review pipeline (REQUIREMENTS.md §6).
- Never upgrade an evidence state automatically (`hearsay → educated estimate →
  observed → screened → verified`; no silent upgrades).
- Never compute a financial figure on an incomplete basis; unknown is never
  replaced by zero or assumption.
- Never present unproven science as established; hypotheses are always labelled.
- Never derive market prices from user chatter; market data comes from
  refreshed, sourced external feeds.
- Never store user API tokens in plaintext; never train on user data without
  explicit consent.
- The Pro Console never executes anything; MCP is read-only; MCP/user-supplied
  content is untrusted, prompt-injection-isolated, and never becomes knowledge.
- No human in the operational loop; "requires qualified external review" is an
  output state, not a human process step.
- Never commit credentials, tokens, API keys, or real supplier/batch/assay/
  partner data to Git, logs, tests, or documentation.

## Engineering workflow

- Use test-driven development: write one failing behavior test, observe the
  expected failure, implement the minimum behavior, then refactor while green.
- Keep invariants (REQUIREMENTS.md §5, R1–R12) in the deterministic layer and
  runtime guards — never only in prompts.
- Use `Decimal` for money and explicit units/currencies; missing evidence yields
  `UNKNOWN`, never zero.
- Preserve immutable snapshots and append-only audit history.
- Run targeted tests after every change and the complete verification gate
  before claiming completion.
- Surface any conflict between REQUIREMENTS.md and an implementation constraint —
  never resolve it silently.

## Verification

Run the project's configured verification gates (lint, type checks, tests) and
the deterministic-engine cross-model check (identical engine outputs across
providers/models) before claiming completion. Report exactly what was verified
and what remains.
