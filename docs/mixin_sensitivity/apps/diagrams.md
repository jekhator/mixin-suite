# mixin-sensitivity. Diagrams

> **Status:** Current module layout for 0.7.0. The decorator and policy diagrams from earlier releases were removed with those surfaces in 0.5.0.

## Module Layout

```
mixin_sensitivity/
+-- __init__.py                       PUBLIC_API re-exports
+-- common/constants/
|   +-- metadata.py                   SENSITIVITY_KEY ("sensitivity")
|   +-- masking.py                    SENSITIVE_MASK_TOKEN, guard message
|   +-- public_api.py                 PUBLIC_API frozenset
+-- services/classify/
|   +-- classify_objects.py           Sensitivity, SensitivityProfile
|   +-- __init__.py                   classify = SensitivityProfile.from_dataclass
+-- repr/_objects.py                  SensitiveRepr, SensitiveDeclarationError
```

## Classification Flow

```
dataclass type --> classify(target)
                     |
                     +-- fields(target)
                     |     metadata["sensitivity"] present?
                     |       yes --> (field name, Sensitivity(value))
                     |       no  --> skipped
                     v
               SensitivityProfile(classes=...)
```

## Repr Masking Flow

```
repr(instance) --> SensitiveRepr.__repr__
                     |
                     +-- for each field (declaration order)
                     |     metadata["sensitivity"] is not None?
                     |       yes --> ***MASKED***
                     |       no  --> repr(value)
                     v
               ClassName(field=value, ...)

construction --> SensitiveRepr.__post_init__
                     |
                     +-- type(self).__repr__ is SensitiveRepr.__repr__ ?
                           no  --> raise SensitiveDeclarationError
```
