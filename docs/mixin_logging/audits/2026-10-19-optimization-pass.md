# Optimization pass audit (2026-10-19)

## Purpose

This document records an optimization pass over every source module under mixin_logging (84 files, excluding the tests tree). The pass looked for correctness defects, dead and duplicated code, control-flow simplifications, typing precision, constants placement, naming, per-request performance in the adapter wrappers, and docs truth. Each file in scope is listed below with its findings, whether it changed, and a note. Public names, adapter entry points, configuration keys, event names and log message text are unchanged except for the three fixes listed under Behavior changes.

## Method

- Scope: all .py files under mixin_logging/ except mixin_logging/**/tests, 84 files, 2,592 lines before the pass.
- Lenses: correctness, dead and duplicated code, control flow, typing, constants, naming, formatting, performance, tests (only where a changed behavior needed a test update), docs truth.
- Verification of findings: defects were confirmed with small scripts run against the unchanged tree on Python 3.12 and 3.14 before any edit. Each fix was re-run through the probe after the edit.
- Changes were committed one concern directory or adapter group at a time, each after the local gates passed.

## Summary

- Files reviewed: 84
- Files changed: 24
- Files unchanged: 60 (each with its findings and reason recorded in the table)
- Findings by lens (a file can carry more than one): performance 16, correctness 7, typing 6, constants 6, dead code 5, duplication 2, control flow 1, naming 1, docs 1
- Formatting: no formatting findings; the ruff format carve-out list is unchanged.

## Behavior changes

1. Correlation context in new threads. The correlation context variable was created without a default and set only at import time in the importing thread. A thread or context started afterwards raised LookupError on the first read, which affected every log call made through the mixin, the stdlib filter and the flush handler in that thread. The variable now defaults to an unset context. Set and clear behavior is unchanged.
2. WSGI empty correlation header. An empty X-Correlation-ID request header raised ValueError from the value object, failing the request. The WSGI value object now treats an empty value as absent and generates a new identifier, matching the ASGI adapter.
3. Flush handler eviction. The handler kept a separate eviction-order sequence that retained entries for buffers already evicted by TTL. A correlation whose buffer had expired and then reappeared was evicted by its stale entry on the next capacity check, and the records it had just buffered were dropped. Eviction now follows the creation order of the live buffers. The obsolete defensive branch and the order sequence are removed.

Module-path changes (no names exported from the package root changed): the flush handler defaults, validation messages and the null correlation key moved from the flush handler modules to the stdlib constants module under the const alias. Code that imported those names by their old module path must switch to the constants module. The default sensitive-field patterns moved to the redaction constants module with the same contents.

## Candidates not applied

These were found during the pass and left unchanged, either because the change alters behavior beyond the objective or because it needs a design decision or a test change in another leg.

- gRPC context lifetime: the interceptor sets and clears the correlation context around continuation(), which returns the handler; the handler executes after the context is cleared. The adapter document says the handler sees the context. A fix needs the handler methods wrapped; this is a design change.
- WSGI middleware generator: the middleware body is a generator, so the context is set only when the response is iterated and cleared only on exhaustion or close.
- WebSocket identifier decoding ignores undecodable bytes instead of rejecting the header, which can silently alter an identifier.
- Redaction default pattern "key" matches substrings such as "keyword", which over-redacts. Changing it alters output.
- Logger resolution in the mixin runs on every log call; caching per class would save a lookup but changes when the logger is created.
- Module-level aliases in the correlation and ambient modules (get_correlation_id and the log_* functions) are public names; a container form would need a public-surface decision.
- Typing of the WebSocket middleware with the ASGI aliases: the adapter tests pass untyped fakes that fail strict typing; the test fakes need retyping first.
- Unused constant RESPONSE_STATUS_KEY in the ASGI constants, and the empty decorators packages, are removal candidates for a later leg.
- The docs for the flush handler and the gRPC adapter contain statements that the pass did not change: the flush handler compatibility note names Python 3.11, and the gRPC note is described above.

