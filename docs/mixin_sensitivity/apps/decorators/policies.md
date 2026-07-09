# Sensitivity Policies: PHI, PII, PCI, SECRET

Four policy value objects, one per sensitivity class. Each implements the `ClassMakerAware` protocol and can be wired into `SensitiveDecorator` for per-class masking customization.

## File Layout

```
mixin_sensitivity/decorators/classes/
├── phi_aware/
│   └── phi_aware_objects.py      ← PhiPolicyAware
├── pii_aware/
│   └── pii_aware_objects.py      ← PiiPolicyAware
├── pci_aware/
│   └── pci_aware_objects.py      ← PciPolicyAware
└── secret_aware/
    └── secret_aware_objects.py   ← SecretPolicyAware
```

## Policy Value Objects

All four are frozen dataclasses with identical shape:

```python
@dataclass(frozen=True, slots=True)
class <PolicyClass>Aware:
    compliance: Compliance
    detection_hints: tuple[str, ...]
    placeholder: str
```

| Class | Purpose | Typical Placeholder |
|-------|---------|---------------------|
| `PhiPolicyAware` | Healthcare data (PHI) masking per HIPAA | `"***PHI***"` |
| `PiiPolicyAware` | Personal information masking per GDPR | `"***PII***"` |
| `PciPolicyAware` | Payment card data masking per PCI-DSS | `"****XXXX"` |
| `SecretPolicyAware` | Credential/token masking | `"***SECRET***"` |

### Common Methods

**`mask(value: str) -> str`**

Returns the `placeholder` (ignores input value). Override this method to implement value-aware masking (e.g., PCI last-4-digits strategy).

```python
phi_policy = PhiPolicyAware(
    compliance=Compliance.HIPAA,
    detection_hints=("name", "ssn", "address"),
    placeholder="[REDACTED]"
)

masked = phi_policy.mask("John Doe")  # → "[REDACTED]"
```

**`looks_sensitive(field_name: str) -> bool`**

Returns `True` if the field name matches any `detection_hint` (case-insensitive substring match). Useful for heuristic field classification when metadata is absent.

```python
phi_policy = PhiPolicyAware(
    compliance=Compliance.HIPAA,
    detection_hints=("name", "ssn", "patient_id"),
    placeholder="[REDACTED]"
)

phi_policy.looks_sensitive("patient_name")      # → True (contains "name")
phi_policy.looks_sensitive("PATIENT_SSN")       # → True (contains "ssn", case-insensitive)
phi_policy.looks_sensitive("appointment_date")  # → False (no hint match)
```

## Usage Examples

### Example 1: PHI Policy (HIPAA)

```python
from dataclasses import dataclass, field
from mixin_sensitivity import sensitive, Sensitivity, SensitiveDecorator
from mixin_sensitivity.decorators.classes.phi_aware import PhiPolicyAware
from mixin_sensitivity.decorators.classes.compliance import Compliance

phi_policy = PhiPolicyAware(
    compliance=Compliance.HIPAA,
    detection_hints=("name", "ssn", "patient_id", "medical_record"),
    placeholder="[HIPAA REDACTED]"
)

decorator = SensitiveDecorator(
    policies=((Sensitivity.PHI, phi_policy),)
)

@decorator
@dataclass(frozen=True, slots=True)
class PatientRecord:
    patient_id: str
    name: str = field(metadata={"sensitivity": "phi"})
    ssn: str = field(metadata={"sensitivity": "phi"})

patient = PatientRecord(
    patient_id="P12345",
    name="Jane Doe",
    ssn="123-45-6789"
)

>>> repr(patient)
"PatientRecord(patient_id='P12345', name=[HIPAA REDACTED], ssn=[HIPAA REDACTED])"
```

### Example 2: PII Policy (GDPR)

```python
from dataclasses import dataclass, field
from mixin_sensitivity import sensitive, Sensitivity, SensitiveDecorator
from mixin_sensitivity.decorators.classes.pii_aware import PiiPolicyAware
from mixin_sensitivity.decorators.classes.compliance import Compliance

pii_policy = PiiPolicyAware(
    compliance=Compliance.GDPR,
    detection_hints=("email", "phone", "address", "ip_address"),
    placeholder="***PII***"
)

decorator = SensitiveDecorator(
    policies=((Sensitivity.PII, pii_policy),)
)

@decorator
@dataclass(frozen=True, slots=True)
class UserProfile:
    user_id: str
    email: str = field(metadata={"sensitivity": "pii"})
    phone: str = field(metadata={"sensitivity": "pii"})

user = UserProfile(
    user_id="u-999",
    email="alice@example.com",
    phone="+1-555-1234"
)

>>> repr(user)
"UserProfile(user_id='u-999', email=***PII***, phone=***PII***)"
```

