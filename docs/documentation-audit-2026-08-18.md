# Documentation audit — 2026-08-18

Scope: repository documentation, release instructions, public onboarding content, source-manifest
references, and the latest GitHub PR/release state. The audit was performed against local `main`
`95e137ee675625b0fdbe3127071187eb97fab1a4` and the live `bnelabs/helpme.green` metadata.

## GitHub and release evidence

- No open pull requests remain. The latest merged change is PR #14, “Add governed multi-platform
  release protocol”, merged to `main`.
- The current CI run for `95e137e` passed Python 3.11, Python 3.12, Python distributions, and the
  container build/rehearsal.
- `v0.1.0-rc.6` is a draft pre-release at tagged commit `955d8ed9779c36d660fe86f5ca3241313a426b7f`.
  It contains six native archives, checksums, Python distributions, and a release manifest. The
  tag predates the current `main` commit; it must not be moved. A later candidate is required to
  package later main-branch changes.
- The RC is intentionally described as controlled-test software: automated checks passed, but
  occasional breakage, rough edges, and behavior changes remain possible. macOS and Windows
  signing/notarization are still stable-publication gates.

## Documents checked

### Updated for the current product and release surface

- `README.md` — current app surface, release candidate, branch/tag distinction, and onboarding page.
- `CHANGELOG.md` — RC status and known stability/signing limitations.
- `docs/release-process.md` — current release evidence, immutable-tag rule, six-target matrix, and
  professional RC wording.
- `docs/deployment.md` — Compose feature defaults, KB routes, current candidate commit, and RC
  warning.
- `docs/knowledge-artifact.md` — current digest/hash/size values and v3-to-v4 migration boundary.
- `docs/kb-management-ui-plan-v2.md` — implementation baseline versus remaining roadmap.
- `docs/kb-operator-runbook.md` — startup job recovery now matches the service implementation.
- `docs/material-handling-framework.md` — canonical five-move orientation framework for the public
  page.
- `design-qa.md` — selected concept comparison, desktop/mobile browser evidence, interaction checks,
  and final visual QA result.
- `website/` — GitHub-ready static onboarding page, real notebook/material assets, screenshots,
  release-binary/Docker/source routes, and Get started interactions.

### Checked and retained as intentional snapshots or binding guidance

- `AGENTS.md` and `REQUIREMENTS.md` remain binding product, safety, provenance, and verification
  contracts.
- `docs/brand-guidelines.md` remains the visual token and material-imagery source used by the new
  page.
- `docs/knowledge-pipeline.md`, `docs/knowledge-retrieval.md`, `docs/open-source-integration.md`,
  and `docs/open-source-reuse.md` remain consistent with the source-aware, provider-configurable,
  licensing-bound knowledge boundary.
- `design-audit-2026-08-11.md`, the original Lab Notebook QA section in `design-qa.md`, and
  `docs/dsh-review.md` are dated design/architecture records. Their dates and historical findings
  are retained rather than rewritten as current release claims.
- `knowledge/research/manual-download-queue.md`,
  `knowledge/research/retrieval-benchmark-2026-08-11.md`, and
  `knowledge/research/academic-library-airtable-review.md` are dated corpus/research snapshots.
  Their 153-source / 102-extracted-source coverage remains consistent with the checked-in artifact
  manifest; failed fetches remain explicitly described as coverage gaps.
- `knowledge/source-manifest.yml`, `knowledge/artifact-manifest.json`, and
  `knowledge/catalog.snapshot.json` retain the source and artifact identities used by the runtime;
  the full SQLite digest remains outside normal Git history pending redistribution review.

## Verification record

- Focused tests: website contract, KB console/recovery, release contract, and frontend asset tests
  passed.
- Full `.venv/bin/pytest -q` passed.
- `ruff check`, `ruff format --check`, `mypy src`, and `compileall` passed.
- `bash scripts/verify_container.sh` passed health, restart recovery, and ordinary-language route
  checks.
- Codex In-app Browser rendered the page at 1280×720 and 390×844, exercised the mobile menu and
  install tabs, and returned no console errors or warnings.
