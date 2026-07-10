"""Tests for CloudSetup client."""

from __future__ import annotations

from typing import Any

from mixin_logging import get_correlation_id
from mixin_logging.adapters.cloud import cloud_client


class TestCloudSetupSetupCorrelationIdApiGateway:
    """Tests for CloudSetup.setup_correlation_id() with API Gateway events."""

    def test_setup_correlation_id_api_gateway_returns_extracted_id(self) -> None:
        """setup_correlation_id() returns extracted correlation_id and sets context."""
        event = {"headers": {"X-Correlation-ID": "api-gw-extracted"}}
        correlation_id = cloud_client.CloudSetup.setup_correlation_id(event)
        assert correlation_id == "api-gw-extracted"
        assert get_correlation_id() == "api-gw-extracted"

    def test_setup_correlation_id_api_gateway_case_insensitive(self) -> None:
        """setup_correlation_id() extracts correlation_id with lowercase header."""
        event = {"headers": {"x-correlation-id": "lowercase-extracted"}}
        correlation_id = cloud_client.CloudSetup.setup_correlation_id(event)
        assert correlation_id == "lowercase-extracted"
        assert get_correlation_id() == "lowercase-extracted"

    def test_setup_correlation_id_api_gateway_with_context_param(self) -> None:
        """setup_correlation_id() accepts optional context parameter."""
        event = {"headers": {"X-Correlation-ID": "api-gw-with-context"}}
        dummy_context = object()
        correlation_id = cloud_client.CloudSetup.setup_correlation_id(
            event,
            context=dummy_context,
        )
        assert correlation_id == "api-gw-with-context"
        assert get_correlation_id() == "api-gw-with-context"


class TestCloudSetupSetupCorrelationIdSQS:
    """Tests for CloudSetup.setup_correlation_id() with SQS events."""

    def test_setup_correlation_id_sqs_returns_extracted_id(self) -> None:
        """setup_correlation_id() returns extracted SQS correlation_id."""
        event = {
            "Records": [
                {
                    "messageAttributes": {
                        "X-Correlation-ID": {"stringValue": "sqs-extracted"}
                    }
                }
            ]
        }
        correlation_id = cloud_client.CloudSetup.setup_correlation_id(event)
        assert correlation_id == "sqs-extracted"
        assert get_correlation_id() == "sqs-extracted"

    def test_setup_correlation_id_sqs_with_context_param(self) -> None:
        """setup_correlation_id() accepts context param with SQS event."""
        event = {
            "Records": [
                {
                    "messageAttributes": {
                        "X-Correlation-ID": {"stringValue": "sqs-with-context"}
                    }
                }
            ]
        }
        dummy_context = object()
        correlation_id = cloud_client.CloudSetup.setup_correlation_id(
            event,
            context=dummy_context,
        )
        assert correlation_id == "sqs-with-context"
        assert get_correlation_id() == "sqs-with-context"


class TestCloudSetupSetupCorrelationIdSNS:
    """Tests for CloudSetup.setup_correlation_id() with SNS events."""

    def test_setup_correlation_id_sns_returns_extracted_id(self) -> None:
        """setup_correlation_id() returns extracted SNS correlation_id."""
        event = {
            "Records": [
                {
                    "Sns": {
                        "MessageAttributes": {
                            "X-Correlation-ID": {"Value": "sns-extracted"}
                        }
                    }
                }
            ]
        }
        correlation_id = cloud_client.CloudSetup.setup_correlation_id(event)
        assert correlation_id == "sns-extracted"
        assert get_correlation_id() == "sns-extracted"

    def test_setup_correlation_id_sns_with_context_param(self) -> None:
        """setup_correlation_id() accepts context param with SNS event."""
        event = {
            "Records": [
                {
                    "Sns": {
                        "MessageAttributes": {
                            "X-Correlation-ID": {"Value": "sns-with-context"}
                        }
                    }
                }
            ]
        }
        dummy_context = object()
        correlation_id = cloud_client.CloudSetup.setup_correlation_id(
            event,
            context=dummy_context,
        )
        assert correlation_id == "sns-with-context"
        assert get_correlation_id() == "sns-with-context"


