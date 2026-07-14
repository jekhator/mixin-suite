"""Test that PUBLIC_API exports are accurate."""

import mixin_retry


class TestPublicAPI:
    """Verify mixin_retry.__all__ matches public_api.PUBLIC_API."""

    def test_public_api_completeness(self) -> None:
        """All public_api.PUBLIC_API names are exported."""
        from mixin_retry.common.constants import public_api as pa

        for name in pa.PUBLIC_API:
            assert hasattr(mixin_retry, name), (
                f"{name} missing from mixin_retry.__all__"
            )

    def test_all_exports_match_public_api(self) -> None:
        """All names in mixin_retry.__all__ are in public_api.PUBLIC_API."""
        from mixin_retry.common.constants import public_api as pa

        for name in mixin_retry.__all__:
            assert name in pa.PUBLIC_API, f"{name} exported but not in PUBLIC_API"
