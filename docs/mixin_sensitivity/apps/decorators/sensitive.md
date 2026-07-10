# The @sensitive Decorator

Repr-layer masking for frozen dataclasses using a taxonomy-driven sensitivity classification. Apply `@sensitive` to any `@dataclass(frozen=True, slots=True)` and mark sensitive fields with `metadata={"sensitivity": "<TAG>"}` to automatically mask them in repr output. Optionally pass `policies` to the decorator constructor to apply per-class masking strategies.

## File Layout & Structure

```
sensitivity_mixin/services/classify/
└── classify_objects.py        ← Sensitivity enum, SensitivityProfile, classify()

sensitivity_mixin/decorators/sensitive/
├── __init__.py
├── sensitive_objects.py       ← SensitiveFieldSet (field introspection + masking)
└── sensitive_client.py        ← SensitiveDecorator + default instance (policies=())

sensitivity_mixin/decorators/constants/
└── sensitive.py               ← DEFAULT_PLACEHOLDER, error messages

sensitivity_mixin/decorators/classes/
├── compliance/
│   └── compliance_objects.py  ← Compliance enum, ClassMakerAware protocol
├── phi_aware/
│   └── phi_aware_objects.py   ← PhiPolicyAware value object
├── pii_aware/
│   └── pii_aware_objects.py   ← PiiPolicyAware value object
├── pci_aware/
│   └── pci_aware_objects.py   ← PciPolicyAware value object
└── secret_aware/
    └── secret_aware_objects.py ← SecretPolicyAware value object
```

## Container Diagram

```
sensitivity_mixin/decorators/sensitive/sensitive_objects.py
═══════════════════════════════════════════════════════════════════════
┌─ [FROZEN] SensitiveFieldSet ──── field introspection + masking ┐
│   profile: SensitivityProfile                                   │
│                                                                 │
│   [fct] from_dataclass(target: type) → Self                   │
│         Introspect dataclass, collect sensitivity metadata     │
│                                                                 │
│   [prp] is_empty → bool                                       │
│         True when no field carries a sensitivity tag           │
│                                                                 │
│   [mth] masked_repr(instance, policies) → str                 │
│         Render repr, masking tagged fields via policies       │
└─────────────────────────────────────────────────────────────────┘

sensitivity_mixin/decorators/sensitive/sensitive_client.py
═══════════════════════════════════════════════════════════════════════
┌─ [FROZEN] SensitiveDecorator ──── inject masking __repr__ ┐
│   policies: tuple[(Sensitivity, ClassMakerAware), ...]    │
│                                                             │
│   [mth] __call__(target: type[Target]) → type[Target]    │
│         Decorate dataclass; inject __repr__               │
│                                                             │
│   [pvt] _require_dataclass(target: type) → None          │
│         Raise TypeError if not a dataclass                │
│                                                             │
│   [pvt] _make_repr(field_set) → Callable                 │
│         Build __repr__ closure bound to policies          │
└─────────────────────────────────────────────────────────────┘

Module-level instance:
  sensitive = SensitiveDecorator(policies=())  ← default, no policies

sensitivity_mixin/decorators/classes/
═══════════════════════════════════════════════════════════════════════
Four policy value objects (all frozen dataclasses with same shape):
  PhiPolicyAware(compliance, detection_hints, placeholder)
  PiiPolicyAware(compliance, detection_hints, placeholder)
  PciPolicyAware(compliance, detection_hints, placeholder)
  SecretPolicyAware(compliance, detection_hints, placeholder)

Each implements ClassMakerAware protocol:
  mask(value: str) → str
  looks_sensitive(field_name: str) → bool
```

## Public API

Export from package root:

```python
from sensitivity_mixin import sensitive, classify, Sensitivity

# Also accessible directly:
from sensitivity_mixin.decorators.sensitive import sensitive
from sensitivity_mixin.services.classify import classify, Sensitivity
```

## Usage Examples

### Example 1: Default Masking (No Policies)

```python
from dataclasses import dataclass, field
from sensitivity_mixin import sensitive

@sensitive
@dataclass(frozen=True, slots=True)
class Credential:
    """Credential with sensitivity masking."""
    user_id: str
    api_key: str = field(metadata={"sensitivity": "secret"})

cred = Credential(user_id="u-123", api_key="sk-abc123xyz")

# repr() uses DEFAULT_PLACEHOLDER ('***') for all tagged fields:
>>> repr(cred)
"Credential(user_id='u-123', api_key=***)"
```

### Example 2: Policy-Wired Decorator

```python
from dataclasses import dataclass, field
from sensitivity_mixin import (
    sensitive,
    Sensitivity,
    SensitiveDecorator,
)
from sensitivity_mixin.decorators.classes.secret_aware import SecretPolicyAware
from sensitivity_mixin.decorators.classes.compliance import Compliance

# Create a custom policy for SECRET fields:
secret_policy = SecretPolicyAware(
    compliance=Compliance.NONE,
    detection_hints=("secret", "token", "key", "password"),
    placeholder="[REDACTED]"
)

# Wire the policy into the decorator:
decorator = SensitiveDecorator(policies=((Sensitivity.SECRET, secret_policy),))

@decorator
@dataclass(frozen=True, slots=True)
class Credential:
    user_id: str
    api_key: str = field(metadata={"sensitivity": "secret"})

cred = Credential(user_id="u-123", api_key="sk-abc123xyz")

# repr() now uses the custom policy placeholder:
>>> repr(cred)
"Credential(user_id='u-123', api_key=[REDACTED])"
```

