"""Tests for PhiPolicyAware masking policy value object."""

from __future__ import annotations

import pytest

from mixin_sensitivity.decorators.classes.compliance import Compliance
from mixin_sensitivity.decorators.classes.phi_aware.phi_aware_objects import (
    PhiPolicyAware,
)


class TestPhiPolicyConstruction:
    """Tests for PhiPolicyAware instantiation and properties."""

    def test_construct_with_all_fields(self) -> None:
        """PhiPolicyAware can be constructed with compliance, hints, and placeholder."""
        policy = PhiPolicyAware(
            compliance=Compliance.HIPAA,
            detection_hints=("ssn", "mrn"),
            placeholder="[REDACTED]",
        )
        assert policy.compliance == Compliance.HIPAA
        assert policy.detection_hints == ("ssn", "mrn")
        assert policy.placeholder == "[REDACTED]"

    def test_construct_with_empty_hints(self) -> None:
        """PhiPolicyAware can be constructed with empty detection_hints."""
        policy = PhiPolicyAware(
            compliance=Compliance.GDPR,
            detection_hints=(),
            placeholder="***",
        )
        assert policy.detection_hints == ()

    def test_construct_with_single_hint(self) -> None:
        """PhiPolicyAware can be constructed with a single detection hint."""
        policy = PhiPolicyAware(
            compliance=Compliance.HIPAA,
            detection_hints=("ssn",),
            placeholder="[X]",
        )
        assert len(policy.detection_hints) == 1
        assert policy.detection_hints[0] == "ssn"


class TestMask:
    """Tests for the mask() method."""

    def test_mask_returns_placeholder_ignoring_input(
        self, hipaa_phi_policy: PhiPolicyAware
    ) -> None:
        """mask() always returns the placeholder, regardless of input."""
        assert hipaa_phi_policy.mask("123456789") == "[PHI REDACTED]"
        assert hipaa_phi_policy.mask("anything") == "[PHI REDACTED]"
        assert hipaa_phi_policy.mask("") == "[PHI REDACTED]"
        assert hipaa_phi_policy.mask("long sensitive value here") == "[PHI REDACTED]"

    def test_mask_returns_correct_placeholder(
        self, gdpr_phi_policy: PhiPolicyAware
    ) -> None:
        """mask() returns the specific placeholder configured for the policy."""
        assert gdpr_phi_policy.mask("value") == "[SANITIZED]"

    def test_mask_with_empty_hints_still_returns_placeholder(
        self, empty_hints_phi_policy: PhiPolicyAware
    ) -> None:
        """mask() returns placeholder even when detection_hints is empty."""
        assert empty_hints_phi_policy.mask("anything") == "***"


class TestLooksSensitive:
    """Tests for the looks_sensitive() method."""

    def test_looks_sensitive_exact_match_lower_case(
        self, hipaa_phi_policy: PhiPolicyAware
    ) -> None:
        """looks_sensitive returns True for exact case-insensitive hint match."""
        assert hipaa_phi_policy.looks_sensitive("ssn") is True
        assert hipaa_phi_policy.looks_sensitive("SSN") is True
        assert hipaa_phi_policy.looks_sensitive("Ssn") is True

    def test_looks_sensitive_substring_match(
        self, hipaa_phi_policy: PhiPolicyAware
    ) -> None:
        """looks_sensitive returns True for substring containing a hint."""
        assert hipaa_phi_policy.looks_sensitive("patient_ssn") is True
        assert hipaa_phi_policy.looks_sensitive("ssn_value") is True
        assert hipaa_phi_policy.looks_sensitive("user_mrn_field") is True
        assert hipaa_phi_policy.looks_sensitive("MRN_ENCRYPTED") is True

    def test_looks_sensitive_miss_returns_false(
        self, hipaa_phi_policy: PhiPolicyAware
    ) -> None:
        """looks_sensitive returns False when field_name matches no hint."""
        assert hipaa_phi_policy.looks_sensitive("name") is False
        assert hipaa_phi_policy.looks_sensitive("email") is False
        assert hipaa_phi_policy.looks_sensitive("age") is False

    def test_looks_sensitive_multiple_hints_any_match(
        self, hipaa_phi_policy: PhiPolicyAware
    ) -> None:
        """looks_sensitive returns True if any hint matches the field name."""
        assert hipaa_phi_policy.looks_sensitive("mrn_field") is True
        assert hipaa_phi_policy.looks_sensitive("patient_id_token") is True
        assert hipaa_phi_policy.looks_sensitive("medical_id_legacy") is True

    def test_looks_sensitive_empty_hints_all_false(
        self, empty_hints_phi_policy: PhiPolicyAware
    ) -> None:
        """looks_sensitive returns False for all fields when hints are empty."""
        assert empty_hints_phi_policy.looks_sensitive("ssn") is False
        assert empty_hints_phi_policy.looks_sensitive("mrn") is False
        assert empty_hints_phi_policy.looks_sensitive("anything") is False

    def test_looks_sensitive_case_insensitive_field_and_hint(
        self, hipaa_phi_policy: PhiPolicyAware
    ) -> None:
        """looks_sensitive is case-insensitive for both field name and hints."""
        # hint="ssn", field="SSN_VALUE" -> lowered both -> matches
        assert hipaa_phi_policy.looks_sensitive("SSN_VALUE") is True
        assert hipaa_phi_policy.looks_sensitive("MrN_number") is True
        assert hipaa_phi_policy.looks_sensitive("PATIENT_ID_HASH") is True

    def test_looks_sensitive_partial_substring_no_match(
        self, hipaa_phi_policy: PhiPolicyAware
    ) -> None:
        """looks_sensitive returns False for partial matches that don't overlap."""
        assert hipaa_phi_policy.looks_sensitive("ss_number") is False
        assert hipaa_phi_policy.looks_sensitive("mr_field") is False


class TestPhiPolicyFrozen:
    """Tests for PhiPolicyAware immutability."""

    def test_phi_policy_is_immutable(self, hipaa_phi_policy: PhiPolicyAware) -> None:
        """PhiPolicyAware instances cannot be mutated."""
        with pytest.raises(AttributeError):
            hipaa_phi_policy.placeholder = "modified"  # type: ignore[misc]

    def test_phi_policy_hashable(self, hipaa_phi_policy: PhiPolicyAware) -> None:
        """PhiPolicyAware instances are hashable."""
        h = hash(hipaa_phi_policy)
        assert isinstance(h, int)

    def test_two_identical_phi_policies_are_equal(self) -> None:
        """Two PHI policies with same values are equal."""
        p1 = PhiPolicyAware(
            compliance=Compliance.HIPAA,
            detection_hints=("ssn",),
            placeholder="[X]",
        )
        p2 = PhiPolicyAware(
            compliance=Compliance.HIPAA,
            detection_hints=("ssn",),
            placeholder="[X]",
        )
        assert p1 == p2
