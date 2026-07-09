# sensitivity-mixin. Architecture

Taxonomy-driven field sensitivity classification and masking for frozen dataclasses. The package provides `@sensitive`, a decorator that injects a masking `__repr__` onto any dataclass with sensitivity-tagged fields, and `classify()`, an introspection function that documents all sensitive fields in a dataclass.

## Package Scope

- **Sensitivity Taxonomy** (`services/classify/`): `Sensitivity` enum (PHI, PII, PCI, SECRET) + `SensitivityProfile` value object
- **Classification Service** (`services/classify/`): `classify()` introspection function returning field-level sensitivity profile
- **Decorator Layer** (`decorators/sensitive/`): `SensitiveDecorator` class + `SensitiveFieldSet` value object + default `sensitive` instance
- **Compliance Contract** (`decorators/classes/compliance/`): `Compliance` enum (HIPAA, GDPR, PCI_DSS, NONE) + `ClassMakerAware` protocol
- **Policy Value Objects** (`decorators/classes/{phi,pii,pci,secret}_aware/`): Four frozen dataclasses implementing `ClassMakerAware` for per-class masking customization
- **Constants** (`decorators/constants/sensitive.py`): `DEFAULT_PLACEHOLDER`, error messages
- **Public API** (`__init__.py`): Curated re-exports: `sensitive`, `Sensitivity`, `SensitivityProfile`, `classify`, `__version__`

## Design Principles

1. **Taxonomy-driven classification**: Decorator reads field `metadata={"sensitivity": "<TAG>"}` where TAG ∈ {PHI, PII, PCI, SECRET}; no hardcoded field-name lists. Enables per-class specialized policies.

2. **Frozen dataclasses only**: Works exclusively on immutable dataclasses (`@dataclass(frozen=True, slots=True)`); prevents accidental state mutation via masking logic.

3. **Repr masking**: The `@sensitive` decorator injects a safe `__repr__` that masks sensitive fields in string representation. Use this at the DTO layer; downstream logging/serialization benefits automatically.

4. **Introspectable classification**: `classify(instance)` returns a `SensitivityProfile` documenting field-level sensitivity. Enables compliance audits, governance layers, and specialized handling per sensitivity class.

5. **Concern-driven structure**: `decorators/` owns the `@sensitive` decorator; `services/` owns `classify()` and `Sensitivity` taxonomy; `decorators/classes/` partitions policies per sensitivity class.

## File Organization

```
sensitivity_mixin/
├── services/                              ← taxonomy + classification layer
│   └── classify/
│       ├── __init__.py                   ← re-exports
│       └── classify_objects.py           ← Sensitivity, SensitivityProfile, classify()
├── decorators/                            ← @sensitive decorator + policies
│   ├── __init__.py
│   ├── constants/
│   │   └── sensitive.py                  ← DEFAULT_PLACEHOLDER, error messages
│   ├── sensitive/
│   │   ├── __init__.py                   ← re-exports sensitive
│   │   ├── sensitive_objects.py          ← SensitiveFieldSet value object
│   │   └── sensitive_client.py           ← SensitiveDecorator, sensitive instance
│   ├── classes/                           ← compliance + per-class policies
│   │   ├── __init__.py
│   │   ├── compliance/
│   │   │   └── compliance_objects.py     ← Compliance enum, ClassMakerAware protocol
│   │   ├── phi_aware/
│   │   │   └── phi_aware_objects.py      ← PhiPolicyAware value object
│   │   ├── pii_aware/
│   │   │   └── pii_aware_objects.py      ← PiiPolicyAware value object
│   │   ├── pci_aware/
│   │   │   └── pci_aware_objects.py      ← PciPolicyAware value object
│   │   └── secret_aware/
│   │       └── secret_aware_objects.py   ← SecretPolicyAware value object
│   └── tests/test_sensitive/              ← decorator + policies tests
│       ├── conftest.py
│       ├── test_sensitive_objects.py
│       ├── test_sensitive_client.py
│       ├── test_compliance.py
│       ├── test_phi_aware.py
│       ├── test_pii_aware.py
│       ├── test_pci_aware.py
│       └── test_secret_aware.py
├── common/                                 ← shared utilities
│   └── constants/
│       └── metadata.py                    ← shared constant: SENSITIVITY_KEY
├── config/
│   ├── __init__.py
│   └── _version.py                       ← __version__
├── __init__.py                            ← curated public API
└── py.typed                               ← PEP 561 type hint marker
```

