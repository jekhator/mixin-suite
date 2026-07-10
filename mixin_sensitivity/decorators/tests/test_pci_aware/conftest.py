"""Shared fixtures for PCI policy tests."""

from __future__ import annotations

import pytest

from mixin_sensitivity.decorators.classes.compliance import Compliance
from mixin_sensitivity.decorators.classes.pci_aware.pci_aware_objects import (
    PciPolicyAware,
)


@pytest.fixture
def pci_dss_policy() -> PciPolicyAware:
    """A PCI-DSS-compliant payment-card masking policy."""
    return PciPolicyAware(
        compliance=Compliance.PCI_DSS,
        detection_hints=("card_token", "card_number", "cvv", "pan"),
        placeholder="[PCI REDACTED]",
    )


@pytest.fixture
def generic_pci_policy() -> PciPolicyAware:
    """A generic PCI masking policy without strict compliance."""
    return PciPolicyAware(
        compliance=Compliance.NONE,
        detection_hints=("payment_token", "card_data"),
        placeholder="****",
    )


@pytest.fixture
def empty_hints_pci_policy() -> PciPolicyAware:
    """A PCI policy with no detection hints."""
    return PciPolicyAware(
        compliance=Compliance.PCI_DSS,
        detection_hints=(),
        placeholder="[CARD_REDACTED]",
    )
