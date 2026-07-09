# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2026-07-06

### Added

- **Class-level @logged decorator**: Apply `@logged("event")` to a class to auto-log entry/exit on all public methods. Each method receives `event.method_name.start` / `.error` logging. Implements target-polymorphic pattern: callable (unchanged) or class (fan-out). Skips private methods, dunders, properties, nested classes, and inherited methods; classmethods and staticmethods are wrapped with their descriptor types preserved. Explicit method-level `@logged` overrides class-level fan-out.

## [0.5.0] - 2026-07-06

### Changed

- **Package rename: logging-mixin to mixin-logging**: Following the govtech OSS suite category-first naming convention (`<category>-<name>`). Distribution name on PyPI changes from `logging-mixin` to `mixin-logging`. Import root changes from `logging_mixin` to `mixin_logging`. The old `logging-mixin` distribution stays live on PyPI for backward compatibility; old pins continue to work.
- **All public symbols remain unchanged**: `LoggingMixin`, `@logged`, correlation ID API (`set_correlation_id`, `get_correlation_id`, `clear_correlation_id`), and all 13 adapters retain their names and signatures. Only the module path changes.
- **Version bump to 0.5.0**: Minor version bump reflects the rename; code content is identical to v0.4.0.

### Migration Guide

Update your imports:
```python
# Old (v0.4.0)
from logging_mixin import LoggingMixin

# New (v0.5.0+)
from mixin_logging import LoggingMixin
```

Update your dependency pin:
```bash
# Old
uv add logging-mixin

# New
uv add mixin-logging
```

## [0.3.0] - 2026-06-10

### Added

- **Public API surface**: Explicit `PUBLIC_API` export from top-level package with lockstep conformance test. `LoggingMixin`, `CorrelationIdInjector`, and adapter middleware classes available directly from `logging_mixin`. Sub-package constants surfaced via `logging_mixin.constants.<adapter>`.

### Changed

- **Standards-conformance sweep**: Unified constants organization and semantic-literal extraction across all adapters and common modules. Canonical docstring-format section headers and deep extraction to dedicated constants modules. Integration with `dto-strict` v0.2.2+ for dataclass configuration and metadata validation.
- **Docstring and naming conformance**: Package-wide consistency in documentation and parameter naming. All public methods, classes, and packages now start with imperative action verbs. One-line verb-phrase docstrings and scoped module docstrings for semantic clarity.
- **Publish workflow trigger**: Release workflow now triggered by version-tag push instead of release-branch. Chore/release-* branch pattern deprecated.

## [0.4.0] - 2026-06-29

### Added

- **5 new correlation-ID adapters**: Extended adapter suite from 8 to 13 for broader protocol coverage:
  - **aiohttp Adapter** (`logging_mixin/adapters/aiohttp/`): Outbound `aiohttp.ClientSession` instrumentation. Injects `X-Correlation-ID` header via `TraceConfig` on every request.
  - **urllib3 Adapter** (`logging_mixin/adapters/urllib3/`): Outbound `urllib3.PoolManager` instrumentation. Injects `X-Correlation-ID` header on every request via `urlopen()` override.
  - **gRPC Adapter** (`logging_mixin/adapters/grpc/`): Inbound gRPC server interceptor. Extracts correlation ID from invocation metadata; auto-generates fallback. Sets context for handler execution.
  - **WebSocket Adapter** (`logging_mixin/adapters/websocket/`): Inbound ASGI WebSocket middleware. Extracts correlation ID from handshake headers; auto-generates fallback. Sets context for WebSocket connection lifecycle.
  - **GraphQL Adapter** (`logging_mixin/adapters/graphql/`): Resolver-context injector. Reads correlation ID from upstream context (set by ASGI/WSGI); exposes via resolver context dict.

- **Optional dependency extras**: Added 3 new extras for the new adapters:
  - `[aiohttp]`: aiohttp client instrumentation
  - `[urllib3]`: urllib3 client instrumentation
  - `[grpc]`: gRPC server instrumentation (requires `grpcio`)

### Changed

