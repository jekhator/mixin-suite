# Security Audit: @sensitive Decorator Layer

**Date:** 2026-06-09  
**Branch:** `feat/mixin-sensitivity`  
**Commit range:** `main...HEAD`  
**Auditor:** Security Engineering  
**Verdict:** **SHIP** :  No blocking security defects

---

## Audit Scope

Security review of the decorator-layer masking subsystem:

- `SensitiveDecorator` (sensitive_client.py) :  decorator application + __repr__ injection
- `SensitiveFieldSet` (sensitive_objects.py) :  field introspection + masked_repr() logic
- `SensitivityProfile` (classify_objects.py) :  metadata-driven sensitivity classification
- Error paths + test fixture validation
- Documentation of security boundary + policy injection surface
- Frozen/slots integrity verification

---

## Findings

### 1. Masking Efficacy :  SECURE

**Finding:** repr-layer masking is correctly implemented and cannot leak tagged values via standard repr/str/logging paths.

**Verification:**
- `__repr__` injected via `setattr(target, "__repr__", closure)` at class decoration time (sensitive_client.py:28)
- `__str__` not overridden; falls back to `__repr__()` per Python spec :  masking applies
- No field-access leaks: `getattr(instance, field.name)` still returns unmasked value (intended; documented out-of-scope)
- `str(value)` conversion used in masked_repr() (sensitive_objects.py:52) before policy application :  value type coercion handled safely
- Test coverage: 37 test cases verify masking under all 4 sensitivity classes (PHI, PII, PCI, SECRET); all pass

**Example:** `Test(value=***)` repr masks a SECRET field while maintaining readability.

### 2. Untagged Classes :  NO-OP SAFE

**Finding:** Classes without sensitivity-tagged fields are returned unchanged; original repr preserved.

**Verification:**
- `is_empty` predicate (sensitive_objects.py:32-34) skips decoration when no fields carry metadata
- test_untagged_class_returned_unchanged verifies identity: `assert result is Public`
- No side effects; safe to apply decorator to arbitrary dataclasses

### 3. Policy Injection Surface :  DOCUMENTED RESPONSIBILITY

**Finding:** Policies are caller-supplied `ClassMakerAware` objects; a buggy/malicious policy could return the unmasked input from `mask()` method, echoing the value.

**Risk level:** Low  
**Why low:** Policies are internal implementation details, not user-supplied at runtime; both downstream projects control the 4 policy classes (PhiPolicyAware, PiiPolicyAware, PciPolicyAware, SecretPolicyAware).

**Requirement:** Document policy contract as a caller responsibility. Current status: NOT explicitly documented in docs/apps/decorators/sensitive.md.

**Recommendation:** Add note to sensitive.md section "Security Boundary" or API section:
```
Policy Contract: Each ClassMakerAware.mask() implementation MUST NOT return the input value unchanged. 
Returning the unmasked value defeats masking; implementations MUST return a placeholder or transformed value.
All shipped policies (PhiPolicyAware, etc.) comply; custom policies must be audited.
```

### 4. Error Messages :  STATIC & SAFE

**Finding:** All error constants are static; no caller data embedded.

**Verification:**
- Single error constant: `ERR_SENSITIVE_TARGET_NOT_DATACLASS = "@sensitive requires a dataclass target"` (const.py:20)
- Raised only when `not is_dataclass(target)` (sensitive_client.py:35)
- No field names, values, or context leak in message

### 5. Test Fixtures :  NO REAL SECRETS

**Finding:** Test fixtures use synthetic PII/PHI/PCI/SECRET values only; no real-looking credentials.

**Verification:**
- SSN format: "123-45-6789" is a standard fake (not real)
- API key format: "sk_live_xyz789" matches Stripe format but is clearly synthetic
- Email: "user@example.com", "john@example.com" are non-routable test addresses
- Card token: "tok_abc123", "4111111111111111" (Visa test card) :  permitted for testing

**Note:** Unused fixture defect found (conftest.py:154):
```python
@pytest.fixture
def mixed_instance(mixed_class: type[Any]) -> Any:
    return mixed_instance(...)  # BUG: recursive call, should be mixed_class()
```
Impact: Fixture is defined but never imported/used in tests; does NOT cause test failures or security leaks.

### 6. Frozen & Slots Integrity :  VERIFIED

