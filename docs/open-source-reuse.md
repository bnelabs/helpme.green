# Open-Source Reuse Register

License register and reuse rules for external open-source circular-economy
projects considered for ingestion into helpme.green's knowledge base or code.
No external content enters the knowledge base outside these rules.

## Reuse rules (binding)

1. **Read, learn, reimplement — don't copy.** Reading open-source projects for
   their logic, architecture, algorithms, and knowledge — and building our own
   implementation upon that understanding — is permissible and intended. Ideas,
   algorithms, facts, and methodologies are not copyrightable; only their
   *expression* (code text, prose, blueprints, diagrams) is protected. We may
   study any of these projects, extract limited information, and re-express it in our own
   structure, attributed via the source register. We never reproduce
   protected expression wholesale, and we never copy code verbatim into our
   codebase without honoring its license.
2. **Share-alike triggers.** Content under CC BY-SA / AGPL / EUPL that is
   copied substantially forces the derived work to carry the same license.
   A facts-only summary with attribution is the safe posture; large copied
   excerpts are not.
3. **No license = no ingestion.** Absent an explicit license grant, treat
   external content as all-rights-reserved ("patent-free" and "free of charge"
   are claims, not copyright licenses). Written permission is required first.
4. **Attribution + no-endorsement must survive into the product.** BSD-3
   requires retaining copyright notices; CC BY-SA requires attribution and
   share-alike; no project's name may be used to endorse helpme.green without
   written permission.
5. **Point-in-time verification.** Entries below were verified on 2026-08-10.
   Re-verify before shipping ingested content, and have derivative-work
   boundaries (especially BY-SA and AGPL) reviewed legally.
6. **EU sui generis database right.** Individual facts are not copyrightable,
   but a *compiled knowledge base* can be protected in the EU by the sui
   generis database right (substantial investment in obtaining, verifying, or
   presenting the data; ~15 years per investment). Extract individual facts
   with attribution; **never bulk-harvest or substantially reuse another
   project's compilation**. The same protection applies to helpme.green's own
   compiled knowledge — it is our asset.

## Register

### 1. Precious Plastic (One Army)

- **Canonical:** https://preciousplastic.com · umbrella https://onearmy.earth/project/precious-plastic · org `ONEARMY` on GitHub
- **License (content):** CC BY-SA 4.0 — verified from the project's own "Open Source" page ("All our content is licensed under Creative Commons Attribution-ShareAlike International 4.0").
- **License (code):** mixed — community platform MIT, academy GPL-3.0, kit/starterkits no LICENSE file.
- **Reusable:** machine blueprints and knowledge for plastic recycling routes (shredder, extruder, sheet press, injection), business tools, community content — with attribution and share-alike.
- **Restrictions:** derived packs that copy their content must be distributed BY-SA; attribution required.
- **Verdict:** retain as a registered plastic reference. Keep any substantially copied derivative
  material BY-SA or obtain separate permission; do not copy the kit’s expression into the product.

### 2. Plastic Odyssey (Technology Platform)

- **Canonical:** https://technology.plasticodyssey.org · main site https://plasticodyssey.org
- **License:** **none found.** "Plans are made available free of charge and patent-free" is a claim about patents, not a copyright grant. No CC/OSI license, no LICENSE file; footers show "© Plastic Odyssey"; downloads gated behind an account (terms of service apply).
- **Reusable (reading):** studying their materials for facts, machine concepts, process logic, and business models is permissible — reading is not copying. Their *expression* (plans, guides, text, images) is not reusable without written permission.
- **Restrictions:** all-rights-reserved default for expression; no bulk harvesting of their content; no reproduction of plans or guides.
- **Verdict:** **study for inspiration and facts (attributed); do not copy or ingest expression.** Obtain written permission before any reproduction. Re-check periodically for a published license.

### 3. Deep Waste App (D.Waste)

