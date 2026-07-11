# mixin-suite Documentation

This directory contains comprehensive documentation for the two composable mixins that make up mixin-suite:

## mixin-logging

**End-to-end correlation-ID propagation across 13 adapters for distributed systems.**

- **[Architecture](mixin_logging/architecture/architecture.md)**: System design, correlation context propagation, and integration patterns
- **[Adapters](mixin_logging/apps/adapters/)**: Instrumentation for ASGI, WSGI, gRPC, GraphQL, Celery, Botocore, Requests, HTTPX, aiohttp, urllib3, WebSocket, Cloud, and Stdlib
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
- **[Decorators](mixin_logging/apps/decorators/logged.md)**: Class-level and method-level @logged decorators
- **[Correlation Context](mixin_logging/apps/context/correlation.md)**: ContextVar-based correlation ID propagation
- **[LoggingMixin](mixin_logging/apps/mixin/mixin.md)**: Base class providing log_info(), log_debug(), and @logged support
- **[Security Audit](mixin_logging/apps/security-audit.md)**: CRLF injection prevention, sanitization, and adapter safety
- **[Historical Changelog](mixin_logging/CHANGELOG-history.md)**: Release notes for prior versions of mixin-logging

## mixin-sensitivity

**Decorator-based sensitivity classification and masking for frozen dataclasses.**

- **[Architecture](mixin_sensitivity/architecture/architecture.md)**: System design and masking strategy
- **[Sensitive Decorator](mixin_sensitivity/apps/decorators/sensitive.md)**: Class-level decorator enabling automatic masking
- **[Compliance Policies](mixin_sensitivity/apps/decorators/compliance.md)**: Taxonomy-driven field classification
- **[Classification API](mixin_sensitivity/apps/decorators/policies.md)**: Policy enforcement and introspection
- **[Classify Service](mixin_sensitivity/services/classify.py)**: Field introspection and sensitivity profile generation (PHI, PII, PCI, SECRET)
- **[Status](mixin_sensitivity/STATUS.md)**: Current feature coverage and known limitations
- **[Historical Changelog](mixin_sensitivity/CHANGELOG-history.md)**: Release notes for prior versions of mixin-sensitivity

## Security & Code Reviews

- [mixin-logging audits](mixin_logging/audits/): Per-adapter and cross-feature security assessments
- [mixin-logging reviews](mixin_logging/reviews/): Code review findings and resolution
- [mixin-sensitivity audits](mixin_sensitivity/audits/): Decorator and classification layer security analysis
- [mixin-sensitivity reviews](mixin_sensitivity/reviews/): Code review findings and resolution

## Getting Started

- See `README.md` in the repository root for installation and quick-start examples.
- See `CONTRIBUTING.md` for development setup and testing procedures.
- See `SECURITY.md` for vulnerability reporting.
