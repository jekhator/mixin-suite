"""Tests for SensitiveFieldSet value object and masking logic."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

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
from mixin_sensitivity.decorators.sensitive.sensitive_objects import SensitiveFieldSet
from mixin_sensitivity.services.classify.classify_objects import Sensitivity


class TestFromDataclass:
    """Tests for SensitiveFieldSet.from_dataclass() classmethod."""

    def test_from_dataclass_builds_field_set_from_tagged_class(
        self, tagged_class: type[Any]
    ) -> None:
        """from_dataclass builds SensitiveFieldSet from a tagged dataclass."""
        field_set = SensitiveFieldSet.from_dataclass(tagged_class)
        assert isinstance(field_set, SensitiveFieldSet)
        assert field_set.profile.is_empty is False

    def test_from_dataclass_empty_for_untagged_class(
        self, untagged_class: type[Any]
    ) -> None:
        """from_dataclass builds empty SensitiveFieldSet for untagged dataclass."""
        field_set = SensitiveFieldSet.from_dataclass(untagged_class)
        assert isinstance(field_set, SensitiveFieldSet)
        assert field_set.is_empty is True

    def test_from_dataclass_partial_tags(self, mixed_class: type[Any]) -> None:
        """from_dataclass handles mixed tagged and untagged fields."""
        field_set = SensitiveFieldSet.from_dataclass(mixed_class)
        assert field_set.is_empty is False
        assert field_set.profile.sensitivity_of("email") == Sensitivity.PII
        assert field_set.profile.sensitivity_of("ssn") == Sensitivity.PHI
        assert field_set.profile.sensitivity_of("username") is None
        assert field_set.profile.sensitivity_of("account_id") is None


class TestIsEmpty:
    """Tests for SensitiveFieldSet.is_empty property."""

    def test_is_empty_true_for_untagged_class(self, untagged_class: type[Any]) -> None:
        """is_empty returns True when no fields are tagged."""
        field_set = SensitiveFieldSet.from_dataclass(untagged_class)
        assert field_set.is_empty is True

    def test_is_empty_false_for_tagged_class(self, tagged_class: type[Any]) -> None:
        """is_empty returns False when any field is tagged."""
        field_set = SensitiveFieldSet.from_dataclass(tagged_class)
        assert field_set.is_empty is False

    def test_is_empty_false_for_mixed_class(self, mixed_class: type[Any]) -> None:
        """is_empty returns False when any field is tagged, even if some are not."""
        field_set = SensitiveFieldSet.from_dataclass(mixed_class)
        assert field_set.is_empty is False


class TestMaskedReprUntagged:
    """Tests for masked_repr with untagged instances (no policies needed)."""

    def test_untagged_instance_default_repr(self, untagged_class: type[Any]) -> None:
        """masked_repr on untagged instance shows all values normally."""
        field_set = SensitiveFieldSet.from_dataclass(untagged_class)
        instance = untagged_class(id=1, title="Widget", price=19.99)
        repr_str = field_set.masked_repr(instance)
        assert "id=1" in repr_str
        assert "title='Widget'" in repr_str
        assert "price=19.99" in repr_str
        assert "Product(" in repr_str

    def test_untagged_instance_with_policies_ignored(
        self, untagged_class: type[Any], hipaa_phi_policy: PhiPolicyAware
    ) -> None:
        """masked_repr ignores policies when instance has no tagged fields."""
        field_set = SensitiveFieldSet.from_dataclass(untagged_class)
        instance = untagged_class(id=42, title="Book")
        policies = {Sensitivity.PHI: hipaa_phi_policy}
        repr_str = field_set.masked_repr(instance, policies=policies)
        assert "id=42" in repr_str
        assert "title='Book'" in repr_str


class TestMaskedReprWithoutPolicies:
    """Tests for masked_repr with tagged fields but no policies (fallback to ***)."""

    def test_tagged_field_without_policy_shows_stars(
        self, tagged_class: type[Any]
    ) -> None:
        """masked_repr shows *** for tagged fields when no policy provided."""
        field_set = SensitiveFieldSet.from_dataclass(tagged_class)
        instance = tagged_class(id=1, ssn="123-45-6789", email="user@example.com")
        repr_str = field_set.masked_repr(instance, policies=None)
        assert "id=1" in repr_str
        assert "ssn=***" in repr_str
        assert "email=***" in repr_str
        assert "123-45-6789" not in repr_str
        assert "user@example.com" not in repr_str

    def test_mixed_tagged_untagged_without_policy(self, mixed_class: type[Any]) -> None:
        """masked_repr shows values for untagged, *** for tagged when no policies."""
        field_set = SensitiveFieldSet.from_dataclass(mixed_class)
        instance = mixed_class(
            account_id=10,
            username="alice",
            email="alice@example.com",
            ssn="999-88-7777",
            created_at="2026-01-01",
        )
        repr_str = field_set.masked_repr(instance, policies=None)
        assert "account_id=10" in repr_str
        assert "username='alice'" in repr_str
        assert "created_at='2026-01-01'" in repr_str
        assert "email=***" in repr_str
        assert "ssn=***" in repr_str
        assert "alice@example.com" not in repr_str
        assert "999-88-7777" not in repr_str


class TestMaskedReprWithPolicies:
    """Tests for masked_repr with matching policies."""

    def test_tagged_field_with_matching_policy(
        self,
        tagged_class: type[Any],
        hipaa_phi_policy: PhiPolicyAware,
        gdpr_pii_policy: PiiPolicyAware,
    ) -> None:
        """masked_repr applies policy.mask() for tagged fields with policies."""
        field_set = SensitiveFieldSet.from_dataclass(tagged_class)
        instance = tagged_class(id=1, ssn="123-45-6789", email="user@example.com")
        policies: Mapping[Sensitivity, PhiPolicyAware | PiiPolicyAware] = {
            Sensitivity.PHI: hipaa_phi_policy,
            Sensitivity.PII: gdpr_pii_policy,
        }
        repr_str = field_set.masked_repr(instance, policies=policies)
        assert "id=1" in repr_str
        assert "ssn=[PHI]" in repr_str
        assert "email=[PII]" in repr_str
        assert "123-45-6789" not in repr_str
        assert "user@example.com" not in repr_str

    def test_partial_policy_coverage(
        self, tagged_class: type[Any], hipaa_phi_policy: PhiPolicyAware
    ) -> None:
        """masked_repr uses policy when available, *** when not."""
        field_set = SensitiveFieldSet.from_dataclass(tagged_class)
        instance = tagged_class(id=2, ssn="456-78-9012", email="bob@example.com")
        policies = {Sensitivity.PHI: hipaa_phi_policy}  # only PHI, no PII
        repr_str = field_set.masked_repr(instance, policies=policies)
        assert "id=2" in repr_str
        assert "ssn=[PHI]" in repr_str
        assert "email=***" in repr_str

    def test_all_four_sensitivity_classes_with_policies(
        self,
        multi_tagged_class: type[Any],
        hipaa_phi_policy: PhiPolicyAware,
        gdpr_pii_policy: PiiPolicyAware,
        pci_dss_policy: PciPolicyAware,
        api_secret_policy: SecretPolicyAware,
    ) -> None:
        """masked_repr correctly masks all four sensitivity classes."""
        field_set = SensitiveFieldSet.from_dataclass(multi_tagged_class)
        instance = multi_tagged_class(
            transaction_id=555,
            name="Jane Smith",
            ssn="111-22-3333",
            card_token="tok_live_abc123",
            api_key="sk_prod_xyz789",
        )
        policies: Mapping[
            Sensitivity,
            PhiPolicyAware | PiiPolicyAware | PciPolicyAware | SecretPolicyAware,
        ] = {
            Sensitivity.PHI: hipaa_phi_policy,
            Sensitivity.PII: gdpr_pii_policy,
            Sensitivity.PCI: pci_dss_policy,
            Sensitivity.SECRET: api_secret_policy,
        }
        repr_str = field_set.masked_repr(instance, policies=policies)
        assert "transaction_id=555" in repr_str
        assert "name=[PII]" in repr_str
        assert "ssn=[PHI]" in repr_str
        assert "card_token=[PCI]" in repr_str
        assert "api_key=[SECRET]" in repr_str
        assert "Jane Smith" not in repr_str
        assert "111-22-3333" not in repr_str
        assert "tok_live_abc123" not in repr_str
        assert "sk_prod_xyz789" not in repr_str


class TestMaskedReprNoneAndIntValues:
    """Tests for masked_repr handling of non-string field values."""

    def test_int_field_converted_to_str(self) -> None:
        """masked_repr calls str() on int values before masking."""

        @dataclass(frozen=True, slots=True)
        class Record:
            id: int
            ssn: int = field(metadata={"sensitivity": Sensitivity.PHI})

        field_set = SensitiveFieldSet.from_dataclass(Record)
        instance = Record(id=1, ssn=123456789)
        policy = PhiPolicyAware(
            compliance=Compliance.HIPAA,
            detection_hints=("ssn",),
            placeholder="[X]",
        )
        repr_str = field_set.masked_repr(instance, policies={Sensitivity.PHI: policy})
        assert "id=1" in repr_str
        assert "ssn=[X]" in repr_str
        assert "123456789" not in repr_str

    def test_untagged_int_field_shown_as_number(self) -> None:
        """masked_repr shows untagged int as int, not quoted."""

        @dataclass(frozen=True, slots=True)
        class Transaction:
            amount: int
            token: str = field(metadata={"sensitivity": Sensitivity.SECRET})

        field_set = SensitiveFieldSet.from_dataclass(Transaction)
        instance = Transaction(amount=9999, token="secret_xyz")
        repr_str = field_set.masked_repr(instance)
        assert "amount=9999" in repr_str
        assert "token=***" in repr_str


class TestMaskedReprFormat:
    """Tests for output format of masked_repr."""

    def test_repr_includes_class_name(self, tagged_class: type[Any]) -> None:
        """masked_repr includes the dataclass name."""
        field_set = SensitiveFieldSet.from_dataclass(tagged_class)
        instance = tagged_class(id=1, ssn="123-45-6789", email="user@example.com")
        repr_str = field_set.masked_repr(instance)
        assert repr_str.startswith("User(")
        assert repr_str.endswith(")")

    def test_repr_field_order_preserved(self, tagged_class: type[Any]) -> None:
        """masked_repr preserves field declaration order."""
        field_set = SensitiveFieldSet.from_dataclass(tagged_class)
        instance = tagged_class(id=1, ssn="123-45-6789", email="user@example.com")
        repr_str = field_set.masked_repr(instance)
        id_pos = repr_str.index("id=")
        ssn_pos = repr_str.index("ssn=")
        email_pos = repr_str.index("email=")
        assert id_pos < ssn_pos < email_pos

    def test_repr_comma_separation(self, multi_tagged_class: type[Any]) -> None:
        """masked_repr separates fields with commas and spaces."""
        field_set = SensitiveFieldSet.from_dataclass(multi_tagged_class)
        instance = multi_tagged_class(
            transaction_id=1,
            name="Test",
            ssn="123-45-6789",
            card_token="token",
            api_key="key",
        )
        repr_str = field_set.masked_repr(instance)
        # Count commas between fields
        assert repr_str.count(", ") >= 4  # At least 4 commas for 5 fields
