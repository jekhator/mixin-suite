# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [0.4.0] - 2026-07-06

### Changed

- Package renamed from `sensitivity-mixin` to `mixin-sensitivity` following the suite's category-first naming convention. Import root changes from `sensitivity_mixin` to `mixin_sensitivity`; all public symbols (`Sensitivity`, `classify`, `@sensitive`, `@classified`, `@phi_aware` backward compatibility) are unchanged.
- GitHub repository renamed to `jekhator/mixin-sensitivity`; the old URL redirects.
- The `sensitivity-mixin` distribution remains live on PyPI at 0.3.1; existing pins keep working. New releases publish as `mixin-sensitivity`.

## [0.3.1] - 2026-06-10

### Fixed

- Documentation code examples used uppercase sensitivity metadata values that raise ValueError at runtime; all examples corrected to the lowercase enum values and verified by execution.

### Added

- README badges; contributing guide, security policy, and code of conduct; changelog project URL.

## [0.3.0] - 2026-06-10

### BREAKING CHANGES

Package renamed from `pii-aware-mixin` to `sensitivity-mixin`. Decorator and API scope broadened to support multiple sensitivity classifications.

### Changed

- **Package name:** `pii-aware-mixin` → `sensitivity-mixin` (import: `sensitivity_mixin`)
- **Decorator:** `@phi_aware` → `@sensitive` (works with broadened taxonomy)
- **Metadata key:** `"phi"` → `"sensitivity"` with values: `"PHI"`, `"PII"`, `"PCI"`, `"SECRET"`
- **Default placeholder:** `<phi:redacted>` → `***` (simpler, more readable)
- **API:** `SensitiveDecorator` accepts optional `policies` tuple for per-class masking customization

### Added

- `@sensitive` decorator with optional policy wiring via `SensitiveDecorator(policies=...)`
- `classify(instance)` → `SensitivityProfile`: introspect field-level sensitivity
- `Sensitivity` enum (PHI, PII, PCI, SECRET): taxonomy-driven classification
- `SensitivityProfile` value object with methods: `has()`, `fields_of()`, `sensitivity_of()`, `is_empty`
- `Compliance` enum (HIPAA, GDPR, PCI_DSS, NONE): governance regime labels for policies
- `ClassMakerAware` protocol: contract all sensitivity policies implement
- Four policy value objects: `PhiPolicyAware`, `PiiPolicyAware`, `PciPolicyAware`, `SecretPolicyAware`
- `SensitiveFieldSet` value object: field introspection + policy-driven masking

### Removed

- `mask_for_logging()` helper: use `repr()` on decorated instances instead
- `to_dict()` helper: use `dataclasses.asdict()` directly
- Previous masking strategy removed; focus shifted to classification + repr-layer policies

### Documentation

- `docs/apps/decorators/sensitive.md`: @sensitive decorator and SensitiveFieldSet
- `docs/apps/decorators/compliance.md`: Compliance enum and ClassMakerAware protocol
- `docs/apps/decorators/policies.md`: Four policy value objects with usage examples

### Why

Broadened scope from PHI-only masking to a taxonomy-driven sensitivity framework supporting healthcare (PHI), personal data (PII), payment data (PCI), and secrets. Per-class policy value objects enable compliance-aware customization (HIPAA, GDPR, PCI-DSS) while keeping the decorator simple by default.

## [0.2.0] - 2026-05-21

### BREAKING CHANGES

API redesigned from mixin-inheritance to decorator-based. Consumers must migrate.

### Removed

- `PiiAwareMixin` class: replaced by `@phi_aware` decorator
- `ReprMixin` class: functionality folded into `@phi_aware` decorator
- `ToDictMixin` class: replaced by module-level `to_dict()` helper
- Requirement for `repr=False` in consumer dataclasses (decorator works on plain `@dataclass(frozen=True, slots=True)`)

### Added

- `@phi_aware` decorator: injects PHI-masking `__repr__` on frozen dataclasses
- `mask_for_logging(instance)` module-level helper: returns dict with PHI fields masked
- `to_dict(instance)` module-level helper: alias for `dataclasses.asdict()` for consistency
- Field metadata key renamed `"sensitive"` → `"phi"` (healthcare-aligned)
- 26 comprehensive tests covering decorator, helpers, edge cases, integration

### Why

Compatible with the canonical "no mixin inheritance on data DTOs" pattern established in downstream QHCG project (2026-05-09). 

v0.1.0 mixin-inheritance API (`class User(PiiAwareMixin, ReprMixin, ToDictMixin)`) caused R003 false-positives in dto-strict v0.2.x when consumers tried to adopt the "no mixin inheritance" rule. The new decorator API allows clean adoption:
- No inheritance, no MRO issues
- Works on plain frozen dataclasses (no `repr=False` boilerplate)
- Explicit module-level helpers (not instance methods)
- Compatible with static analysis tools

### Migration Guide

**v0.1.0 (old, deprecated):**
```python
from pii_aware_mixin import PiiAwareMixin, ReprMixin, ToDictMixin

@dataclass(frozen=True, slots=True, repr=False)
class User(PiiAwareMixin, ReprMixin, ToDictMixin):
    id: int
    api_token: str = field(metadata={"sensitive": True})

user = User(id=1, api_token="sk-123")
user.mask_for_logging()    # instance method
repr(user)                 # mixin's __repr__
user.to_dict()             # instance method
```

**v0.2.0 (new):**
```python
from pii_aware_mixin import phi_aware, mask_for_logging, to_dict

@phi_aware
@dataclass(frozen=True, slots=True)
class User:
    id: int
    api_token: str = field(metadata={"phi": True})

user = User(id=1, api_token="sk-123")
mask_for_logging(user)  # module-level helper
repr(user)              # decorator's __repr__
to_dict(user)           # module-level helper
```

**Changes per file:**
1. Remove mixin inheritance from class definition
2. Add `@phi_aware` decorator above `@dataclass`
3. Remove `repr=False` from `@dataclass` (no longer needed)
4. Change `metadata={"sensitive": True}` → `metadata={"phi": True}`
5. Replace `instance.mask_for_logging()` → `mask_for_logging(instance)`
6. Replace `instance.to_dict()` → `to_dict(instance)`

## [0.1.0] - 2026-05-18

### Added

- `PiiAwareMixin`: metadata-driven masking via `mask_for_logging()` instance method
- `ReprMixin`: structured `__repr__()` with automatic field masking
- `ToDictMixin`: JSON serialization via `to_dict()` and `from_dict()` instance methods
- Field metadata key `"sensitive"` to mark fields for masking
- Comprehensive tests for all three mixins and composition patterns
- README with quick start, API reference, logging integration examples

### Design

Three composable mixin classes for frozen dataclasses, using Python's MRO for clean composition.
All work independently or together. Full-mask strategy: sensitive fields become `<MASKED>` in logs and `<masked: sensitive>` in reprs.
