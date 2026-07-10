"""Sensitivity classification: the taxonomy and a dataclass's field-to-class profile."""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Self

from mixin_sensitivity.common.constants import metadata as const


class Sensitivity(StrEnum):
    """The sealed taxonomy of sensitive-data classes."""

    PHI = "phi"
    PII = "pii"
    PCI = "pci"
    SECRET = "secret"


@dataclass(frozen=True, slots=True)
class SensitivityProfile:
    """A dataclass's fields paired with their sensitivity class."""

    classes: tuple[tuple[str, Sensitivity], ...]

    @classmethod
    def from_dataclass(cls, target: type) -> Self:
        """Read each field's sensitivity metadata into a field-to-class profile."""
        pairs: list[tuple[str, Sensitivity]] = []
        for field in fields(target):
            kind = field.metadata.get(const.SENSITIVITY_KEY)
            if kind is not None:
                pairs.append((field.name, Sensitivity(kind)))
        return cls(classes=tuple(pairs))

    @property
    def is_empty(self) -> bool:
        """Return True when no field carries a sensitivity class."""
        return not self.classes

    def sensitivity_of(self, name: str) -> Sensitivity | None:
        """Return the sensitivity class of a field, or None when it is unclassified."""
        for field_name, field_kind in self.classes:
            if field_name == name:
                return field_kind
        return None

    def has(self, kind: Sensitivity) -> bool:
        """Return True when any field carries the given sensitivity class."""
        return any(field_kind == kind for _, field_kind in self.classes)

    def fields_of(self, kind: Sensitivity) -> tuple[str, ...]:
        """Return the names of the fields carrying the given sensitivity class."""
        return tuple(
            field_name for field_name, field_kind in self.classes if field_kind == kind
        )