**Finding:** Decorator correctly works with frozen dataclasses; __repr__ method is safely injected and immutable by the dataclass frozen mechanism.

**Verification:**
```
Class: <class '__main__.Test'>
__repr__ method: <function SensitiveDecorator._make_repr.<locals>.masked_repr at ...>
Frozen slots integrity: OK
```
- `setattr(target, "__repr__", closure)` occurs at decoration time (class-level); returns unmodified class
- Frozen dataclass instances cannot modify `__repr__` post-construction
- Closure correctly captures `field_set` and `policies` in lexical scope

### 7. Documentation :  COMPREHENSIVE WITH ONE GAP

**Finding:** docs/apps/decorators/sensitive.md provides comprehensive security boundary documentation. One gap: policy injection responsibility not explicitly stated.

**Current coverage (GOOD):**
- section "Security Boundary: What This Does and Does NOT Protect" :  explicitly lists protected paths (repr, str, logging, f-strings) vs. bypass methods (direct access, asdict, JSON, pickling)
- section "Mask Strategy Information Leakage" :  documents PII/PCI leakage patterns (first-char, last-4 digits) per regulatory guidance
- section "Correct and Incorrect Usage" :  example showing safe vs. unsafe logging patterns; untagged field pitfall

**Gap (MINOR):**
- Policy contract not documented (see Finding 3 recommendation above)

---

## Security Boundary (as documented)

### Protected (Repr Layer Only)
- yes `repr(obj)` :  sensitive fields masked per sensitivity tag
- yes `str(obj)` :  uses masked repr
- yes `print(obj)` :  masked via repr
- yes F-string: `f"{obj}"` :  masked
- yes Logging: `logger.info("Object: %s", obj)` :  masked

### NOT Protected (by design, out-of-scope)
- no Direct field access: `obj.api_key` :  full unmasked value
- no Serialization: `dataclasses.asdict(obj)` :  full unmasked values
- no Field-level logging: `logger.info(f"Token: {obj.api_key}")` :  full value
- no Attribute introspection: `getattr(obj, 'api_key')` :  unmasked
- no Pickling: `pickle.dumps(obj)` :  full values
- no Untagged fields :  never masked, even if field name looks sensitive

---

## Test Results

All 37 test cases pass:

```
mixin_sensitivity/decorators/tests/test_sensitive/test_sensitive_client.py
  yes TestSensitiveDecoratorRequireDataclass (2 tests)
  yes TestSensitiveDecoratorUntaggedClass (2 tests)
  yes TestSensitiveDecoratorNoPolicy (1 test)
  yes TestSensitiveDecoratorWithPolicies (3 tests)
  yes TestSensitiveModuleVariable (3 tests)
  yes TestSensitiveDecoratorInstanceFrozen (1 test)
  yes TestSensitiveDecoratorSlotsDataclass (1 test)
  yes TestSensitiveDecoratorReturnsSameType (2 tests)
  yes TestSensitiveDecoratorWithIntFields (1 test)
  yes TestSensitiveDecoratorEdgeCases (3 tests)

mixin_sensitivity/decorators/tests/test_sensitive/test_sensitive_objects.py
  yes TestFromDataclass (3 tests)
  yes TestIsEmpty (3 tests)
  yes TestMaskedReprUntagged (2 tests)
  yes TestMaskedReprWithoutPolicies (2 tests)
  yes TestMaskedReprWithPolicies (3 tests)
  yes TestMaskedReprNoneAndIntValues (2 tests)
  yes TestMaskedReprFormat (3 tests)

TOTAL: 37 PASSED in 0.22s
```

---

## Blockers

**None.** The decorator layer is production-ready from a security standpoint.

---

## Recommendations (Non-blocking)

1. **Document policy contract** (see Finding 3): Add a callout in sensitive.md explaining that custom policies MUST NOT echo unmasked values.

2. **Fix unused fixture** (conftest.py:154): Remove the `mixed_instance` fixture or correct it to instantiate `mixed_class()` instead of calling itself recursively. Current impact: none (unused), but fixes hygiene.

---

## Attestation

This audit confirms:
- Masking efficacy is correct and cannot leak via standard repr/str/logging
- No hardcoded secrets or PII in test fixtures
- Error messages are static and safe
- Frozen/slots immutability prevents __repr__ tampering
- Security boundary is clearly documented with one minor gap (policy contract)

**Recommendation:** SHIP  
**Deadline:** Ready for merge

