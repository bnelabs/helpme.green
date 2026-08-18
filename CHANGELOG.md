# Changelog

All notable helpme.green changes are recorded here. Release tags use the `vMAJOR.MINOR.PATCH`
format and are immutable after publication.

## [Unreleased]

### Changed

- Continue to keep provider configuration, credentials, local runtime data, and uncleared knowledge
  downloads outside release artifacts.
- Release validation, release-note generation, native-bundle packaging, and bundle verification are
  available as maintainer-run scripts; no GitHub Actions release workflow or published tag is yet
  part of the repository.

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
