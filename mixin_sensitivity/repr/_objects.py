"""Repr mixin for masking sensitive dataclass fields."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Final

from mixin_sensitivity.services.classify import Sensitivity

ERR_SENSITIVE_MASKED_REPR: Final = "***MASKED***"
ERR_SENSITIVE_REPR_NOT_OVERRIDDEN: Final = (
    "SensitiveRepr adopter must use @dataclass(..., repr=False) "
    "to avoid silent repr shadowing. "
    "If the adopter has __post_init__, call SensitiveRepr.__post_init__(self) "
    "(explicit call required: slots dataclass re-creation breaks zero-arg super on 3.11)."
)


class SensitiveDeclarationError(Exception):
    """Raised when SensitiveRepr is adopted without proper repr=False setting."""

    pass


class SensitiveRepr:
    """Adoption mixin: masks sensitive fields in dataclass __repr__.

    Inheriting dataclasses MUST use @dataclass(frozen=True, slots=True, repr=False)
    to avoid silent shadowing of the masking __repr__. A __post_init__ guard
    raises SensitiveDeclarationError if repr=False is omitted.

    If an adopting class has its own __post_init__, it must call
    SensitiveRepr.__post_init__(self) to trigger the guard (explicit call required:
    slots dataclass re-creation breaks zero-arg super() on Python 3.11).

    Attributes:
        Inheriting dataclasses may mark fields via
        field(metadata={"sensitivity": Sensitivity.X}).

    Example:
        @dataclass(frozen=True, slots=True, repr=False)
        class Patient(SensitiveRepr):
            name: str
            ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})

        p = Patient(name="Alice", ssn="123-45-6789")
        print(repr(p))
        # Patient(name='Alice', ssn='***MASKED***')
    """

    def __post_init__(self) -> None:
        """Guard against silent repr shadowing.

        Raises SensitiveDeclarationError if the adopter's @dataclass
        generated its own __repr__ instead of using SensitiveRepr's.
        """
        if type(self).__repr__ is not SensitiveRepr.__repr__:
            raise SensitiveDeclarationError(ERR_SENSITIVE_REPR_NOT_OVERRIDDEN)

    def __repr__(self) -> str:
        """Repr with sensitive fields masked.

        Reads field(metadata={"sensitivity": Sensitivity.X}) markers.
        Replaced marked values with ERR_SENSITIVE_MASKED_REPR token.
        Field metadata remains introspectable unchanged.
        """
        if not is_dataclass(self):
            return object.__repr__(self)

        parts = []
        for field_obj in fields(self):
            value = getattr(self, field_obj.name)
            metadata = field_obj.metadata or {}
            sensitivity = metadata.get("sensitivity")

            if sensitivity is not None and isinstance(sensitivity, Sensitivity):
                display_value = ERR_SENSITIVE_MASKED_REPR
            else:
                display_value = repr(value)

            parts.append(f"{field_obj.name}={display_value}")

        class_name = type(self).__name__
        return f"{class_name}({', '.join(parts)})"
