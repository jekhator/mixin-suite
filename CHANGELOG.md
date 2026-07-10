# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

### Added

- **Consolidation of mixin-logging and mixin-sensitivity into a single distribution.**
  - This release combines two independently-maintained packages: mixin-logging (v0.6.0) and mixin-sensitivity (v0.4.0).
  - Both packages retain their original import roots: `mixin_logging` and `mixin_sensitivity`.
  - The unified distribution provides composable mixins for structured logging with correlation-ID propagation and sensitive-data classification.

### Includes

- **mixin-logging features** (v0.6.0): End-to-end correlation-ID propagation via 13 adapters (ASGI, WSGI, WebSocket, gRPC, GraphQL, Stdlib, HTTPX, Requests, aiohttp, urllib3, Botocore, Celery, Cloud). Class-level and method-level `@logged` decorators. Correlation-ID context propagation across async/await and task boundaries.

- **mixin-sensitivity features** (v0.4.0): Decorator-based sensitivity classification and masking for frozen dataclasses. Taxonomy support: PHI, PII, PCI, SECRET. Automatic masking in repr and introspection via `classify()`. Zero runtime dependencies.

### References

- Historical mixin-logging changelog: see `docs/mixin_logging/CHANGELOG-history.md`
- Historical mixin-sensitivity changelog: see `docs/mixin_sensitivity/CHANGELOG-history.md`

### Note

The original distributions remain live on PyPI:
- `mixin-logging` (v0.6.0 and prior): https://pypi.org/project/mixin-logging/
- `mixin-sensitivity` (v0.4.0 and prior): https://pypi.org/project/mixin-sensitivity/

New consumers should use the unified `mixin-suite` distribution. Existing consumers of the separate packages can continue using them without changes.
