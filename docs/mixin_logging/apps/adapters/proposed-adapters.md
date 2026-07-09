# Proposed Adapters for `logging-mixin`

Looking at the existing 8 adapters, here are some natural additions grouped by category.

---

## Inbound HTTP / Edge

- **gRPC** :  extract correlation ID from gRPC metadata (common in microservice meshes alongside HTTP)
- **WebSocket** :  extract from handshake headers; many WS frameworks (Starlette, Django Channels) aren't covered by ASGI alone
- **GraphQL** :  middleware for Strawberry/Ariadne to extract from HTTP headers or inject into resolver context

---

## Outbound / Propagation

- **aiohttp** :  async HTTP client used heavily in older async stacks; fills the gap between httpx and requests
- **urllib3** :  low-level; useful for teams that don't use requests sessions directly
- **httplib2** :  niche but common in Google API clients

---

## Task / Message Queues

- **RQ (Redis Queue)** :  popular lightweight alternative to Celery; same enqueue→worker propagation pattern
- **Dramatiq** :  growing adoption; has a middleware system that maps naturally to your adapter pattern
- **arq** :  async-native Redis task queue for asyncio stacks
- **Kafka (`confluent-kafka` / `aiokafka`)** :  producer injects ID into message headers; consumer extracts on the other side
- **RabbitMQ (`pika` / `aio-pika`)** :  same pattern via AMQP message headers

---

## Cloud / Serverless

- **GCP Cloud Functions / Cloud Run** :  extract from `X-Cloud-Trace-Context` or `traceparent` headers
- **Azure Functions** :  extract from `x-ms-client-request-id` or custom headers
- **AWS Step Functions** :  extract from execution input JSON

---

## Observability / Structured Logging

- **OpenTelemetry** :  bridge your correlation ID into/out of the OTel `traceparent` / W3C Trace Context format; makes `logging-mixin` interoperable with Jaeger, Zipkin, Datadog, etc. :  probably the highest-value addition
- **structlog** :  many teams use structlog instead of stdlib logging; a processor that stamps `correlation_id` into the event dict

---

## Database / ORMs

- **SQLAlchemy** :  inject correlation ID as a SQL comment (e.g. `/* correlation_id=abc123 */`) via the `before_cursor_execute` event; extremely useful for tracing slow queries back to requests
- **asyncpg / psycopg3** :  same idea for raw async drivers

---

> **Highest priority:** The **OpenTelemetry** bridge and **SQLAlchemy** adapter would arguably add the most value, covering observability interop and database traceability :  two gaps the current adapter set doesn't touch at all.
