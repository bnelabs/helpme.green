# Release process

Status: the release contract, maintainer-run scripts, and checked-in GitHub Actions workflows are
present. The delivery matrix below describes the release surface. Stable publication remains gated
on signed/notarized macOS and Windows credentials and target verification.

Current evidence: `v0.1.0-rc.6` is a draft pre-release built from tagged release commit
`955d8ed9779c36d660fe86f5ca3241313a426b7f`. Its release workflow passed the Python 3.11/3.12,
package, container, and six native-target jobs on 2026-08-18. The draft contains native archives,
Python distributions, `SHA256SUMS`, and `release-manifest.json`; it is not a stable signed release.
User-facing wording should describe this honestly and professionally: automated checks are present,
but an RC may still occasionally break, change behavior, or expose unfinished edges.
The current `main` branch is `95e137ee675625b0fdbe3127071187eb97fab1a4`, so changes after the RC
tag are not represented by the existing binary. Do not move the immutable RC tag; advance the source
version and create the next candidate when a new build is intended.

This document is the release contract for helpme.green. A release is a reproducible, tested,
versioned point in Git history with a reviewed release note, checksums, and provenance. It is not a
permission to authorize physical, legal, financial, purchasing, shipment, production, or permit
actions.

## Version contract

- The canonical application version is `src/helpme_green/__init__.py:__version__`.
- `pyproject.toml` reads that value dynamically; do not maintain a second version literal.
- Stable Git tags are `vMAJOR.MINOR.PATCH`, for example `v0.1.0`.
- Pre-releases use `vMAJOR.MINOR.PATCH-rc.N` and must not be marked latest.
- `PATCH` is for compatible fixes, `MINOR` for compatible features, and `MAJOR` for incompatible
  public changes. While the project remains below `1.0.0`, the public API is still developmental.
- A published tag, release, image tag, and release asset are immutable. Fix a release with a new
  version; never replace an asset under an existing version.

The release checker verifies the tag against the source version before building anything.

## Delivery matrix

| Target | Native release asset | Hosted build target | Required validation |
| --- | --- | --- | --- |
| Linux amd64 | `helpme-green-VERSION-linux-amd64.tar.gz` | `ubuntu-24.04` | bundle start, `/healthz`, session route |
| Linux arm64 | `helpme-green-VERSION-linux-arm64.tar.gz` | `ubuntu-24.04-arm` | bundle start, `/healthz`, session route |
| macOS arm64 | `helpme-green-VERSION-macos-arm64.zip` | `macos-15` | bundle start, `/healthz`, codesign, notarization |
| macOS amd64 | `helpme-green-VERSION-macos-amd64.zip` | `macos-15-intel` | bundle start, `/healthz`, codesign, notarization |
| Windows amd64 | `helpme-green-VERSION-windows-amd64.zip` | `windows-2025` | bundle start, `/healthz`, Authenticode |
| Windows arm64 | `helpme-green-VERSION-windows-arm64.zip` | `windows-11-arm` | bundle start, `/healthz`, Authenticode |

The container release is a separate Linux image published for `linux/amd64` and `linux/arm64`.
macOS and Windows users who choose Docker use that Linux image through Docker Desktop; they are not
native macOS or Windows container images.

Native bundles are PyInstaller one-directory distributions. They include application code and the
checked-in static, asset, skill, and source-manifest metadata required by the local runtime. They do
not include `.data`, provider keys, encryption keys, raw source downloads, or a model.

## Release sequence

1. Make the change on a branch and update the relevant changelog section.
2. Run the complete local gate:

   ```bash
   .venv/bin/pytest -q
   .venv/bin/ruff check .
   .venv/bin/ruff format --check .
   .venv/bin/python -m mypy src
   .venv/bin/python -m compileall -q src tests
   bash scripts/verify_container.sh
   ```

3. Merge the reviewed change to `main` and confirm the exact merge commit.
4. For a downloadable release candidate, set the source version to the candidate value, then create
   and push an annotated pre-release tag only after the version checker passes:

   ```bash
   git tag -a v0.1.0-rc.6 -m "helpme.green v0.1.0-rc.6"
   git push origin v0.1.0-rc.6
   ```

   The workflow builds and attaches all six native bundles as unsigned pre-release assets, so they
   can be downloaded and tested without pretending that they are stable signed binaries.
5. For stable publication, update the source version and changelog to the final value, then create
   and push the annotated stable tag:

   ```bash
   git tag -a v0.1.0 -m "helpme.green v0.1.0"
   git push origin v0.1.0
   ```

6. The checked-in release workflow rebuilds the exact tag, runs the test and container gates, creates
   all six native bundles, writes `SHA256SUMS`, and creates a draft GitHub Release with the assets.
7. Review the generated notes and the asset matrix. A stable release must have signed/notarized
   macOS and Windows assets. If signing credentials are absent, the workflow must stop before a
   stable release is published.
8. Publish the draft release manually. The container job publishes the matching GHCR image with
   the tag and immutable digest, and records build provenance.
9. Verify a clean download and install for at least one native target and both container platforms;
   verify `/healthz`, restart recovery, and an ordinary-language session route. Record any target
   that could not be exercised as unverified rather than treating the build as proof.

## Signing and provenance

The release workflow uses GitHub Actions artifact attestations for native files and the container
image when the repository supports that GitHub feature. This user-owned private repository does not
support persisted GitHub attestations, so its release evidence is SHA-256 checksums for every asset
plus BuildKit provenance/SBOM metadata on the container image. Stable native publication requires
these repository or organization secrets:

- `MACOS_CERTIFICATE_BASE64`, `MACOS_CERTIFICATE_PASSWORD`, `MACOS_SIGNING_IDENTITY`;
- `APPLE_ID`, `APPLE_APP_PASSWORD`, `APPLE_TEAM_ID`;
- `WINDOWS_CERTIFICATE_BASE64`, `WINDOWS_CERTIFICATE_PASSWORD`.

The signing workflow imports certificates into temporary runner-local stores, signs only the staged
release bundle, timestamps the signature, and removes temporary credential files. Secrets must never
be placed in the repository, release notes, artifacts, logs, or application settings.

## Knowledge artifact boundary

The current `.data/knowledge.db` and `knowledge/source-downloads/` remain outside normal releases.
The checked-in artifact manifest may be changed to `ready` only after source-by-source redistribution
and privacy review, scrubbed packaging, checksum verification, and a clean-directory bootstrap test.
An uncleared database must never be copied into a native bundle, container image, or GitHub Release.

The repository is currently private and does not yet declare a project-level distribution licence.
Before changing repository visibility or distributing the source/binaries outside the controlled
GitHub audience, select and record the applicable code, asset, and reference-content licences. Do
not infer a licence from the presence of a Git repository or from third-party dependency licences.

## Release-note checklist

Every release note must state:

- version, date, exact commit, and stable/pre-release status;
- highlights, fixes, security changes, and breaking/compatibility changes;
- the native asset table with platform, architecture, filename, and SHA-256;
- container image reference and digest;
- installation, configuration, upgrade, and rollback instructions;
- model/provider prerequisites and the fact that no credentials or model are bundled;
- knowledge-corpus publication status, attribution, and reuse limitations;
- known target-specific verification gaps.
