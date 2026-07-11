"""Shared dataclass fixtures for the classify feature tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from mixin_sensitivity.services.classify.classify_objects import Sensitivity


@pytest.fixture
def mixed_type() -> type[Any]:  # noqa: dto-strict-R006  # fixture
    """A frozen dataclass with multiple sensitivity classes and one untagged field."""

    @dataclass(frozen=True, slots=True)
    class Record:
        id: int
        name: str = field(metadata={"sensitivity": Sensitivity.PII})
        ssn: str = field(metadata={"sensitivity": Sensitivity.PHI})
        card_token: str = field(metadata={"sensitivity": Sensitivity.PCI})
        api_key: str = field(metadata={"sensitivity": Sensitivity.SECRET})
        description: str = ""

    return Record


@pytest.fixture
def unclassified_type() -> type[Any]:  # noqa: dto-strict-R006  # fixture
    """A frozen dataclass with no sensitivity-tagged fields."""

    @dataclass(frozen=True, slots=True)
    class Public:
        id: int
        title: str
        created_at: str = ""

    return Public
