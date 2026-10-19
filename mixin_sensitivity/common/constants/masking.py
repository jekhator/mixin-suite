"""Repr masking constants for SensitiveRepr. Imported as const."""

from typing import Final

SENSITIVE_MASK_TOKEN: Final = "***MASKED***"
ERR_SENSITIVE_REPR_NOT_OVERRIDDEN: Final = (
    "SensitiveRepr adopter must use @dataclass(..., repr=False) "
    "to avoid silent repr shadowing. "
    "If the adopter has __post_init__, call SensitiveRepr.__post_init__(self) "
    "(explicit call required: slots dataclass re-creation breaks zero-arg super on 3.11)."
)
