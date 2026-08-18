# Changelog

All notable helpme.green changes are recorded here. Release tags use the `vMAJOR.MINOR.PATCH`
format and are immutable after publication.

## [Unreleased]

### Changed

- Continue to keep provider configuration, credentials, local runtime data, and uncleared knowledge
  downloads outside release artifacts.
- Release validation, release-note generation, native-bundle packaging, bundle verification, and
  target-runner automation are now part of the repository.
- Publish the static newcomer onboarding page through GitHub Pages, with binary, Docker, and source
  getting-started routes and the material-handling framework.
- Refresh the documentation audit and release/deployment guidance to record the public repository,
  live Pages URL, current merge commit, and post-publication verification.

## [0.1.0-rc.6] - 2026-08-18

### Fixed

- Add a native Linux arm64 bundle, built and smoke-tested on the hosted Ubuntu arm64 runner, so
  Linux users are not limited to the container image.
- Use the explicit Python tar extraction data filter on supported runtimes, removing the warning
  about Python 3.14's default extraction-filter change from native bundle smoke tests.
- Download workflow artifacts with the GitHub CLI in the draft-release job, avoiding the current
  artifact action's deprecated internal `Buffer()` warning while retaining pinned Node 24 upload
  actions.

### Release status

- This is a release candidate for controlled testing. The automated checks have passed, but
  occasional breakage, rough edges, and behavior changes remain possible before a stable release.
- macOS and Windows assets remain unsigned in the candidate; stable signing/notarization is still a
  publication gate.

## [0.1.0-rc.5] - 2026-08-18

### Fixed

- Replace the remaining Node 20-targeting artifact download action with the current Node 24
  release, and refresh artifact uploads to the current release.

## [0.1.0-rc.4] - 2026-08-18

### Fixed

- Pin the native cryptography dependency to a release with published macOS universal2 and Windows
  ARM64 wheels, preventing target runners from compiling against incompatible system OpenSSL
  libraries.
- Update Docker and attestation workflow actions to current Node 24-compatible releases while
  retaining immutable commit pins.

## [0.1.0-rc.3] - 2026-08-18

### Fixed

- Release-gate formatting is clean for the downloadable candidate workflow.

## [0.1.0-rc.2] - 2026-08-18

### Fixed

- Private-repository release runs now retain native assets using checksums when GitHub persisted
  artifact attestations are unavailable.

## [0.1.0-rc.1] - 2026-08-18

### Added

- First downloadable cross-platform release candidate for Linux amd64, macOS arm64/amd64, and
  Windows amd64/arm64.
- Target-runner smoke checks, checksums, draft release notes, and provenance metadata.

### Known limitations

- This release candidate is unsigned on macOS and Windows; stable publication remains blocked until
  the documented signing and notarization credentials are configured.
- The application still requires a separately configured compatible model provider or LocalAI
  endpoint; no model or provider key is bundled.
- The current derived knowledge database remains local-only until source-by-source redistribution
  review is complete.

## [0.1.0] - 2026-08-18

### Added

- Initial versioned release baseline for the conversation-first local assistant.
- Docker-first delivery with a Linux `amd64` and `arm64` multi-platform image path.
- Target-specific native bundle packaging for Linux, macOS, and Windows, with release-time smoke
  verification, checksums, and signing hooks.
- Release documentation covering versioning, provenance, source boundaries, and upgrade/rollback.

### Known limitations

- The application still requires a separately configured compatible model provider or LocalAI
  endpoint; no model or provider key is bundled.
- The current derived knowledge database remains local-only until source-by-source redistribution
  review is complete.
- Stable macOS and Windows native artifacts require the signing and notarization credentials listed
  in the release process.
