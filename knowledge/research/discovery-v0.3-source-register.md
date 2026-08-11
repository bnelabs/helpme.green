# Knowledge v0.3 discovery source register

Research cut-off and access date: **2026-07-14**

Geographic decision context: **European Union / Bulgaria**

Pack scope: **copper cable, homogeneous ferrous material, mixed ferrous and non-ferrous metals,
metal-bearing fines, mixed WEEE polymers, bonded metal-plastic composites, and cooling-appliance
WEEE**

This register supports preliminary discovery only. It is not a permit opinion, waste
classification, buyer specification, equipment selection, safety procedure, laboratory method,
processing instruction, quotation, or product-release decision. Every imported v0.3 record remains
Draft.

## Source hierarchy and decisions

| Source key | Type | Exact source and location | Claims supported | Material limitations | Decision |
|---|---|---|---|---|---|
| `eu-wfd-2025` | Binding EU law | [Directive 2008/98/EC, consolidated 16 October 2025](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02008L0098-20251016), Articles 3, 6, 13, 23 and 35 | Waste status, treatment authorization, protection, and record gates for copper direct sale and processing | The consolidated text is a documentation aid. Current Bulgarian implementation and case facts require qualified legal review. It provides no composition, acceptance, yield, or price evidence. | **ACCEPT** for legal gates only |
| `eu-copper-eow-715-2013` | Binding EU law | [Regulation (EU) No 715/2013](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX:32013R0715), Articles 3 to 5 and Annex I | Fail-closed copper-scrap status and output-qualification gates | Applies only when every criterion, quality-management duty, and statement-of-conformity requirement is met. It does not make untreated insulated cable or an untested fraction a product. | **ACCEPT** for legal and output gates only |
| `eu-wsr-2024-1157` | Binding EU law | [Regulation (EU) 2024/1157](https://eur-lex.europa.eu/eli/reg/2024/1157/oj), Articles 2, 4, 18, 27, 85 and 86 | Shipment and destination review for copper routes | The control route depends on classification, destination, transition provisions, and shipment facts. No shipment determination is made. | **ACCEPT** for qualified-review gates only |
| `eu-weee-directive-2012` | Binding EU law | [Directive 2012/19/EU](https://eur-lex.europa.eu/eli/dir/2012/19/oj/eng), Annex VII | Selective treatment, external cable, WEEE polymer, and cooling-appliance component gates | Applies only to WEEE within scope. National implementation and the actual component inventory require qualified review. It supplies no buyer specification or performance evidence. | **ACCEPT** for selective-treatment gates only |
| `eu-waste-treatment-bat-2018` | Binding EU BAT conclusions | [Commission Implementing Decision (EU) 2018/1147](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02018D1147-20180817), BAT 2, BAT 5, BAT 25 to BAT 30, and output-quality provisions | Risk-based characterisation, acceptance, dangerous-item controls, high-level mechanical-treatment capability classes, cooling-WEEE specialist controls, output tracking, and residue accounting | Applies only to defined activities and installations. It does not prove site authorization, small-scale applicability, equipment performance, or any route economics. | **ACCEPT** with installation-scope limitation |
| `eu-pops-regulation-2025` | Binding EU law | [Regulation (EU) 2019/1021, consolidated 4 August 2025](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02019R1021-20250804), Article 7 and Annex IV | Fail-closed POP review for WEEE plastics with suspected flame retardants | Current applicability, concentration limits, sampling, classification, and date require qualified review. No actual stream is classified by the pack. | **ACCEPT** for legal and analytical gates only |
| `jrc-weee-plastics-2016` | Official JRC technical publication | [Revision of methods to assess material efficiency of energy related products and potential requirements, JRC104065](https://publications.jrc.ec.europa.eu/repository/handle/JRC104065), Chapter 5 and repository abstract | WEEE polymer heterogeneity, sorting barriers, additive and flame-retardant interaction, dismantling, and qualification needs | Product-policy research, not a buyer specification or proof that a particular fraction is recyclable. Technology and product mix vary. No yield or cost is transferred. | **ACCEPT** for discovery-level technical gates |

## Coverage map

| Family | Material profile | Route coverage | Interaction coverage | Decision-readiness gaps intentionally retained |
|---|---|---|---|---|
| Copper cable | Conductor, insulation, optional screen or armour, fillers, and attachments | Direct sale; external toll processing; eligible controlled stripping; mechanical granulation and physical separation; controlled hold for evidence. Toll and stripping remain `RESEARCH_SUPPORTED` until route-specific partner/capability evidence exists. | No additional imported interaction in this first pack; structure variation remains a route requirement | Representative cable mix and composition, geometry-specific eligibility, qualified legal and safety review, partner and buyer specifications, quotations, bounded capability and mass-balance evidence, actual energy, labour, wear, all residues |
| Homogeneous ferrous | Ferrous body with possible coatings and attachments | Characterise and sell directly | No interaction imported; apparent homogeneity failure mode is recorded | Grade, coatings, contamination, receiver grade, deductions, shipment route, and complete quotation |
| Mixed metals | Loose ferrous, non-ferrous, and possible dangerous items | Inspection, optional liberation and classification, physical separation, output qualification | Dangerous-item and poor-liberation failure mode is recorded | Composition, attachments, liberation need, facility capability, residues, buyer outputs, and all-in economics |
| Metal-bearing fines | Metal-bearing fines, moisture, and foreign fines | Hold for evidence; qualify processor or receiver only after characterisation | Fines plus moisture expands characterisation, handling, storage, and mass-balance scope | Qualified sampling and analysis, particle-size and moisture basis, hazardous constituents, receiver envelope, residue responsibility, testing and processing quotations |
| Mixed WEEE polymers | Mixed thermoplastics, fillers, reinforcements, possible flame retardants, coatings, and inserts | Identify, screen, sort candidate fractions, and qualify outputs | Suspected flame retardant expands technical sorting, POP, WEEE, output, and residue gates | Representative polymer and additive evidence, legal classification, sorting capability, property requirements, buyer acceptance, controlled residues, full economics |
| Metal-plastic composites | Layered metal, bonded polymer, coatings, and attachments | Map structure, assess liberation, physically separate, and qualify | No additional imported interaction in this first pack; incomplete liberation and cross-contamination failure mode is recorded | Interface and bond evidence, liberation behavior, dust and wear, mass closure, output purity and properties, buyer acceptance, CAPEX and OPEX quotations |
| Cooling-appliance WEEE | Cabinet, liner, foam, compressor and circuit, oil, possible refrigerant, and cables | Authorised specialist depollution, controlled dismantling, physical separation, and qualification | Refrigerator plus suspected refrigerant activates specialist, emissions, explosion, captured-media, and residue gates | Appliance and refrigerant identification, prior depollution, authorised specialist acceptance, every output and residue destination, complete specialist quotation |

## Numeric-claim decision

The discovery cards intentionally contain:

- no performance estimates;
- no cost estimates;
- no yield ranges;
- no throughput or utilization assumptions;
- no energy, labour, consumable, maintenance, wear, testing, logistics, residue, equipment,
  installation, working-capital, financing, price, deduction, or rejection-cost values;
- no revenue, net-value, incremental-value, or purchase-ceiling calculation.

The accepted sources establish legal or technical gates and high-level capability classes, but do
not provide a validated transfer method to the specific feed, facility, annual scale, equipment
configuration, geography, price year, or buyer. Missing values therefore remain unknown or
quotation-required rather than zero.

## Excluded claims and routes

- No chemical, thermal, or biological processing recipe, parameter, dosing instruction, or
  operating recommendation is included.
- No WEEE polymer is presumed mechanically recyclable merely because a polymer family is suspected.
- No cooling appliance is presumed depolluted from labels, hearsay, or visual condition.
- No metal-bearing fines route proceeds from visual appearance alone.
- No composite liberation performance is transferred across structures or equipment.
- No supplier statement, commercial label, or administrator action converts waste into product or
  weak evidence into verified truth.
- No novel hypothesis is claimed in this pack. A separate hypothesis would require documented
  searches across every governed precedent domain before import.

## Review and activation boundary

Before any card can be considered for activation, its actual feed envelope and intended route need
separate review in materials/process engineering, safety/environmental, legal/compliance,
product/buyer, and commercial/financial domains. Activation is outside this pack and must not occur
automatically after validation or import.

Domain clearances are content-digest-bound. Reimporting changed Draft content requires new review in
every domain; prior decisions remain immutable history but cannot clear the changed record. Reviewers
must hold a current, separately granted qualification for the exact domain, and the activation
administrator cannot supply the record's domain decisions.
