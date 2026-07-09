"""Shared fixtures for sensitive decorator tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from mixin_sensitivity.decorators.classes.compliance import Compliance
from mixin_sensitivity.decorators.classes.pci_aware.pci_aware_objects import (
    PciPolicyAware,
)
from mixin_sensitivity.decorators.classes.phi_aware.phi_aware_objects import (
    PhiPolicyAware,
)
from mixin_sensitivity.decorators.classes.pii_aware.pii_aware_objects import (
    PiiPolicyAware,
)
from mixin_sensitivity.decorators.classes.secret_aware.secret_aware_objects import (
    SecretPolicyAware,
)
from mixin_sensitivity.services.classify.classify_objects import Sensitivity


@pytest.fixture
def hipaa_phi_policy() -> PhiPolicyAware:
    """A HIPAA-compliant PHI masking policy."""
    return PhiPolicyAware(
        compliance=Compliance.HIPAA,
        detection_hints=("ssn", "mrn"),
        placeholder="[PHI]",
    )


@pytest.fixture
def gdpr_pii_policy() -> PiiPolicyAware:
    """A GDPR-compliant PII masking policy."""
    return PiiPolicyAware(
        compliance=Compliance.GDPR,
        detection_hints=("email", "phone"),
        placeholder="[PII]",
    )


@pytest.fixture
def pci_dss_policy() -> PciPolicyAware:
    """A PCI-DSS-compliant payment-card masking policy."""
    return PciPolicyAware(
        compliance=Compliance.PCI_DSS,
        detection_hints=("card_token",),
        placeholder="[PCI]",
    )


@pytest.fixture
def api_secret_policy() -> SecretPolicyAware:
    """A credential-masking policy for API secrets."""
    return SecretPolicyAware(
        compliance=Compliance.NONE,
        detection_hints=("api_key", "token"),
        placeholder="[SECRET]",
    )


@pytest.fixture
def tagged_class() -> type[Any]:
    """A frozen dataclass with sensitivity-tagged fields."""

    @dataclass(frozen=True, slots=True)
    class User:
        id: int
        ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})
        email: str = field(metadata={"sensitivity": Sensitivity.PII})

    return User


@pytest.fixture
def multi_tagged_class() -> type[Any]:
    """A frozen dataclass with multiple sensitivity classes."""

    @dataclass(frozen=True, slots=True)
    class Payment:
        transaction_id: int
        name: str = field(metadata={"sensitivity": Sensitivity.PII})
        ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})
        card_token: str = field(metadata={"sensitivity": Sensitivity.PCI})
        api_key: str = field(metadata={"sensitivity": Sensitivity.SECRET})

    return Payment


@pytest.fixture
def untagged_class() -> type[Any]:
    """A frozen dataclass with no sensitivity-tagged fields."""

    @dataclass(frozen=True, slots=True)
    class Product:
        id: int
        title: str
        price: float = 0.0

    return Product


@pytest.fixture
def mixed_class() -> type[Any]:
    """A frozen dataclass with some tagged and some untagged fields."""

    @dataclass(frozen=True, slots=True)
    class Account:
        account_id: int
        username: str
        email: str = field(metadata={"sensitivity": Sensitivity.PII})
        ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})
        created_at: str = ""

    return Account


@pytest.fixture
def non_dataclass() -> type[Any]:
    """A non-dataclass that should fail @sensitive decorator."""

    class RegularClass:
        def __init__(self, value: str) -> None:
            self.value = value

    return RegularClass


@pytest.fixture
def tagged_instance(tagged_class: type[Any]) -> Any:
    """An instance of a tagged dataclass."""
    return tagged_class(id=1, ssn="123-45-6789", email="user@example.com")


@pytest.fixture
def multi_tagged_instance(multi_tagged_class: type[Any]) -> Any:
    """An instance of a multi-tagged dataclass."""
    return multi_tagged_class(
        transaction_id=999,
        name="John Doe",
        ssn="987-65-4321",
        card_token="tok_abc123",
        api_key="sk_live_xyz789",
    )


@pytest.fixture
def mixed_instance(mixed_class: type[Any]) -> Any:
    """An instance of a mixed tagged/untagged dataclass."""
    return mixed_class(
        account_id=42,
        username="jdoe",
        email="john@example.com",
        ssn="111-22-3333",
        created_at="2026-01-01",
    )
