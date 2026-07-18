"""Cross-cutting test constants shared across apps (not exported in PUBLIC_API)."""

from __future__ import annotations

from typing import Final

"""Event base names used in @logged decorator tests."""

EVENT_PROCESS: Final = "process"
EVENT_AUDIT: Final = "audit"
EVENT_VALIDATE: Final = "validate"


"""Expected log-event strings emitted by @logged."""

EVENT_PROCESS_START: Final = "process.start"
EVENT_PROCESS_END: Final = "process.end"
EVENT_PROCESS_ERROR: Final = "process.error"
EVENT_AUDIT_START: Final = "audit.start"
EVENT_AUDIT_END: Final = "audit.end"
EVENT_AUDIT_ERROR: Final = "audit.error"
EVENT_VALIDATE_START: Final = "validate.start"
EVENT_VALIDATE_END: Final = "validate.end"
EVENT_VALIDATE_ERROR: Final = "validate.error"


"""Correlation ID test values."""

CORRELATION_ID_TRACE: Final = "test-trace-123"
CORRELATION_ID_TEST: Final = "test-id"
CORRELATION_ID_CUSTOM: Final = "correlation-456"
CORRELATION_ID_FIRST: Final = "first-id"
CORRELATION_ID_SECOND: Final = "second-id"
CORRELATION_ID_SOMETHING: Final = "something"
CORRELATION_ID_SOME: Final = "some-id"
CORRELATION_ID_ID1: Final = "id-1"
CORRELATION_ID_ID2: Final = "id-2"
CORRELATION_ID_ABC: Final = "abc"
CORRELATION_ID_XYZ: Final = "trace-xyz"
CORRELATION_ID_XYZ_SHORT: Final = "trace-abc"


"""Unset correlation ID sentinel."""

UNSET_CORRELATION_MARKER: Final = "-"


"""Custom exception error code."""

ERROR_CODE_CUSTOM: Final = "ERR_CUSTOM"


"""Log record extra-fields for caller kwargs."""

FIELD_USER_ID: Final = "user_id"
FIELD_ACTION: Final = "action"
FIELD_CUSTOM: Final = "custom"
FIELD_MASKED: Final = "masked"
FIELD_INSTANCE: Final = "instance"
FIELD_EXTRA: Final = "extra"


"""Sample field values."""

USER_ID_42: Final = "user-42"
ACTION_CREATE: Final = "create"
USER_ID_GENERIC: Final = "42"


"""Additional correlation ID test values for adapter/WSGI/ASGI."""

CORRELATION_ID_VALID_ID_123: Final = "valid-id-123"
CORRELATION_ID_HEX: Final = "a1b2c3d4e5f6"
CORRELATION_ID_SHOULD_BE_CLEARED: Final = "should-be-cleared"
CORRELATION_ID_ABC_123: Final = "abc-123"
CORRELATION_ID_PRESET_ID_123: Final = "preset-id-123"
CORRELATION_ID_TEST_ID_456: Final = "test-id-456"


"""HTTP-related test constants."""

HTTP_STATUS_200_OK: Final = "200 OK"
HTTP_HEADER_CONTENT_TYPE: Final = "content-type"
HTTP_MIME_TEXT_PLAIN: Final = "text/plain"
HTTP_EVENT_RESPONSE_START: Final = "http.response.start"
HTTP_EVENT_RESPONSE_BODY: Final = "http.response.body"
HTTP_EVENT_REQUEST: Final = "http.request"


"""Exception match strings for pytest.raises()."""

RAISE_MATCH_BOOM: Final = "boom"
RAISE_MATCH_TEST_ERROR: Final = "test error"
RAISE_MATCH_LOGGED_CONTAINER_EVENT_EMPTY: Final = (
    "LoggedContainer.event must be non-empty"
)


"""Logger names for testing."""

LOGGER_NAME_TEST: Final = "test"
LOGGER_NAME_CUSTOM: Final = "custom_logger"
LOGGER_NAME_RECORD_COLLECTOR_ATTACHED: Final = "test_record_collector.attached"


"""Log record messages and text."""

RECORD_MSG_HELLO: Final = "hello"
RECORD_MSG_WARNING_TEXT: Final = "warning text"
RECORD_MSG_CAPTURED: Final = "captured message"
RECORD_MSG_PREFIX: Final = "msg-"
RECORD_LINE_NO_42: Final = 42


"""Log level names."""

LOG_LEVEL_WARNING: Final = "WARNING"
LOG_LEVEL_INFO: Final = "INFO"


"""Httpx adapter test constants."""

HTTPX_CORR_ID_SAFE: Final = "safe-id-123"
HTTPX_CORR_ID_TEST: Final = "test-id-456"
HTTPX_CORR_ID_ASYNC: Final = "async-id"
HTTPX_CORR_ID_XYZ: Final = "id-xyz"


"""Error message test constants for @logged decorator tests."""

ERROR_MSG_CUSTOM_WORK_FAILED: Final = "something went wrong"
ERROR_MSG_RUNTIME_NO_CODE: Final = "runtime error without code"
