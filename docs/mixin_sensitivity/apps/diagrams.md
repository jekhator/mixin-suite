# Diagrams

> **Location:** `sensitivity-mixin/docs/apps/diagrams.md`
> **Status:** 0.3.0 taxonomy-driven architecture. All containers implemented with full method signatures.

## Sensitivity Taxonomy & Classification

```
sensitivity_mixin/services/classify/classify_objects.py
═══════════════════════════════════════════════════════════════════════
Sensitivity enum:  (PHI, PII, PCI, SECRET)

SensitivityProfile value object:
  classes: tuple[tuple[str, Sensitivity], ...]  ← field name → sensitivity pairs
  
  @classmethod from_dataclass(target: type) → Self
    ↳ introspect dataclass for sensitivity-tagged fields
    
  is_empty: bool (property)
    ↳ True when no field carries a sensitivity class
    
  sensitivity_of(name: str) → Sensitivity | None
    ↳ return the sensitivity class of a field
    
  has(kind: Sensitivity) → bool
    ↳ True when any field carries the given sensitivity class
    
  fields_of(kind: Sensitivity) → tuple[str, ...]
    ↳ return names of fields carrying the given sensitivity class

classify(instance: object) → SensitivityProfile
  ↳ [NOT IN DIAGRAMS.MD SCOPE: this is a service]
```

## Compliance Contract

```
sensitivity_mixin/decorators/classes/compliance/compliance_objects.py
═══════════════════════════════════════════════════════════════════════
[IMPLEMENTED]

┌─ Compliance (StrEnum) ────────────────────────────────────────────┐
│   HIPAA  = "hipaa"                                                │
│   GDPR   = "gdpr"                                                 │
│   PCI_DSS = "pci-dss"                                            │
│   NONE   = "none"                                                 │
│                                                                   │
│   Regulatory regimes a sensitivity policy can enforce             │
└───────────────────────────────────────────────────────────────────┘

┌─ ClassMakerAware (Protocol) ──────────────────────────────────────┐
│   [mth] mask(value: str) → str                                   │
│         Return the masked form of a sensitive value               │
│                                                                   │
│   [mth] looks_sensitive(field_name: str) → bool                  │
│         Return True when a field name reads as sensitive          │
│                                                                   │
│   Contract every per-class sensitivity policy satisfies           │
└───────────────────────────────────────────────────────────────────┘
```

## Per-Class Policy Objects (Objects-Only)

```
sensitivity_mixin/decorators/classes/phi_aware/phi_aware_objects.py
═══════════════════════════════════════════════════════════════════════
[IMPLEMENTED]

┌─ [FROZEN] PhiPolicyAware ────────────────────────────────────────┐
│   compliance: Compliance                                          │
│   detection_hints: tuple[str, ...]                               │
│   placeholder: str                                                │
│                                                                   │
│   [mth] mask(value: str) → str                                   │
│         Return the masked replacement for a sensitive value       │
│                                                                   │
│   [mth] looks_sensitive(field_name: str) → bool                  │
│         Return True when the field name matches a detection hint  │
│                                                                   │
│   PHI masking policy bound to its regulatory regime               │
└───────────────────────────────────────────────────────────────────┘


sensitivity_mixin/decorators/classes/pii_aware/pii_aware_objects.py
═══════════════════════════════════════════════════════════════════════
[IMPLEMENTED]

┌─ [FROZEN] PiiPolicyAware ────────────────────────────────────────┐
│   compliance: Compliance                                          │
│   detection_hints: tuple[str, ...]                               │
│   placeholder: str                                                │
│                                                                   │
│   [mth] mask(value: str) → str                                   │
│         Return the masked replacement for a sensitive value       │
│                                                                   │
│   [mth] looks_sensitive(field_name: str) → bool                  │
│         Return True when the field name matches a detection hint  │
│                                                                   │
│   PII masking policy bound to its regulatory regime               │
└───────────────────────────────────────────────────────────────────┘


sensitivity_mixin/decorators/classes/pci_aware/pci_aware_objects.py
═══════════════════════════════════════════════════════════════════════
[IMPLEMENTED]

┌─ [FROZEN] PciPolicyAware ────────────────────────────────────────┐
│   compliance: Compliance                                          │
│   detection_hints: tuple[str, ...]                               │
│   placeholder: str                                                │
│                                                                   │
│   [mth] mask(value: str) → str                                   │
│         Return the masked replacement for a sensitive value       │
│                                                                   │
│   [mth] looks_sensitive(field_name: str) → bool                  │
│         Return True when the field name matches a detection hint  │
│                                                                   │
│   PCI masking policy bound to its regulatory regime               │
└───────────────────────────────────────────────────────────────────┘


sensitivity_mixin/decorators/classes/secret_aware/secret_aware_objects.py
═══════════════════════════════════════════════════════════════════════
[IMPLEMENTED]

┌─ [FROZEN] SecretPolicyAware ──────────────────────────────────────┐
│   compliance: Compliance                                          │
│   detection_hints: tuple[str, ...]                               │
│   placeholder: str                                                │
│                                                                   │
│   [mth] mask(value: str) → str                                   │
│         Return the masked replacement for a sensitive value       │
│                                                                   │
│   [mth] looks_sensitive(field_name: str) → bool                  │
│         Return True when the field name matches a detection hint  │
│                                                                   │
│   Credential-masking policy bound to its regulatory regime        │
└───────────────────────────────────────────────────────────────────┘
```

## @sensitive Decorator Layer

```
sensitivity_mixin/decorators/sensitive/sensitive_objects.py
═══════════════════════════════════════════════════════════════════════
[IMPLEMENTED]

┌─ [FROZEN] SensitiveFieldSet ──────────────────────────────────────┐
│   profile: SensitivityProfile                                     │
│                                                                   │
│   @classmethod from_dataclass(target: type) → Self               │
│         Build the field set from a dataclass's sensitivity       │
│         metadata                                                  │
│                                                                   │
│   is_empty: bool (property)                                      │
│         Return True when no field carries a sensitivity class    │
│                                                                   │
│   masked_repr(instance: object) → str                            │
│         Render the instance repr with tagged fields replaced     │
│         by the placeholder (***).                                │
│                                                                   │
│   A dataclass's sensitivity profile plus its masking surface     │
└───────────────────────────────────────────────────────────────────┘


sensitivity_mixin/decorators/sensitive/sensitive_client.py
═══════════════════════════════════════════════════════════════════════
[IMPLEMENTED]

Target = TypeVar("Target")

┌─ [FROZEN] SensitiveDecorator ────────────────────────────────────┐
│   policies: tuple[tuple[Sensitivity, ClassMakerAware], ...]      │
│                                                                   │
│   [mth] __call__(target: type[Target]) → type[Target]            │
│         Decorate a dataclass with a masking __repr__; no-op       │
│         when untagged                                             │
│                                                                   │
│   [mth] _require_dataclass(target: type) → None                  │
│         Raise TypeError when the target is not a dataclass       │
│                                                                   │
│   [mth] _make_repr(                                              │
│           field_set: SensitiveFieldSet                           │
│         ) → Callable[[object], str]                              │
│         Build a __repr__ closure resolving each tagged field     │
│         through its policy                                       │
│                                                                   │
│   Decorator that injects a sensitivity-masking __repr__ into     │
│   a dataclass                                                    │
└───────────────────────────────────────────────────────────────────┘

Module-level instance:
  sensitive = SensitiveDecorator(policies=())
    ↳ ready-to-use decorator (re-exported from sensitivity_mixin)
```
