"""Tests for CloudCorrelation.from_event() extraction logic."""

from __future__ import annotations

from mixin_logging.adapters.cloud import cloud_objects as objs
from mixin_logging.adapters.constants import cloud as const


class TestCloudCorrelationFromEventApiGateway:
    """Tests for CloudCorrelation.from_event() with API Gateway events."""

    def test_from_event_api_gateway_with_correlation_header_extracts_id(self) -> None:
        """from_event() extracts correlation_id from API Gateway headers."""
        event = {"headers": {"X-Correlation-ID": "api-gw-id-123"}}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.correlation_id == "api-gw-id-123"
        assert correlation.extracted is True

    def test_from_event_api_gateway_case_insensitive_header_extraction(self) -> None:
        """from_event() extracts correlation_id from lowercase header."""
        event = {"headers": {"x-correlation-id": "lowercase-id"}}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.correlation_id == "lowercase-id"
        assert correlation.extracted is True

    def test_from_event_api_gateway_mixed_case_header_extraction(self) -> None:
        """from_event() extracts correlation_id from mixed-case header."""
        event = {"headers": {"X-correlation-ID": "mixed-case-id"}}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.correlation_id == "mixed-case-id"
        assert correlation.extracted is True

    def test_from_event_api_gateway_headers_none_generates_id(self) -> None:
        """from_event() generates id when headers is None."""
        event = {"headers": None}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.extracted is False
        assert len(correlation.correlation_id) == const.GENERATED_ID_LENGTH

    def test_from_event_api_gateway_headers_missing_generates_id(self) -> None:
        """from_event() generates id when headers key missing."""
        event: dict[str, object] = {}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.extracted is False
        assert len(correlation.correlation_id) == const.GENERATED_ID_LENGTH


class TestCloudCorrelationFromEventSQS:
    """Tests for CloudCorrelation.from_event() with SQS events."""

    def test_from_event_sqs_extracts_correlation_from_message_attributes(self) -> None:
        """from_event() extracts correlation_id from SQS messageAttributes."""
        event = {
            "Records": [
                {
                    "messageAttributes": {
                        "X-Correlation-ID": {"stringValue": "sqs-id-456"}
                    }
                }
            ]
        }
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.correlation_id == "sqs-id-456"
        assert correlation.extracted is True

    def test_from_event_sqs_no_attributes_generates_id(self) -> None:
        """from_event() generates id when SQS messageAttributes missing."""
        event: dict[str, object] = {"Records": [{}]}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.extracted is False
        assert len(correlation.correlation_id) == const.GENERATED_ID_LENGTH

    def test_from_event_sqs_empty_records_generates_id(self) -> None:
        """from_event() generates id when Records is empty."""
        event: dict[str, object] = {"Records": []}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.extracted is False
        assert len(correlation.correlation_id) == const.GENERATED_ID_LENGTH


class TestCloudCorrelationFromEventSNS:
    """Tests for CloudCorrelation.from_event() with SNS events."""

    def test_from_event_sns_extracts_correlation_from_message_attributes(self) -> None:
        """from_event() extracts correlation_id from SNS MessageAttributes."""
        event = {
            "Records": [
                {
                    "Sns": {
                        "MessageAttributes": {
                            "X-Correlation-ID": {"Value": "sns-id-789"}
                        }
                    }
                }
            ]
        }
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.correlation_id == "sns-id-789"
        assert correlation.extracted is True

    def test_from_event_sns_no_sns_key_generates_id(self) -> None:
        """from_event() generates id when SNS key missing from record."""
        event: dict[str, object] = {"Records": [{"messageAttributes": {}}]}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.extracted is False
        assert len(correlation.correlation_id) == const.GENERATED_ID_LENGTH

    def test_from_event_sns_no_message_attributes_generates_id(self) -> None:
        """from_event() generates id when MessageAttributes missing."""
        event: dict[str, object] = {"Records": [{"Sns": {}}]}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.extracted is False
        assert len(correlation.correlation_id) == const.GENERATED_ID_LENGTH


