# Copper cable v0.2 source register

Research cut-off and access date: **2026-07-13**

Geographic decision context: **Bulgaria / European Union**

Card scope: **characterized insulated copper cable; direct sale, external toll processing,
controlled stripping, and granulation with physical separation**

This register is evidence inventory, not an approval, permit opinion, buyer specification,
equipment selection, operating instruction, or price quotation. Card claims remain conservative;
supplier statements stay supplier statements, output stays waste unless lawfully demonstrated
otherwise, and every batch requires representative evidence.

## Claim map

- `M-STATUS`: waste/hazard status, origin, and evidence requirements for the material profile.
- `ALL-STATUS`: no automatic product or end-of-waste conclusion; authorization and qualified review.
- `ALL-SHIP`: domestic/cross-border shipment controls and the 2026 procedure transition.
- `ALL-QA`: incoming inspection, segregation, output control, residue control, and traceability.
- `SALE-REF`: direct sale is a waste route against written buyer criteria, not a price assumption.
- `TOLL-CONTROL`: partner authorization, written feed envelope, mass/assay settlement, and residue responsibility.
- `STRIP-SCOPE`: cable-specific feasibility only; productivity and recovery cannot be generalized.
- `GRAN-CLASS`: purpose-designed size reduction, physical separation, dust control, and declared equipment class.
- `GRAN-QUALITY`: prospective copper output must satisfy receiver criteria and, where claimed, all binding copper-scrap criteria.
- `COST-GAP`: evidence is insufficient for a normalized 2026 EUR per input tonne value.

## Candidate register

