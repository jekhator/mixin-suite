"""Tests for PiiPolicyAware masking policy value object."""

from __future__ import annotations

import pytest

from mixin_sensitivity.decorators.classes.compliance import Compliance
from mixin_sensitivity.decorators.classes.pii_aware.pii_aware_objects import (
    PiiPolicyAware,
)


class TestPiiPolicyConstruction:
    """Tests for PiiPolicyAware instantiation and properties."""

    def test_construct_with_all_fields(self) -> None:
        """PiiPolicyAware can be constructed with compliance, hints, and placeholder."""
        policy = PiiPolicyAware(
            compliance=Compliance.GDPR,
            detection_hints=("email", "phone"),
            placeholder="[REDACTED]",
        )
        assert policy.compliance == Compliance.GDPR
        assert policy.detection_hints == ("email", "phone")
        assert policy.placeholder == "[REDACTED]"

    def test_construct_with_empty_hints(self) -> None:
        """PiiPolicyAware can be constructed with empty detection_hints."""
        policy = PiiPolicyAware(
            compliance=Compliance.GDPR,
            detection_hints=(),
            placeholder="***",
        )
        assert policy.detection_hints == ()

    def test_construct_with_many_hints(self) -> None:
        """PiiPolicyAware can be constructed with multiple detection hints."""
        hints = ("email", "phone", "ssn", "address", "zip", "dob")
        policy = PiiPolicyAware(
            compliance=Compliance.GDPR,
            detection_hints=hints,
            placeholder="[X]",
        )
        assert len(policy.detection_hints) == 6
        assert policy.detection_hints == hints


class TestMask:
    """Tests for the mask() method."""

    def test_mask_returns_placeholder_ignoring_input(
        self, gdpr_pii_policy: PiiPolicyAware
    ) -> None:
        """mask() always returns the placeholder, regardless of input."""
        assert gdpr_pii_policy.mask("john@example.com") == "[PII REDACTED]"
        assert gdpr_pii_policy.mask("555-1234") == "[PII REDACTED]"
        assert gdpr_pii_policy.mask("") == "[PII REDACTED]"

    def test_mask_returns_correct_placeholder(
        self, generic_pii_policy: PiiPolicyAware
    ) -> None:
        """mask() returns the specific placeholder configured for the policy."""
        assert generic_pii_policy.mask("any-value") == "***"

    def test_mask_with_empty_hints_still_returns_placeholder(
        self, empty_hints_pii_policy: PiiPolicyAware
    ) -> None:
        """mask() returns placeholder even when detection_hints is empty."""
        assert empty_hints_pii_policy.mask("sensitive") == "[MASKED]"


class TestLooksSensitive:
    """Tests for the looks_sensitive() method."""

    def test_looks_sensitive_exact_match_case_insensitive(
        self, gdpr_pii_policy: PiiPolicyAware
    ) -> None:
        """looks_sensitive returns True for exact case-insensitive hint match."""
        assert gdpr_pii_policy.looks_sensitive("email") is True
        assert gdpr_pii_policy.looks_sensitive("EMAIL") is True
        assert gdpr_pii_policy.looks_sensitive("Email") is True
        assert gdpr_pii_policy.looks_sensitive("phone") is True
        assert gdpr_pii_policy.looks_sensitive("PHONE") is True

    def test_looks_sensitive_substring_match(
        self, gdpr_pii_policy: PiiPolicyAware
    ) -> None:
        """looks_sensitive returns True for substring containing a hint."""
        assert gdpr_pii_policy.looks_sensitive("user_email") is True
        assert gdpr_pii_policy.looks_sensitive("email_address") is True
        assert gdpr_pii_policy.looks_sensitive("primary_phone") is True
        assert gdpr_pii_policy.looks_sensitive("person_name_full") is True

    def test_looks_sensitive_miss_returns_false(
        self, gdpr_pii_policy: PiiPolicyAware
    ) -> None:
        """looks_sensitive returns False when field_name matches no hint."""
        assert gdpr_pii_policy.looks_sensitive("age") is False
        assert gdpr_pii_policy.looks_sensitive("account_id") is False
        assert gdpr_pii_policy.looks_sensitive("created_at") is False

    def test_looks_sensitive_multiple_hints_any_match(
        self, generic_pii_policy: PiiPolicyAware
    ) -> None:
        """looks_sensitive returns True if any hint matches the field name."""
        assert generic_pii_policy.looks_sensitive("street_address") is True
        assert generic_pii_policy.looks_sensitive("zip_code_value") is True
        assert generic_pii_policy.looks_sensitive("credit_card_last_four") is True

    def test_looks_sensitive_empty_hints_all_false(
        self, empty_hints_pii_policy: PiiPolicyAware
    ) -> None:
        """looks_sensitive returns False for all fields when hints are empty."""
        assert empty_hints_pii_policy.looks_sensitive("email") is False
        assert empty_hints_pii_policy.looks_sensitive("phone") is False
        assert empty_hints_pii_policy.looks_sensitive("anything") is False

    def test_looks_sensitive_no_false_positives_on_partial(
        self, gdpr_pii_policy: PiiPolicyAware
    ) -> None:
        """looks_sensitive does not match partial substrings of hints."""
        assert gdpr_pii_policy.looks_sensitive("emai_field") is False
        assert gdpr_pii_policy.looks_sensitive("ail_address") is False


class TestPiiPolicyFrozen:
    """Tests for PiiPolicyAware immutability."""

    def test_pii_policy_is_immutable(self, gdpr_pii_policy: PiiPolicyAware) -> None:
        """PiiPolicyAware instances cannot be mutated."""
        with pytest.raises(AttributeError):
            gdpr_pii_policy.placeholder = "modified"  # type: ignore[misc]

    def test_pii_policy_hashable(self, gdpr_pii_policy: PiiPolicyAware) -> None:
        """PiiPolicyAware instances are hashable."""
        h = hash(gdpr_pii_policy)
        assert isinstance(h, int)

    def test_two_identical_pii_policies_are_equal(self) -> None:
        """Two PII policies with same values are equal."""
        p1 = PiiPolicyAware(
            compliance=Compliance.GDPR,
            detection_hints=("email",),
            placeholder="[X]",
        )
        p2 = PiiPolicyAware(
            compliance=Compliance.GDPR,
            detection_hints=("email",),
            placeholder="[X]",
        )
        assert p1 == p2
