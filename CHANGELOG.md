# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

## [0.5.0] - 2026-07-22

### Removed

- **`@logged` decorator and `LoggedClient` class (mixin_logging)**: Decorator surface removed in favor of capability-contract patterns. Retained LoggingMixin, ambient log_* functions, FlushOnWarningHandler, and correlation-ID context. Consumers migrate by adopting LoggingMixin directly into service classes.
- **`@sensitive` decorator (mixin_sensitivity)**: Sensitive field marking now via field metadata only. Removed decorator surface; kept Sensitivity enum, SensitivityProfile, and classify() function. Repr-masking now available through SensitiveRepr adoption mixin (new).
- **`@retried` decorator and `RetryClient` class (mixin_retry)**: Replaced with capability-contract RetryPolicy and RetryExecutor (new). Consumers use wrap(fn, policy) or call(fn, *args, policy=..., **kwargs).

### Added

- **RetryPolicy + RetryExecutor capability** (mixin_retry): Exponential backoff retry strategy as a first-class DTO contract. `RetryPolicy` frozen+slots dataclass with fields: max_attempts, backoff_base_seconds, backoff_multiplier, backoff_max_seconds, jitter, should_retry (predicate, unwraps __cause__), retry_on (exception types). `RetryExecutor` client class with `wrap(fn, policy)` (primary form, rebind once, call many) and `call(fn, *args, policy=..., **kwargs)` (per-call convenience). Supports sync and async functions. Backoff calculated as min(base * (multiplier^attempt), max); jitter adds ±10% when enabled. Full test coverage with async/sync branches, predicate unwrapping, max-attempts exhaustion, backoff bounds validation.
- **SensitiveRepr adoption mixin** (mixin_sensitivity): Inherited by frozen+slots dataclasses to mask sensitive fields in `__repr__`. Reads existing field(metadata={"sensitivity": Sensitivity.X}) markers, replaces marked values with `***MASKED***` token in repr output. Field metadata remains introspectable (classify() unaffected). Zero impact on dataclass behavior beyond repr; no instance state (slots-safe).
- **mixin_latency (NEW root)**: High-precision elapsed-time measurement. `LatencyClock` client class with classmethod `start()` -> running clock; bound method `stop()` -> `LatencyMeasurement` DTO (duration_ms with LATENCY_ROUNDING_DECIMALS rounding rule). Context-manager form: `with LatencyClock.measure() as clock:` (classmethod returning CM, bound-method idiom). Zero dependencies; no decorator surface. Measurement backed by perf_counter(); LatencyMeasurement frozen+slots with named constants for rounding and field names.

### Changed

- **All five roots versioned to 0.5.0** (mixin_latency joins mixin_logging, mixin_notifications, mixin_retry, mixin_sensitivity). Suite-wide lockstep versioning enforced by CI gate (test_all_mixin_roots_report_same_version).

### Fixed

- Wheel no longer ships conftest/test-constants files.

## [0.4.0] - 2026-07-21

### Added

- **LoggedClient enrichment: payload_from_request and timed latency tracking**: New optional parameters to the @logged decorator enable automatic extraction of request context fields and per-call latency measurement. `payload_from_request` (Callable) extracts fields from method arguments and enriches the .start event; guarded to prevent extractor failures from breaking the wrapped call (failures log WARNING and continue). `timed` (bool) measures wall-clock latency via time.perf_counter(), emitting latency_ms float field in .end and .error events. Backward compatible (both opt-in); no volume increase for existing code; threads through class-level decoration for consistency.

- **AmbientLogger root-export from mixin_logging**: Frozen-slots client for module-level logging with auto-injected correlation_id from ContextVar. Bound methods (log_debug, log_info, log_warning, log_error, log_exception) enable shared instrumentation outside per-class LoggingMixin patterns. Complements existing class-bound logging.

- **FlushOnWarningHandler for mixin_logging**: Correlation-aware buffering handler in `mixin_logging.adapters.stdlib` that buffers log records per correlation ID and flushes buffered records when a WARNING+ severity record arrives for that correlation. Suppresses verbose DEBUG/INFO logs during successful operations while materializing full context trails on failure. Improves signal-to-noise in log aggregation for multi-step workflows (Celery tasks, batch processors, multi-minute flows). Features per-correlation FIFO buffering with configurable TTL eviction (lazy, no background threads), per-correlation capacity constraints via `deque(maxlen)`, global max-correlations cap, and thread-safe operation via stdlib handler lock discipline. Includes frozen-slots config dataclass with comprehensive validation, 16 tests (100% coverage), detailed documentation with lifecycle diagrams, security audit, and run-verified README example demonstrating multi-correlation isolation.

## [0.3.0] - 2026-07-17

### Added

- **mixin_retry `__version__` export**: Added version consistency across all three mixin roots. New `mixin_retry/config/_version.py` sources a single string, exported from `mixin_retry.__init__` alongside RetryClient, RetryContainer, and retried. All three roots (mixin_logging, mixin_sensitivity, mixin_retry) now report an identical `__version__` string. Updated PUBLIC_API and validator in mixin_retry to allow non-callable string exports.
- **`@logged` payload callback feature (opt-in)**: New `payload_from_result` and `payload_from_exc` optional parameters on `LoggedClient` and the `logged()` factory. When `payload_from_result` is provided (a callable that takes the result and returns a dict), a new success event with suffix `.end` is emitted on successful method completion, enriched with the payload fields as structured log record keys. When absent, behavior is unchanged (no success event, no log-volume increase for existing consumers). New `.end` property on LoggedContainer derives `<event>.end` suffix. Implemented for both sync and async instance methods; threads through class-level decoration. Error path unchanged. Opt-in design ensures backward compatibility.

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
