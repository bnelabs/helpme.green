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

---

# Public onboarding page — selected concept option 2

final result: passed

Date: 2026-08-18
Source visual truth: `/Users/barisnacierzeren/Documents/ChatGPT/helpme.green/website/assets/concept-option-2.png`
Implementation: `/Users/barisnacierzeren/Documents/ChatGPT/helpme.green/website/index.html`
Rendered evidence: `/Users/barisnacierzeren/Documents/ChatGPT/helpme.green/website/assets/screenshots/onboarding-viewport-desktop.png`
Mobile evidence: `/Users/barisnacierzeren/Documents/ChatGPT/helpme.green/website/assets/screenshots/onboarding-viewport-mobile.png`
Get-started evidence: `/Users/barisnacierzeren/Documents/ChatGPT/helpme.green/website/assets/screenshots/onboarding-get-started-desktop.png`, `/Users/barisnacierzeren/Documents/ChatGPT/helpme.green/website/assets/screenshots/onboarding-get-started-mobile.png`
Combined comparison input: `/Users/barisnacierzeren/Documents/ChatGPT/helpme.green/website/assets/screenshots/qa-concept-vs-onboarding.png`
Browser: Codex In-app Browser

## Comparison state and normalization

- Desktop implementation viewport: 1280×720 CSS px, device pixel ratio 1, screenshot pixels 1280×720.
- Mobile implementation viewport: 390×844 CSS px, device pixel ratio 1, screenshot pixels 390×844.
- Source concept: 864×1821 px. The comparison input uses its 864×720 top composition crop beside the 1280×720 desktop implementation capture; both are normalized to equal comparison-card widths for review. The source is a long concept board, so this pass judges the shared hero/rail/paper composition and uses separate rendered captures for responsive and Get started states.
- State: public onboarding page at top of page for the desktop comparison; binary tab selected in the Get started state; no user data or provider credentials present.

## Full-view and focused comparison evidence

The combined comparison shows the selected direction carried through: dark green navigation rail,
warm paper canvas, editorial serif headline, restrained utility sans text, numbered progression, and
a notebook/material reference visual. The implementation uses the real helpme.green notebook capture
and project-owned material assets instead of the concept's illustrative notebook photo or invented
controls. The focused review covered the release banner and hero, the five-phase framework, the
material-handling cards, the binary/Docker/source tabs, and the 390×844 responsive menu state.

## Required fidelity surfaces

- Fonts and typography: the page uses the repository's serif/sans/handwritten fallback direction;
  large editorial headlines, compact uppercase labels, and readable body copy preserve the source
  hierarchy. Exact typeface rendering remains platform-dependent because no webfont is bundled.
- Spacing and layout rhythm: the fixed desktop rail, generous paper sections, ruled cards, dark
  notebook block, and stacked mobile layout follow the concept's cadence. The mobile tabs were
  tightened to remain within the 390px viewport without horizontal page overflow.
- Colors and visual tokens: the implementation maps the existing brand tokens (`#f1eee6`,
  `#fffdf7`, `#203d1c`, `#80935e`, `#a66d17`, and `#bd5e4d`) to the concept's paper/forest/amber
  direction.
- Image quality and asset fidelity: the public page uses the checked-in brand mark, field-journal
  image, material examples, and browser-rendered notebook screenshot. The selected concept remains a
  design reference and is not presented as a product screenshot.
- Copy and content: the page adds a visible Get started path, six-target RC binary guidance, Docker
  and source routes, checksum instructions, handling framework, product limits, and a professional
  pre-release warning grounded in the current release workflow.

## Findings and comparison history

- [P2 — fixed] Mobile installation tabs initially exceeded the narrow content width and exposed a
  horizontal scrollbar. The mobile rule now removes the 125px minimum tab width; the final 390px
  capture has `scrollWidth` 375px inside a 390px viewport and all three labels are visible.
- No actionable P0, P1, or remaining P2 findings after the fix. P3 polish remains possible for
  exact cross-platform font matching and additional screenshot states.

## Interaction and browser evidence

- Mobile Menu toggled `aria-expanded` from `false` to `true`; selecting “How it works” closed the
  menu and moved to `#how-it-works`.
- Installation tabs switch `aria-selected` and panel visibility across Release binary, Docker, and
  From source without a page reload.
- Desktop and mobile Get started anchors were captured after image loading; the mobile target aligned
  at the section top (`targetTop` within 1px).
- Browser console errors and warnings: none returned by the Codex In-app Browser.
- `node --check website/app.js`, focused website tests, and `git diff --check` passed.
