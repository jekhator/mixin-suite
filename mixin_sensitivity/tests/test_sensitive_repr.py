"""Tests for SensitiveRepr adoption mixin."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from mixin_sensitivity import (
    SensitiveDeclarationError,
    SensitiveRepr,
    Sensitivity,
    classify,
)


class TestSensitiveRepr:
    """Test SensitiveRepr adoption mixin masking behavior."""

    def test_repr_without_repr_false_raises_error(self) -> None:
        """Adopter without repr=False raises SensitiveDeclarationError.

        Silent shadowing is prevented: dataclass-generated __repr__
        cannot be used without being detected.
        """
        with pytest.raises(
            SensitiveDeclarationError,
            match="must use @dataclass.*repr=False",
        ):

            @dataclass(frozen=True, slots=True)
            class PatientBad(SensitiveRepr):
                name: str
                ssn: str = field(
                    metadata={"sensitivity": Sensitivity.PHI}
                )

            PatientBad(name="Alice", ssn="123-45-6789")

    def test_repr_with_single_sensitive_field(self) -> None:
        """SensitiveRepr masks single sensitive field."""

        @dataclass(frozen=True, slots=True, repr=False)
        class Patient(SensitiveRepr):
            name: str
            ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})

        p = Patient(name="Alice", ssn="123-45-6789")
        repr_str = repr(p)

        assert "name='Alice'" in repr_str
        assert "***MASKED***" in repr_str
        assert "123-45-6789" not in repr_str

    def test_repr_with_multiple_sensitive_fields(self) -> None:
        """SensitiveRepr masks multiple sensitive fields."""

        @dataclass(frozen=True, slots=True, repr=False)
        class Account(SensitiveRepr):
            username: str
            password: str = field(metadata={"sensitivity": Sensitivity.SECRET})
            api_key: str = field(metadata={"sensitivity": Sensitivity.SECRET})

        a = Account(username="alice", password="secret123", api_key="key456")
        repr_str = repr(a)

        assert "username='alice'" in repr_str
        assert repr_str.count("***MASKED***") == 2
        assert "secret123" not in repr_str
        assert "key456" not in repr_str

    def test_repr_with_no_sensitive_fields(self) -> None:
        """SensitiveRepr on dataclass with no sensitive fields."""

        @dataclass(frozen=True, slots=True, repr=False)
        class PublicData(SensitiveRepr):
            name: str
            email: str

        p = PublicData(name="Bob", email="bob@example.com")
        repr_str = repr(p)

        assert "name='Bob'" in repr_str
        assert "email='bob@example.com'" in repr_str
        assert "***MASKED***" not in repr_str

    def test_repr_mixed_sensitivity_levels(self) -> None:
        """SensitiveRepr handles mixed sensitivity levels."""

        @dataclass(frozen=True, slots=True, repr=False)
        class MixedData(SensitiveRepr):
            public_field: str
            pii_field: str = field(metadata={"sensitivity": Sensitivity.PII})
            phi_field: str = field(metadata={"sensitivity": Sensitivity.PHI})
            secret_field: str = field(metadata={"sensitivity": Sensitivity.SECRET})

        m = MixedData(
            public_field="public",
            pii_field="pii_value",
            phi_field="phi_value",
            secret_field="secret_value",
        )
        repr_str = repr(m)

        assert "public_field='public'" in repr_str
        assert "pii_value" not in repr_str
        assert "phi_value" not in repr_str
        assert "secret_value" not in repr_str
        assert repr_str.count("***MASKED***") == 3

    def test_metadata_introspection_unchanged(self) -> None:
        """Field metadata remains introspectable after repr()."""

        @dataclass(frozen=True, slots=True, repr=False)
        class Patient(SensitiveRepr):
            name: str
            ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})

        p = Patient(name="Alice", ssn="123-45-6789")
        profile = classify(Patient)

        assert profile.has(Sensitivity.PHI)
        repr(p)
        profile_after = classify(Patient)
        assert profile_after.has(Sensitivity.PHI)

    def test_sensitive_repr_preserves_order(self) -> None:
        """SensitiveRepr preserves field order in repr."""

        @dataclass(frozen=True, slots=True, repr=False)
        class OrderedData(SensitiveRepr):
            first: str
            second: str = field(metadata={"sensitivity": Sensitivity.PHI})
            third: str

        o = OrderedData(first="a", second="b", third="c")
        repr_str = repr(o)

        first_pos = repr_str.find("first")
        second_pos = repr_str.find("***MASKED***")
        third_pos = repr_str.find("third")

        assert first_pos < second_pos < third_pos

    def test_sensitive_repr_with_non_string_types(self) -> None:
        """SensitiveRepr masks sensitive non-string types."""

        @dataclass(frozen=True, slots=True, repr=False)
        class NumberData(SensitiveRepr):
            id: int
            card_number: int = field(metadata={"sensitivity": Sensitivity.PCI})

        n = NumberData(id=1, card_number=4111111111111111)
        repr_str = repr(n)

        assert "id=1" in repr_str
        assert "4111111111111111" not in repr_str
        assert "***MASKED***" in repr_str

    def test_repr_class_name_correct(self) -> None:
        """SensitiveRepr includes correct class name in repr."""

        @dataclass(frozen=True, slots=True, repr=False)
        class CustomClass(SensitiveRepr):
            value: str

        c = CustomClass(value="test")
        repr_str = repr(c)

        assert repr_str.startswith("CustomClass(")
        assert repr_str.endswith(")")

    def test_adopter_with_own_post_init_and_super_call(self) -> None:
        """Adopter with __post_init__ calling super() still guards correctly."""

        @dataclass(frozen=True, slots=True, repr=False)
        class PatientWithInit(SensitiveRepr):
            name: str
            ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})
            _initialized: bool = field(init=False, default=False)

            def __post_init__(self) -> None:
                super().__post_init__()
                object.__setattr__(self, "_initialized", True)

        p = PatientWithInit(name="Alice", ssn="123-45-6789")
        repr_str = repr(p)

        assert "name='Alice'" in repr_str
        assert "***MASKED***" in repr_str
        assert "123-45-6789" not in repr_str
        assert p._initialized is True

    def test_adopter_with_own_post_init_without_repr_false_raises(self) -> None:
        """Adopter with __post_init__ still guarded when repr=False omitted."""

        with pytest.raises(
            SensitiveDeclarationError,
            match="must use @dataclass.*repr=False",
        ):

            @dataclass(frozen=True, slots=True)
            class PatientWithInitBad(SensitiveRepr):
                name: str

                def __post_init__(self) -> None:
                    super().__post_init__()

            PatientWithInitBad(name="Alice")
