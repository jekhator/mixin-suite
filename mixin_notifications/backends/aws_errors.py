"""Error classification shared by the AWS notification backends."""

from __future__ import annotations

from collections.abc import Mapping

from mixin_notifications.backends._objects import DeliveryResult
from mixin_notifications.common.constants import backends as const


class AwsErrorClassifier:
    """Map AWS client exceptions to a failed DeliveryResult with a retry hint."""

    @staticmethod
    def failure(
        backend_name: str, detail_prefix: str, error: Exception
    ) -> DeliveryResult:
        """Build a failed result; throttling and service-side codes are retryable."""
        error_code = AwsErrorClassifier.error_code(error)
        return DeliveryResult(
            delivered=False,
            backend_name=backend_name,
            detail=f"{detail_prefix}: {error_code or error.__class__.__name__}",
            retryable=error_code in const.RETRYABLE_AWS_ERROR_CODES,
        )

    @staticmethod
    def error_code(error: Exception) -> str:
        """Return the AWS error code from a botocore-style response, or an empty string."""
        response = getattr(error, "response", None)
        if not isinstance(response, Mapping):
            return ""
        error_section = response.get("Error")
        if not isinstance(error_section, Mapping):
            return ""
        code = error_section.get("Code")
        return code if isinstance(code, str) else ""
