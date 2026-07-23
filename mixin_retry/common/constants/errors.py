"""Error messages for retry operations."""

from typing import Final

ERR_RETRY_MAX_ATTEMPTS: Final = "max_attempts must be >= 1"
ERR_RETRY_BACKOFF_BASE: Final = "backoff_base_seconds must be > 0"
ERR_RETRY_BACKOFF_MULTIPLIER: Final = "backoff_multiplier must be > 0"
ERR_RETRY_BACKOFF_MAX: Final = "backoff_max_seconds must be > 0"
ERR_RETRY_POLICY_REQUIRED: Final = "policy is required for call()"
