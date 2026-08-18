# Changelog

All notable helpme.green changes are recorded here. Release tags use the `vMAJOR.MINOR.PATCH`
format and are immutable after publication.

## [Unreleased]

### Changed

- Continue to keep provider configuration, credentials, local runtime data, and uncleared knowledge
  downloads outside release artifacts.
- Release validation, release-note generation, native-bundle packaging, bundle verification, and
  target-runner automation are now part of the repository.

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
