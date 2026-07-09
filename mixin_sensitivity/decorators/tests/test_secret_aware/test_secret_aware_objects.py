"""Tests for SecretPolicyAware masking policy value object."""

from __future__ import annotations

import pytest

from mixin_sensitivity.decorators.classes.compliance import Compliance
from mixin_sensitivity.decorators.classes.secret_aware.secret_aware_objects import (
    SecretPolicyAware,
)


class TestSecretPolicyConstruction:
    """Tests for SecretPolicyAware instantiation and properties."""

    def test_construct_with_all_fields(self) -> None:
        """SecretPolicyAware can be constructed with compliance, hints, and placeholder."""
        policy = SecretPolicyAware(
            compliance=Compliance.NONE,
            detection_hints=("api_key", "token"),
            placeholder="[REDACTED]",
        )
        assert policy.compliance == Compliance.NONE
        assert policy.detection_hints == ("api_key", "token")
        assert policy.placeholder == "[REDACTED]"

    def test_construct_with_empty_hints(self) -> None:
        """SecretPolicyAware can be constructed with empty detection_hints."""
        policy = SecretPolicyAware(
            compliance=Compliance.NONE,
            detection_hints=(),
            placeholder="***",
        )
        assert policy.detection_hints == ()

    def test_construct_with_many_hints(self) -> None:
        """SecretPolicyAware can be constructed with multiple detection hints."""
        hints = (
            "api_key",
            "api_secret",
            "token",
            "password",
            "private_key",
            "secret",
        )
        policy = SecretPolicyAware(
            compliance=Compliance.NONE,
            detection_hints=hints,
            placeholder="[X]",
        )
        assert len(policy.detection_hints) == 6


class TestMask:
    """Tests for the mask() method."""

    def test_mask_returns_placeholder_ignoring_input(
        self, api_secret_policy: SecretPolicyAware
    ) -> None:
        """mask() always returns the placeholder, regardless of input."""
        assert api_secret_policy.mask("sk_live_abc123def456") == "[SECRET REDACTED]"
        assert api_secret_policy.mask("super_secret_token_12345") == "[SECRET REDACTED]"
        assert api_secret_policy.mask("") == "[SECRET REDACTED]"

    def test_mask_returns_correct_placeholder(
        self, database_secret_policy: SecretPolicyAware
    ) -> None:
        """mask() returns the specific placeholder configured for the policy."""
        assert (
            database_secret_policy.mask("postgres://user:pass@host") == "***HIDDEN***"
        )

    def test_mask_with_empty_hints_still_returns_placeholder(
        self, empty_hints_secret_policy: SecretPolicyAware
    ) -> None:
        """mask() returns placeholder even when detection_hints is empty."""
        assert empty_hints_secret_policy.mask("secret") == "[REDACTED]"


class TestLooksSensitive:
    """Tests for the looks_sensitive() method."""

    def test_looks_sensitive_exact_match_case_insensitive(
        self, api_secret_policy: SecretPolicyAware
    ) -> None:
        """looks_sensitive returns True for exact case-insensitive hint match."""
        assert api_secret_policy.looks_sensitive("api_key") is True
        assert api_secret_policy.looks_sensitive("API_KEY") is True
        assert api_secret_policy.looks_sensitive("Api_Key") is True
        assert api_secret_policy.looks_sensitive("token") is True
        assert api_secret_policy.looks_sensitive("TOKEN") is True

    def test_looks_sensitive_substring_match(
        self, api_secret_policy: SecretPolicyAware
    ) -> None:
        """looks_sensitive returns True for substring containing a hint."""
        assert api_secret_policy.looks_sensitive("user_api_key") is True
        assert api_secret_policy.looks_sensitive("api_key_hash") is True
        assert api_secret_policy.looks_sensitive("access_token") is True
        assert api_secret_policy.looks_sensitive("oauth_password") is True

    def test_looks_sensitive_miss_returns_false(
        self, api_secret_policy: SecretPolicyAware
    ) -> None:
        """looks_sensitive returns False when field_name matches no hint."""
        assert api_secret_policy.looks_sensitive("username") is False
        assert api_secret_policy.looks_sensitive("endpoint") is False
        assert api_secret_policy.looks_sensitive("retry_count") is False

    def test_looks_sensitive_multiple_hints_any_match(
        self, database_secret_policy: SecretPolicyAware
    ) -> None:
        """looks_sensitive returns True if any hint matches the field name."""
        assert database_secret_policy.looks_sensitive("db_password_encrypted") is True
        assert database_secret_policy.looks_sensitive("connection_string_uri") is True
        assert database_secret_policy.looks_sensitive("aws_private_key") is True

    def test_looks_sensitive_empty_hints_all_false(
        self, empty_hints_secret_policy: SecretPolicyAware
    ) -> None:
        """looks_sensitive returns False for all fields when hints are empty."""
        assert empty_hints_secret_policy.looks_sensitive("api_key") is False
        assert empty_hints_secret_policy.looks_sensitive("password") is False
        assert empty_hints_secret_policy.looks_sensitive("anything") is False


class TestSecretPolicyFrozen:
    """Tests for SecretPolicyAware immutability."""

    def test_secret_policy_is_immutable(
        self, api_secret_policy: SecretPolicyAware
    ) -> None:
        """SecretPolicyAware instances cannot be mutated."""
        with pytest.raises(AttributeError):
            api_secret_policy.placeholder = "modified"  # type: ignore[misc]

    def test_secret_policy_hashable(self, api_secret_policy: SecretPolicyAware) -> None:
        """SecretPolicyAware instances are hashable."""
        h = hash(api_secret_policy)
        assert isinstance(h, int)

    def test_two_identical_secret_policies_are_equal(self) -> None:
        """Two SECRET policies with same values are equal."""
        p1 = SecretPolicyAware(
            compliance=Compliance.NONE,
            detection_hints=("api_key",),
            placeholder="[X]",
        )
        p2 = SecretPolicyAware(
            compliance=Compliance.NONE,
            detection_hints=("api_key",),
            placeholder="[X]",
        )
        assert p1 == p2