| Source key | Type | Publisher | Title and exact URL | Publication or quotation date | Access date | Geography and scale context | Claims supported | Limitations | Confidence | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `eu-wfd-2025` | Regulation | European Parliament and Council | [Directive 2008/98/EC on waste, consolidated 16 October 2025](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02008L0098-20251016) | Published/consolidated 2025-10-16 | 2026-07-13 | EU; all waste-holder and treatment scales in scope | `M-STATUS`, `ALL-STATUS`, `ALL-QA`, `SALE-REF`, `TOLL-CONTROL` | Consolidated text is a documentation aid; authentic Official Journal acts and current Bulgarian implementation require qualified legal review. No batch composition, recovery, or cost evidence. | High | **ACCEPT** — authoritative legal framework; mapped in material, sale, and toll cards. |
| `eu-copper-eow-715-2013` | Regulation | European Commission | [Regulation (EU) No 715/2013 establishing criteria determining when copper scrap ceases to be waste](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX:32013R0715) | Published 2013-07-26 | 2026-07-13 | EU; each consignment for which end-of-waste is asserted | `ALL-STATUS`, `ALL-QA`, `SALE-REF`, `STRIP-SCOPE`, `GRAN-QUALITY` | Applies only when every input, treatment, quality-management, grading, analysis, and statement-of-conformity requirement is satisfied. Does not turn insulated cable or a processor statement into product evidence. | High | **ACCEPT** — binding source for cable treatment and prospective copper-scrap quality context. |
| `bg-wma-official-2022` | Regulation / official translation | Ministry of Environment and Water, Bulgaria | [Waste Management Act, official English translation](https://www.moew.government.bg/static/media/ups/tiny/Waste_Management_Act.pdf) | Published/update list through 2022-03-01 | 2026-07-13 | Bulgaria; waste activities at all scales | `M-STATUS`, Bulgarian legal orientation | English translation lists amendments only through March 2022 and cannot establish current 2026 obligations. Current Bulgarian text, site permit, waste code, and competent-authority position must be verified. | Medium | **ACCEPT WITH LIMITATION** — material-profile orientation only; explicit staleness warning retained. |
| `eu-wsr-2024-1157` | Regulation | European Parliament and Council | [Regulation (EU) 2024/1157 on shipments of waste](https://eur-lex.europa.eu/eli/reg/2024/1157/oj) | Published 2024-04-30 | 2026-07-13 | EU and covered international movements; each in-scope shipment | `ALL-SHIP`, `SALE-REF`, `TOLL-CONTROL` | Control route depends on waste classification, destination, transition provisions, and shipment facts. Not a batch-level determination. | High | **ACCEPT** — authoritative 2026 shipment framework. |
| `bg-moew-wsr-notice-2026` | Official technical / administrative notice | Ministry of Environment and Water, Bulgaria | [New rules on waste transport in the EU and a mandatory electronic system to be introduced from 21 May](https://www.moew.government.bg/en/new-rules-on-waste-transport-in-the-eu-and-a-mandatory-electronic-system-to-be-introduced-from-21-may/) | Published 2026-04-08 | 2026-07-13 | Bulgaria/EU; in-scope cross-border procedures from 2026-05-21 | `ALL-SHIP` | Public notice, not a permit, classification, or procedure decision for a specific shipment. | High | **ACCEPT** — current Bulgarian authority confirmation of the transition date and electronic procedure. |
| `eu-wt-bat-2018` | Regulation / official BAT conclusions | European Commission | [Implementing Decision (EU) 2018/1147 establishing BAT conclusions for waste treatment](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02018D1147-20180817) | Published 2018-08-17; corrigendum noted in 2025 | 2026-07-13 | EU; defined Industrial Emissions Directive installation thresholds, including metal-waste shredders | `ALL-QA`, `STRIP-SCOPE`, `GRAN-CLASS` | Applicability depends on installation scope and permit. Industrial controls do not prove a smaller site's authorization, performance, or cost. | High | **ACCEPT** — authoritative control reference, applied conservatively. |
| `jrc-copper-eow-2011` | Official technical study | European Commission Joint Research Centre | [End-of-waste Criteria for Copper and Copper Alloy Scrap — Technical Proposals, JRC64207](https://publications.jrc.ec.europa.eu/repository/handle/JRC64207) | Published 2011-06-09 | 2026-07-13 | EU copper-scrap recycling chain; sector-level assessment | `ALL-QA`, `STRIP-SCOPE`, background to `GRAN-QUALITY` | Predates binding Regulation (EU) No 715/2013. Used only for background; supplies no Konverta-specific yield or cost. | Medium | **ACCEPT WITH LIMITATION** — official technical history, subordinate to the regulation. |
| `lee-cable-separation-2016` | Peer-reviewed original study | Korean Institute of Resources Recycling | [Highly Efficient Mechanical Separation Process for Recycling Waste Jelly-Filled Communication Cables](https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART002119652) | Journal issue 2016; page quoted 2026-07-13 | 2026-07-13 | Republic of Korea; one reported continuous equipment configuration at 55 kg/h for jelly-filled communication cable | `STRIP-SCOPE` | Specific cable and equipment outside the EU. Does not validate manual productivity, other geometries, local safety, annual scale, or economics. | Medium | **ACCEPT WITH LIMITATION** — supports cable-specific feasibility only; no numeric estimate imported. |
| `stokkermill-ks-2026` | Equipment-supplier statement | Stokkermill Recycling Machinery | [K-S series wire granulators — official product page](https://www.stokkermill.com/recycling-machines/cables-wires-granulator) | Page quoted 2026-07-13 | 2026-07-13 | Italian manufacturer/international market; declared 80–130 kg/h input and 8.5–13 kW installed power for two models | `GRAN-CLASS` | Commercial declaration, not independent test. Feed mix, utilization, actual draw, recovery, purity, labour, wear, maintenance, and annual throughput are unknown. | Low | **ACCEPT AS COMMERCIAL EVIDENCE** — native figures retained in source metadata; no annual or cost conversion. |
| `eldan-powerkat-b-2026` | Equipment-supplier statement | Eldan Recycling A/S | [REDOMA Powerkat B official product sheet](https://eldan-recycling.com/wp-content/uploads/2021/06/Powerkat-B-Cable-Plant.pdf) | Product sheet quoted 2026-07-13 | 2026-07-13 | Danish manufacturer/international market; declared 825–950 kg/h input for a stated 50–60% copper cable basis | `GRAN-CLASS` | Commercial declaration for a specific line. Does not establish Konverta feed performance, annual utilization, actual energy, crew, maintenance, wear, or cost. | Low | **ACCEPT AS COMMERCIAL EVIDENCE** — used only to bound equipment class; no plant estimate imported. |
| `pita-cable-separation-2018` | Peer-reviewed original study | Minerals journal | [Pita and Castilho, Separation of Copper from Electric Cable Waste Based on Mineral Processing Methods: A Case Study](https://doi.org/10.3390/min8110517) | Published 2018-11-08 | 2026-07-13 | Portugal; main jigging and shaking-table tests used 2.5 kg, while separate flotation tests used 50 g | `GRAN-CLASS`, evidence of feed/process sensitivity | Reports narrow laboratory results for selected gravity methods. It is not evidence for a commercial dry granulator, annual throughput, Konverta recovery, or cost. | Medium | **ACCEPT WITH LIMITATION** — supports the need for representative trials; reported ~97% results were not generalized into the card. |
| `martins-elutriation-2019` | Peer-reviewed original study | Particuology / Elsevier | [Recovery of valuable metals from waste cables by employing mechanical processing followed by spouted bed elutriation](https://doi.org/10.1016/j.partic.2018.12.002) | Article metadata quoted 2026-07-13; volume published 2019 | 2026-07-13 | Brazil; experimental coaxial and internet-cable batches | Evidence of cable-specific separation variability | Different cable constructions and experimental equipment; no EU facility, commercial-scale, cost, or generic yield applicability. | Medium | **ACCEPT FOR REGISTER ONLY** — reinforces variability; not needed for an imported estimate. |
| `mtb-cablebox-one-2025` | Equipment-supplier statement | MTB Recycling | [Cablebox One compact system brochure](https://www.mtb-recycling.fr/wp-content/uploads/2025/01/compact-system-cb1-web-part-3.pdf) | Brochure quoted 2026-07-13 | 2026-07-13 | French manufacturer/international market; declared 0.5–2 t/h and 220 kW system power | `GRAN-CLASS` | Commercial declaration; installed/system power is not measured electricity use. Feed basis, actual throughput, utilization, labour, recovery, wear, and price are not established. | Low | **ACCEPT FOR REGISTER ONLY** — native commercial context retained; no OPEX or annual conversion. |
| `eurostat-electricity-nonhousehold` | Official statistics | Eurostat | [Electricity prices for non-household consumers, dataset nrg_pc_205](https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_205/default/table?lang=en) | Dataset quoted 2026-07-13 | 2026-07-13 | EU/Bulgaria; national price bands, consumption bands, and reporting periods | Potential input to `COST-GAP` after tariff and measured-consumption selection | Cannot produce EUR/input-t without actual machine draw, utilization, Bulgarian tariff eligibility, taxes, levies, contract terms, and measured throughput. | High for dataset; none for route normalization | **REJECT FOR CARD NUMERIC CLAIM** — authoritative context but insufficient normalization chain. |
| `eurostat-labour-cost` | Official statistics | Eurostat | [Labour cost levels by NACE activity, dataset lc_lci_lev](https://ec.europa.eu/eurostat/databrowser/view/lc_lci_lev/default/table?lang=en) | Dataset quoted 2026-07-13 | 2026-07-13 | EU/Bulgaria; national/sector aggregates | Potential input to `COST-GAP` after crew and productive-hour evidence | Sector average cannot establish Konverta loaded labour rate, crew size, supervision, downtime, or labour hours per input tonne. | High for dataset; none for route normalization | **REJECT FOR CARD NUMERIC CLAIM** — would create false precision without pilot and payroll evidence. |
| `issuewire-onwang-2026` | Advertorial / press-release syndication | IssueWire / Onwang | [Turning Scrap Wire into Recoverable Value](https://www.issuewire.com/pdf/2026/03/turning-scrap-wire-into-recoverable-value-inside-the-growing-market-for-industrial-cable-recycling-equipment-IssueWire.pdf) | Page quoted 2026-07-13 | 2026-07-13 | Commercial marketing; scale claims not independently verified | None accepted | Syndicated promotional content, unclear technical review and claim provenance. | Low | **REJECT** — no authoritative or independently verifiable basis. |
| `medcrave-cable-review-2019` | Secondary article | MedCrave Material Science & Engineering International Journal | [Recycling of waste electrical cables](https://medcraveonline.com/MSEIJ/MSEIJ-03-00099.pdf) | Page quoted 2026-07-13 | 2026-07-13 | Unclear generalization from a limited experimental case | None accepted | Process basis and provenance are weaker than the available original studies; reported values are not an adequate commercial basis. | Low | **REJECT** — superseded by clearer primary evidence. |
| `bio-route-candidate-2015` | Peer-reviewed original study, out of scope | Minerals Engineering / Elsevier | [Copper leaching from waste electric cables by biohydrometallurgy](https://doi.org/10.1016/j.mineng.2014.12.029) | Article metadata quoted 2026-07-13 | 2026-07-13 | Laboratory study outside the approved physical/mechanical route scope | None accepted | Method class is outside this phase, carries a different hazard and permitting profile, and would require specialist review. | Medium for its narrow study | **REJECT FOR THIS PACK** — prohibited route scope; no content imported. |
| `steam-route-candidate-2015` | Peer-reviewed original study, out of scope | Waste Management / Elsevier | [Recovery of copper from PVC multiwire cable waste by steam gasification](https://doi.org/10.1016/j.wasman.2015.08.001) | Published online 2015-08-14 | 2026-07-13 | Laboratory study outside the approved physical/mechanical route scope | None accepted | Method class is outside this phase and entails a materially different emissions, safety, and permitting assessment. | Medium for its narrow study | **REJECT FOR THIS PACK** — prohibited route scope; no content imported. |
| `reddit-machine-claims` | Anonymous/community marketing posts | Reddit posters and equipment marketers | [Example community discussion: granulated copper](https://www.reddit.com/r/ScrapMetal/comments/1mnlgq9/granulated_copper/) | Page quoted 2026-07-13 | 2026-07-13 | Anecdotal equipment use; unknown feed and scale | None accepted | Identity, calibration, feed basis, measurement method, completeness, and commercial incentives are unresolved. | Low | **REJECT** — unverifiable provenance and no defensible claim basis. |

## Numeric-claim decisions

### Accepted numeric context

- The binding copper-scrap criterion in Regulation (EU) No 715/2013 is recorded as a strict
  foreign-material threshold of **less than 2% by weight**. It is a legal compliance predicate, not
  an empirical quality estimate; actual stripped or granulated output quality remains unknown.
- Every card output yield is explicitly `UNKNOWN` and has no numeric bounds. Actual outgoing
  fractions must be measured, weighed, and mass-closed before any economic decision uses them.
- Manufacturer capacity and installed-power figures remain in native form in source metadata and
  this register. They are evidence of equipment class only.

### Deliberately absent numeric context

All four cards have empty `cost_estimates`. The public-source review did not establish a defensible
2026 EUR per input tonne range with the required feed, geography, annual scale, inclusions, and
exclusions. In particular:

- installed motor or system power is not measured electricity draw;
- nameplate input capacity is not measured sustained throughput;
- no supported annual operating-hours assumption is available;
- no verified crew, loaded labour rate, consumable use, wear rate, maintenance plan, downtime, or
  residue-disposal quotation is available;
- no current binding equipment quotation or toll-processing proposal is available;
- volatile copper and polymer prices are intentionally outside processing-cost cards.

Accordingly, no public price, statistical series, or vendor claim was converted into EUR/input-t.
The comparison engine should surface missing cost components until current quotations and a
representative Konverta pilot provide the required evidence.

All four cards also have empty `performance_estimates`. Available studies and manufacturer statements
use laboratory batches or hourly nameplate declarations, while the schema requires an annual-scale
context. Converting those claims to tonnes/year would require an unsupported utilization assumption.

## Next evidence required before activation

1. Qualified Bulgarian waste-code, hazardous-property, site-permit, and shipment review.
2. Representative input composition, cable-family distribution, moisture, foreign-material, and mass evidence.
3. Written buyer and processor acceptance criteria, authorizations, sampling terms, settlement terms,
   rejection terms, and residue responsibility.
4. Current equipment and service quotations with explicit inclusions, exclusions, warranty, and feed basis.
5. Approved pilot measurements for mass closure, actual energy, labour, consumables, wear,
   maintenance, downtime, quality, and all residues.
6. Independent output characterization and buyer acceptance before any value or product-status claim.

No card in this pack is approved or active merely because it validates or imports successfully.
