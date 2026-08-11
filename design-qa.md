# helpme.green Lab Notebook v2 — design QA

Final result: passed

Date: 2026-08-11  
Reference concept: `/Users/barisnacierzeren/.codex/generated_images/019ff1c6-23b3-7ac1-ace8-cf7cc0a86b62/exec-bbe4151e-db74-4acd-98dc-3909906c9e5c.png`  
Browser: Codex In-app Browser  
Verified viewports: 1440×1000 desktop and 390×844 mobile

## Product shift

The surface is now a field notebook rather than a transcript. Natural language remains the entry point, but each observation becomes part of a persistent investigation page with a visible phase rail, material reference board, bounded working read, and an explicit next question.

## Fidelity ledger

| Point | Reference intent | Render evidence | Result |
| --- | --- | --- | --- |
| Primary object | Editorial notebook spread | Two-page working spread with left evidence page and right working read | Passed |
| Orientation | Visible phase progression | Observe → Identify → Understand → Options → Next steps rail, dots, and page count | Passed |
| Material context | Reference imagery matched to the subject | Post-use/process-scrap boards for plastics, metals, cable/harness, paper/board, glass, and textiles | Passed |
| Metal discrimination | Real but composed metal scrap | Dedicated steel, aluminium, copper, brass, stainless, and mixed-metal assets load independently | Passed |
| Typography | Editorial handwritten title with quiet utility text | Serif read, restrained sans labels, and compact field-note title | Passed |
| Light/dark | Calm paper and dark field modes | Theme toggle updates tokens, surfaces, copy, borders, controls, and imagery framing | Passed |
| Motion | Page-turn transition | Forward/back page-turn classes use a restrained 0.62s animation with reduced-motion fallback | Passed |
| Mobile | Keep orientation and actions usable | Horizontal phase rail, stacked notebook pages, overlay library drawer, no horizontal overflow at 390px | Passed |
| Branding | Mark, wordmark, favicon | Project-owned `brand-mark.png`, lowercase wordmark, PNG favicon, and touch icon are wired | Passed |

## Interaction evidence

- Selecting `Cu — Copper` and `PP — Polypropylene` adds reference chips to the current page and keeps their dedicated images selected in the library.
- Moving to Identify and returning to Observe preserves the saved references and the original phase content.
- A natural-language observation (`A scuffed copper cable offcut has exposed strands and a worn dark jacket.`) is saved to the current page and remains after moving between phases.
- The forward transition exposes `page-turn-forward` while the notebook is changing phase; reverse navigation uses the corresponding back animation.
- New note starts a fresh page while retaining the prior note in the browser-local history.
- Material Library opens as a desktop rail and as a mobile overlay with a backdrop and close action.
- Dark mode and light mode were each inspected; both retain the same hierarchy and interaction affordances.
- Browser console verification returned no errors or warnings on desktop or mobile QA tabs.

## Reality/coherence rule for material imagery

All runtime material images are composed as post-use or process scrap specimens, not pristine product catalog shots. The visual cues are intentionally material-relevant: cuts, torn edges, scuffs, dents, deformation, exposed fibers or conductors, punched holes, abrasion, oxidation, and controlled contamination where appropriate. The images are contextual references only; they do not identify a polymer, alloy, textile composition, or treatment and are never presented as testing evidence.

## Accessibility and trust

- Semantic headings, labels, buttons, and live status text remain in the markup.
- Focus rings, 44px-class touch targets, keyboard observation submission, `Shift+Enter` line breaks, and reduced-motion behavior are retained.
- Material references, observations, and assistant reads are stored per phase in browser-local state; moving between phases does not discard them.
- This is a browser and implementation audit, not a full WCAG conformance claim. Screen-reader output, native safe-area rendering, color measurement under every display profile, and provider-backed content quality still need dedicated checks.
