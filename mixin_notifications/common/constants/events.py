"""Constants for NotificationEvent validation."""

ERR_NOTIFICATION_EMPTY_CATEGORY = "category must be non-empty"
ERR_NOTIFICATION_EMPTY_TITLE = "title must be non-empty"
ERR_NOTIFICATION_EMPTY_FINGERPRINT = "fingerprint must be non-empty"
ERR_ATTACHMENT_EMPTY_FILENAME = "attachment filename must be non-empty"
ERR_ATTACHMENT_EMPTY_CONTENT_TYPE = "attachment content_type must be non-empty"

EGRESS_TITLE_TEMPLATE = "{category}: {severity} notification"
EGRESS_REDACTED_BODY = "[content redacted for external delivery]"
EGRESS_COUNT_METADATA_KEY = "sensitive_count_metadata"
METADATA_KEY_TOPIC_ARN = "topic_arn"
