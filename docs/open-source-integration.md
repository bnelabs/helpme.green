# Open-source reference integration

helpme.green is a circular-economy R&D assistant, not a bundle of copied product logic. External
projects enter as references, capabilities, or reusable software only after their scope and licence
are checked.

## How a reference becomes useful

1. Record the publisher, URL, material families, jurisdiction, scale, access mode, licence note, and
   limitations in [`knowledge/source-manifest.yml`](../knowledge/source-manifest.yml).
2. Fetch and extract the source into the local working store when access and reuse terms allow it.
3. Chunk and optionally embed the extracted text; retain hashes and retrieval metadata.
4. Retrieve only passages relevant to the user’s current question.
5. Let the model explain the passage in context, with uncertainty and limitations stated naturally.

The source registry and database are reference infrastructure. They do not turn a source page into a
guarantee about a particular feedstock, machine, site, product, permit, or business outcome.

## Current reference families

- Community and open-source practice: practical workshop, reuse, and material-handling orientation.
  These references are retrieved by the same source-relevance path as every other source.
- Machinery manufacturers: declared equipment capability and operating-envelope references. A vendor
  page is not an independently demonstrated throughput or site design.
- Scientific and engineering literature: route and mechanism context. A paper does not transfer its
  feedstock, laboratory conditions, yield, or economics to a user’s material automatically.
- Official regulators and standards bodies: jurisdiction and HSE context. They are not a substitute
  for current site-specific professional review.
- Industry and low-tech practice: useful operating knowledge, clearly separated from official or
  peer-reviewed material.

## Licence boundary

Raw downloads and extracted text stay outside the normal Git tree unless redistribution is explicitly
allowed. The repository carries the source queue, metadata, hashes, retrieval benchmark, and research
notes. See [`open-source-reuse.md`](open-source-reuse.md) and
[`knowledge-artifact.md`](knowledge-artifact.md) for attribution and distribution rules.

## Operating boundary

External material informs retrieval and explanation only. It does not create a user workflow, a
hidden questionnaire, or a guarantee about a particular material, machine, site, permit, or market.
The public surface stays ordinary-language and the source metadata stays available for inspection
without becoming the answer itself.
