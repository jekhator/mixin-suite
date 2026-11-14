# mixin-sensitivity Flow Trace

This trace follows `mixin_sensitivity/repr/_objects.py` and `mixin_sensitivity/services/classify/` as shipped in 0.7.0.

## Class definition (adoption)

1. The subclass is declared `@dataclass(frozen=True, slots=True, repr=False)` and inherits `SensitiveRepr`.
2. `repr=False` keeps the dataclass from generating a `__repr__`, so `SensitiveRepr.__repr__` is the one in effect.
3. Fields that carry a sensitivity class declare `field(metadata={"sensitivity": Sensitivity.X})`.

If `repr=False` is omitted, step 2 does not hold. The first construction calls `SensitiveRepr.__post_init__`, which sees that `type(self).__repr__` is not `SensitiveRepr.__repr__` and raises `SensitiveDeclarationError`.

## Construction

1. The dataclass `__init__` assigns the fields.
2. `__post_init__` runs. For an adopter without its own `__post_init__`, this is `SensitiveRepr.__post_init__`, which performs the guard in step above.

## repr(instance)

1. `SensitiveRepr.__repr__` runs. If the object is not a dataclass, it falls back to `object.__repr__`.
2. For each field in declaration order, the metadata is read: `field_obj.metadata.get("sensitivity")`.
   - Not None (any enum member or string marker): the value is shown as `***MASKED***`.
   - None: `repr(getattr(self, name))` is shown.
3. The parts are joined as `ClassName(name=value, ...)`.

Field metadata is not changed by the masking, so `classify()` returns the same profile before and after a repr.

## classify(target)

1. `classify` is `SensitivityProfile.from_dataclass`. It takes the dataclass type.
2. `dataclasses.fields(target)` is read; fields with a `"sensitivity"` metadata key are collected as `(name, Sensitivity(value))`.
3. The result is a frozen `SensitivityProfile`. Its methods answer `is_empty`, `sensitivity_of(name)`, `has(kind)` and `fields_of(kind)`.

## REAL RUN OUTPUT

Output of the example below, run with `uv run --all-extras python` on Python 3.14 against the 0.7.0 tree:

```python
from dataclasses import dataclass, field

from mixin_sensitivity import (
    Sensitivity,
    SensitiveDeclarationError,
    SensitiveRepr,
    classify,
)


@dataclass(frozen=True, slots=True, repr=False)
class Patient(SensitiveRepr):
    name: str
    ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})
    card: str = field(default="", metadata={"sensitivity": Sensitivity.PCI})
    note: str = ""


patient = Patient(name="Alice", ssn="123-45-6789", card="4111111111111111", note="follow-up")
print(repr(patient))
print(classify(Patient).classes)
print(classify(Patient).fields_of(Sensitivity.PHI))
print(classify(Patient).sensitivity_of("note"))


@dataclass(frozen=True, slots=True)
class Unguarded(SensitiveRepr):
    ssn: str = field(default="", metadata={"sensitivity": Sensitivity.PII})


try:
    Unguarded(ssn="987-65-4321")
except SensitiveDeclarationError as error:
    print("SensitiveDeclarationError:", type(error).__name__)
```

```
Patient(name='Alice', ssn=***MASKED***, card=***MASKED***, note='follow-up')
(('ssn', <Sensitivity.PHI: 'phi'>), ('card', <Sensitivity.PCI: 'pci'>))
('ssn',)
None
SensitiveDeclarationError: SensitiveDeclarationError
```

## Invariants

- No sensitive value is printed by `repr()`; the token `***MASKED***` replaces it.
- Unmarked fields print exactly as `repr()` of the value.
- A dataclass that bypasses `SensitiveRepr`'s repr fails at construction, not at log time.
