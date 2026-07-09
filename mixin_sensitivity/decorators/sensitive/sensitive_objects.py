"""Masking field-set value object for the @sensitive decorator."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Self, cast

from mixin_sensitivity.decorators.classes.compliance import ClassMakerAware
from mixin_sensitivity.decorators.constants import sensitive as const
from mixin_sensitivity.services.classify.classify_objects import (
    Sensitivity,
    SensitivityProfile,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance


@dataclass(frozen=True, slots=True)
class SensitiveFieldSet:
    """A dataclass's sensitivity profile plus its masking surface."""

    profile: SensitivityProfile

    @classmethod
    def from_dataclass(cls, target: type) -> Self:
        """Build the field set from a dataclass's sensitivity metadata."""
        return cls(profile=SensitivityProfile.from_dataclass(target))

    @property
    def is_empty(self) -> bool:
        """Return True when no field carries a sensitivity class."""
        return self.profile.is_empty

    def masked_repr(
        self,
        instance: object,
        policies: Mapping[Sensitivity, ClassMakerAware] | None = None,
    ) -> str:
        """Render the instance repr, masking tagged fields through their policies."""
        policy_for = policies or {}
        parts: list[str] = []
        for field in fields(cast("DataclassInstance", instance)):
            value = getattr(instance, field.name)
            kind = self.profile.sensitivity_of(field.name)
            if kind is None:
                parts.append(f"{field.name}={value!r}")
                continue
            policy = policy_for.get(kind)
            parts.append(
                f"{field.name}={policy.mask(str(value)) if policy else const.DEFAULT_PLACEHOLDER}"
            )
        return f"{type(instance).__name__}({', '.join(parts)})"
