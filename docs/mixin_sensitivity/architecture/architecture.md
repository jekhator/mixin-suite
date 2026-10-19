# mixin-sensitivity. Architecture

> **Package:** `mixin-sensitivity` (Apache-2.0, Python 3.12 or newer), part of the mixin-suite distribution.
> **Code:** `mixin_sensitivity/`
> **Flow trace:** [flow-trace.md](flow-trace.md)

## Package Scope

Classify sensitive fields of frozen dataclasses (PHI, PII, PCI, SECRET) and keep their values out of `repr()`. The package does not detect sensitive data in free text and does not encrypt or store anything.

## Design Principles

- Classification lives in field metadata, so the dataclass stays the single source of truth
- Masking is fail-closed: any marker, enum or string, masks the value
- Stdlib only; no runtime dependencies
- Adoption is explicit: `SensitiveRepr` must be inherited together with `repr=False`

## File Organization

```
mixin_sensitivity/
+-- __init__.py                  curated public API (PUBLIC_API)
+-- config/_version.py           single-source __version__
+-- common/constants/
|   +-- metadata.py              SENSITIVITY_KEY
|   +-- masking.py               mask token and guard message
|   +-- public_api.py            PUBLIC_API frozenset
+-- services/classify/
|   +-- classify_objects.py      Sensitivity, SensitivityProfile
|   +-- __init__.py              classify = SensitivityProfile.from_dataclass
+-- repr/_objects.py             SensitiveRepr, SensitiveDeclarationError
```

## Public API

```python
from mixin_sensitivity import (
    PUBLIC_API,
    Sensitivity,
    SensitiveDeclarationError,
    SensitiveRepr,
    SensitivityProfile,
    classify,
)
```

### Sensitivity

StrEnum with the members `PHI` ("phi"), `PII` ("pii"), `PCI` ("pci") and `SECRET` ("secret").

### SensitivityProfile

Frozen, slots dataclass with `classes: tuple[tuple[str, Sensitivity], ...]`. Methods: `from_dataclass(target)`, `is_empty`, `sensitivity_of(name)`, `has(kind)`, `fields_of(kind)`.

### classify

`classify` is `SensitivityProfile.from_dataclass`. Pass the dataclass type, not an instance.

### SensitiveRepr

Adoption mixin. Subclasses must be declared `@dataclass(frozen=True, slots=True, repr=False)`. Its `__post_init__` guard raises `SensitiveDeclarationError` when the subclass has its own generated `__repr__`. A subclass with its own `__post_init__` must call `SensitiveRepr.__post_init__(self)` explicitly.

## Integration Patterns

### Pattern 1: Mask sensitive fields in repr

```python
```

Output:

```
```

### Pattern 2: Classification introspection

```python
profile = classify(Patient)
phi_fields = profile.fields_of(Sensitivity.PHI)
```

Use the profile for compliance reports or for routing values to special handling.

## Testing Strategy

- Tests live beside the code under `mixin_sensitivity/**/tests`
- Coverage gate: 100 percent statement coverage on Python 3.12

## Dependencies

- Runtime: none (stdlib only)
- Development: pytest, mypy, ruff

## Version and Release

- **Current:** 0.7.0
- **Versioning:** `mixin_sensitivity/config/_version.py` is the single source, re-exported from `__init__`; the distribution version is dynamic in `pyproject.toml`.
- All five roots are versioned in lockstep; a CI test checks that they report the same version.