## Gate results

Local gates on the branch after the final code commit (Python 3.12 and 3.14 as the workflows name them):

- pytest with coverage and a 100 percent floor: 598 passed on 3.12 and 598 passed on 3.14; coverage 100 percent; statements 1,596 (before the pass 1,609); branches 232 (before 238). The test count is unchanged because no test was added or removed; one test was renamed and its assertion tightened.
- ruff check: all checks passed.
- ruff format check with the repository exclusion: 227 files already formatted.
- mypy over the five roots: no issues in 228 source files.
- strict-module over the five roots: exit status 0 with no violations.
- loc-cap over the 34 listed directories: all within the cap.
- Markdown dash check: no matches in the repository.
- Attribution check over the branch commits: no matches.

The test results for the tests tree are appended by the follow-up pass.

## Per-file table

Each source file under mixin_logging (excluding tests) appears once. Findings carry a lens tag in brackets.

| Path | Findings | Changed | Note |
| --- | --- | --- | --- |
| mixin_logging/__init__.py | none | no | Curated public API; exports unchanged. |
| mixin_logging/adapters/__init__.py | none | no | Package docstring only. |
| mixin_logging/adapters/aiohttp/__init__.py | none | no | Re-exports only. |
| mixin_logging/adapters/aiohttp/aiohttp_client.py | none | no | Stateless TraceConfig surface; already minimal. |
| mixin_logging/adapters/aiohttp/aiohttp_objects.py | [perf] per-character generator in the safety check; from_context validates twice (kept as the invariant guard) | yes | Set disjointness test; from_context check kept for the None path. |
| mixin_logging/adapters/asgi/__init__.py | none | no | Re-exports; ASGIApp stays exported. |
| mixin_logging/adapters/asgi/asgi_client.py | [perf] wrapper object built per request only to set the context and call the app | yes | Middleware sets the context and awaits the app directly; ASGIApp kept as public API. |
| mixin_logging/adapters/asgi/asgi_objects.py | [perf] per-character generator in the safety check | yes | Set disjointness test; aliases unchanged. |
| mixin_logging/adapters/botocore/__init__.py | none | no | Re-exports only. |
| mixin_logging/adapters/botocore/botocore_client.py | [typing] Any for botocore session, client and request objects (dependency ships no stubs) | no | No concrete type available without stubs; left as Any. |
| mixin_logging/adapters/botocore/botocore_objects.py | [perf] per-character generator in the safety check | yes | Set disjointness test. |
| mixin_logging/adapters/celery/__init__.py | none | no | Re-exports only. |
| mixin_logging/adapters/celery/celery_client.py | [constants] literal request-headers attribute name where a constant exists | yes | Uses the adapter constant; behavior unchanged. |
| mixin_logging/adapters/celery/celery_objects.py | [perf] per-character generator in the safety check | yes | Set disjointness test. |
| mixin_logging/adapters/cloud/__init__.py | none | no | Re-exports only. |
| mixin_logging/adapters/cloud/cloud_client.py | [typing] context argument typed Any with a noqa (cloud function context object) | no | Kept; the runtime context type is provider-defined. |
| mixin_logging/adapters/cloud/cloud_objects.py | [perf] per-character generator in the safety check | yes | Set disjointness test; event extraction order unchanged. |
| mixin_logging/adapters/constants/__init__.py | none | no | Package docstring only. |
| mixin_logging/adapters/constants/aiohttp.py | none | no | Constants only. |
| mixin_logging/adapters/constants/asgi.py | [dead] RESPONSE_STATUS_KEY has no source reference (test references only) | no | Candidate for removal with a test update in a later leg. |
| mixin_logging/adapters/constants/botocore.py | none | no | Constants only. |
| mixin_logging/adapters/constants/celery.py | none | no | TASK_REQUEST_HEADERS_ATTR now used by the client. |
| mixin_logging/adapters/constants/cloud.py | none | no | Constants only. |
| mixin_logging/adapters/constants/fastapi.py | none | no | Constants only. |
| mixin_logging/adapters/constants/graphql.py | none | no | Constants only. |
| mixin_logging/adapters/constants/grpc.py | [naming] UNSAFE_CHARS spelled differently from UNSAFE_HEADER_CHARS elsewhere | no | Name kept; it is part of the module surface. |
| mixin_logging/adapters/constants/httpx.py | none | no | Constants only. |
| mixin_logging/adapters/constants/requests.py | none | no | Constants only. |
| mixin_logging/adapters/constants/stdlib.py | [constants] flush-handler defaults, validation messages and null key defined in the objects module | yes | Moved here under the const alias. |
| mixin_logging/adapters/constants/urllib3.py | none | no | Constants only. |
| mixin_logging/adapters/constants/websocket.py | none | no | Constants only. |
| mixin_logging/adapters/constants/wsgi.py | none | no | Constants only. |
| mixin_logging/adapters/fastapi/__init__.py | none | no | Re-exports only. |
| mixin_logging/adapters/fastapi/constants.py | none | no | Constants only. |
| mixin_logging/adapters/fastapi/fastapi_client.py | [perf] header mapping copied per request; [control] in-function import on every dependency call | yes | Reads the request headers mapping directly (verified with a live request); module-level import. |
| mixin_logging/adapters/fastapi/fastapi_objects.py | [perf] per-character generator in the safety check; [typing] header argument typed as dict | yes | Set disjointness test; argument typed as Mapping. |
| mixin_logging/adapters/graphql/__init__.py | none | no | Re-exports only. |
| mixin_logging/adapters/graphql/graphql_client.py | none | no | inject returns a merged copy by contract; kept. |
| mixin_logging/adapters/graphql/graphql_objects.py | none | no | Value object already minimal. |
| mixin_logging/adapters/grpc/__init__.py | none | no | Re-exports only. |
| mixin_logging/adapters/grpc/grpc_client.py | [correctness] correlation context is set and cleared around continuation(), which only returns the handler; the handler runs later without the context (verified by probe; the adapter doc says otherwise) | no | Needs a design change that wraps the handler methods; reported, not changed. |
| mixin_logging/adapters/grpc/grpc_objects.py | [perf] per-character generator in the safety check; dict(metadata) per RPC kept because dict() keeps the last duplicate | yes | Set disjointness test; lookup semantics unchanged. |
| mixin_logging/adapters/httpx/__init__.py | none | no | Re-exports only. |
| mixin_logging/adapters/httpx/httpx_client.py | none | no | Event hooks already minimal. |
| mixin_logging/adapters/httpx/httpx_objects.py | [perf] per-character generator in the safety check | yes | Set disjointness test. |
| mixin_logging/adapters/requests/__init__.py | none | no | Re-exports only. |
| mixin_logging/adapters/requests/requests_client.py | none | no | Adapter mount logic already minimal. |
| mixin_logging/adapters/requests/requests_objects.py | [perf] per-character generator in the safety check | yes | Set disjointness test. |
| mixin_logging/adapters/stdlib/__init__.py | none | no | Re-exports only. |
| mixin_logging/adapters/stdlib/flush_handler_client.py | [correctness] stale eviction-order entries evicted a re-created live buffer and dropped its records (verified by probe); [dead] defensive branch behind a pragma; [dead] unused record argument; [constants] literal sentinel | yes | Eviction uses dict insertion order; see Behavior changes. |
| mixin_logging/adapters/stdlib/flush_handler_objects.py | [constants] error messages and defaults defined in the objects module | yes | Moved to the stdlib constants module. |
| mixin_logging/adapters/stdlib/stdlib_client.py | none | no | Per-record stamp is already minimal. |
| mixin_logging/adapters/urllib3/__init__.py | none | no | Re-exports only. |
| mixin_logging/adapters/urllib3/urllib3_client.py | none | no | Header mapping copy is required so the caller mapping is not mutated. |
| mixin_logging/adapters/urllib3/urllib3_objects.py | [perf] per-character generator in the safety check | yes | Set disjointness test. |
| mixin_logging/adapters/websocket/__init__.py | none | no | Re-exports only. |
| mixin_logging/adapters/websocket/websocket_client.py | [typing] Any aliases where the ASGI adapter declares concrete ones | no | Not changed: the adapter tests pass untyped fakes that fail strict typing; candidate for the test leg. |
| mixin_logging/adapters/websocket/websocket_objects.py | [perf] per-character generator in the safety check; [correctness] decode with errors ignored silently alters non-UTF-8 IDs | yes | Set disjointness test; decode behavior unchanged and reported as a candidate. |
| mixin_logging/adapters/wsgi/__init__.py | none | no | Re-exports only. |
| mixin_logging/adapters/wsgi/wsgi_client.py | [typing] Optional in a signature; [correctness] middleware body is a generator, so the context is set only on iteration and cleared only on exhaustion or close | yes | Union syntax; generator behavior reported, not changed. |
| mixin_logging/adapters/wsgi/wsgi_objects.py | [correctness] empty correlation header raised ValueError from the value object; [typing] Optional alias; [perf] per-character generator | yes | Empty guard added (verified by probe); union syntax; set disjointness test. |
| mixin_logging/ambient/__init__.py | none | no | Re-exports only. |
| mixin_logging/ambient/ambient_client.py | [dup] five copies of the extra-building steps; [constants] literal key and sentinel | yes | One private helper; constants from the correlation module. |
| mixin_logging/common/__init__.py | none | no | Re-exports only. |
| mixin_logging/common/constants/__init__.py | none | no | Re-exports only. |
| mixin_logging/common/constants/public_api.py | none | no | Public name set matches the top-level exports (checked). |
| mixin_logging/common/constants/tests.py | [docs] shared test constants live in the source tree | no | Confirm wheel exclusion in a later leg. |
| mixin_logging/config/__init__.py | none | no | Package docstring only. |
| mixin_logging/config/_version.py | none | no | Version unchanged; the release cut belongs to a later leg. |
| mixin_logging/context/__init__.py | none | no | Package docstring only. |
| mixin_logging/context/constants/__init__.py | none | no | Package docstring only. |
| mixin_logging/context/constants/correlation.py | none | no | Constants only. |
| mixin_logging/context/correlation/__init__.py | none | no | Re-exports only. |
| mixin_logging/context/correlation/correlation_client.py | [correctness] ContextVar created without a default; first read in a new thread raises LookupError (verified on 3.12 and 3.14) | yes | Default added; import-time set removed; module-level aliases kept as public API. |
| mixin_logging/context/correlation/correlation_objects.py | none | no | Value object already minimal. |
| mixin_logging/decorators/__init__.py | [dead] package with no modules left | no | Candidate for removal in a later leg. |
| mixin_logging/decorators/constants/__init__.py | [dead] package with no modules left | no | Candidate for removal in a later leg. |
| mixin_logging/mixin/__init__.py | none | no | Package docstring only. |
| mixin_logging/mixin/mixin.py | [dup] conditional update of the extra mapping; [perf] logger resolved per call | yes | Single mapping expression; per-call logger lookup kept (candidate: cache per class). |
| mixin_logging/redaction/__init__.py | none | no | Re-exports only. |
| mixin_logging/redaction/constants/__init__.py | none | no | Re-exports only. |
| mixin_logging/redaction/constants/redaction.py | [constants] default sensitive patterns defined in the filter module | yes | Default pattern set added here as a frozenset. |
| mixin_logging/redaction/redaction_client.py | none | no | Attach helper already minimal. |
| mixin_logging/redaction/redaction_objects.py | [perf] key list copied per record; pattern set rebuilt per call; [correctness] default key pattern matches substrings such as keyword | yes | Iterates fields directly and uses the shared pattern set; substring behavior unchanged and reported. |
