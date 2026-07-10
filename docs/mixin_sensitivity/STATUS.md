# Project Status: sensitivity-mixin 0.3.0

## Overview

**sensitivity-mixin** is a Python library providing taxonomy-driven sensitivity classification and masking for frozen dataclasses.

- **Package:** `sensitivity_mixin` (Apache-2.0, Python 3.11+)
- **Current version:** 0.3.0 (unreleased)

## What's Implemented

### Core Features
- **Sensitivity taxonomy:** Four classification levels: `Sensitivity` enum with `PHI` (Protected Health Information), `PII` (Personally Identifiable Information), `PCI` (Payment Card Industry data), `SECRET` (API tokens, passwords, credentials)
- **`classify(instance)` function:** Returns `SensitivityProfile` documenting field-level sensitivity for compliance auditing and governance
- **`@sensitive` decorator:** Injects a sensitivity-aware `__repr__()` that masks sensitive fields in string representation (repr, str, logging the object)
  - Default instance uses `DEFAULT_PLACEHOLDER` (`***`) for all tagged fields
  - Optional `policies` parameter on `SensitiveDecorator` enables per-class masking customization
- **Per-class policy contracts:** `Compliance` enum + `ClassMakerAware` protocol for custom masking strategies
- **Four policy value objects:** `PhiPolicyAware`, `PiiPolicyAware`, `PciPolicyAware`, `SecretPolicyAware` - frozen dataclasses with `mask()` and `looks_sensitive()` methods for per-class customization

### Architecture
- **Classification layer** (`services/classify/`): `Sensitivity` enum + `SensitivityProfile` + `classify()` function
- **Decorator layer** (`decorators/sensitive/`): `SensitiveDecorator` + `SensitiveFieldSet` + default `sensitive` instance
- **Compliance contract** (`decorators/classes/compliance/`): `Compliance` enum + `ClassMakerAware` protocol
- **Policy value objects** (`decorators/classes/{phi,pii,pci,secret}_aware/`): Four interchangeable policy implementations
- **Constants** (`decorators/constants/sensitive.py`): `DEFAULT_PLACEHOLDER`, error messages
- **Public API** (`__init__.py`): Re-exports `sensitive`, `Sensitivity`, `SensitivityProfile`, `classify`, `__version__`

### Test Coverage
- 133 tests across all layers with 100% coverage on decorator + classify layers
- Coverage includes: Sensitivity enum, SensitivityProfile queries, SensitiveFieldSet masking, SensitiveDecorator application, all four policies, Compliance enum, ClassMakerAware validation
- Edge cases: untagged fields, empty profiles, policy lookup, no-policy scenarios

## Security Boundary

The `@sensitive` decorator provides **repr-layer masking only**. It protects sensitive fields in string representation (logging the object) but does not protect:
- Direct field access (`obj.field` returns full value)
- Serialization (`dataclasses.asdict()`, JSON encoding)
- Field-level logging

See `docs/apps/decorators/sensitive.md` for detailed security boundary documentation and safe usage patterns.

## Planned Features

- **Serialization masking:** Extend masking beyond repr to `to_dict()` / `to_json()` methods
- **Untagged field detection:** Lint/CI gate to catch sensitive-sounding field names without explicit metadata tags
- **Custom policy builders:** High-level factory functions to construct policies from templates (e.g., "PII with GDPR compliance")

## Documentation

- **README.md**: Installation, quick start, API reference, policy-driven masking examples, migration guide
- **docs/architecture/architecture.md**: File organization, container types, public API, integration patterns (default + policies + introspection)
- **docs/apps/decorators/sensitive.md**: `@sensitive` decorator feature brief, usage examples, security boundary, integration notes
- **docs/apps/decorators/compliance.md**: `Compliance` enum and `ClassMakerAware` protocol documentation
- **docs/apps/decorators/policies.md**: Four policy value objects with per-class usage examples and customization patterns
