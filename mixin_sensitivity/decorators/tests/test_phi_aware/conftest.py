"""Shared fixtures for PHI policy tests."""

from __future__ import annotations

import pytest

from mixin_sensitivity.decorators.classes.compliance import Compliance
from mixin_sensitivity.decorators.classes.phi_aware.phi_aware_objects import (
    PhiPolicyAware,
)


@pytest.fixture
def hipaa_phi_policy() -> PhiPolicyAware:
    """A HIPAA-compliant PHI masking policy."""
    return PhiPolicyAware(
        compliance=Compliance.HIPAA,
        detection_hints=("ssn", "mrn", "medical_id", "patient_id"),
        placeholder="[PHI REDACTED]",
    )


@pytest.fixture
def gdpr_phi_policy() -> PhiPolicyAware:
    """A GDPR-compliant PHI masking policy."""
    return PhiPolicyAware(
        compliance=Compliance.GDPR,
        detection_hints=("health_record", "diagnosis", "prescription"),
        placeholder="[SANITIZED]",
    )


@pytest.fixture
def empty_hints_phi_policy() -> PhiPolicyAware:
    """A PHI policy with no detection hints."""
    return PhiPolicyAware(
        compliance=Compliance.HIPAA,
        detection_hints=(),
        placeholder="***",
    )
