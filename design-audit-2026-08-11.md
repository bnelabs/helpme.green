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

## AI-assisted comparison flow

The next interaction keeps the same distinction between a real sample, library examples, and the assistant's first read:

1. The user adds a real sample photo and chooses its form: whole piece, flakes/chips, granules/pellets, powder/dust, mixed pieces, or a closed container. The resized photo stays in browser-local notebook state; it is not silently sent to the assistant.
2. Granules, powder/dust, mixed pieces, and closed containers show a clear limit before comparison. Unknown dust is not opened or spread just to make a better photo.
3. The user adds optional condition, origin, and comparison detail, then selects one or more library examples.
4. “Compare carefully” sends the written observations, sample form, sample context, and selected example labels through the existing ordinary-language assistant route. The prompt requires a description of visible or supplied details and an explicit limit instead of a forced material name.
5. The result is shown with plain headings: what fits or what can be seen, what the photo cannot tell us, what might change this, and the next simple check.
6. Any new observation, changed sample detail, changed sample form, or changed example selection clears the old comparison so stale reasoning is not presented as current.

This slice is still text-and-context assisted. It does not claim to inspect photo pixels or identify a material from an image. A future vision-capable comparison can be added only when the provider contract, consent, retention, and source boundaries are explicit. The next asset pass should add separate real scrap examples for whole pieces, flakes, granules, and powder/dust rather than reusing one image for every form.

## Remaining boundaries

This audit covers the UI, assets, interaction model, local evidence capture, and comparison request path. It does not certify material identity, environmental claims, provider-backed answer quality, photo-pixel analysis, server-backed phase sync, production deployment, screen-reader output, native safe-area rendering, or full WCAG conformance.
