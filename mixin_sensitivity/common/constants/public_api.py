"""Public API export names for mixin-sensitivity.

Names exported from mixin_sensitivity.__init__: Sensitivity, SensitiveRepr,
SensitiveDeclarationError, SensitivityProfile, classify(). PUBLIC_API itself
is exported and self-included in this frozenset.
"""

from typing import Final

PUBLIC_API: Final = frozenset(
    {
        "Sensitivity",
        "SensitiveDeclarationError",
        "SensitiveRepr",
        "SensitivityProfile",
        "PUBLIC_API",
        "__version__",
        "classify",
    },
)
