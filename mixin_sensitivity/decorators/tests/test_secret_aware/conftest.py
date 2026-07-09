"""Shared fixtures for SECRET policy tests."""

from __future__ import annotations

import pytest

from mixin_sensitivity.decorators.classes.compliance import Compliance
from mixin_sensitivity.decorators.classes.secret_aware.secret_aware_objects import (
    SecretPolicyAware,
)


@pytest.fixture
def api_secret_policy() -> SecretPolicyAware:
    """A credential-masking policy for API secrets."""
    return SecretPolicyAware(
        compliance=Compliance.NONE,
        detection_hints=("api_key", "api_secret", "token", "password"),
        placeholder="[SECRET REDACTED]",
    )


@pytest.fixture
def database_secret_policy() -> SecretPolicyAware:
    """A credential-masking policy for database credentials."""
    return SecretPolicyAware(
        compliance=Compliance.NONE,
        detection_hints=("db_password", "connection_string", "private_key"),
        placeholder="***HIDDEN***",
    )


@pytest.fixture
def empty_hints_secret_policy() -> SecretPolicyAware:
    """A SECRET policy with no detection hints."""
    return SecretPolicyAware(
        compliance=Compliance.NONE,
        detection_hints=(),
        placeholder="[REDACTED]",
    )
