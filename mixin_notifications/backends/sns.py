"""AWS SNS notification backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mixin_notifications.backends._objects import DeliveryResult
from mixin_notifications.events._objects import NotificationEvent


@dataclass(frozen=True, slots=True)
class SNSBackend:
    """AWS SNS notification backend.

    Requires: boto3>=1.28.0 (installed via [sns] extra).
    """

    sns_client: Any
    default_topic_arn: str

    @property
    def external_egress(self) -> bool:
        """SNS sends data externally to AWS."""
        return True

    def send(self, event: NotificationEvent) -> DeliveryResult:
        """Publish notification to SNS topic."""
        from mixin_notifications.common.constants import events as const

        topic_arn = self.default_topic_arn
        for key, value in event.metadata:
            if key == const.METADATA_KEY_TOPIC_ARN:
                topic_arn = value
                break

        title = event.title
        body = event.body

        message_attributes = {
            "category": {
                "DataType": "String",
                "StringValue": event.category,
            },
            "severity": {
                "DataType": "String",
                "StringValue": event.severity.value,
            },
            "fingerprint": {
                "DataType": "String",
                "StringValue": event.fingerprint,
            },
        }

        if event.correlation_id:
            message_attributes["correlation_id"] = {
                "DataType": "String",
                "StringValue": event.correlation_id,
            }

        try:
            response = self.sns_client.publish(
                TopicArn=topic_arn,
                Subject=title,
                Message=body,
                MessageAttributes=message_attributes,
            )

            message_id = response.get("MessageId", "unknown")
            return DeliveryResult(
                delivered=True,
                backend_name="SNSBackend",
                detail=f"message_id: {message_id}",
                retryable=False,
            )
        except Exception as error:
            error_code = getattr(error, "response", {}).get("Error", {}).get("Code", "")
            retryable_codes = {
                "Throttling",
                "ThrottledException",
                "TooManyRequestsException",
                "ServiceUnavailable",
                "InternalError",
            }
            is_retryable = error_code in retryable_codes

            return DeliveryResult(
                delivered=False,
                backend_name="SNSBackend",
                detail=f"sns_error: {error_code or error.__class__.__name__}",
                retryable=is_retryable,
            )
