"""Tests for PciPolicyAware masking policy value object."""

from __future__ import annotations

import pytest

from mixin_sensitivity.decorators.classes.compliance import Compliance
from mixin_sensitivity.decorators.classes.pci_aware.pci_aware_objects import (
    PciPolicyAware,
)


class TestPciPolicyConstruction:
    """Tests for PciPolicyAware instantiation and properties."""

    def test_construct_with_all_fields(self) -> None:
        """PciPolicyAware can be constructed with compliance, hints, and placeholder."""
        policy = PciPolicyAware(
            compliance=Compliance.PCI_DSS,
            detection_hints=("card_token", "card_number"),
            placeholder="[REDACTED]",
        )
        assert policy.compliance == Compliance.PCI_DSS
        assert policy.detection_hints == ("card_token", "card_number")
        assert policy.placeholder == "[REDACTED]"

    def test_construct_with_empty_hints(self) -> None:
        """PciPolicyAware can be constructed with empty detection_hints."""
        policy = PciPolicyAware(
            compliance=Compliance.PCI_DSS,
            detection_hints=(),
            placeholder="****",
        )
        assert policy.detection_hints == ()

    def test_construct_with_many_hints(self) -> None:
        """PciPolicyAware can be constructed with multiple detection hints."""
        hints = ("card_token", "card_number", "cvv", "pan", "expiry")
        policy = PciPolicyAware(
            compliance=Compliance.PCI_DSS,
            detection_hints=hints,
            placeholder="[X]",
        )
        assert len(policy.detection_hints) == 5


class TestMask:
    """Tests for the mask() method."""

    def test_mask_returns_placeholder_ignoring_input(
        self, pci_dss_policy: PciPolicyAware
    ) -> None:
        """mask() always returns the placeholder, regardless of input."""
        assert pci_dss_policy.mask("4532015112830366") == "[PCI REDACTED]"
        assert pci_dss_policy.mask("378282246310005") == "[PCI REDACTED]"
        assert pci_dss_policy.mask("") == "[PCI REDACTED]"

    def test_mask_returns_correct_placeholder(
        self, generic_pci_policy: PciPolicyAware
    ) -> None:
        """mask() returns the specific placeholder configured for the policy."""
        assert generic_pci_policy.mask("token123") == "****"

    def test_mask_with_empty_hints_still_returns_placeholder(
        self, empty_hints_pci_policy: PciPolicyAware
    ) -> None:
        """mask() returns placeholder even when detection_hints is empty."""
        assert empty_hints_pci_policy.mask("sensitive") == "[CARD_REDACTED]"


class TestLooksSensitive:
    """Tests for the looks_sensitive() method."""

    def test_looks_sensitive_exact_match_case_insensitive(
        self, pci_dss_policy: PciPolicyAware
    ) -> None:
        """looks_sensitive returns True for exact case-insensitive hint match."""
        assert pci_dss_policy.looks_sensitive("card_token") is True
        assert pci_dss_policy.looks_sensitive("CARD_TOKEN") is True
        assert pci_dss_policy.looks_sensitive("Card_Token") is True
        assert pci_dss_policy.looks_sensitive("cvv") is True
        assert pci_dss_policy.looks_sensitive("CVV") is True

    def test_looks_sensitive_substring_match(
        self, pci_dss_policy: PciPolicyAware
    ) -> None:
        """looks_sensitive returns True for substring containing a hint."""
        assert pci_dss_policy.looks_sensitive("user_card_token") is True
        assert pci_dss_policy.looks_sensitive("card_token_hash") is True
        assert pci_dss_policy.looks_sensitive("encrypted_card_number") is True
        assert pci_dss_policy.looks_sensitive("pan_value") is True

    def test_looks_sensitive_miss_returns_false(
        self, pci_dss_policy: PciPolicyAware
    ) -> None:
        """looks_sensitive returns False when field_name matches no hint."""
        assert pci_dss_policy.looks_sensitive("amount") is False
        assert pci_dss_policy.looks_sensitive("merchant_id") is False
        assert pci_dss_policy.looks_sensitive("transaction_id") is False

    def test_looks_sensitive_multiple_hints_any_match(
        self, generic_pci_policy: PciPolicyAware
    ) -> None:
        """looks_sensitive returns True if any hint matches the field name."""
        assert generic_pci_policy.looks_sensitive("payment_token_encrypted") is True
        assert generic_pci_policy.looks_sensitive("card_data_blob") is True

    def test_looks_sensitive_empty_hints_all_false(
        self, empty_hints_pci_policy: PciPolicyAware
    ) -> None:
        """looks_sensitive returns False for all fields when hints are empty."""
        assert empty_hints_pci_policy.looks_sensitive("card_token") is False
        assert empty_hints_pci_policy.looks_sensitive("cvv") is False
        assert empty_hints_pci_policy.looks_sensitive("anything") is False


class TestPciPolicyFrozen:
    """Tests for PciPolicyAware immutability."""

    def test_pci_policy_is_immutable(self, pci_dss_policy: PciPolicyAware) -> None:
        """PciPolicyAware instances cannot be mutated."""
        with pytest.raises(AttributeError):
            pci_dss_policy.placeholder = "modified"  # type: ignore[misc]

    def test_pci_policy_hashable(self, pci_dss_policy: PciPolicyAware) -> None:
        """PciPolicyAware instances are hashable."""
        h = hash(pci_dss_policy)
        assert isinstance(h, int)

    def test_two_identical_pci_policies_are_equal(self) -> None:
        """Two PCI policies with same values are equal."""
        p1 = PciPolicyAware(
            compliance=Compliance.PCI_DSS,
            detection_hints=("card_token",),
            placeholder="[X]",
        )
        p2 = PciPolicyAware(
            compliance=Compliance.PCI_DSS,
            detection_hints=("card_token",),
            placeholder="[X]",
        )
        assert p1 == p2