### Example 3: PCI Policy

```python
from dataclasses import dataclass, field
from mixin_sensitivity import sensitive, Sensitivity, SensitiveDecorator
from mixin_sensitivity.decorators.classes.pci_aware import PciPolicyAware
from mixin_sensitivity.decorators.classes.compliance import Compliance

pci_policy = PciPolicyAware(
    compliance=Compliance.PCI_DSS,
    detection_hints=("card_number", "credit_card", "cvv"),
    placeholder="****XXXX"
)

decorator = SensitiveDecorator(
    policies=((Sensitivity.PCI, pci_policy),)
)

@decorator
@dataclass(frozen=True, slots=True)
class PaymentMethod:
    account_id: str
    card_number: str = field(metadata={"sensitivity": "pci"})

payment = PaymentMethod(
    account_id="a-1",
    card_number="4111111111111111"
)

>>> repr(payment)
"PaymentMethod(account_id='a-1', card_number=****XXXX)"
```

### Example 4: SECRET Policy

```python
from dataclasses import dataclass, field
from mixin_sensitivity import sensitive, Sensitivity, SensitiveDecorator
from mixin_sensitivity.decorators.classes.secret_aware import SecretPolicyAware
from mixin_sensitivity.decorators.classes.compliance import Compliance

secret_policy = SecretPolicyAware(
    compliance=Compliance.NONE,
    detection_hints=("api_key", "secret", "token", "password"),
    placeholder="[REDACTED]"
)

decorator = SensitiveDecorator(
    policies=((Sensitivity.SECRET, secret_policy),)
)

@decorator
@dataclass(frozen=True, slots=True)
class ApiCredential:
    client_id: str
    api_key: str = field(metadata={"sensitivity": "secret"})

cred = ApiCredential(
    client_id="c-123",
    api_key="sk-1234567890abcdef"
)

>>> repr(cred)
"ApiCredential(client_id='c-123', api_key=[REDACTED])"
```

### Example 5: Multiple Policies

```python
from mixin_sensitivity import Sensitivity, SensitiveDecorator
from mixin_sensitivity.decorators.classes.phi_aware import PhiPolicyAware
from mixin_sensitivity.decorators.classes.pii_aware import PiiPolicyAware
from mixin_sensitivity.decorators.classes.secret_aware import SecretPolicyAware
from mixin_sensitivity.decorators.classes.compliance import Compliance

# Define policies for each class:
phi_policy = PhiPolicyAware(
    compliance=Compliance.HIPAA,
    detection_hints=("ssn", "medical"),
    placeholder="***PHI***"
)

pii_policy = PiiPolicyAware(
    compliance=Compliance.GDPR,
    detection_hints=("email", "name"),
    placeholder="***PII***"
)

secret_policy = SecretPolicyAware(
    compliance=Compliance.NONE,
    detection_hints=("api_key", "token"),
    placeholder="***SECRET***"
)

# Wire all three:
decorator = SensitiveDecorator(
    policies=(
        (Sensitivity.PHI, phi_policy),
        (Sensitivity.PII, pii_policy),
        (Sensitivity.SECRET, secret_policy),
    )
)

@decorator
@dataclass(frozen=True, slots=True)
class MedicalApiUser:
    user_id: str
    email: str = field(metadata={"sensitivity": "pii"})
    ssn: str = field(metadata={"sensitivity": "phi"})
    api_token: str = field(metadata={"sensitivity": "secret"})

user = MedicalApiUser(
    user_id="u-1",
    email="dr.smith@clinic.com",
    ssn="123-45-6789",
    api_token="sk-med-api-token"
)

>>> repr(user)
"MedicalApiUser(user_id='u-1', email=***PII***, ssn=***PHI***, api_token=***SECRET***)"
```

## Customization

All policy fields are mutable at construction time. Create custom instances for your masking strategy:

```python
# Use a different placeholder:
my_phi_policy = PhiPolicyAware(
    compliance=Compliance.HIPAA,
    detection_hints=("name", "ssn"),
    placeholder="[PROTECTED]"
)

# Extend detection hints:
my_secret_policy = SecretPolicyAware(
    compliance=Compliance.NONE,
    detection_hints=("api_key", "secret", "token", "password", "auth_header"),
    placeholder="***"
)
```

Each policy is a frozen dataclass; it cannot be modified after construction. Create new instances for different configurations.

## Testing

See `mixin_sensitivity/decorators/tests/test_sensitive/`:

- `test_sensitive_client.py` :  Decorator with multiple policies, field masking via policy lookup
- `test_phi_aware.py`, `test_pii_aware.py`, `test_pci_aware.py`, `test_secret_aware.py` :  Per-class tests covering `mask()` and `looks_sensitive()` methods

Coverage: 100% on all policy source files.
