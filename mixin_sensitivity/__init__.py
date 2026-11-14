"""Sensitive-data classification and dataclass repr masking."""

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
