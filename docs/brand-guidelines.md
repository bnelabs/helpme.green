# helpme.green Lab Notebook — brand guidelines

helpme.green is a calm field instrument for turning an uncertain situation into a clearer next check. The visual language combines a tactile paper notebook, a quiet botanical mark, and carefully framed post-use material specimens. It should feel professional, observant, and useful without becoming clinical or decorative for its own sake.

## Brand idea and voice

The product starts with ordinary language and gradually gives the user a working record. Use short, direct copy: “What do you see?”, “Name the material with care”, and “What could change this?” Keep uncertainty visible. Never imply that an illustrative image, model read, or reference label is a confirmed material identity, test result, permit, yield, or business outcome.

## Plain language rule

User-facing copy should sound like a capable person helping at a workbench. Prefer “your notes”, “library examples”, “first look”, “what fits”, and “next simple check”. Keep words such as evidence, provenance, taxonomy, reference cues, working hypothesis, and discriminates inside implementation or source documentation; do not make the user learn them to use the product.

## Logo and mark

- Primary mark: [`assets/brand-mark.png`](../assets/brand-mark.png), the contour-leaf emblem used in the header and future avatar/social surfaces.
- Favicon: [`assets/favicon.png`](../assets/favicon.png), the transparent PNG export used by the browser tab.
- Wordmark: `helpme.green`, always lowercase. Set `helpme` in the editorial serif and `.green` in moss.
- Lockup: place the mark to the left of the wordmark with 8–10px in compact UI and 12–16px in larger brand placements.
- Clear space: reserve at least the mark’s visible leaf width around the lockup.
- Minimum sizes: 18px for favicon use, 24px for compact UI, and 32px for a visible header mark.

Do not stretch, rotate, outline, recolor with gradients, add a drop shadow, place the mark in a generic badge, or add an unapproved slogan. Keep the transparent PNG as the runtime source of truth.

## Color system

| Token | Light mode | Dark mode | Role |
| --- | --- | --- | --- |
| Canvas | `#f1eee6` | `#101a14` | Ambient page ground |
| Paper | `#fffdf7` | `#18241b` | Notebook and primary writing surface |
| Paper alt | `#f8f5ed` | `#1d2a20` | Working-read page and secondary panels |
| Ink | `#1d281e` | `#f4f0e5` | Primary reading text |
| Ink soft | `#39463a` | `#d7d8c9` | Supporting content |
| Forest | `#203d1c` | `#d7e7ae` | Primary action and progress signal |
| Moss | `#80935e` | `#a9bf7d` | Brand accent and active state |
| Amber | `#a66d17` | `#edbd62` | “Could change this” and attention cue |
| Coral | `#bd5e4d` | `#ef9c89` | Error or risk cue |

Light mode should read like warm archival paper. Dark mode should read like a deep green work surface, not a black chat interface. Accent colors are signals: use them to show state, progression, or attention rather than as decoration.

## Typography

- Editorial voice: `Iowan Old Style`, `Baskerville`, `Times New Roman`, serif fallback.
- Utility text: `Inter`, then the system sans stack.
- Handwritten field title: `Segoe Print`, `Bradley Hand`, `Comic Sans MS`, cursive fallback; use sparingly for the editable note title and empty-state observation hint.
- Use uppercase only for short structural labels such as `OBSERVE`, `WORKING READ`, and `MATERIAL REFERENCES`.
- Keep labels quiet, headings compact, and body copy comfortably readable. Do not introduce a one-off display typeface for a single component.

## Surfaces, transparency, and depth

The notebook is the main object. Use a small number of stable surfaces: the paper spread, the quiet phase rail, and the library panel. Transparency is reserved for the sticky header and mobile drawer backdrop; critical text always sits on an opaque or near-opaque readable surface.

- Use blur only where it separates a surface from the canvas.
- Keep borders warm and low-contrast, with stronger borders on focus and selected states.
- Use soft shadows to lift the notebook, not to make every control look like a floating card.
- Respect reduced-transparency preferences by falling back to solid panels and borders.

## Motion

Motion explains navigation and preserves orientation:

- Page changes use a restrained `page-turn-forward` / `page-turn-back` transition around 0.62s.
- The phase rail and progress dots remain stable while the spread turns.
- The material drawer uses a smooth horizontal reveal with a quiet backdrop.
- Hover and focus movement is limited to small elevation or border changes.
- `prefers-reduced-motion: reduce` collapses animation and smooth scrolling.

Do not use looping decoration near the writing surface, parallax on text, or animation that competes with typing and reading.

## Material imagery standard

Material images are field-guide references, never evidence. Every family and subtype should be shown as a cleanly composed post-use or process-scrap specimen rather than a virgin product sample. The specimen should include enough physically plausible cues to distinguish the family without becoming ugly:

