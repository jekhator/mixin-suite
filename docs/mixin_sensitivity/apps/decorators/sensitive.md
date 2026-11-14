# SensitiveRepr (adoption mixin)

> **Status:** Current. This page replaces the removed `@sensitive` decorator page, which described the decorator surface removed in 0.5.0.
> **Code:** `mixin_sensitivity/repr/_objects.py`, `mixin_sensitivity/services/classify/`

## What it does

`SensitiveRepr` is an adoption mixin for frozen, slots dataclasses. It masks every field whose metadata carries a sensitivity class when the object is printed with `repr()`. The field metadata stays readable through `classify()`.

## Adopting it

```python
```

Output:

```
```

The example was executed with `uv run --all-extras python` on Python 3.14 against the 0.7.0 tree.

## Rules

- Declare the subclass with `repr=False`; otherwise the first construction raises `SensitiveDeclarationError`.
- If the subclass has its own `__post_init__`, call `SensitiveRepr.__post_init__(self)` from it.
- Markers can be a `Sensitivity` member or its string value; both mask the field.

## Classification

`classify(Patient)` returns a `SensitivityProfile`. Pass the dataclass type. The profile lists classified fields, and `fields_of(kind)` returns the names for one class.

## Not covered

- Masking applies to `repr()` only. It does not change `str()` for types that define their own `__str__`, and it does not redact values inside `extra` log fields (use `mixin_logging` redaction for that).
