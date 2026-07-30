"""AWS SES notification backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mixin_notifications.backends._objects import DeliveryResult, NotificationBackend
from mixin_notifications.events._objects import NotificationEvent


@dataclass(frozen=True, slots=True)
class SESBackend:
    """AWS SES notification backend with attachment support.

    Requires: boto3>=1.28.0 (installed via [ses] extra).
    """

    ses_client: Any
    to_addresses: tuple[str, ...]
    from_address: str

    @property
    def external_egress(self) -> bool:
        """SES sends data externally to AWS."""
        return True

    def send(self, event: NotificationEvent) -> DeliveryResult:
        """Send notification email via SES with attachments."""
        from email import encoders
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        try:
            msg = MIMEMultipart()
            msg["Subject"] = event.title
            msg["From"] = self.from_address
            msg["To"] = ", ".join(self.to_addresses)

            msg.attach(MIMEText(event.body, "plain"))

            for attachment in event.attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {attachment.filename}",
                )
                msg.attach(part)

            response = self.ses_client.send_raw_email(
                RawMessage={"Data": msg.as_string()}
            )

            message_id = response.get("MessageId", "unknown")
            return DeliveryResult(
                delivered=True,
                backend_name="SESBackend",
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
                backend_name="SESBackend",
                detail=f"ses_error: {error_code or error.__class__.__name__}",
                retryable=is_retryable,
            )