## Public API

Exported from package root (`sensitivity_mixin/__init__.py`):

- `sensitive`: the default decorator instance (`SensitiveDecorator(policies=())`)
- `Sensitivity`: the taxonomy enum (PHI, PII, PCI, SECRET)
- `SensitivityProfile`: immutable field-sensitivity documentation
- `classify()`: introspection function returning field-level profile
- `__version__`: package version string

## Container Types

### Sensitivity (enum, `services/classify`)

Taxonomy enum for field-level sensitivity classification:

- `Sensitivity.PHI`: Protected Health Information (healthcare/medical records)
- `Sensitivity.PII`: Personally Identifiable Information (names, emails, SSNs)
- `Sensitivity.PCI`: Payment Card Industry (credit card numbers)
- `Sensitivity.SECRET`: Credentials, API tokens, secrets

### SensitivityProfile (value object, `services/classify`)

Immutable documentation of all sensitive fields in a dataclass:

- `classes: tuple[tuple[str, Sensitivity], ...]`: field name → sensitivity mapping
- `has(kind: Sensitivity) → bool`: check for a sensitivity class
- `fields_of(kind: Sensitivity) → tuple[str, ...]`: get field names of a class
- `sensitivity_of(name: str) → Sensitivity | None`: get the class of a field
- `is_empty → bool`: property indicating no fields are tagged

Factory: `classify(instance) → SensitivityProfile` from `services/classify`

### SensitiveFieldSet (value object, `decorators/sensitive`)

Immutable introspection + masking surface:

- `profile: SensitivityProfile`: the field-level classification
- `from_dataclass(target: type) → Self`: factory inspecting a dataclass
- `is_empty: bool`: True when no fields carry a sensitivity tag
- `masked_repr(instance, policies) → str`: render repr with fields masked via policies

### SensitiveDecorator (decorator, `decorators/sensitive`)

Injects a masking `__repr__` onto a dataclass:

- `policies: tuple[tuple[Sensitivity, ClassMakerAware], ...]`: optional per-class masking policies
- `__call__(target: type[Target]) → type[Target]`: decorator entry point
- `_require_dataclass(target: type) → None`: validates target is a dataclass
- `_make_repr(field_set: SensitiveFieldSet) → Callable`: builds the `__repr__` closure

Module-level `sensitive = SensitiveDecorator(policies=())` is the default ready-to-use instance.

### Compliance (enum, `decorators/classes/compliance`)

Governance regime labels:

- `Compliance.HIPAA`: healthcare data protection
- `Compliance.GDPR`: general data protection regulation
- `Compliance.PCI_DSS`: payment card industry standards
- `Compliance.NONE`: no regulatory mandate (e.g., test fixtures)

### ClassMakerAware (protocol, `decorators/classes/compliance`)

Contract all sensitivity policies implement:

- `mask(value: str) → str`: return masked replacement
- `looks_sensitive(field_name: str) → bool`: heuristic field-name matching

### Policy Value Objects (`decorators/classes/{phi,pii,pci,secret}_aware`)

Four frozen dataclasses implementing `ClassMakerAware`:

- `PhiPolicyAware`: healthcare data masking per `Compliance` regime
- `PiiPolicyAware`: personal information masking per `Compliance` regime
- `PciPolicyAware`: payment card masking per `Compliance` regime
- `SecretPolicyAware`: credential masking per `Compliance` regime

