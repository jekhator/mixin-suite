"""Repr mixin for masking sensitive dataclass fields."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Final

from mixin_sensitivity.services.classify import Sensitivity

ERR_SENSITIVE_MASKED_REPR: Final = "***MASKED***"


class SensitiveRepr:
    """Adoption mixin: masks sensitive fields in dataclass __repr__.

    Inheriting dataclasses must be frozen+slots dataclasses with fields
    optionally marked via field(metadata={"sensitivity": Sensitivity.X}).

    Example:
        @dataclass(frozen=True, slots=True)
        class Patient(SensitiveRepr):
            name: str
            ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})

        p = Patient(name="Alice", ssn="123-45-6789")
        print(repr(p))
        # Patient(name='Alice', ssn='***MASKED***')
    """

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
