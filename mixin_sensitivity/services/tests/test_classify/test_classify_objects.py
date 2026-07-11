"""Tests for Sensitivity StrEnum and SensitivityProfile value object."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from mixin_sensitivity import classify
from mixin_sensitivity.services.classify.classify_objects import (
    Sensitivity,
    SensitivityProfile,
)


class TestSensitivity:
    """Tests for the Sensitivity StrEnum taxonomy."""

    def test_has_four_members(self) -> None:
        """Sensitivity has exactly PHI, PII, PCI, SECRET."""
        assert len(Sensitivity) == 4

    def test_phi_member_exists_with_value_phi(self) -> None:
        """PHI member has value 'phi'."""
        assert Sensitivity.PHI == "phi"
        assert Sensitivity.PHI.value == "phi"

    def test_pii_member_exists_with_value_pii(self) -> None:
        """PII member has value 'pii'."""
        assert Sensitivity.PII == "pii"
        assert Sensitivity.PII.value == "pii"

    def test_pci_member_exists_with_value_pci(self) -> None:
        """PCI member has value 'pci'."""
        assert Sensitivity.PCI == "pci"
        assert Sensitivity.PCI.value == "pci"

    def test_secret_member_exists_with_value_secret(self) -> None:
        """SECRET member has value 'secret'."""
        assert Sensitivity.SECRET == "secret"
        assert Sensitivity.SECRET.value == "secret"

    def test_is_str_enum(self) -> None:
        """Sensitivity members are strings and can be compared to str."""
        assert isinstance(Sensitivity.PHI, str)
        assert Sensitivity.PHI in {"phi", "pii"}


class TestFromDataclass:
    """Tests for SensitivityProfile.from_dataclass() classmethod."""

    def test_reads_tagged_fields_into_classes_tuple(  # noqa: dto-strict-R006
        self, mixed_type: type[Any]
    ) -> None:
        """from_dataclass collects sensitivity-tagged fields as (name, Sensitivity) pairs."""
        profile = SensitivityProfile.from_dataclass(mixed_type)
        assert profile.classes == (
            ("name", Sensitivity.PII),
            ("ssn", Sensitivity.PHI),
            ("card_token", Sensitivity.PCI),
            ("api_key", Sensitivity.SECRET),
        )

    def test_preserves_field_declaration_order(self, mixed_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """Pairs appear in the order fields are declared in the dataclass."""
        profile = SensitivityProfile.from_dataclass(mixed_type)
        field_names = tuple(name for name, _ in profile.classes)
        assert field_names == ("name", "ssn", "card_token", "api_key")

    def test_excludes_untagged_fields(self, mixed_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """Fields without sensitivity metadata are not included."""
        profile = SensitivityProfile.from_dataclass(mixed_type)
        field_names = tuple(name for name, _ in profile.classes)
        assert "id" not in field_names
        assert "description" not in field_names

    def test_empty_classes_when_no_tags(self, unclassified_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """from_dataclass yields an empty tuple when no field is sensitivity-tagged."""
        profile = SensitivityProfile.from_dataclass(unclassified_type)
        assert profile.classes == ()

    def test_returns_sensitivity_profile_instance(self, mixed_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """Return type is a SensitivityProfile."""
        profile = SensitivityProfile.from_dataclass(mixed_type)
        assert isinstance(profile, SensitivityProfile)


class TestIsEmpty:
    """Tests for SensitivityProfile.is_empty property."""

    def test_true_when_no_tags(self, unclassified_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """is_empty is True when classes tuple is empty."""
        profile = SensitivityProfile.from_dataclass(unclassified_type)
        assert profile.is_empty is True

    def test_false_when_tags_exist(self, mixed_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """is_empty is False when at least one field is tagged."""
        profile = SensitivityProfile.from_dataclass(mixed_type)
        assert profile.is_empty is False


class TestSensitivityOf:
    """Tests for SensitivityProfile.sensitivity_of() method."""

    def test_returns_sensitivity_for_tagged_field(self, mixed_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """Returns the Sensitivity class for a tagged field by name."""
        profile = SensitivityProfile.from_dataclass(mixed_type)
        assert profile.sensitivity_of("name") == Sensitivity.PII
        assert profile.sensitivity_of("ssn") == Sensitivity.PHI
        assert profile.sensitivity_of("card_token") == Sensitivity.PCI
        assert profile.sensitivity_of("api_key") == Sensitivity.SECRET

    def test_returns_none_for_untagged_field(self, mixed_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """Returns None for a field without sensitivity metadata."""
        profile = SensitivityProfile.from_dataclass(mixed_type)
        assert profile.sensitivity_of("id") is None
        assert profile.sensitivity_of("description") is None

    def test_returns_none_for_absent_field_name(self, mixed_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """Returns None for a name that does not exist in the dataclass."""
        profile = SensitivityProfile.from_dataclass(mixed_type)
        assert profile.sensitivity_of("nonexistent") is None
        assert profile.sensitivity_of("foo") is None

    def test_returns_none_on_empty_profile(self, unclassified_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """Returns None for any field name when profile is empty."""
        profile = SensitivityProfile.from_dataclass(unclassified_type)
        assert profile.sensitivity_of("id") is None
        assert profile.sensitivity_of("title") is None


class TestHas:
    """Tests for SensitivityProfile.has() method."""

    def test_true_when_sensitivity_present(self, mixed_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """Returns True when the given sensitivity class is in the profile."""
        profile = SensitivityProfile.from_dataclass(mixed_type)
        assert profile.has(Sensitivity.PII) is True
        assert profile.has(Sensitivity.PHI) is True
        assert profile.has(Sensitivity.PCI) is True
        assert profile.has(Sensitivity.SECRET) is True

    def test_false_when_sensitivity_absent(self, unclassified_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """Returns False when the given sensitivity class is not in the profile."""
        profile = SensitivityProfile.from_dataclass(unclassified_type)
        assert profile.has(Sensitivity.PHI) is False
        assert profile.has(Sensitivity.PII) is False
        assert profile.has(Sensitivity.PCI) is False
        assert profile.has(Sensitivity.SECRET) is False


class TestFieldsOf:
    """Tests for SensitivityProfile.fields_of() method."""

    def test_returns_field_names_for_present_class(self, mixed_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """Returns tuple of field names carrying the given sensitivity class."""
        profile = SensitivityProfile.from_dataclass(mixed_type)
        assert profile.fields_of(Sensitivity.PII) == ("name",)
        assert profile.fields_of(Sensitivity.PHI) == ("ssn",)
        assert profile.fields_of(Sensitivity.PCI) == ("card_token",)
        assert profile.fields_of(Sensitivity.SECRET) == ("api_key",)

    def test_returns_empty_tuple_for_absent_class(  # noqa: dto-strict-R006
        self, unclassified_type: type[Any]
    ) -> None:
        """Returns empty tuple when the given sensitivity class is not present."""
        profile = SensitivityProfile.from_dataclass(unclassified_type)
        assert profile.fields_of(Sensitivity.PHI) == ()
        assert profile.fields_of(Sensitivity.PII) == ()
        assert profile.fields_of(Sensitivity.PCI) == ()
        assert profile.fields_of(Sensitivity.SECRET) == ()

    def test_preserves_field_order_in_return_tuple(self, mixed_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """Field names in the returned tuple preserve declaration order."""
        profile = SensitivityProfile.from_dataclass(mixed_type)
        assert isinstance(profile.fields_of(Sensitivity.PII), tuple)


class TestFrozenProfile:
    """Tests for SensitivityProfile immutability and hashability."""

    def test_profile_is_frozen(self, mixed_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """SensitivityProfile instances cannot be mutated."""
        profile = SensitivityProfile.from_dataclass(mixed_type)
        with pytest.raises((FrozenInstanceError, AttributeError)):
            object.__setattr__(profile, "id", "test")  # type: ignore[attr-defined]

    def test_profile_is_hashable(self, mixed_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """SensitivityProfile instances are hashable and can go in a set."""
        profile = SensitivityProfile.from_dataclass(mixed_type)
        h = hash(profile)
        assert isinstance(h, int)
        s = {profile}
        assert profile in s

    def test_two_profiles_with_same_classes_are_equal(  # noqa: dto-strict-R006
        self, mixed_type: type[Any]
    ) -> None:
        """Two profiles built from identical dataclasses are equal."""
        profile1 = SensitivityProfile.from_dataclass(mixed_type)
        profile2 = SensitivityProfile.from_dataclass(mixed_type)
        assert profile1 == profile2


class TestClassifyBinding:
    """Tests for the public classify() entry point binding."""

    def test_classify_is_from_dataclass_method(self) -> None:
        """classify is bound to SensitivityProfile.from_dataclass."""
        assert classify == SensitivityProfile.from_dataclass

    def test_classify_returns_profile(self, mixed_type: type[Any]) -> None:  # noqa: dto-strict-R006
        """Calling classify(Dataclass) returns a populated SensitivityProfile."""
        profile = classify(mixed_type)
        assert isinstance(profile, SensitivityProfile)
        assert profile.is_empty is False
        assert len(profile.classes) == 4

    def test_classify_imported_from_package_root(self) -> None:
        """classify is available from mixin_sensitivity package root."""
        from mixin_sensitivity import classify as public_classify

        assert public_classify == SensitivityProfile.from_dataclass