Each carries: `compliance: Compliance`, `detection_hints: tuple[str, ...]`, `placeholder: str`

## Integration Patterns

### Pattern 1: Default Repr Masking (No Policies)

```python
from sensitivity_mixin import sensitive
from dataclasses import dataclass, field

@sensitive
@dataclass(frozen=True, slots=True)
class Credential:
    user_id: str
    secret: str = field(metadata={"sensitivity": "secret"})

cred = Credential(user_id="u1", secret="sk-abc123")
repr(cred)  # Credential(user_id='u1', secret=***)
```

The decorator uses `DEFAULT_PLACEHOLDER` (`***`) for all tagged fields. Use this for all sensitive DTOs.

### Pattern 2: Policy-Driven Masking

```python
from sensitivity_mixin import sensitive, Sensitivity, SensitiveDecorator
from sensitivity_mixin.decorators.classes.secret_aware import SecretPolicyAware
from sensitivity_mixin.decorators.classes.compliance import Compliance
from dataclasses import dataclass, field

secret_policy = SecretPolicyAware(
    compliance=Compliance.NONE,
    detection_hints=("secret", "token", "key"),
    placeholder="***REDACTED***"
)

decorator = SensitiveDecorator(policies=((Sensitivity.SECRET, secret_policy),))

@decorator
@dataclass(frozen=True, slots=True)
class Credential:
    user_id: str
    secret: str = field(metadata={"sensitivity": "secret"})

cred = Credential(user_id="u1", secret="sk-abc123")
repr(cred)  # Credential(user_id='u1', secret=***REDACTED***)
```

Wire policies for per-class customization. See `docs/apps/decorators/policies.md` for detailed examples.

### Pattern 3: Classification Introspection

```python
from sensitivity_mixin import sensitive, classify, Sensitivity
from dataclasses import dataclass, field

@sensitive
@dataclass(frozen=True, slots=True)
class User:
    id: str
    email: str = field(metadata={"sensitivity": "pii"})
    ssn: str = field(metadata={"sensitivity": "phi"})

user = User(id="u1", email="alice@example.com", ssn="123-45-6789")
profile = classify(user)

# Use profile for compliance audits or specialized handling
if profile.has(Sensitivity.PHI):
    log_audit(f"Accessed PHI: {profile.fields_of(Sensitivity.PHI)}")
    apply_governance_policy(profile)
```

Use `classify()` for compliance audits, logging governance, and per-class handling strategies.

## Testing Strategy

- **Services/classify tests** (100% coverage): Sensitivity enum, SensitivityProfile construction, `classify()` introspection, all profile query methods
- **Sensitive objects tests** (100% coverage): SensitiveFieldSet factory, field introspection, `masked_repr()` with/without policies, `is_empty` predicate
- **Sensitive client tests** (100% coverage): decorator application, TypeError on non-dataclass, repr output verification, policy wiring
- **Compliance tests** (100% coverage): `Compliance` enum values, `ClassMakerAware` protocol validation
- **Policy tests** (100% coverage): `PhiPolicyAware`, `PiiPolicyAware`, `PciPolicyAware`, `SecretPolicyAware` - `mask()` and `looks_sensitive()` methods
- **Constants tests**: `DEFAULT_PLACEHOLDER`, error message texts
- **Integration tests**: metadata key wiring, frozen/slots compatibility, no side effects on decorated class

## Dependencies

- **Python**: ≥3.11
- **External**: None (stdlib only: dataclasses, typing, typing_extensions, enum)
- **Internal**: `services.classify`, `decorators.constants.metadata` modules

## Version & Release

- **Current**: 0.3.0 (taxonomy-driven architecture, @sensitive with policies, classify() introspection, compliance + policy contracts)
- **Release trigger**: push `release-0.3.0` tag; CI runs `publish.yml` (OIDC)
- **Versioning**: `sensitivity_mixin/config/_version.py` single-source, re-exported in `__init__`, `pyproject.toml` dynamic=[\"version\"]
