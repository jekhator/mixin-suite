"""The @sensitive decorator that injects a masking __repr__."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, is_dataclass
from typing import TypeVar

from mixin_sensitivity.decorators.classes.compliance import ClassMakerAware
from mixin_sensitivity.decorators.constants import sensitive as const
from mixin_sensitivity.decorators.sensitive import sensitive_objects as objs
from mixin_sensitivity.services.classify.classify_objects import Sensitivity

Target = TypeVar("Target")


@dataclass(frozen=True, slots=True)
class SensitiveDecorator:
    """Decorator that injects a sensitivity-masking __repr__ into a dataclass."""

    policies: tuple[tuple[Sensitivity, ClassMakerAware], ...]

    def __call__(self, target: type[Target]) -> type[Target]:
        """Decorate a dataclass with a masking __repr__; no-op when untagged."""
        self._require_dataclass(target)
        field_set = objs.SensitiveFieldSet.from_dataclass(target)
        if field_set.is_empty:
            return target
        setattr(target, "__repr__", self._make_repr(field_set))
        return target

    @staticmethod
    def _require_dataclass(target: type) -> None:
        """Raise TypeError when the target is not a dataclass."""
        if not is_dataclass(target):
            raise TypeError(const.ERR_SENSITIVE_TARGET_NOT_DATACLASS)

    def _make_repr(self, field_set: objs.SensitiveFieldSet) -> Callable[[object], str]:
        """Build a __repr__ closure binding the field set to the decorator's policies."""
        policy_for = dict(self.policies)

        def masked_repr(instance: object) -> str:
            return field_set.masked_repr(instance, policies=policy_for)

        return masked_repr


sensitive = SensitiveDecorator(policies=())