- **Canonical:** https://github.com/sumn2u/deep-waste-app · site https://www.dwaste.live/
- **License:** **BSD-3-Clause** (in-repo LICENSE, Copyright (c) 2023, Suman Kunwar). Companion REST API: MIT. Training dataset on Kaggle (`sumn2u/garbage-classification-v2`): **MIT**.
- **Reusable:** full app code, trained TFLite classifier (~22 MB, in-repo), 6-class labels file — commercially reusable with attribution; no-endorsement clause.
- **Restrictions/warnings:** in-repo labels (6 classes) do **not** match the dataset/README taxonomy (10 classes) — verify real model outputs before relying on them. Dataset images were "collected from various internet sources"; underlying photo rights are not granted by the MIT/BSD licenses.
- **Verdict:** optional future vision reference. Useful as a waste-taxonomy seed, but model outputs
  must remain untrusted observations rather than repository knowledge.

### 4. Fleetbase

- **Canonical:** https://fleetbase.io · https://github.com/fleetbase
- **License:** **AGPL-3.0** (full application, not a library); dual-licensed via the Fleetbase Commercial License (FCL) for closed-source commercial use. Extension modules (fleetops, pallet) also AGPL.
- **Reusable:** self-hosted internal use free under AGPL; any close integration/modification in a SaaS triggers AGPL source-disclosure for the combined work unless FCL is purchased.
- **Verdict:** **out of scope.** Logistics/fleet *execution* conflicts with the advisory-only and no-marketplace boundaries (REQUIREMENTS.md §16). Revisit only if that boundary changes; then budget for AGPL compliance or FCL.

### 5. CIRCULOOS

- **Canonical:** https://circuloos.eu · code under `european-dynamics-rnd` on GitHub (Horizon Europe grant 101092295)
- **License:** platform code **EUPL-1.2** (copyleft; derived works must be EUPL-compatible). The GRETA/FICUS calculation engines have **no public source repo** — not verifiably open source. The GRETA output data model (EF 3.1 / EU PEF LCA indicators) is published but that repo carries **no license file**.
- **Reusable:** the Environmental Footprint 3.1 methodology *as referenced knowledge* (methodologies and indicator definitions are not copyrightable expression). Not the code.
- **Restrictions:** no ingestion of the data-model repo content without a license; no integration of the platform.
- **Verdict:** reference the EF 3.1 / EU PEF methodology in the source register for the sustainability dimension; skip the platform and engines.

### 6. PV ICE (NREL)

- **Canonical:** https://github.com/NatLabRockies/PV_ICE (GitHub `NREL/PV_ICE` redirects here) · docs: pv-ice.readthedocs.io (rate-limited/unverified at check time)
- **License:** **BSD-3-Clause** — LICENSE.md verified (Copyright 2020–2024 Alliance for Sustainable Energy, LLC; adds a US-Government no-endorsement clause; GitHub reports SPDX NOASSERTION for that reason).
- **Reusable:** full tool — mass/energy-flow models for PV in the circular economy, c-Si module/material baselines (published "for use in other projects"), EROI/EPBT methodology, scenario comparison of redesign/reuse/recycling pathways. Commercial use permitted with attribution.
- **Verdict:** **priority source** for a future PV/solar-panel material family; its mass-closure discipline aligns with the economics invariants. Register as a vetted source (BSD-3, commercial-safe).

## Attribution strings

When content from a registered project is cited in an evaluation output, carry:

- **BSD-3 (PV ICE, Deep Waste):** "Copyright (c) <year> <holder>. Licensed under BSD 3-Clause. See <source URL>." + no-endorsement respect.
- **CC BY-SA (Precious Plastic):** "© One Army / Precious Plastic, CC BY-SA 4.0. <source URL>." — and keep any derived pack under BY-SA.
- **All:** never imply endorsement by the source project.

## Integration notes for the knowledge pipeline

- External projects enter as **sources** (source-register entries) before retrieval can use them.
- Their content supports route and capability context (machines, processes, business models), not a
  guaranteed composition, safety, permit, or economic outcome for a specific stream.
- Sourcer Agent must record: exact source URL, license, verification date, applicability, limitations — mirroring this register's format.

---

*Verification date: 2026-08-10. This register is a factual summary of license texts, not legal advice; derivative-work boundaries are fact-dependent and should be reviewed by counsel before shipping ingested content.*
