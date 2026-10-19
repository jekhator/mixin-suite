"""Constants for notification backends. Imported as const."""

from typing import Final

RETRYING_BACKEND_NAME: Final = "RetryingBackend"
RETRY_EXHAUSTED_DETAIL: Final = "exhausted retries"
RETRY_NON_RETRYABLE_DETAIL: Final = "non-retryable exception"
DEAD_LETTER_FAILED_DETAIL: Final = "dead_letter failed"
DEAD_LETTER_OUTCOME_DETAIL: Final = "dead_letter outcome"
RETRYABLE_AWS_ERROR_CODES: Final = frozenset(
    {
        "Throttling",
        "ThrottledException",
        "TooManyRequestsException",
        "ServiceUnavailable",
        "InternalError",
    },
)
