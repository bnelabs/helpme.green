# Academic Library / Airtable review

Review date: 2026-08-11

Input: `Academic Library_ Library - Airtable.pdf` supplied outside the repository. The export contains 51 pages of source cards. The PDF contains 61 unique non-Airtable hyperlink targets after duplicate annotations are collapsed; some cards contain more than one paper and some cards repeat a paper.

## Decision

Add the high-value sources to the governed candidate manifest, then ingest them through the normal source pipeline. The selected set is concentrated on the questions this KB must answer well:

- feedstock composition, contamination, and source separation;
- mechanical-recycling routes for PE, HDPE, PP, PET, and flexible films;
- material testing, degradation, quality, and application fit;
- HSE, additives, NIAS, migration, and microplastics measurement;
- route comparison, LCA, techno-economics, and limits of chemical recycling;
- sorting and characterization methods, including NIR and machine learning.

The sources are references, not a single source of truth. They are registered with limitations and authority tiers; ingestion does not promote their statements to claims automatically.

## Sources added to the manifest

The following 35 source IDs were added to `knowledge/source-manifest.yml`:

1. `king-county-mrf-assessment-2022`
2. `eu-plastics-recycling-terminology-2023`
3. `hdpe-recovery-pathways-2024`
4. `hdpe-voc-contamination-chain-2024`
5. `plastic-pyrolysis-lca-2023`
6. `recycled-content-quantification-review-2025`
7. `hdpe-recyclate-characterization-2024`
8. `pp-yogurt-cup-closed-loop-2024`
9. `hdpe-repeated-recycling-2023`
10. `rhdpe-toys-safety-2024`
11. `flexible-film-inks-recycling-2024`
12. `recyqmeter-recycled-quality-2025`
13. `recycling-quality-alignment-2025`
14. `flexible-recycling-process-mfa-2022`
15. `flexible-recycling-quality-economics-2022`
16. `flexible-single-stream-feasibility-2023`
17. `advanced-post-sorting-tradeoffs-2026`
18. `plastics-additives-complexity-2024`
19. `advanced-plastics-recycling-analysis-2024`
20. `polyethylene-recycling-degradation-quality-2024`
21. `recycled-plastics-safety-assessment-2023`
22. `pp-mechanical-solvent-recycling-2023`
23. `polyolefin-waste-light-olefins-2024`
24. `mixed-polyester-recycling-lca-2024`
25. `pet-degradation-recycling-review-2024`
26. `nir-polyolefin-differentiation-2026`
27. `nir-polyolefin-bulk-properties-2023`
28. `plastic-recycling-cascade-2024`
29. `flexible-packaging-waste-flows-2025`
30. `microplastics-research-review-2024`
31. `microplastics-food-regulatory-science-2024`
32. `global-plastic-waste-pathways-2024`
33. `plastic-gasification-tea-lca-2023`
34. `hydrothermal-waste-plastics-lca-2023`
35. `plastic-to-x-pathways-pet-2023`

## Already represented or intentionally not duplicated

- The OECD recycled-content report in the PDF is already represented by the governed PDF source `oecd-recycled-content-requirements`. The Airtable landing page was not registered as a duplicate.
- The PDF's second copy of the Nature Food food-loss paper was treated as a duplicate, not a second source.
- The PDF's duplicate Cross-Linked Polyolefins link was not added because it is a narrower review with lower immediate value than the selected feedstock, quality, HSE, and route sources.

## Deferred or not added

These are useful context in the right project, but they do not materially improve the first KB retrieval scope for evaluating recycling feedstock, equipment, HSE, and route feasibility:

- PET consumer-behaviour and deposit-return modelling (`Think before you throw!`);
- landfill methane and food-loss system studies;
- marine-plastic stock modelling;
- green nudges for single-use cutlery;
- broad plastic-alternative greenhouse-gas comparisons;
- the US PET collection and demand study;
- the ASTM workshop marketing/lead-capture URL, which is not a stable technical source;
- the separate chemical end-of-life flow paper, which is broader background than the current decision-support scope;
- the cross-linked-polyolefin review, unless a future cable-insulation or XLPO workstream is opened;
- the PET/PEF blend paper and other new-materials papers, unless a product-development workstream is opened.

Deferral is not a quality judgement. It keeps retrieval focused and avoids allowing broad policy or unrelated environmental studies to crowd out feedstock and process evidence. They can be reintroduced as a separate systems or product-design collection.

## Ingestion and access handling

The selected sources remain candidate references until fetched and extracted. A paywall, anti-bot page, JavaScript shell, or inaccessible PDF is recorded as an access failure and placed in the manual-download queue; it is never represented as if its full text had been read.

For manually downloaded material:

1. Put the file under the ignored `.data/manual-source-downloads/<source-id>/` directory.
2. Preserve the original URL, publisher, publication date, edition, and SHA-256 hash.
3. Import it only after checking that the file corresponds to the registered source.
4. Keep licensed raw files out of Git; commit the manifest entry, provenance note, and derived catalog metadata only.

## How these sources should be used in answers

For a plastics-recycling question, retrieval should first identify the material family, process route, contamination, end-use, and jurisdiction. The answer layer should then combine the most relevant source chunks with the user's own facts, state what is measured versus inferred, and give a next test or decision. A review article can frame a route; it cannot prove that a particular bale, machine, permit, or product will work.
