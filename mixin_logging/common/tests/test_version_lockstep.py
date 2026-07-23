"""Verify version lockstep across both packages and dist."""

from __future__ import annotations

import importlib.metadata


class TestVersionLockstep:
    """Version consistency across packages and installed dist."""

    def test_all_mixin_roots_version_match(self) -> None:
        """All 5 mixin roots must have same version."""
        from mixin_latency.config._version import __version__ as latency_version
        from mixin_logging.config._version import (
            __version__ as logging_version,
        )
        from mixin_notifications.config._version import (
            __version__ as notifications_version,
        )
        from mixin_retry.config._version import __version__ as retry_version
        from mixin_sensitivity.config._version import (
            __version__ as sensitivity_version,
        )

        versions = {
            "mixin_logging": logging_version,
            "mixin_sensitivity": sensitivity_version,
            "mixin_retry": retry_version,
            "mixin_notifications": notifications_version,
            "mixin_latency": latency_version,
        }

        for name, version in versions.items():
            assert version == logging_version, (
                f"{name} version {version} != "
                f"mixin_logging version {logging_version}"
            )

    def test_package_versions_match_dist_version(self) -> None:
        """Package versions must match the installed mixins dist version."""
        from mixin_logging.config._version import __version__ as logging_version

        try:
            dist_version = importlib.metadata.version("mixin-suite")
        except importlib.metadata.PackageNotFoundError:
            dist_version = None

        if dist_version is not None:
            assert logging_version == dist_version, (
                f"Package version {logging_version} != "
                f"installed dist version {dist_version}"
            )
