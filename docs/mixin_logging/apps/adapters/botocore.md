# logging-mixin. Botocore Adapter

> **Location:** `logging-mixin/docs/apps/adapters/botocore.md`
> **Status:** Implemented. Outbound AWS SDK correlation-ID propagation via the botocore `before-sign` event.
> **Code location:** `mixin_logging/adapters/botocore/` (`botocore_objects.py` + `botocore_client.py`); constants in `mixin_logging/adapters/constants/botocore.py`.
> **Diagrams:** `docs/apps/adapters/diagrams.md` (Botocore Subsystem Structure).
> **Sibling docs:** `docs/apps/adapters/asgi.md`, `docs/apps/context/correlation.md`.

## Purpose

Propagate the current correlation ID onto outbound AWS SDK requests (boto3 / botocore / aiobotocore) so a single inbound request can be traced through every downstream AWS call (Bedrock, Textract, Comprehend, S3, and the rest) and into CloudTrail.

## Category

Outbound Propagation, the same category as the httpx and requests adapters, specialized for the AWS SDK rather than a raw HTTP client.

## Behavior

- `CorrelationIdInjector.register_on_session(session)` subscribes the handler on a botocore `Session` event emitter, which affects every client built from that session.
- `CorrelationIdInjector.register_on_client(client)` scopes it to a single boto3 client via `client.meta.events`.
- Both register against the `before-sign` event so `X-Correlation-ID` is injected into the canonical request before SigV4 signing, and is therefore covered by the signature. Registering at `before-send` would leave the header unsigned and strippable.
- On each outbound request the handler reads the current correlation ID from the `ContextVar` via `BotocoreCorrelation.from_context()`. If it is unset or unsafe the handler is a no-op; otherwise it sets the header on the `AWSRequest`, using `replace_header` when the key already exists to avoid duplicate entries in botocore's `HTTPHeaders` mapping.

## Value Object

`BotocoreCorrelation` (frozen, slots) captures the `correlation_id` bound for the outbound header:

- `from_context()`. read the ContextVar; returns `None` if unset or unsafe (no raise).
- `header_tuple`. returns `(CORRELATION_ID_HEADER, correlation_id)`.
- `__post_init__` + `_is_safe`. reject empty values, values over 128 chars, and values containing CR / LF / null.

## Constants

`mixin_logging/adapters/constants/botocore.py`:

- `CORRELATION_ID_HEADER = "X-Correlation-ID"` (matches inbound ASGI/WSGI for round-trip consistency)
- `CORRELATION_ID_MAX_LENGTH = 128`
- `BEFORE_SIGN_EVENT = "before-sign"`
- `UNSAFE_HEADER_CHARS = frozenset({"\r", "\n", "\0"})`
- `ERR_CORRELATION_ID_UNSAFE`

## Installation

Install the `botocore` optional dependency:

```bash
uv add "logging-mixin[botocore]"
```

Or with pip:

```bash
pip install "logging-mixin[botocore]"
```

## Compatibility

boto3 / botocore sync clients; aiobotocore shares the same (synchronous) event emitter. The adapter is duck-typed against the botocore event system, and any caller already has the AWS SDK installed.

## Example Usage

```python
import boto3
from mixin_logging.adapters.botocore.botocore_client import CorrelationIdInjector

client = boto3.client("bedrock-runtime", region_name="us-east-1")
CorrelationIdInjector.register_on_client(client)
# Every call now carries X-Correlation-ID into the signed request (and CloudTrail)
client.invoke_model(modelId="...", body=b"...")
```

## See Also

- **Adapters overview / ASGI:** `docs/apps/adapters/asgi.md`
- **Diagram:** `docs/apps/adapters/diagrams.md`
- **Correlation Context:** `docs/apps/context/correlation.md`