- **Canonical import-idiom enforcement**: Applied `ruff isort` + `PLC0414` (redundant-self-aliases) to standardize imports across adapters. Removed self-referential re-exports in adapter `__init__` files (PR #51).
- **LOC-cap scoping refinement**: Adjusted line-count enforcement to target source code only, excluding tests. Configuration in `[tool.dto-strict.loc-cap]` remains (hard_cap=300, soft_target=200), but scope now focuses on maintainability of production code (PR #50).
- **Documentation improvements**: Extensive docs refresh: adapter table expansion, correlation semantics clarification, FAQ additions, version sweep across README and guides. Code of Conduct alignment with Contributor Covenant 2.1 (PR #44, #47).

### Fixed

- **Publish workflow trigger**: Corrected publish.yml to fire on GitHub Release published (suite standard), not on push to main. Prevents accidental PyPI uploads from merge commits (PR #49).
- **Pyright editor integration**: Added `venv` binding in pyrightconfig.json for editor type-server resolution, enabling accurate type hints in VS Code (PR #48).

## [0.2.0] - 2026-06-05

### Added

- **Complete correlation-ID adapter suite**: 8 adapters for end-to-end correlation ID propagation across the full request/response lifecycle:
  - **ASGI Adapter** (`logging_mixin/adapters/asgi/`): FastAPI, Starlette, Quart, and other ASGI frameworks. `AsgiCorrelation` value object extracts or generates correlation ID from ASGI request scope. `CorrelationIdMiddleware` propagates across request lifecycle. Input validation via `_is_safe()` rejects control characters (`\r\n\0`), enforces max length (128 bytes), guards against invalid UTF-8. Response header injection automatically echoes correlation ID.
  - **WSGI Adapter** (`logging_mixin/adapters/wsgi/`): Django, Flask, Pyramid, and other WSGI frameworks. Inbound middleware extraction + response header injection.
  - **HTTPX Adapter** (`logging_mixin/adapters/httpx/`): Outbound `httpx.Client` and async `httpx.AsyncClient` instrumentation. Injects `X-Correlation-ID` on every request.
  - **Requests Adapter** (`logging_mixin/adapters/requests/`): Outbound `requests.Session` instrumentation via `CorrelationHTTPAdapter`. Injects `X-Correlation-ID` on every request.
  - **Botocore Adapter** (`logging_mixin/adapters/botocore/`): AWS SDK instrumentation. Injects `X-Correlation-ID` into all AWS service calls via event system hooks.
  - **Celery Adapter** (`logging_mixin/adapters/celery/`): Task-boundary propagation via Celery signals (publish → prerun → postrun). Maintains correlation ID across async task execution.
  - **Stdlib Adapter** (`logging_mixin/adapters/stdlib/`): `logging.Filter` implementation. Stamps `correlation_id` on every `LogRecord` automatically.
  - **Cloud Adapter** (`logging_mixin/adapters/cloud/`): Inbound AWS Lambda event extraction. Supports API Gateway, ALB, SQS, SNS, EventBridge, and top-level direct-invoke. Auto-generates fallback correlation ID if not present.

- **ASGI Adapter Robustness Hardening**: Input validation and defensive decoding to prevent log/header injection and resource exhaustion:
  - CRLF injection and log injection prevention via `_is_safe()`: rejects control characters (`\r\n\0`), enforces 128-byte max length, and requires non-empty values.
  - UTF-8 decoding safety: try-except guard on header decoding; invalid UTF-8 triggers UUID4 fallback rather than crash.
  - Empty-string rejection: validation guards against semantic invariant violation (empty correlation IDs).
  - Type-safe header iteration: defensive handling of ASGI header byte-tuples; malformed headers skipped gracefully.

- **Optional-dependency extras**: Added explicit package extras for all adapter dependencies:
  - `[httpx]`: HTTPX client instrumentation
  - `[requests]`: Requests client instrumentation
  - `[celery]`: Celery task propagation
  - `[botocore]`: AWS SDK instrumentation
  - `[all]`: Installs all adapter dependencies at once (convenience extra)

### Changed

- **Dependency management**: Adopted `uv` for faster, more predictable lock-file generation. Committed `uv.lock`; CI migrated to `astral-sh/setup-uv@v4`.
- **Python version requirement**: Dropped Python 3.10 support. Now requires Python >=3.11 (3.11 and 3.12 supported).
- **Package layout**: Root-layout restructure: `logging_mixin/adapters/` package with 8 specialized adapter modules (objects/ + client/ split per adapter type).
- **LOC-cap CI gate**: Automated line-count enforcement via `dto-strict loc-cap` subcommand; vendored `scripts/check_loc_cap.py` removed. Configuration in `[tool.dto-strict.loc-cap]` (hard_cap=300, soft_target=200).

### Removed

- **Python 3.10 classifier**: Dropped from supported versions in `pyproject.toml`.

## [0.1.0] - 2026-05-15

### Added

- Initial release.
- Core logging mixin infrastructure.
- Correlation ID context management.
