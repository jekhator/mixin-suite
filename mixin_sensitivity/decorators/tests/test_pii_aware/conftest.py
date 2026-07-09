"""Shared fixtures for PII policy tests."""

from __future__ import annotations

import pytest

from mixin_sensitivity.decorators.classes.compliance import Compliance
from mixin_sensitivity.decorators.classes.pii_aware.pii_aware_objects import (
    PiiPolicyAware,
)


@pytest.fixture
def gdpr_pii_policy() -> PiiPolicyAware:
    """A GDPR-compliant PII masking policy."""
    return PiiPolicyAware(
        compliance=Compliance.GDPR,
        detection_hints=("email", "phone", "ssn", "name"),
        placeholder="[PII REDACTED]",
    )


@pytest.fixture
def generic_pii_policy() -> PiiPolicyAware:
    """A generic PII masking policy."""
    return PiiPolicyAware(
        compliance=Compliance.NONE,
        detection_hints=("address", "zip_code", "credit_card"),
        placeholder="***",
    )


@pytest.fixture
def empty_hints_pii_policy() -> PiiPolicyAware:
    """A PII policy with no detection hints."""
    return PiiPolicyAware(
        compliance=Compliance.GDPR,
        detection_hints=(),
        placeholder="[MASKED]",
    )
