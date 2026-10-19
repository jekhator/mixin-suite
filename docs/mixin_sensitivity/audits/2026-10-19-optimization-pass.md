# Optimization pass audit (2026-10-19): mixin_sensitivity

## Purpose

This document records an optimization pass over every Python file under mixin_sensitivity/ (19 files, source and tests). The pass looked for correctness defects, dead and duplicated code, control-flow simplifications, typing precision, constants placement, naming, per-call performance, test determinism and docs truth. The repr masking path was the focus: a fail-open marker check and the constants placement. Each file is listed in the table at the end with its findings, whether it changed, and a note.

## Method

- Scope: all .py files under mixin_sensitivity/ (source and tests), 19 files after the pass including the new masking constants module.
- Lenses: correctness, dead and duplicated code, control flow, typing, constants, naming, performance, tests, docs truth.
- Verification: defects were confirmed where they could be shown by running code: small probes ran against the pre-pass tree (commit 3a57a8b) and against the changed tree on Python 3.12.
- Changes were committed one group at a time (source, then tests), each after the local gates passed.

## Summary

- Files reviewed: 19
- Files changed or added: 9
- Files unchanged: 10 (each with its reason in the table)
- Files with at least one finding: 8
- Findings by lens (a file can carry more than one): assertion 2, constants 3, correctness 1, coverage 1, dead 1, docs 3, naming 1, performance 1, typing 1
- Tests before and after: 41 before, 42 after (pytest collection of mixin_sensitivity)
- Coverage: 100 percent branch coverage of the whole suite before and after; see the repository section in the mixin_logging audit for the gate outputs.

## Behavior changes

1. Fail-closed masking. SensitiveRepr masked a field only when its marker was a Sensitivity member. A plain string marker such as "phi", which classify() accepts, was printed unmasked. Any non-None marker now masks the field. A probe on the pre-pass tree printed the SSN unmasked; the changed tree masks it. CHANGELOG Fixed entry: Repr masking of string markers.
2. Constants location. SENSITIVE_MASK_TOKEN and ERR_SENSITIVE_REPR_NOT_OVERRIDDEN moved from the repr module to common/constants/masking.py under the const alias. Code that imported them from the old module path must import them from the constants module. CHANGELOG Changed entry: Repr masking constants.

## Deferred candidates

These were found during the pass and left unchanged, because the change alters behavior beyond the objective or needs a design decision.

- docs/mixin_sensitivity (STATUS.md, architecture/architecture.md, architecture/flow-trace.md, apps/decorators, apps/diagrams.md, the 2026-06-09 audit and review, CHANGELOG-history.md) describe the removed @sensitive decorator, the sensitivity_mixin import name and a Python 3.11 floor. They are outside this pass markdown scope and are listed for the documentation pass.
- The SensitiveRepr adoption message keeps its Python 3.11 rationale about zero-argument super. The package floor is now 3.12; the rationale should be re-checked on 3.12 and 3.14 before the message text changes.
- A marker value that is not a valid Sensitivity name is masked at repr time and rejected only by classify(). Validating marker values at class creation would surface typos earlier; that is a design change and is deferred.
- Method docstrings are kept; the method docstring ruling is pending.

## Per-file table

Each Python file under mixin_sensitivity/ appears once. Findings carry a lens tag in brackets.

| Path | Findings | Changed | Note |
| --- | --- | --- | --- |
| mixin_sensitivity/__init__.py | [docs] multi-line module docstring; module docstrings are one line | yes | One-line docstring; the quick start is in the README. |
| mixin_sensitivity/common/__init__.py | none | no | Package docstring only. |
| mixin_sensitivity/common/constants/__init__.py | none | no | Package docstring only. |
| mixin_sensitivity/common/constants/masking.py | [constants] masking token and adoption error text lived in the repr module | yes (new) | Holds SENSITIVE_MASK_TOKEN and ERR_SENSITIVE_REPR_NOT_OVERRIDDEN under the const alias. |
| mixin_sensitivity/common/constants/metadata.py | [docs] stray string literal after the module docstring | yes | Literal removed; module docstring one line. |
| mixin_sensitivity/common/constants/public_api.py | none | no | Export partition documented in the module. |
| mixin_sensitivity/common/tests/test_public_api.py | none | no | Checks export parity; no finding. |
| mixin_sensitivity/config/__init__.py | none | no | Package docstring only. |
| mixin_sensitivity/config/_version.py | none | yes | Version bump to 0.7.0 (release lockstep); not a finding. |
| mixin_sensitivity/repr/__init__.py | [docs] empty package initializer without a docstring | yes | One-line docstring added. |
| mixin_sensitivity/repr/_objects.py | [correctness] only Sensitivity members masked; plain string markers that classify() accepts were shown unmasked; [constants] literal metadata key and messages outside constants; [dead] pass in an exception body; [performance] or {} allocation per field; [typing] untyped parts list | yes | Any non-None marker masks (fail-closed); constants read from the constants modules; redundant pass removed; metadata read without copying. |
| mixin_sensitivity/services/__init__.py | none | no | Package docstring only. |
| mixin_sensitivity/services/classify/__init__.py | none | no | Re-exports and the classify binding; no finding. |
| mixin_sensitivity/services/classify/classify_objects.py | [naming] loop variable named field | yes | Renamed dataclass_field. |
| mixin_sensitivity/services/tests/__init__.py | none | no | Package docstring only. |
| mixin_sensitivity/services/tests/test_classify/__init__.py | none | no | Package docstring only. |
| mixin_sensitivity/services/tests/test_classify/conftest.py | none | no | Shared fixtures typed and documented; no finding. |
| mixin_sensitivity/services/tests/test_classify/test_classify_objects.py | [assertion] frozen test set an attribute that is not a field, so it passed for the wrong reason; [assertion] order test asserted only the container type | yes | Frozen test assigns a field and expects FrozenInstanceError; order test uses a two-field class and checks the names. |
| mixin_sensitivity/tests/test_sensitive_repr.py | [constants] literal mask token in assertions; [coverage] no regression for a plain string marker | yes | Constant token in assertions; string-marker test added; a probe on the pre-pass tree shows the plain string marker unmasked. |
