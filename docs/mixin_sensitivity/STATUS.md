# Project Status: mixin-sensitivity 0.7.0

## Overview

mixin-sensitivity is a stdlib-only Python package for classifying the sensitive fields of dataclasses and masking them in `repr()`. It is one of the five roots of the mixin-suite distribution.

- **Package:** `mixin_sensitivity` (Apache-2.0, Python 3.12 or newer)
- **Current version:** 0.7.0 (matches `mixin_sensitivity/config/_version.py`)
- **Dependencies:** none

## Public API

Exported from `mixin_sensitivity` (see `PUBLIC_API`):

- `Sensitivity`: StrEnum taxonomy with `PHI`, `PII`, `PCI` and `SECRET`
- `SensitivityProfile`: frozen value object describing which fields carry which class
- `classify(target)`: alias of `SensitivityProfile.from_dataclass`; takes a dataclass type
- `SensitiveRepr`: adoption mixin that masks sensitive fields in `__repr__`
- `SensitiveDeclarationError`: raised when `SensitiveRepr` is adopted without `repr=False`
- `__version__`, `PUBLIC_API`

## What Is Implemented

- Field-level classification through `field(metadata={"sensitivity": Sensitivity.X})`
- A plain string marker (for example `"phi"`) is also masked, so the masking fails closed
- `SensitiveRepr.__repr__` replaces each marked value with `***MASKED***`; unmarked fields print normally
- Fail-fast guard: a subclass whose `@dataclass` generated its own `__repr__` raises `SensitiveDeclarationError` on construction
- Field metadata stays introspectable; `classify()` reads it without change

## Removed in Earlier Releases

- The `@sensitive` decorator, the policy value objects and the compliance layer were removed in 0.5.0. Field metadata plus `SensitiveRepr` replaces them.
- Earlier releases used the import name `sensitivity_mixin`; the import name is `mixin_sensitivity`.

## Verification

- Run-verified examples: see [architecture/architecture.md](architecture/architecture.md) and the README-level examples in the flow trace.
- Gates on the 0.7.0 tree: pytest with 100 percent coverage on Python 3.12, mypy and ruff, and the strict-module check on Python 3.14.

## Records

- Dated audits and reviews live under `audits/` and `reviews/`. They record the verdicts at the time they were written.
- Release history: [CHANGELOG-history.md](CHANGELOG-history.md).
