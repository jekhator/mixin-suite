"""Sensitivity classification: taxonomy, the field-to-class profile, and classify()."""

from mixin_sensitivity.services.classify.classify_objects import (
    Sensitivity,
    SensitivityProfile,
)

classify = SensitivityProfile.from_dataclass

__all__ = ["Sensitivity", "SensitivityProfile", "classify"]
