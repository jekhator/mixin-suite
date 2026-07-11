"""Verify version lockstep across both packages and dist."""

from __future__ import annotations

import importlib.metadata


class TestVersionLockstep:
    """Version consistency across packages and installed dist."""

    def test_mixin_logging_version_matches_sensitivity(self) -> None:
        """Both packages must have the same version."""
        from mixin_logging.config._version import __version__ as logging_version
        from mixin_sensitivity.config._version import (
            __version__ as sensitivity_version,
        )

        assert logging_version == sensitivity_version, (
            f"mixin_logging version {logging_version} != "
            f"mixin_sensitivity version {sensitivity_version}"
        )

    def test_package_versions_match_dist_version(self) -> None:
        """Package versions must match the installed mixins dist version."""
        from mixin_logging.config._version import __version__ as logging_version

        try:
            dist_version = importlib.metadata.version("mixins")
        except importlib.metadata.PackageNotFoundError:
            dist_version = None

        if dist_version is not None:
            assert logging_version == dist_version, (
                f"Package version {logging_version} != "
                f"installed dist version {dist_version}"
            )
