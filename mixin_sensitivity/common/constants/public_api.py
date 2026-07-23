"""Public API export names for mixin-sensitivity.

Names exported from mixin_sensitivity.__init__: Sensitivity, SensitiveRepr,
SensitivityProfile, classify(). PUBLIC_API itself is exported and
self-included in this frozenset.
"""

from typing import Final

PUBLIC_API: Final = frozenset(
    {
        "Sensitivity",
        "SensitiveRepr",
        "SensitivityProfile",
        "PUBLIC_API",
        "__version__",
        "classify",
    },
)
