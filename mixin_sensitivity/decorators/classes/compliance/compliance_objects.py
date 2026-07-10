"""Compliance tags and the policy contract for sensitivity-aware masking."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol


class Compliance(StrEnum):
    """Regulatory regimes a sensitivity policy can enforce."""

    HIPAA = "hipaa"
    GDPR = "gdpr"
    PCI_DSS = "pci-dss"
    NONE = "none"


class ClassMakerAware(Protocol):
    """Contract every per-class sensitivity policy satisfies."""

    def mask(self, value: str) -> str:
        """Return the masked form of a sensitive value."""
        ...

    def looks_sensitive(self, field_name: str) -> bool:
        """Return True when a field name reads as sensitive."""
        ...
