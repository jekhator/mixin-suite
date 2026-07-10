# Compliance Contract Layer

The `Compliance` enum and `ClassMakerAware` protocol define the governance boundaries for sensitivity-aware masking policies.

## File Layout

```
sensitivity_mixin/decorators/classes/compliance/
└── compliance_objects.py  ← Compliance enum, ClassMakerAware protocol
```

## Compliance Enum

Regulatory regimes that sensitivity policies can enforce:

```python
class Compliance(StrEnum):
    """Regulatory regimes a sensitivity policy can enforce."""
    HIPAA = "hipaa"
    GDPR = "gdpr"
    PCI_DSS = "pci-dss"
    NONE = "none"
```

Used as a label on policy value objects to document governance intent. Not enforced at runtime; intended for auditing and compliance reporting.

**Examples:**
- `Compliance.HIPAA`: policy enforces HIPAA masking rules for PHI (Protected Health Information)
- `Compliance.GDPR`: policy enforces GDPR masking rules for PII (Personally Identifiable Information)
- `Compliance.PCI_DSS`: policy enforces PCI-DSS rules for credit card data (PCI)
- `Compliance.NONE`: policy has no regulatory mandate (e.g., test fixtures)

## ClassMakerAware Protocol

Every per-class sensitivity policy satisfies this contract:

```python
class ClassMakerAware(Protocol):
    """Contract every per-class sensitivity policy satisfies."""

    def mask(self, value: str) -> str:
        """Return the masked form of a sensitive value."""
        ...

    def looks_sensitive(self, field_name: str) -> bool:
        """Return True when a field name reads as sensitive."""
        ...
```

### Methods

**`mask(value: str) -> str`**

Return the masked replacement for a sensitive value. Implementations typically ignore the input value and return a fixed placeholder (e.g., `"***"`), but may implement more nuanced masking (e.g., first-character retention for PII, last-4-digits retention for PCI).

**`looks_sensitive(field_name: str) -> bool`**

Return `True` when the field name matches a heuristic detection hint. Intended for optional automatic field classification when metadata is absent.

The `sensitivity_mixin.decorators.classes` module provides four policy value objects that implement this protocol, one per sensitivity class (PHI, PII, PCI, SECRET). See `policies.md` for details.

## Usage

Policies are instantiated and wired into the `@sensitive` decorator:

```python
from sensitivity_mixin import Sensitivity, SensitiveDecorator
from sensitivity_mixin.decorators.classes.secret_aware import SecretPolicyAware
from sensitivity_mixin.decorators.classes.compliance import Compliance

secret_policy = SecretPolicyAware(
    compliance=Compliance.NONE,
    detection_hints=("secret", "token", "key", "password"),
    placeholder="***SECRET***"
)

decorator = SensitiveDecorator(
    policies=((Sensitivity.SECRET, secret_policy),)
)

@decorator
@dataclass(frozen=True, slots=True)
class Credential:
    api_key: str = field(metadata={"sensitivity": "secret"})

# repr() now masks api_key using secret_policy.mask()
```

See `sensitive.md` for full decorator usage patterns.

## Testing

See `sensitivity_mixin/decorators/tests/test_sensitive/`:

- `test_sensitive_client.py`: Decorator with multiple policies, field masking via policy lookup
- Per-policy tests in `test_*_aware.py` files: compliance tag values, detection_hints, masking behavior

Coverage: 100% on compliance layer source files.