- Plastics: scuffed, torn, cut, crumpled, snapped, or deformed pieces with appropriate translucency and molded features.
- Metals: punched or sheared offcuts, bent pieces, cut wire, worn surfaces, restrained oxidation, and recognizable alloy color/finish differences.
- Cable and harness: cut jacket ends, exposed conductors, frayed insulation, worn sleeves, and generic damaged connectors.
- Paper and board: torn edges, creases, visible flute or fiber, scuffed print/coating, and compressed or folded structure.
- Glass: rounded or tumbled cullet, thick offcuts, bottle-glass color, edge wear, and safe controlled composition rather than dangerous shards.
- Textiles: frayed yarns, worn surfaces, torn seams, cut straps, netting, and believable weave differences.

Keep lighting, scale, and background consistent across the library so the materials feel like one professionally photographed reference collection. Never use an image to certify polymer, alloy, fiber content, contamination, or recyclability; keep the observation, source, and any test result attached to the page.

## AI-assisted comparison

Comparison is a three-part relationship: the user’s real sample and notes, the library’s contextual examples, and the assistant’s first read. The interface must keep those roles visibly separate.

- Let the user add up to three local sample photos, condition, origin, and the question they want compared.
- Ask what form the sample is: whole piece, flakes/chips, granules/pellets, powder/dust, mixed pieces, or a closed container.
- Send written notes, sample form, sample context, and selected library example labels to the ordinary-language assistant route.
- For granules, powder/dust, mixed pieces, and closed containers, show a plain warning that a photo may not be enough and keep the result from forcing one material name.
- Label the result `Assistant comparison — first read` and keep “what fits” or “what I can see”, “what this photo cannot tell us”, “what might change this”, and “next simple check” visible in the answer.
- Never imply that the assistant inspected pixels, confirmed a polymer/alloy/fibre, produced a test result, or certified a route unless a separately approved evidence and provider contract supports that claim.
- Keep unknown dust closed rather than directing the user to spread or handle it for a photo.
- Clear a comparison whenever the sample, notes, form, or library selection changes, so the page cannot display stale reasoning as if it were current.

## Taxonomy

The first library layer covers:

- Plastics: PP, HDPE, LDPE, ABS, PET, PVC, and PS.
- Metals: carbon steel, aluminium, copper, brass, stainless steel, and mixed metal.
- Cable & Harness: copper conductor cable, aluminium conductor cable, control harness, data cable, and coaxial cable.
- Paper & Board: corrugated board, kraft paper, office paper, coated paper, and fiberboard.
- Glass: clear, green, amber, and glass fiber.
- Textiles: cotton, polyester, nylon, wool, blended textile, and elastane.

Add future families only when each has a coherent scrap visual, a bounded label, and an explicit note that the library is contextual rather than diagnostic.

## Responsive rules

Design from the smallest supported width upward:

- At narrow widths keep the header to the mark, wordmark, new-note action, and compact mode control.
- Keep phase navigation horizontally scrollable but compact; never hide the current phase or overall count.
- Stack the notebook pages vertically and keep the page-turn relationship visible.
- Present the Material Library as a right-side overlay with a backdrop and a clear close action.
- Keep primary actions at least 44px high and prevent horizontal page overflow at 320px and 390px.
- Preserve touch spacing, visible focus, readable titles, and enough bottom padding for mobile browser controls.

## Accessibility and trust

Preserve semantic headings, labels, buttons, live status text, keyboard submission, visible focus, reduced-motion handling, and honest connection/error states. Do not describe the product as fully WCAG-compliant without dedicated assistive-technology and contrast audits.

## Asset inventory

- [`assets/brand-mark.png`](../assets/brand-mark.png) — transparent contour-leaf logo mark.
- [`assets/favicon.png`](../assets/favicon.png) — transparent favicon export.
- [`assets/material-plastics.webp`](../assets/material-plastics.webp) — mixed post-use/process plastic scrap board.
- [`assets/material-metals.webp`](../assets/material-metals.webp) — mixed metal offcut board.
- `assets/material-steel.webp`, `material-aluminium.webp`, `material-copper.webp`, `material-brass.webp`, `material-stainless.webp`, `material-mixed-metal.webp` — dedicated metal subtype boards.
- `assets/material-pp.webp`, `material-hdpe.webp`, `material-ldpe.webp`, `material-abs.webp`, `material-pet.webp`, `material-pvc.webp`, `material-ps.webp` — dedicated plastic subtype boards.
- [`assets/material-cable-harness.webp`](../assets/material-cable-harness.webp), [`assets/material-paper.webp`](../assets/material-paper.webp), [`assets/material-glass.webp`](../assets/material-glass.webp), [`assets/material-textiles.webp`](../assets/material-textiles.webp) — post-use/process scrap family boards for the remaining initial categories.

Keep images separable from the interface, compositional lighting consistent, and all imagery subordinate to the user’s own observation and evidence.