class TestCloudSetupSetupCorrelationIdEventBridge:
    """Tests for CloudSetup.setup_correlation_id() with EventBridge events."""

    def test_setup_correlation_id_eventbridge_returns_extracted_id(self) -> None:
        """setup_correlation_id() returns extracted EventBridge correlation_id."""
        event = {"detail": {"correlation_id": "eventbridge-extracted"}}
        correlation_id = cloud_client.CloudSetup.setup_correlation_id(event)
        assert correlation_id == "eventbridge-extracted"
        assert get_correlation_id() == "eventbridge-extracted"

    def test_setup_correlation_id_eventbridge_with_context_param(self) -> None:
        """setup_correlation_id() accepts context param with EventBridge event."""
        event = {"detail": {"correlation_id": "eventbridge-with-context"}}
        dummy_context = object()
        correlation_id = cloud_client.CloudSetup.setup_correlation_id(
            event,
            context=dummy_context,
        )
        assert correlation_id == "eventbridge-with-context"
        assert get_correlation_id() == "eventbridge-with-context"


class TestCloudSetupSetupCorrelationIdTopLevel:
    """Tests for CloudSetup.setup_correlation_id() with top-level correlation_id."""

    def test_setup_correlation_id_toplevel_returns_extracted_id(self) -> None:
        """setup_correlation_id() returns extracted top-level correlation_id."""
        event = {"correlation_id": "toplevel-extracted"}
        correlation_id = cloud_client.CloudSetup.setup_correlation_id(event)
        assert correlation_id == "toplevel-extracted"
        assert get_correlation_id() == "toplevel-extracted"

    def test_setup_correlation_id_toplevel_with_context_param(self) -> None:
        """setup_correlation_id() accepts context param with top-level event."""
        event = {"correlation_id": "toplevel-with-context"}
        dummy_context = object()
        correlation_id = cloud_client.CloudSetup.setup_correlation_id(
            event,
            context=dummy_context,
        )
        assert correlation_id == "toplevel-with-context"
        assert get_correlation_id() == "toplevel-with-context"


class TestCloudSetupSetupCorrelationIdGenerated:
    """Tests for CloudSetup.setup_correlation_id() with generated IDs."""

    def test_setup_correlation_id_empty_event_returns_generated_id(self) -> None:
        """setup_correlation_id() generates and sets correlation_id for empty event."""
        event: dict[str, Any] = {}
        correlation_id = cloud_client.CloudSetup.setup_correlation_id(event)
        assert isinstance(correlation_id, str)
        assert len(correlation_id) == 12
        assert get_correlation_id() == correlation_id

    def test_setup_correlation_id_unsafe_header_returns_generated_id(self) -> None:
        """setup_correlation_id() generates id when header value is unsafe."""
        event = {"headers": {"X-Correlation-ID": "bad\r\nvalue"}}
        correlation_id = cloud_client.CloudSetup.setup_correlation_id(event)
        assert isinstance(correlation_id, str)
        assert len(correlation_id) == 12
        assert get_correlation_id() == correlation_id

    def test_setup_correlation_id_generated_with_context_param(self) -> None:
        """setup_correlation_id() generates id and accepts context param."""
        event: dict[str, Any] = {}
        dummy_context = object()
        correlation_id = cloud_client.CloudSetup.setup_correlation_id(
            event,
            context=dummy_context,
        )
        assert isinstance(correlation_id, str)
        assert len(correlation_id) == 12
        assert get_correlation_id() == correlation_id

    def test_setup_correlation_id_generated_ids_are_unique(self) -> None:
        """setup_correlation_id() generates unique IDs for different calls."""
        event1: dict[str, Any] = {}
        event2: dict[str, Any] = {}
        id1 = cloud_client.CloudSetup.setup_correlation_id(event1)
        id2 = cloud_client.CloudSetup.setup_correlation_id(event2)
        assert id1 != id2
