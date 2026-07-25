"""mixin-sensitivity: sensitive-data classification for frozen dataclasses.

Quick start:
    from dataclasses import dataclass, field
    from mixin_sensitivity import classify, Sensitivity

    @dataclass(frozen=True, slots=True)
    class Patient:
        name: str
        ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})

    profile = classify(Patient)
    print(profile.has(Sensitivity.PHI))  # True

Key features:
    - Sensitive-data classification taxonomy (PHI, PII, PCI, SECRET)
    - Field metadata key "sensitivity" for tagged fields
    - Frozen dataclass compatible
"""

from mixin_sensitivity.common.constants.public_api import PUBLIC_API
from mixin_sensitivity.config._version import __version__
from mixin_sensitivity.repr._objects import (
    SensitiveDeclarationError,
    SensitiveRepr,
)
from mixin_sensitivity.services.classify import (
    Sensitivity,
    SensitivityProfile,
    classify,
)

__all__ = [
    "PUBLIC_API",
    "Sensitivity",
    "SensitiveDeclarationError",
    "SensitiveRepr",
    "SensitivityProfile",
    "__version__",
    "classify",
]