### Example 3: Multi-Class Policies

```python
from sensitivity_mixin import (
    sensitive,
    Sensitivity,
    SensitiveDecorator,
)
from sensitivity_mixin.decorators.classes.secret_aware import SecretPolicyAware
from sensitivity_mixin.decorators.classes.pii_aware import PiiPolicyAware
from sensitivity_mixin.decorators.classes.compliance import Compliance

secret_policy = SecretPolicyAware(
    compliance=Compliance.NONE,
    detection_hints=("secret", "token", "key"),
    placeholder="***SECRET***"
)

pii_policy = PiiPolicyAware(
    compliance=Compliance.GDPR,
    detection_hints=("email", "name", "ssn"),
    placeholder="***PII***"
)

# Wire both policies:
decorator = SensitiveDecorator(
    policies=(
        (Sensitivity.SECRET, secret_policy),
        (Sensitivity.PII, pii_policy),
    )
)

@decorator
@dataclass(frozen=True, slots=True)
class User:
    id: str
    email: str = field(metadata={"sensitivity": "pii"})
    api_key: str = field(metadata={"sensitivity": "secret"})

user = User(id="u1", email="alice@example.com", api_key="sk-abc123")

>>> repr(user)
"User(id='u1', email=***PII***, api_key=***SECRET***)"
```

## Security Boundary: What This Does and Does NOT Protect

`@sensitive` is a **repr-layer masking tool**, not a complete confidentiality boundary. The decorator masks sensitive fields when you log or print the object, but does **not** protect against direct field access, serialization, or metadata-based attacks.

### Protected (Repr Layer Only)
- ✓ `repr(obj)`: sensitive fields masked
- ✓ `str(obj)` / `print(obj)`: uses masked repr
- ✓ Logging the object: `logger.info("Object: %s", obj)` is masked
- ✓ F-string with object: `f"Object: {obj}"` is masked
- ✓ Error tracebacks showing the object: masked

### NOT Protected (Bypass Methods)
- ✗ **Direct field access**: `obj.api_key` returns **full unmasked value**
- ✗ **Serialization**: `dataclasses.asdict(obj)` contains **full unmasked values**
- ✗ **Field-level logging**: `logger.info(f"Token: {obj.api_key}")` exposes **full value**
- ✗ **Attribute introspection**: `getattr(obj, 'api_key')` returns **full unmasked value**
- ✗ **Pickling**: `pickle.dumps(obj)` contains **full values**
- ✗ **Untagged fields**: fields without `metadata={"sensitivity": "..."}` are **never masked**

**Design principle**: `@sensitive` operates at the **object boundary** (repr layer), not the **field boundary**. Use it on DTOs at logging boundaries. Avoid field-level logging and direct serialization without additional masking layers.

## Policy Contract

When wiring policies into `SensitiveDecorator`, policies are trusted caller code. Each policy implements `mask(value: str) -> str` and `looks_sensitive(field_name: str) -> bool`. The `mask()` output replaces the field value in the rendered repr; a policy that echoes its input or performs insufficient redaction would leak the sensitive value. Policies are frozen dataclass instances created at decoration time and remain constant for all instances of the decorated class. Ensure policies apply correct masking logic before decoration (there is no runtime validation of mask output strength).

## Integration Notes

- **With logging**: Use `@sensitive` at the DTO layer; at log boundaries, emit DTOs and let repr masking provide the first line of defense. Service classes log safe metadata (customer_id, event type), not full DTOs.

- **With policies**: When no policies are passed to `SensitiveDecorator`, all sensitive fields render as `DEFAULT_PLACEHOLDER` (`***`). Pass policies to `SensitiveDecorator(policies=...)` for per-class masking customization.

- **With compliance**: The `Compliance` enum (`HIPAA`, `GDPR`, `PCI_DSS`, `NONE`) labels policy intent. Each policy value object carries a `Compliance` tag and a tuple of `detection_hints` (case-insensitive field-name patterns) to support heuristic field classification.

- **Field introspection**: `SensitiveFieldSet.from_dataclass()` uses Python's `dataclasses.fields()` to introspect the target class at decoration time. Metadata is read from the field's `metadata` dict; defaults are ignored.

## Testing

See `sensitivity_mixin/decorators/tests/test_sensitive/`:

- `test_sensitive_objects.py`: SensitiveFieldSet construction, masking logic with/without policies, is_empty predicate
- `test_sensitive_client.py`: Decorator application, TypeError on non-dataclass, repr output verification, policy wiring
- `conftest.py`: Fixture dataclasses for testing

Coverage: 100% on decorator layer source files.
