"""Tests for the SensitiveDecorator that injects masking __repr__."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from mixin_sensitivity.decorators.classes.compliance import Compliance
from mixin_sensitivity.decorators.classes.phi_aware.phi_aware_objects import (
    PhiPolicyAware,
)
from mixin_sensitivity.decorators.classes.pii_aware.pii_aware_objects import (
    PiiPolicyAware,
)
from mixin_sensitivity.decorators.sensitive.sensitive_client import (
    SensitiveDecorator,
    sensitive,
)
from mixin_sensitivity.services.classify.classify_objects import Sensitivity


class TestSensitiveDecoratorRequireDataclass:
    """Tests for decorator requirement that target is a dataclass."""

    def test_requires_dataclass_raises_type_error(self) -> None:
        """SensitiveDecorator raises TypeError when applied to non-dataclass."""
        decorator = SensitiveDecorator(policies=())

        class RegularClass:
            pass

        with pytest.raises(TypeError, match="@sensitive requires a dataclass target"):
            decorator(RegularClass)

    def test_function_raises_type_error(self) -> None:
        """SensitiveDecorator raises TypeError when applied to function."""
        decorator = SensitiveDecorator(policies=())

        def my_function() -> None:
            pass

        with pytest.raises(TypeError):
            decorator(my_function)  # type: ignore[arg-type]


class TestSensitiveDecoratorUntaggedClass:
    """Tests for decorator behavior on untagged dataclasses."""

    def test_untagged_class_returned_unchanged(self) -> None:
        """Decorator returns untagged class unchanged (no-op)."""

        @dataclass(frozen=True, slots=True)
        class Public:
            id: int
            name: str

        decorator = SensitiveDecorator(policies=())
        original_repr = Public.__repr__
        result = decorator(Public)
        # Untagged class should be returned unchanged with original repr
        assert result is Public
        # __repr__ should not be replaced for untagged classes
        assert Public(id=1, name="test").__repr__() == original_repr(
            Public(id=1, name="test")
        )

    def test_untagged_instance_default_repr(self) -> None:
        """Untagged instance shows normal dataclass repr (no masking)."""

        @dataclass(frozen=True, slots=True)
        class Item:
            id: int
            title: str

        decorator = SensitiveDecorator(policies=())
        decorator(Item)
        instance = Item(id=42, title="Widget")
        repr_str = repr(instance)
        assert "id=42" in repr_str
        assert "title='Widget'" in repr_str


class TestSensitiveDecoratorNoPolicy:
    """Tests for decorator with tagged class but empty policies tuple."""

    def test_tagged_class_with_no_policies_masks_with_stars(self) -> None:
        """Tagged class decorated with empty policies tuple masks to ***."""

        @dataclass(frozen=True, slots=True)
        class User:
            id: int
            ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})

        decorator = SensitiveDecorator(policies=())
        result = decorator(User)
        assert result is User  # Decorator modifies in place
        instance = User(id=1, ssn="123-45-6789")
        repr_str = repr(instance)
        assert "id=1" in repr_str
        assert "ssn=***" in repr_str
        assert "123-45-6789" not in repr_str


class TestSensitiveDecoratorWithPolicies:
    """Tests for decorator with configured policies."""

    def test_decorated_tagged_class_masks_with_policy(self) -> None:
        """Tagged class decorated with policies masks fields via policy.mask()."""

        @dataclass(frozen=True, slots=True)
        class Account:
            id: int
            ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})

        phi_policy = PhiPolicyAware(
            compliance=Compliance.HIPAA,
            detection_hints=("ssn",),
            placeholder="[PHI]",
        )
        decorator = SensitiveDecorator(policies=((Sensitivity.PHI, phi_policy),))
        result = decorator(Account)
        assert result is Account
        instance = Account(id=1, ssn="123-45-6789")
        repr_str = repr(instance)
        assert "id=1" in repr_str
        assert "ssn=[PHI]" in repr_str
        assert "123-45-6789" not in repr_str

    def test_multiple_policies_all_applied(self) -> None:
        """Decorator with multiple policies applies all policies."""

        @dataclass(frozen=True, slots=True)
        class Record:
            id: int
            ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})
            email: str = field(metadata={"sensitivity": Sensitivity.PII})

        phi_policy = PhiPolicyAware(
            compliance=Compliance.HIPAA,
            detection_hints=("ssn",),
            placeholder="[PHI_MASKED]",
        )
        pii_policy = PiiPolicyAware(
            compliance=Compliance.GDPR,
            detection_hints=("email",),
            placeholder="[PII_MASKED]",
        )
        decorator = SensitiveDecorator(
            policies=(
                (Sensitivity.PHI, phi_policy),
                (Sensitivity.PII, pii_policy),
            )
        )
        decorator(Record)
        instance = Record(id=42, ssn="999-88-7777", email="user@example.com")
        repr_str = repr(instance)
        assert "id=42" in repr_str
        assert "ssn=[PHI_MASKED]" in repr_str
        assert "email=[PII_MASKED]" in repr_str
        assert "999-88-7777" not in repr_str
        assert "user@example.com" not in repr_str

    def test_partial_policy_coverage(self) -> None:
        """Decorator with partial policies uses *** for unmatched sensitivity classes."""

        @dataclass(frozen=True, slots=True)
        class Payment:
            id: int
            ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})
            card: str = field(metadata={"sensitivity": Sensitivity.PCI})

        phi_policy = PhiPolicyAware(
            compliance=Compliance.HIPAA,
            detection_hints=("ssn",),
            placeholder="[PHI]",
        )
        # Only PHI policy, no PCI policy
        decorator = SensitiveDecorator(policies=((Sensitivity.PHI, phi_policy),))
        decorator(Payment)
        instance = Payment(id=1, ssn="123-45-6789", card="tok_abc")
        repr_str = repr(instance)
        assert "ssn=[PHI]" in repr_str
        assert "card=***" in repr_str


class TestSensitiveModuleVariable:
    """Tests for the module-level sensitive variable."""

    def test_sensitive_is_decorator_instance(self) -> None:
        """sensitive is a SensitiveDecorator instance with empty policies."""
        assert isinstance(sensitive, SensitiveDecorator)
        assert sensitive.policies == ()

    def test_sensitive_can_be_used_as_decorator(self) -> None:
        """sensitive can be used as a class decorator directly."""

        @sensitive
        @dataclass(frozen=True, slots=True)
        class Item:
            id: int
            secret: str = field(metadata={"sensitivity": Sensitivity.SECRET})

        instance = Item(id=1, secret="hide_me")
        repr_str = repr(instance)
        assert "secret=***" in repr_str
        assert "hide_me" not in repr_str

    def test_sensitive_in_stacked_decorator_order(self) -> None:
        """sensitive works correctly when stacked with dataclass decorator."""

        @sensitive
        @dataclass(frozen=True, slots=True)
        class Document:
            doc_id: int
            ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})

        instance = Document(doc_id=100, ssn="555-66-7777")
        repr_str = repr(instance)
        assert "doc_id=100" in repr_str
        assert "ssn=***" in repr_str
        assert "555-66-7777" not in repr_str


class TestSensitiveDecoratorInstanceFrozen:
    """Tests for decorator handling of frozen dataclass instances."""

    def test_frozen_dataclass_instances_work(self) -> None:
        """Decorated frozen dataclass instances function correctly."""

        @dataclass(frozen=True, slots=True)
        class FrozenUser:
            id: int
            ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})

        phi_policy = PhiPolicyAware(
            compliance=Compliance.HIPAA,
            detection_hints=("ssn",),
            placeholder="[MASKED]",
        )
        decorator = SensitiveDecorator(policies=((Sensitivity.PHI, phi_policy),))
        decorator(FrozenUser)
        instance = FrozenUser(id=1, ssn="123-45-6789")
        # Frozen instances cannot be mutated
        with pytest.raises(AttributeError):
            instance.id = 2  # type: ignore[misc]
        # But repr should work
        repr_str = repr(instance)
        assert "[MASKED]" in repr_str


class TestSensitiveDecoratorSlotsDataclass:
    """Tests for decorator with slots=True dataclasses."""

    def test_slots_dataclass_decorator_works(self) -> None:
        """Decorator works with slots=True dataclasses."""

        @dataclass(frozen=True, slots=True)
        class SlottedUser:
            id: int
            email: str = field(metadata={"sensitivity": Sensitivity.PII})

        pii_policy = PiiPolicyAware(
            compliance=Compliance.GDPR,
            detection_hints=("email",),
            placeholder="[REDACTED]",
        )
        decorator = SensitiveDecorator(policies=((Sensitivity.PII, pii_policy),))
        decorator(SlottedUser)
        instance = SlottedUser(id=1, email="user@example.com")
        repr_str = repr(instance)
        assert "email=[REDACTED]" in repr_str
        assert "user@example.com" not in repr_str


class TestSensitiveDecoratorReturnsSameType:
    """Tests for decorator returning the same type unchanged."""

    def test_decorator_returns_same_class_reference(self) -> None:
        """Decorator returns the same class object (modified in place)."""

        @dataclass(frozen=True, slots=True)
        class MyClass:
            value: str = field(metadata={"sensitivity": Sensitivity.SECRET})

        secret_policy = PhiPolicyAware(
            compliance=Compliance.NONE,
            detection_hints=("value",),
            placeholder="[X]",
        )
        decorator = SensitiveDecorator(policies=((Sensitivity.SECRET, secret_policy),))
        result = decorator(MyClass)
        assert result is MyClass
        assert result.__name__ == "MyClass"

    def test_decorated_class_remains_instantiable(self) -> None:
        """Decorated class can still be instantiated normally."""

        @dataclass(frozen=True, slots=True)
        class Product:
            id: int
            code: str = field(metadata={"sensitivity": Sensitivity.SECRET})

        decorator = SensitiveDecorator(policies=())
        decorator(Product)
        # Should be instantiable without errors
        instance = Product(id=42, code="secret123")
        assert instance.id == 42
        assert instance.code == "secret123"


class TestSensitiveDecoratorWithIntFields:
    """Tests for decorator with non-string field values."""

    def test_int_field_converted_in_masked_repr(self) -> None:
        """Decorator masks int fields by converting to str first."""

        @dataclass(frozen=True, slots=True)
        class Record:
            name: str
            secret_code: int = field(metadata={"sensitivity": Sensitivity.SECRET})

        secret_policy = PhiPolicyAware(
            compliance=Compliance.NONE,
            detection_hints=("secret_code",),
            placeholder="[X]",
        )
        decorator = SensitiveDecorator(policies=((Sensitivity.SECRET, secret_policy),))
        decorator(Record)
        instance = Record(name="Test", secret_code=123456)
        repr_str = repr(instance)
        assert "secret_code=[X]" in repr_str
        assert "123456" not in repr_str


class TestSensitiveDecoratorEdgeCases:
    """Tests for edge cases and corner scenarios."""

    def test_decorator_with_empty_dataclass(self) -> None:
        """Decorator handles dataclass with no fields gracefully."""

        @dataclass(frozen=True, slots=True)
        class Empty:
            pass

        decorator = SensitiveDecorator(policies=())
        result = decorator(Empty)
        assert result is Empty

    def test_decorator_twice_on_same_class(self) -> None:
        """Decorator can be applied twice (second application replaces first)."""

        @dataclass(frozen=True, slots=True)
        class Item:
            ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})

        phi_policy_1 = PhiPolicyAware(
            compliance=Compliance.HIPAA,
            detection_hints=("ssn",),
            placeholder="[FIRST]",
        )
        phi_policy_2 = PhiPolicyAware(
            compliance=Compliance.HIPAA,
            detection_hints=("ssn",),
            placeholder="[SECOND]",
        )
        decorator1 = SensitiveDecorator(policies=((Sensitivity.PHI, phi_policy_1),))
        decorator2 = SensitiveDecorator(policies=((Sensitivity.PHI, phi_policy_2),))
        decorator1(Item)
        decorator2(Item)  # Apply second decorator
        instance = Item(ssn="999-88-7777")
        repr_str = repr(instance)
        # Second decorator should have overwritten the first
        assert "[SECOND]" in repr_str
        assert "[FIRST]" not in repr_str

    def test_invalid_sensitivity_metadata_raises_error(self) -> None:
        """Invalid sensitivity metadata value causes ValueError during decoration."""

        @dataclass(frozen=True, slots=True)
        class BadRecord:
            field: str = field(metadata={"sensitivity": "invalid_enum_value"})

        decorator = SensitiveDecorator(policies=())
        with pytest.raises(ValueError):
            decorator(BadRecord)
