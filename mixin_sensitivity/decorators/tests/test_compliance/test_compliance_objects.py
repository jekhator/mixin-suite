"""Tests for Compliance StrEnum and ClassMakerAware protocol."""

from __future__ import annotations

import pytest

from mixin_sensitivity.decorators.classes.compliance import Compliance
from mixin_sensitivity.decorators.classes.phi_aware.phi_aware_objects import (
    PhiPolicyAware,
)


class TestCompliance:
    """Tests for the Compliance regulatory regime StrEnum."""

    def test_has_four_members(self) -> None:
        """Compliance has exactly HIPAA, GDPR, PCI_DSS, NONE."""
        assert len(Compliance) == 4

    def test_hipaa_member_exists_with_value_hipaa(self) -> None:
        """HIPAA member has value 'hipaa'."""
        assert Compliance.HIPAA == "hipaa"
        assert Compliance.HIPAA.value == "hipaa"

    def test_gdpr_member_exists_with_value_gdpr(self) -> None:
        """GDPR member has value 'gdpr'."""
        assert Compliance.GDPR == "gdpr"
        assert Compliance.GDPR.value == "gdpr"

    def test_pci_dss_member_exists_with_value_pci_dss(self) -> None:
        """PCI_DSS member has value 'pci-dss'."""
        assert Compliance.PCI_DSS == "pci-dss"
        assert Compliance.PCI_DSS.value == "pci-dss"

    def test_none_member_exists_with_value_none(self) -> None:
        """NONE member has value 'none'."""
        assert Compliance.NONE == "none"
        assert Compliance.NONE.value == "none"

    def test_is_str_enum(self) -> None:
        """Compliance members are strings."""
        assert isinstance(Compliance.HIPAA, str)
        assert Compliance.HIPAA in {"hipaa", "gdpr"}


class TestClassMakerAwareProtocol:
    """Tests for ClassMakerAware protocol contract satisfaction."""

    def test_protocol_satisfied_by_phi_policy_aware(self) -> None:
        """PhiPolicyAware satisfies ClassMakerAware structurally."""
        policy = PhiPolicyAware(
            compliance=Compliance.HIPAA,
            detection_hints=("ssn", "medical_id"),
            placeholder="[REDACTED]",
        )
        assert callable(policy.mask)
        assert callable(policy.looks_sensitive)
        assert isinstance(policy.mask("123456789"), str)
        assert isinstance(policy.looks_sensitive("ssn"), bool)

    def test_protocol_methods_are_callable(self) -> None:
        """ClassMakerAware.mask and looks_sensitive are callable."""
        policy = PhiPolicyAware(
            compliance=Compliance.GDPR,
            detection_hints=("email", "phone"),
            placeholder="***",
        )
        assert hasattr(policy, "mask")
        assert hasattr(policy, "looks_sensitive")

    def test_policy_frozen_immutable(self) -> None:
        """Policy instances are frozen and immutable."""
        policy = PhiPolicyAware(
            compliance=Compliance.HIPAA,
            detection_hints=("field",),
            placeholder="[X]",
        )
        with pytest.raises(AttributeError):
            policy.placeholder = "modified"  # type: ignore[misc]
