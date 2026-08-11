# Manual-download queue

Last checked: **2026-08-11** against the expanded 153-source manifest. The current digest has 102 sources with a latest extracted document; 51 registered candidates have no latest readable document.

These are reputable references that the bounded fetcher could not digest automatically. They remain
registered in `knowledge/source-manifest.yml`, but their failed fetches are not treated as evidence.
If you manually download a file, keep the original filename, URL, publication/version date, and a
SHA-256 hash. Do not commit the file or the SQLite database. Put the local copy under an untracked
folder such as `.data/manual-source-downloads/<source-id>/` and provide it for a reviewed local
import or replace the manifest URL with an explicitly licensed, machine-readable copy.

## Current queue

| Source ID | Resource | Current blocker | Useful manual action |
|---|---|---|---|
| `eu-wfd-2025` | [Waste Framework Directive consolidated text](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02008L0098-20251016) | EUR-Lex returned a 202 shell with no extractable text to the bounded fetcher | Download the English HTML/PDF from the EUR-Lex page and retain the Official Journal/CELEX metadata |
| `eu-copper-eow-715-2013` | [Copper scrap end-of-waste Regulation](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX:32013R0715) | EUR-Lex 202 shell; no readable body | Download the official English PDF/HTML; do not use a third-party legal mirror as the legal source |
| `eu-wsr-2024-1157` | [Waste Shipments Regulation](https://eur-lex.europa.eu/eli/reg/2024/1157/oj) | EUR-Lex 202 shell; no readable body | Download the Official Journal text or a reviewed PDF export |
| `eu-waste-treatment-bat-2018` | [Waste-treatment BAT conclusions](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02018D1147-20180817) | EUR-Lex 202 shell; no readable body | Download the Official Journal PDF/HTML and retain the consolidated-date note |
| `eu-pops-regulation-2025` | [POPs Regulation consolidated text](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02019R1021-20250804) | EUR-Lex 202 shell; no readable body | Download the current consolidated text; verify Annex IV and the consolidation date |
| `eu-weee-directive-2012` | [WEEE Directive](https://eur-lex.europa.eu/eli/dir/2012/19/oj/eng) | EUR-Lex 202 shell; no readable body | Download the English Official Journal text/PDF and retain the national-implementation limitation |
| `eu-wt-bat-2018` | [Waste-treatment BAT conclusions alias](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02018D1147-20180817) | Same EUR-Lex 202 shell; no readable body | Download once and preserve both governed source IDs if both register entries are used |
| `eu-packaging-packaging-waste-regulation-2025` | [Packaging and Packaging Waste Regulation](https://eur-lex.europa.eu/eli/reg/2025/40/oj) | EUR-Lex 202 shell; no readable body | Download the English Official Journal text/PDF; retain CELEX `32025R0040` |
| `eu-ecodesign-sustainable-products-regulation-2024` | [Ecodesign for Sustainable Products Regulation](https://eur-lex.europa.eu/eli/reg/2024/1781/oj) | EUR-Lex 202 shell; no readable body | Download the English Official Journal text/PDF; retain CELEX `32024R1781` |
| `pita-cable-separation-2018` | [Cable-waste copper separation study](https://www.mdpi.com/2075-4701/8/11/517) | Publisher returned an automated-access block | Download the open-access article PDF from the publisher or repository and retain licence/authors |
| `erema-regrindpro-technical-sheet` | [EREMA RegrindPro technical data](https://www.erema.com/en/regrind_pro_technical_data/) | Main URL triggered an access challenge; a query-string fallback is now registered | If the fallback still fails, download the current technical data page/PDF and record the model/date |
| `erema-regrindpro-technical-data-current` | [EREMA RegrindPro current page](https://www.erema.com/en/regrind_pro_technical_data/) | Same access challenge as the legacy catalog ID | Same manual action as the legacy ID; keep one source copy and two provenance records only if needed |
| `echa-safety-data-sheets` | [ECHA safety-data-sheet guidance](https://echa.europa.eu/safety-data-sheets) | ECHA returned an automated-access block | Download the current ECHA guidance PDF from the page and retain the revision date |
| `echa-plastic-additives-mapping` | [ECHA plastic-additives mapping exercise](https://echa.europa.eu/mapping-exercise-plastic-additives-initiative) | ECHA returned an automated-access block | Download the page/report manually; retain the ECHA URL and current regulatory-status warning |
| `tomra-plastics-sorting` | [TOMRA plastics sorting applications](https://www.tomra.com/en-ie/waste-metal-recycling/applications/waste-recycling/plastics) | TOMRA returned an automated-access block | Download the current application brochure or technical sheet from TOMRA |
| `tomra-gainnext` | [TOMRA GAINnext](https://www.tomra.com/waste-metal-recycling/products/machines/gainnext) | TOMRA returned an automated-access block | Download the current GAINnext product sheet or test-centre document |
| `tomra-holygrail` | [TOMRA digital-watermark and tracer sorting context](https://www.tomra.com/news-and-media/feature-articles/holygrail-intelligent-sorting-to-achieve-a-circular-economy-for-packaging) | TOMRA returned an automated-access block | Download the feature article or an official project/product PDF |
| `starlinger-recycling-brochure` | Starlinger post-consumer recycling brochure | Direct PDF returned a fetch failure | Download the current brochure from [Starlinger brochures](https://www.starlinger.com/en/recycling-technology/brochures) |
| `starlinger-recostar-sheet` | Starlinger recoSTAR dynamic art technical sheet | Direct PDF returned a fetch failure | Download the current model sheet from Starlinger and record model/revision |
| `precious-plastic-machines` | [Precious Plastic machine overview](https://www.preciousplastic.com/solutions/machines/overview) | Current URL returned 404/changed-site content | Use the local downloaded Precious Plastic kit already mounted for the project, or download the current machine library from the official site |
| `sciencedirect-plastic-recycling-open-access` | [ScienceDirect engineering review](https://www.sciencedirect.com/science/article/pii/S2666086524000122) | Publisher returned an automated-access block | Download through the publisher/library entitlement or locate the author’s legal open-access repository copy; retain DOI and licence |

### Academic Library expansion queue

The following selected Airtable references were registered but could not be fetched by the bounded retriever. `Source fetch failed safely` is intentionally conservative: it means the retriever did not obtain a trustworthy document, not that the paper is unimportant or that its findings were verified.

| Source ID | Resource | Current blocker | Useful manual action |
|---|---|---|---|
| `eu-plastics-recycling-terminology-2023` | [Clarifying European terminology in plastics recycling](https://www.sciencedirect.com/science/article/pii/S2452223623001190?via%3Dihub) | ScienceDirect fetch failed safely | Download the article or a lawful author manuscript; retain DOI, licence, and version |
| `hdpe-recovery-pathways-2024` | [Recovery pathway assessment of recycled HDPE](https://www.sciencedirect.com/science/article/pii/S2212827124000763) | ScienceDirect fetch failed safely | Download the article or lawful repository copy; preserve the case-study scope |
| `hdpe-voc-contamination-chain-2024` | [Volatile organic contaminants in HDPE milk bottles](https://www.sciencedirect.com/science/article/pii/S0959652624020195?via%3Dihub) | ScienceDirect fetch failed safely | Download the article or lawful repository copy; retain methods and sampling details |
| `plastic-pyrolysis-lca-2023` | [Post-use plastic to plastic via pyrolysis](https://www.sciencedirect.com/science/article/pii/S0959652623030251?via%3Dihub) | ScienceDirect fetch failed safely | Download the article or lawful repository copy; retain allocation and feed assumptions |
| `recycled-content-quantification-review-2025` | [Quantification of recycled content in plastics](https://www.sciencedirect.com/science/article/pii/S0921344925003040?via%3Dihub) | ScienceDirect fetch failed safely | Download the review or lawful author manuscript; retain analytical-method caveats |
| `hdpe-recyclate-characterization-2024` | [Data-driven HDPE recyclate characterization](https://www.sciencedirect.com/science/article/pii/S0921344924001332?via%3Dihub) | ScienceDirect fetch failed safely | Download the article; preserve FTIR, DSC, TGA, rheology, and sample details |
| `pp-yogurt-cup-closed-loop-2024` | [Closed-loop recycling of PP yogurt cups](https://www.sciencedirect.com/science/article/pii/S0921344924001320?via%3Dihub) | ScienceDirect fetch failed safely | Download the article or lawful repository copy; retain the separately collected-feed limitation |
| `hdpe-repeated-recycling-2023` | [Repeated recycling of HDPE milk bottles](https://www.sciencedirect.com/science/article/pii/S0921344922005663) | ScienceDirect fetch failed safely | Download the article or lawful repository copy; retain the controlled-extrusion scope |
| `rhdpe-toys-safety-2024` | [Safety of recycled HDPE for child toys](https://www.sciencedirect.com/science/article/pii/S0304389424020612?via%3Dihub) | ScienceDirect fetch failed safely | Download the article; preserve migration, NIAS, and product-safety test details |
| `flexible-film-inks-recycling-2024` | [Printed flexible packaging recycling](https://www.sciencedirect.com/science/article/pii/S0304389424009543?via%3Dihub) | ScienceDirect fetch failed safely | Download the article; preserve ink, VOC, filtration, and degassing details |
| `recyqmeter-recycled-quality-2025` | [RecyQMeter recycled-plastics quality](https://www.sciencedirect.com/science/article/pii/S0956053X25002570?via%3Dihub) | ScienceDirect fetch failed safely | Download the article or lawful repository copy; retain the scoring method and validation scope |
| `recycling-quality-alignment-2025` | [Quality alignment across the circular plastics chain](https://www.sciencedirect.com/science/article/pii/S0956053X25001631?via%3Dihub) | ScienceDirect fetch failed safely | Download the article; preserve how each actor defines purity and quality |
| `flexible-recycling-process-mfa-2022` | [Flexible-plastics recycling performance and material flow](https://www.sciencedirect.com/science/article/pii/S0956053X22004470?via%3Dihub) | ScienceDirect fetch failed safely | Download the article; preserve yield, transparency, and CEFLEX test conditions |
| `flexible-recycling-quality-economics-2022` | [Flexible-plastics quality and economic assessment](https://www.sciencedirect.com/science/article/pii/S0956053X22004275?via%3Dihub) | ScienceDirect fetch failed safely | Download the article; preserve hot/cold wash, filtration, degassing, and deodorization assumptions |
| `flexible-single-stream-feasibility-2023` | [Flexible packaging from single-stream collection](https://www.sciencedirect.com/science/article/abs/pii/S0921344923000459?via%3Dihub) | ScienceDirect fetch failed safely | Download the article or lawful repository copy; retain collection, yield, and end-market assumptions |
| `advanced-post-sorting-tradeoffs-2026` | [Post-sorting plastic packaging trade-offs](https://www.nature.com/articles/s41586-026-10606-4) | Redirect target outside the explicit source allowlist | Download the Nature article or lawful manuscript; alternatively register the verified redirect host explicitly |
| `plastics-additives-complexity-2024` | [Chemical complexity of plastics and life-cycle outcomes](https://www.nature.com/articles/s41578-024-00705-x) | Redirect target outside the explicit source allowlist | Download the Nature Reviews article or lawful manuscript; retain the additives and HSE caveats |
| `advanced-plastics-recycling-analysis-2024` | [Circular solutions for advanced plastics recycling](https://www.nature.com/articles/s44286-024-00121-6) | Redirect target outside the explicit source allowlist | Download the Nature Chemical Engineering article or lawful manuscript; preserve pilot-failure lessons |
| `polyethylene-recycling-degradation-quality-2024` | [Polyethylene degradation and recycled quality](https://www.nature.com/articles/s41467-024-52856-8) | Redirect target outside the explicit source allowlist | Download the Nature Communications article or lawful manuscript; retain rheology and degradation scope |
| `recycled-plastics-safety-assessment-2023` | [Safety assessment of recycled post-consumer plastics](https://www.mdpi.com/2313-4321/8/6/87) | Publisher fetch failed safely | Download the open-access article PDF; verify article licence and preserve the test population |
| `pp-mechanical-solvent-recycling-2023` | [Mechanical and solvent-based PP recycling](https://www.pnas.org/doi/suppl/10.1073/pnas.2306902120) | Publisher fetch failed safely | Download the article and supplement from PNAS; retain LCA boundaries and product-quality assumptions |
| `polyolefin-waste-light-olefins-2024` | [Polyolefin waste to light olefins](https://www.science.org/doi/10.1126/science.adq7316) | Publisher fetch failed safely | Download the Science article or lawful manuscript; preserve catalyst, temperature, yield, and laboratory scale |
| `mixed-polyester-recycling-lca-2024` | [Mixed polyester recycling and environmental benefits](https://www.cell.com/one-earth/fulltext/S2590-3322(24)00583-9) | Redirect target outside the explicit source allowlist | Download the One Earth article or lawful manuscript; preserve polyester composition and separation assumptions |
| `pet-degradation-recycling-review-2024` | [PET degradation and mechanical recycling review](https://pubs.rsc.org/en/content/articlelanding/2024/su/d4su00485j) | Publisher fetch failed safely | Download the RSC article or lawful manuscript; retain PET-specific scope |
| `nir-polyolefin-differentiation-2026` | [NIR spectra and ML for polyolefin differentiation](https://pubs.acs.org/doi/10.1021/acspolymersau.5c00131) | Publisher fetch failed safely | Download the ACS article or lawful manuscript; retain calibration and validation data |
| `nir-polyolefin-bulk-properties-2023` | [NIR spectra and bulk polyolefin properties](https://pubs.acs.org/doi/10.1021/acs.macromol.3c02290?ref=PDF) | Publisher fetch failed safely | Download the ACS article or lawful manuscript; preserve correlation and confirmatory-test limits |
| `plastic-recycling-cascade-2024` | [Plastic recycling cascade](https://chemistry-europe.onlinelibrary.wiley.com/doi/10.1002/cssc.202301320) | Publisher fetch failed safely | Download the article or lawful manuscript; preserve the route-cascade perspective rather than treating it as a plant design |
| `microplastics-food-regulatory-science-2024` | [Microplastics and nanoplastics in human food](https://pubs.acs.org/doi/10.1021/acs.analchem.3c05408) | Publisher fetch failed safely | Download the ACS article or lawful manuscript; retain measurement uncertainty and regulatory-science scope |
| `global-plastic-waste-pathways-2024` | [Pathways to reduce global plastic waste](https://www.science.org/doi/10.1126/science.adr3837) | Publisher fetch failed safely | Download the Science article or lawful manuscript; preserve global-model assumptions |
| `plastic-gasification-tea-lca-2023` | [Mixed-plastic gasification TEA/LCA](https://pubs.rsc.org/en/content/articlelanding/2023/gc/d3gc00679d) | Publisher fetch failed safely | Download the RSC article or lawful manuscript; retain feed-price, scale, utility, and allocation assumptions |
| `hydrothermal-waste-plastics-lca-2023` | [Hydrothermal treatment of waste plastics](https://link.springer.com/article/10.1007/s10924-023-02792-3) | Redirect target outside the explicit source allowlist | Download the Springer article or lawful manuscript; preserve allocation and energy assumptions |
| `plastic-to-x-pathways-pet-2023` | [Plastic-to-X pathways for PET bottles](https://onlinelibrary.wiley.com/doi/full/10.1002/adsu.202300068) | Publisher fetch failed safely | Download the Wiley article or lawful manuscript; retain PET-specific route and circularity assumptions |

## Manual import checklist

1. Confirm the file is the exact source, not an unattributed summary.
2. Record source URL, publisher, title, author/version/date, licence, download date, and SHA-256.
3. Preserve the source ID so retrieval evaluation and provenance remain stable.
4. Run the reviewed extractor and inspect the first/last pages for truncation, OCR failure, tables,
   and legal footnotes.
5. Mark the source as extracted only after the content hash and extraction status are recorded.
6. Keep any claim candidate subject to the existing two-review promotion gate.
