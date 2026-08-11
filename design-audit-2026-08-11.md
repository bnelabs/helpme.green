# helpme.green whole-surface design audit — resolved direction

Date: 2026-08-11  
Surface: local helpme.green browser app  
Reference direction: Lab Notebook / field guide

## Previous problem

The former surface was a polished chat entry point: the dominant object was a message thread, the response was read as stacked transcript items, and the context rail was descriptive rather than useful. That made the product feel like a styled ChatGPT clone even though the underlying assistant and safety architecture were appropriate.

## New design decision

The central object is now a persistent notebook spread. Natural language remains the first input, but the result is organized into five user-visible phases:

1. Observe — describe what is in front of you.
2. Identify — keep a working material name with care.
3. Understand — hold evidence and missing context together.
4. Options — compare possible directions without overclaiming.
5. Next steps — choose the smallest useful check.

The phase rail, page dots, page count, and notebook copy make progress legible without exposing internal skills, retrieval mechanics, or model routing.

## Resolved findings

- The transcript metaphor is replaced by a working artifact.
- The response is presented as a bounded working read, evidence list, change conditions, and next question.
- Observations, references, replies, and drafts are stored per phase in browser-local state.
- Returning to any phase preserves its page content; starting a new note archives the previous note in the local history.
- The Material Library provides a real visual reference layer across plastics, metals, cable/harness, paper/board, glass, and textiles.
- Light and dark modes share the same hierarchy and use different paper/field tokens rather than a simple color inversion.
- Motion communicates page changes and drawer state, with reduced-motion fallback.
- Mobile stacks the spread, keeps phase navigation visible, and turns the library into an overlay drawer.

## Reality standard

Material images are deliberately post-use or process scrap: scuffed, cut, torn, bent, crumpled, frayed, punched, worn, or otherwise plausibly handled. Metal subtypes have dedicated images so steel, aluminium, copper, brass, stainless, and mixed metal can be visually discriminated without looking like a dirty industrial catalog. The library remains illustrative; it is not a substitute for testing or source-backed identification.

## Remaining boundaries

This audit covers the UI, assets, interaction model, and local browser behavior. It does not certify material identity, environmental claims, provider-backed answer quality, production deployment, screen-reader output, native safe-area rendering, or full WCAG conformance.
