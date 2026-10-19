# mixin-suite Documentation

This directory holds the documentation for the five composable roots that make up mixin-suite. The top-level [README](../README.md) has installation and run-verified quick starts.

## mixin_logging

**Correlation-ID propagation across framework adapters for distributed systems.**

- **[Architecture](mixin_logging/architecture/architecture.md)**: system design, correlation context propagation and integration patterns
- **[Adapters](mixin_logging/apps/adapters/)**: instrumentation for ASGI, WSGI, gRPC, GraphQL, Celery, Botocore, Requests, HTTPX, aiohttp, urllib3, WebSocket, Cloud, FastAPI and Stdlib
  - [ASGI Adapter](mixin_logging/apps/adapters/asgi.md)
  - [WSGI Adapter](mixin_logging/apps/adapters/wsgi.md)
  - [gRPC Adapter](mixin_logging/apps/adapters/grpc.md)
  - [GraphQL Adapter](mixin_logging/apps/adapters/graphql.md)
  - [Celery Adapter](mixin_logging/apps/adapters/celery.md)
  - [Botocore Adapter](mixin_logging/apps/adapters/botocore.md)
  - [Requests Adapter](mixin_logging/apps/adapters/requests.md)
  - [HTTPX Adapter](mixin_logging/apps/adapters/httpx.md)
  - [aiohttp Adapter](mixin_logging/apps/adapters/aiohttp.md)
  - [urllib3 Adapter](mixin_logging/apps/adapters/urllib3.md)
  - [WebSocket Adapter](mixin_logging/apps/adapters/websocket.md)
  - [Cloud Adapter](mixin_logging/apps/adapters/cloud.md)
  - [Stdlib Adapter](mixin_logging/apps/adapters/stdlib.md)
  - [Flush-on-Warning Handler](mixin_logging/apps/adapters/flush-handler.md)
- **[Correlation Context](mixin_logging/apps/context/correlation.md)**: ContextVar-based correlation ID propagation
- **[LoggingMixin](mixin_logging/apps/mixin/mixin.md)**: base class providing log_info(), log_debug(), log_warning(), log_error() and log_exception()
- **[Redaction](mixin_logging/redaction/README.md)**: log-record masking for sensitive field names
- **[Security Audit](mixin_logging/apps/security-audit.md)**: CRLF injection prevention, sanitization and adapter safety
- **[Historical Changelog](mixin_logging/CHANGELOG-history.md)**: release notes for prior versions of mixin-logging

## mixin_sensitivity

**Sensitivity classification and repr masking for frozen dataclasses.**

- **[Status](mixin_sensitivity/STATUS.md)**: current feature coverage
- **[Architecture](mixin_sensitivity/architecture/architecture.md)**: package scope, public API and integration patterns
- **[Flow Trace](mixin_sensitivity/architecture/flow-trace.md)**: how the repr masking and classification run
- **[SensitiveRepr](mixin_sensitivity/apps/decorators/sensitive.md)**: adoption mixin that masks marked fields in repr output
- **[Diagrams](mixin_sensitivity/apps/diagrams.md)**: module layout and flows
- **[Classification source](../mixin_sensitivity/services/classify/classify_objects.py)**: Sensitivity taxonomy and SensitivityProfile
- **[Archived policy pages](mixin_sensitivity/apps/decorators/policies.md)**: policy value objects removed in 0.5.0
- **[Historical Changelog](mixin_sensitivity/CHANGELOG-history.md)**: release notes for prior versions of mixin-sensitivity

## mixin_retry

**Exponential backoff with jitter, driven by RetryPolicy and RetryExecutor.**

- **[README](mixin_retry/README.md)**: usage, parameters and run-verified example
- **[Flow Trace](mixin_retry/architecture/flow-trace.md)**: how the retry loop and backoff run
- **[Optimization Pass Audit](mixin_retry/audits/2026-10-19-optimization-pass.md)**: 0.7.0 changes and gate results

## mixin_latency

**Elapsed-time measurement with a perf_counter-backed clock.** The API is documented in the top-level [README](../README.md#public-api) and its run-verified examples.

## mixin_notifications

**Notification events, backends, guarded dispatch, suppression and an egress gate.**

- **[README](mixin_notifications/README.md)**: service-class, attachment, retry and AWS backend examples, with the egress-gate limitation
- **[Flow Trace](mixin_notifications/architecture/flow-trace.md)**: dispatch, egress gate and retry flows
- **[Security Audit](mixin_notifications/audits/2026-07-29-0.6.0-delivery-security-audit.md)**: 0.6.0 delivery semantics audit
- **[Architecture Review](mixin_notifications/reviews/2026-07-29-0.6.0-delivery-architecture-review.md)**: design and backward compatibility review

## Security and Code Reviews

- [mixin-logging audits](mixin_logging/audits/): per-adapter and cross-feature security assessments
- [mixin-logging reviews](mixin_logging/reviews/): code review findings and their resolution
- [mixin-sensitivity audits](mixin_sensitivity/audits/): decorator-layer security analysis (historical) and the 0.7.0 optimization pass
- [mixin-sensitivity reviews](mixin_sensitivity/reviews/): code review findings and their resolution (historical)
- [mixin-retry audits](mixin_retry/audits/): 0.7.0 optimization pass
- [mixin-notifications audits](mixin_notifications/audits/) and [reviews](mixin_notifications/reviews/): 0.6.0 delivery records and the 0.7.0 optimization pass

## Getting Started

- See `README.md` in the repository root for installation and quick-start examples.
- See `CONTRIBUTING.md` for development setup and testing procedures.
- See `SECURITY.md` for vulnerability reporting.