class TestCloudCorrelationFromEventBridge:
    """Tests for CloudCorrelation.from_event() with EventBridge events."""

    def test_from_event_eventbridge_extracts_correlation_from_detail(self) -> None:
        """from_event() extracts correlation_id from EventBridge detail."""
        event = {"detail": {"correlation_id": "eventbridge-id"}}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.correlation_id == "eventbridge-id"
        assert correlation.extracted is True

    def test_from_event_eventbridge_no_detail_generates_id(self) -> None:
        """from_event() generates id when detail is None."""
        event = {"detail": None}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.extracted is False
        assert len(correlation.correlation_id) == const.GENERATED_ID_LENGTH

    def test_from_event_eventbridge_detail_missing_generates_id(self) -> None:
        """from_event() generates id when detail key missing."""
        event: dict[str, object] = {}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.extracted is False
        assert len(correlation.correlation_id) == const.GENERATED_ID_LENGTH


class TestCloudCorrelationFromEventTopLevel:
    """Tests for CloudCorrelation.from_event() with top-level correlation_id."""

    def test_from_event_top_level_extracts_correlation_id(self) -> None:
        """from_event() extracts correlation_id from top-level event key."""
        event = {"correlation_id": "toplevel-id"}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.correlation_id == "toplevel-id"
        assert correlation.extracted is True

    def test_from_event_top_level_missing_generates_id(self) -> None:
        """from_event() generates id when top-level correlation_id missing."""
        event: dict[str, object] = {}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.extracted is False
        assert len(correlation.correlation_id) == const.GENERATED_ID_LENGTH


class TestCloudCorrelationFromEventPrecedence:
    """Tests for CloudCorrelation.from_event() source precedence."""

    def test_from_event_headers_takes_precedence_over_records(self) -> None:
        """from_event() prefers headers over Records."""
        event = {
            "headers": {"X-Correlation-ID": "from-headers"},
            "Records": [
                {
                    "messageAttributes": {
                        "X-Correlation-ID": {"stringValue": "from-records"}
                    }
                }
            ],
        }
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.correlation_id == "from-headers"
        assert correlation.extracted is True

    def test_from_event_headers_takes_precedence_over_detail(self) -> None:
        """from_event() prefers headers over detail."""
        event = {
            "headers": {"X-Correlation-ID": "from-headers"},
            "detail": {"correlation_id": "from-detail"},
        }
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.correlation_id == "from-headers"
        assert correlation.extracted is True

    def test_from_event_records_takes_precedence_over_detail(self) -> None:
        """from_event() prefers Records over detail."""
        event = {
            "Records": [
                {
                    "messageAttributes": {
                        "X-Correlation-ID": {"stringValue": "from-records"}
                    }
                }
            ],
            "detail": {"correlation_id": "from-detail"},
        }
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.correlation_id == "from-records"
        assert correlation.extracted is True

    def test_from_event_detail_takes_precedence_over_toplevel(self) -> None:
        """from_event() prefers detail over top-level correlation_id."""
        event = {
            "detail": {"correlation_id": "from-detail"},
            "correlation_id": "from-toplevel",
        }
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.correlation_id == "from-detail"
        assert correlation.extracted is True


class TestCloudCorrelationFromEventUnsafeFallback:
    """Tests for CloudCorrelation.from_event() fallback on unsafe values."""

    def test_from_event_header_with_crlf_generates_id(self) -> None:
        """from_event() generates id when header value contains CRLF."""
        event = {"headers": {"X-Correlation-ID": "bad\r\nvalue"}}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.extracted is False
        assert len(correlation.correlation_id) == const.GENERATED_ID_LENGTH

    def test_from_event_header_with_null_byte_generates_id(self) -> None:
        """from_event() generates id when header value contains null byte."""
        event = {"headers": {"X-Correlation-ID": "bad\x00value"}}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.extracted is False
        assert len(correlation.correlation_id) == const.GENERATED_ID_LENGTH

    def test_from_event_header_overlong_generates_id(self) -> None:
        """from_event() generates id when header value exceeds length cap."""
        overlong_id = "a" * 129
        event = {"headers": {"X-Correlation-ID": overlong_id}}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.extracted is False
        assert len(correlation.correlation_id) == const.GENERATED_ID_LENGTH

    def test_from_event_header_empty_generates_id(self) -> None:
        """from_event() generates id when header value is empty string."""
        event = {"headers": {"X-Correlation-ID": ""}}
        correlation = objs.CloudCorrelation.from_event(event)
        assert correlation.extracted is False
        assert len(correlation.correlation_id) == const.GENERATED_ID_LENGTH
