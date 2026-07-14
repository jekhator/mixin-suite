# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

(empty; see [0.2.0] below)

## [0.2.0] - 2026-07-14

### Added

- **New mixin_retry root**: Composable retry logic via the `@retried` class-capable decorator. Supports sync and async functions/methods with full-jitter exponential backoff, configurable predicate-based retry conditions (retry_on), max retries, and base delay. Decorator operates on class methods, static methods, and module-level functions. Includes comprehensive test coverage (100%) with async context propagation verification.
- **Redaction filter for mixin_logging**: New `mixin_logging.filters.redaction` module providing sensitivity-aware log masking via RedactionFilter. Integrates with mixin_sensitivity classification taxonomy (PHI, PII, PCI, SECRET) to mask sensitive fields in log records before emission. First cross-root integration between mixin_logging and mixin_sensitivity. Enables production-safe logging of classified dataclass instances.
- **FastAPI adapter for correlation-ID propagation**: New `mixin_logging.adapters.fastapi` module providing CorrelationIdMiddleware for FastAPI applications and get_correlation_id_dependency for FastAPI route handlers. The middleware extracts or generates correlation IDs from request headers, sets them into logging context, injects them into response headers, and cleans up context on request exit. Mirrors the ASGI adapter but with FastAPI-idiomatic patterns (BaseHTTPMiddleware, dependency injection). Full test coverage with 25 tests including edge cases for header extraction, safety validation, and context cleanup.
- **Classmethod and staticmethod logging fallback**: The `@logged` decorator now emits start/error events for classmethods and staticmethods using a module-level logger fallback when no LoggingMixin instance is available. Events are derived from the decorated class's module and class name, maintaining the same payload shape as instance-method events (error_type and code fields). Both sync and async variants are supported.
- **Test coverage: 100% statement coverage**: Increased test coverage to 100% (1269 statements across mixin_logging, mixin_sensitivity, and mixin_retry). CI gate updated to require 100% coverage to catch any regressions. Added comprehensive tests for async classmethod and staticmethod error paths in the @logged decorator.
- **Python 3.14 CI matrix**: Expanded test matrix to include Python 3.14 alongside Python 3.11. Updated pyproject.toml classifiers to advertise Python 3.14 support. All tests pass on both versions with zero compatibility issues.

### Changed

- **Tool config section rename**: Renamed pyproject.toml tool configuration sections from `[tool.dto-strict]` and `[tool.dto-strict.loc-cap]` to `[tool.strict-module]` and `[tool.strict-module.loc-cap]` respectively for consistency with domain-suite and the strict-module package naming convention. Configuration values remain unchanged.
- **Strict-suite dependency pin to 0.2.0**: Updated CI and coverage gate dependencies to strict-suite v0.2.0, incorporating R010/R011 linting fixes (collections.abc import standardization, function-to-container refactoring).

### Fixed

- **Full-corpus conformance**: Standardized all imports to use collections.abc (vs. deprecated typing module re-exports). Removed all inline code comments per house rules (only noqa/exception tags retained). Removed employer name references from review documentation. Applied ruff formatting across entire codebase.

## [0.1.1] - 2026-07-11

### Fixed

- Documentation conformance release: README badges and per-package run-verified examples, docs index, corrected extras list formatting, canonical docs tree naming, and removal of internal artifacts. No code changes.

## [0.1.0] - 2026-07-09

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
