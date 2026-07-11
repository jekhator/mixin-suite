# mixin_sensitivity Flow Trace

## Architecture Overview

mixin_sensitivity/decorators/sensitive/sensitive_client.py  (+ classify, compliance)
═══════════════════════════════════════════════════════════════════════════════════════
Imports: dataclass, is_dataclass; SensitivityProfile, Sensitivity, ClassMakerAware
┌─ [ENUM,StrEnum] Sensitivity ──────────┐  PHI = "phi" ; PII = "pii" ; PCI = "pci" ; SECRET = "secret"  └─...
┌─ [PROTOCOL] ClassMakerAware ──────────┐  mask(value: str) -> str  ;  looks_sensitive(field_name: str) -> bool  └─...
┌─ [DATACLASS,frozen,slots] SensitivityProfile ──────────┐  classes: tuple[(str, Sensitivity), ...] ; from_dataclass[cls_meth] ; is_empty[prop] ; sensitivity_of(name) ; has(kind) ; fields_of(kind)  └─...
┌─ [DATACLASS,frozen,slots] SensitiveFieldSet ──────────┐  profile: SensitivityProfile ; from_dataclass[cls_meth] ; is_empty[prop] ; masked_repr(instance, policies) -> str  └─...
┌─ [DATACLASS,frozen,slots] SensitiveDecorator ──────────┐  policies: tuple[(Sensitivity, ClassMakerAware), ...] ; __call__(target) ; _require_dataclass(target)⚠ ; _make_repr(field_set)  └─...

## FLOW TRACE

① CONSTRUCT  SensitiveDecorator(policies=()) or the default `sensitive` with empty policies
      └─ sensitive = SensitiveDecorator(policies=())
      ← Empty tuple: default masking uses DEFAULT_PLACEHOLDER="***"

② DECORATE   @sensitive on a dataclass whose fields carry field(metadata={"sensitivity": Sensitivity.PHI/PII/PCI/SECRET}) ⚠ SENSITIVE

   @sensitive
   @dataclass(frozen=True)
   class Patient: ──▶ __call__(target=Patient)
      ├─ _require_dataclass(target) ──⚠─▶ is_dataclass(Patient) → True ✓ (if False: raise TypeError(ERR_SENSITIVE_TARGET_NOT_DATACLASS))
      ├─ SensitiveFieldSet.from_dataclass(target)
      │     └─ SensitivityProfile.from_dataclass(target)
      │           └─ for field in fields(target):
      │                 ├─ kind = field.metadata.get("sensitivity")
      │                 │     ← Read ONCE from field.metadata dict
      │                 ├─ if kind is not None: pairs.append((field.name, Sensitivity(kind)))
      │                 ├─ Example: Patient.mrn has metadata={"sensitivity": "phi"}
      │                 │     └─ kind="phi" ──▶ Sensitivity.PHI
      │                 └─ Example: Patient.name has no sensitivity metadata
      │                       └─ kind=None ──▶ skip
      │           └─ return SensitivityProfile(classes=(("mrn", Sensitivity.PHI), ("ssn", Sensitivity.PII)))
      ├─ field_set.is_empty → len(classes) > 0 → False (has tagged fields)
      │     └─ Return early if is_empty=True (no fields tagged, no repr injection needed)
      ├─ _make_repr(field_set) ──▶ Build closure binding policy_for=dict(self.policies)
      │     └─ def masked_repr(instance: object) -> str:
      │           return field_set.masked_repr(instance, policies=policy_for)
      ├─ setattr(target, "__repr__", masked_repr) ← Replace class __repr__ with masked version
      └─ return target (Patient now has custom __repr__)

③ REPR   repr(patient_instance) ──▶ masked_repr(instance, policies=policy_for)
      ├─ for field in fields(instance):
      │     ├─ field.name="name", value="Ada Lovelace"
      │     │     ├─ kind = profile.sensitivity_of("name")
      │     │     │     └─ Loop through classes: ("mrn", PHI), ("ssn", PII) → name not found → None
      │     │     └─ kind=None ──▶ parts.append("name='Ada Lovelace'")
      │     ├─ field.name="mrn", value="MRN-12345"
      │     │     ├─ kind = profile.sensitivity_of("mrn")
      │     │     │     └─ Loop: ("mrn", PHI) matches ──▶ return Sensitivity.PHI
      │     │     ├─ policy = policy_for.get(Sensitivity.PHI)  ← policy_for=dict((PHI, policy1), ...)
      │     │     ├─ if policy is not None: mask via policy.mask(str(value))
      │     │     └─ if policy is None: use DEFAULT_PLACEHOLDER="***"
      │     │           └─ parts.append("mrn=***")
      │     └─ field.name="ssn", value="123-45-6789"
      │           ├─ kind = profile.sensitivity_of("ssn")
      │           │     └─ Loop: ("ssn", PII) matches ──▶ return Sensitivity.PII
      │           ├─ policy = policy_for.get(Sensitivity.PII)  ← not in policies tuple
      │           └─ policy=None ──▶ parts.append("ssn=***")
      └─ return "Patient(name='Ada Lovelace', mrn=***, ssn=***)"

④ NO-OP on untagged dataclass

   @sensitive
   @dataclass(frozen=True)
   class Address: ──▶ __call__(target=Address)
      ├─ _require_dataclass(Address) → True
      ├─ SensitiveFieldSet.from_dataclass(target)
      │     └─ SensitivityProfile.from_dataclass(target)
      │           └─ for field in fields(Address):
      │                 ├─ field.name="street", metadata={} → kind=None ──▶ skip
      │                 └─ field.name="city", metadata={} → kind=None ──▶ skip
      │           └─ return SensitivityProfile(classes=())
      ├─ field_set.is_empty → len(classes)==0 → True
      │     └─ return target EARLY (no repr injection)
      └─ return target (unchanged, default repr used)
           └─ repr(address) ──▶ Address(street='123 Main St', city='Boston')

## REAL RUN OUTPUT

Example output with @sensitive decorator on tagged and untagged dataclasses:
```
Patient repr: Patient(name='Ada Lovelace', mrn=***, ssn=***)
Address repr: Address(street='123 Main St', city='Boston')
CreditCard repr: CreditCard(holder_name='Ada Lovelace', card_number=***)
```

Key observations:
- Decorator reads field.metadata["sensitivity"] exactly once during decoration (lazy binding at @decorator time)
- No-op when no fields are tagged (is_empty check short-circuits repr injection)
- Masked repr rendered via SensitiveFieldSet.masked_repr(), which loops all fields every time repr() is called
- Policy dispatch is optional: if policies tuple is empty (default), all tagged fields → DEFAULT_PLACEHOLDER="***"
- Non-tagged fields render their value unchanged (e.g., name='Ada Lovelace' not masked)
- Closure binding in _make_repr ensures policy_for dict persists across repr() calls
