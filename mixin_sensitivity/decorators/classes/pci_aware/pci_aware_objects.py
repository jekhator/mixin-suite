"""PCI sensitivity policy value object."""

from __future__ import annotations

from dataclasses import dataclass

from mixin_sensitivity.decorators.classes.compliance import Compliance


@dataclass(frozen=True, slots=True)
class PciPolicyAware:
    """PCI masking policy bound to its regulatory regime."""

    compliance: Compliance
    detection_hints: tuple[str, ...]
    placeholder: str

    def mask(self, value: str) -> str:
        """Return the masked replacement for a sensitive value."""
        return self.placeholder

    def looks_sensitive(self, field_name: str) -> bool:
        """Return True when the field name matches a detection hint."""
        lowered = field_name.lower()
        return any(hint.lower() in lowered for hint in self.detection_hints)
