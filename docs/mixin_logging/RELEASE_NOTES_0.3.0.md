# Release Notes - 0.3.0

**2026-06-10**

## Overview

logging-mixin 0.3.0 standardizes the public API surface and enforces conformance across all sub-packages, adapters, and test suites. Additive release; no breaking changes.

## Major Features

### Public API Surface (PR #40)

Explicit `PUBLIC_API` export from top-level package with lockstep conformance test:

- **Top-level exports**: `LoggingMixin`, `CorrelationIdInjector`, and adapter middleware classes available directly from `mixin_logging`
- **Sub-package constants**: All adapter-specific configuration constants surfaced via `mixin_logging.constants.<adapter>`
- **Conformance enforcement**: Test suite validates that public API remains stable across releases; breaking API additions flagged at CI

### Standards-Conformance Sweep (PR #41)

Unified constants organization and semantic-literal extraction across all adapters and common modules:

- **Constants dividers**: Canonical docstring-format section headers (`# → Literal values` / `# ← Context`)
- **Deep extraction**: `MagicNumber`/`EnvironmentVariable`/`HeaderName` literals moved to dedicated `constants/` modules per sub-package
- **dto-strict gate**: Integration with `dto-strict` v0.2.2+ for @dataclass configuration + @phi_aware metadata validation
- **Publish trigger migration**: Release workflow now triggered by version-tag push (not release-branch); `chore/release-*` branch pattern deprecated

### Docstring & Naming Conformance Sweep (PR #42)

Package-wide consistency in documentation and parameter naming:

- **One-line verb-phrase docstrings**: All public methods, classes, and packages now start with imperative action verbs (e.g., "Generate correlation ID for…", "Inject header into…")
- **Scoped module docstrings**: Each module includes a 2-3 line docstring describing its responsibility within the sub-package
- **Intuitive test parameter names**: Test fixtures and helper functions renamed for semantic clarity (e.g., `mock_request` → `sample_asgi_scope`, `event` → `inbound_event`)
- **Zero API changes**: All updates are documentation and naming only; runtime behavior unchanged

## API Stability

No breaking API changes. All new exports and constants are **additive only**:

- Existing `LoggingMixin` usage unchanged
- Adapter middleware classes available via both old (direct import) and new (top-level) paths
- All existing tests pass without modification

## Installation

```bash
uv add logging-mixin
```

With optional dependencies:

```bash
uv add "logging-mixin[celery]"      # Celery task propagation
uv add "logging-mixin[requests]"    # Requests client instrumentation
```

Requires Python 3.11+.

## Documentation

- `docs/`: Complete documentation (architecture, adapters, context, decorators)
- `docs/architecture/architecture.md`: System design and package structure
- `docs/apps/adapters/README.md`: Adapter overview and navigation
- `README.md`: Updated with 0.3.0 conformance improvements

## See Also

- [README.md](../../README.md): Quick start and core API
- [docs/apps/adapters/README.md](apps/adapters/README.md): Complete adapter overview
