"""Suite-wide version consistency tests."""

from __future__ import annotations


class TestSuiteVersionConsistency:
    """Verify all mixin roots report consistent versions."""

    def test_all_mixin_roots_report_same_version(self) -> None:
        """All four mixin roots (__version__) report identical version string."""
        import mixin_logging
        import mixin_notifications
        import mixin_retry
        import mixin_sensitivity

        logging_version = mixin_logging.__version__
        notifications_version = mixin_notifications.__version__
        sensitivity_version = mixin_sensitivity.__version__
        retry_version = mixin_retry.__version__

        assert logging_version == notifications_version == sensitivity_version == retry_version
        assert logging_version == "0.3.0"
