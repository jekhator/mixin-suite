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

## Test tree pass

This section records the pass over the test tree. Scope: every .py file under mixin_logging/**/tests/ (80 files at the start of the pass). The shared fixtures moved to a root conftest, which sits outside the tests tree and covers every test under the package.

### Test tree summary

- Files reviewed: 80
- Files changed: 53 (52 edited and 2 removed: one empty conftest and one duplicate suite-level version test)
- New test files: 1 conftest under mixin_logging/ambient/tests; 1 root conftest at mixin_logging/conftest.py
- Findings by lens (a file can carry more than one): duplication 21, constants 18, determinism 10, assertion 7, coverage 7, typing 5, naming 5, dead code 4, structure 2, lint 2. Every finding is either fixed or listed under Deferred candidates below.
- Tests: 598 before the pass, 609 after (same pytest command on Python 3.12)
- Coverage: 100.00 percent before and after, with branch coverage on

Lenses used: structure (Test classes, fixtures in conftest), determinism (clocks, sleeps, handler and logger state left behind), assertion strength (conditional or vacuous checks, weak counts, silent skips), duplication (fakes, handlers, factories and fixtures repeated across files), typing (fakes typed to the adapter aliases where the middleware annotations need them), constants (literal lengths, hex alphabets and error text where a constant exists), naming (test names that disagree with their assertions), coverage (behaviour touched by the adapter changes without a named test), lint (suppression comments that do nothing), dead code (unused classes and files).

### Behavior changes (test pass)

1. gRPC interceptor binding. The correlation context is now set while each handler callable runs (unary, streaming and streamed responses), not around the continuation call. The adapter document describes the actual behaviour. This is the only source behaviour change in this pass and is listed in the CHANGELOG under Fixed.
2. Typing only. The websocket middleware aliases (Scope, Receive, Send, App) now refer to the ASGI adapter aliases instead of Any. No runtime change.

Candidates from the source pass resolved in this pass: gRPC context lifetime (item 1 above) and WebSocket typing of the test fakes (item 2 above).

### Deferred candidates

- Value-object contract tests are structurally identical across the aiohttp, botocore, celery, cloud, fastapi, grpc, httpx, requests, urllib3, websocket and wsgi adapters. A single parametrized contract module would remove a large share of these tests. Deferred: it changes the test layout of eleven adapter test trees and needs a layout decision first.
- Bare pytest.raises(FrozenInstanceError) and pytest.raises(AttributeError) in the correlation objects and mixin tests assert the exception type only. The standard library message text is not a project contract, so no match string is added.
- The FastAPI dependency error text lives in mixin_logging/adapters/fastapi/constants.py, outside the adapters constants package used by every other adapter. Moving it is a source layout change.
- The per-adapter request and environ factories (make_request, make_environ, make_trace_params, make_prepared_request) build different library types. They stay per adapter.
- Fixture parameters in the ASGI client tests are untyped. Annotating them adds churn with no behaviour effect, and mypy does not check untyped test functions.
- Candidates from the source pass still open (source behaviour, outside this pass): the WebSocket identifier decode that ignores undecodable bytes; the redaction default key pattern that matches substrings; the WSGI middleware generator that sets the context only on iteration; the per-call logger lookup in the mixin.

### Gate results

- Test gate on Python 3.12 and 3.14: pytest -v --cov --cov-fail-under=100 passes with 609 tests and 100.00 percent coverage on both.
- Type check: mypy over mixin_latency, mixin_logging, mixin_notifications, mixin_retry and mixin_sensitivity under Python 3.14 reports no issues.
- Lint and format: ruff 0.15.14 check passes; format check passes with the mixin_notifications/dispatch/_client.py carve-out.
- Strict self-lint: strict-module 0.4.0 passes on all five roots under Python 3.14, and the LOC-cap loop reports no failures.
- Markdown dash check and commit attribution check: no matches.

### Test-tree table

Each test file from the start of the pass has one line. Changed means the file differs from the state after the source pass (commit 2308cf2).

| Path | Findings | Changed | Note |
| --- | --- | --- | --- |
| mixin_logging/adapters/tests/__init__.py | none | no | Package marker. |
| mixin_logging/adapters/tests/test_aiohttp/__init__.py | none | no | Package marker. |
| mixin_logging/adapters/tests/test_aiohttp/conftest.py | [duplication] autouse reset fixture repeated in every adapter conftest | yes | Reset moved to the root conftest. |
| mixin_logging/adapters/tests/test_aiohttp/test_aiohttp_client.py | none | no | Structure, names and assertions checked; no finding. |
| mixin_logging/adapters/tests/test_aiohttp/test_aiohttp_objects.py | [constants] literal lengths 128 and 129 in place of the max-length constant | yes | Max-length constant used in the boundary inputs. |
| mixin_logging/adapters/tests/test_asgi/__init__.py | none | no | Package marker. |
| mixin_logging/adapters/tests/test_asgi/conftest.py | [duplication] reset, service and capture fixtures repeated; [typing] receive, send and app fakes typed Any | yes | Fixtures moved to root conftest; fakes typed with the ASGI aliases. |
| mixin_logging/adapters/tests/test_asgi/test_asgi_client.py | [assertion] response test accepted any header value and did not count headers; [constants] hex alphabet and length literals | yes | Exactly one correlation header with a generated ID is asserted. |
| mixin_logging/adapters/tests/test_asgi/test_asgi_objects.py | [constants] hex alphabet and length literals repeated | yes | Shared generated-ID shape constants. |
| mixin_logging/adapters/tests/test_botocore/__init__.py | none | no | Package marker. |
| mixin_logging/adapters/tests/test_botocore/conftest.py | [duplication] autouse reset fixture repeated | yes | Reset moved to the root conftest. |
| mixin_logging/adapters/tests/test_botocore/test_botocore_client.py | none | no | Structure, names and assertions checked; no finding. |
| mixin_logging/adapters/tests/test_botocore/test_botocore_objects.py | [constants] literal length 129 | yes | Max-length constant used. |
| mixin_logging/adapters/tests/test_celery/__init__.py | none | no | Package marker. |
| mixin_logging/adapters/tests/test_celery/conftest.py | [determinism] real celery signal handlers connected by tests and never disconnected | yes | Fixture connects for one test and disconnects on teardown. |
| mixin_logging/adapters/tests/test_celery/test_celery_client.py | [determinism] signal leak as above; [assertion] None-headers test asserted nothing; [naming] isolation test name did not match its body | yes | Uses the connected-signals fixture; asserts the context is unchanged; renamed to match the round trip. |
| mixin_logging/adapters/tests/test_celery/test_celery_objects.py | [constants] literal length 129 | yes | Max-length constant used. |
| mixin_logging/adapters/tests/test_cloud/__init__.py | none | no | Package marker. |
| mixin_logging/adapters/tests/test_cloud/conftest.py | [dead] file empty after the shared reset fixture moved | yes | File removed. |
| mixin_logging/adapters/tests/test_cloud/test_cloud_client.py | [constants] generated-ID length literal | yes | Shared generated-ID length constant. |
| mixin_logging/adapters/tests/test_cloud/test_cloud_extraction.py | [constants] literal length 129 | yes | Max-length constant used. |
| mixin_logging/adapters/tests/test_cloud/test_cloud_objects.py | [constants] literal length 129 | yes | Max-length constant used. |
| mixin_logging/adapters/tests/test_fastapi/__init__.py | none | no | Package marker. |
| mixin_logging/adapters/tests/test_fastapi/conftest.py | [dead] unused service class and import; [structure] imports inside handler bodies | yes | Unused class removed; imports moved to module top. |
| mixin_logging/adapters/tests/test_fastapi/test_fastapi_client.py | [constants] dependency error matched by literal text; [structure] imports inside test bodies | yes | Matches the module error constant; imports moved to module top; regression for the dependency error kept. |
| mixin_logging/adapters/tests/test_fastapi/test_fastapi_objects.py | [constants] generated-ID shape literals | yes | Shared generated-ID shape constant. |
| mixin_logging/adapters/tests/test_graphql/__init__.py | none | no | Package marker. |
| mixin_logging/adapters/tests/test_graphql/conftest.py | [duplication] autouse reset fixture repeated | yes | Reset moved to the root conftest. |
| mixin_logging/adapters/tests/test_graphql/test_graphql_client.py | none | no | Structure, names and assertions checked; no finding. |
| mixin_logging/adapters/tests/test_graphql/test_graphql_objects.py | none | no | Structure, names and assertions checked; no finding. |
| mixin_logging/adapters/tests/test_grpc/__init__.py | none | no | Package marker. |
| mixin_logging/adapters/tests/test_grpc/conftest.py | [duplication] autouse reset fixture repeated; [coverage] no in-process server fixture for the binding behaviour | yes | Reset moved to root; in-process server fixture added with teardown. |
| mixin_logging/adapters/tests/test_grpc/test_grpc_client.py | [assertion] tests asserted the continuation saw the ID, not the handler; [coverage] no streaming, early-close or live-server tests | yes | Rewritten around real handlers: unary, streaming, early close, error paths and a live RPC. Source defect fixed in its own commit. |
| mixin_logging/adapters/tests/test_grpc/test_grpc_objects.py | [constants] generated-ID shape literals | yes | Shared generated-ID shape constant. |
| mixin_logging/adapters/tests/test_httpx/__init__.py | none | no | Package marker. |
| mixin_logging/adapters/tests/test_httpx/conftest.py | [duplication] autouse reset fixture repeated | yes | Reset moved to the root conftest. |
| mixin_logging/adapters/tests/test_httpx/test_httpx_client.py | [naming] event hook test name said list while the body checks a mapping | yes | Renamed to describe the check. |
| mixin_logging/adapters/tests/test_httpx/test_httpx_objects.py | [constants] literal length 129 | yes | Max-length constant used. |
| mixin_logging/adapters/tests/test_requests/__init__.py | none | no | Package marker. |
| mixin_logging/adapters/tests/test_requests/conftest.py | [duplication] autouse reset fixture repeated; [determinism] test HTTP server socket not closed | yes | Reset moved to root; server socket closed on teardown. |
| mixin_logging/adapters/tests/test_requests/test_requests_client.py | [determinism] real session requests had no timeout | yes | Shared local-server timeout constant passed to each request. |
| mixin_logging/adapters/tests/test_requests/test_requests_objects.py | [constants] literal length 129 | yes | Max-length constant used. |
| mixin_logging/adapters/tests/test_stdlib/__init__.py | none | no | Package marker. |
| mixin_logging/adapters/tests/test_stdlib/conftest.py | [duplication] reset fixture repeated; [duplication] record factory and handler classes repeated; [determinism] named global loggers left with handlers | yes | Record factory, fake clock and scoped logger factory with teardown. |
| mixin_logging/adapters/tests/test_stdlib/test_flush_handler_client.py | [duplication] 18 inline record constructions and a local clock; [constants] config messages matched by literal text; [naming] lock test did not test a lock; [coverage] no regression for eviction of a re-created correlation | yes | Rewritten on shared fixtures; error constants used; regression test added and shown to fail on the prior eviction code. |
| mixin_logging/adapters/tests/test_stdlib/test_stdlib_client.py | [duplication] four local handler classes and inline records; [determinism] filters left on named global loggers | yes | Shared collector and record factory; scoped loggers cleaned up after each test. |
| mixin_logging/adapters/tests/test_urllib3/__init__.py | none | no | Package marker. |
| mixin_logging/adapters/tests/test_urllib3/conftest.py | [duplication] autouse reset fixture repeated | yes | Reset moved to the root conftest. |
| mixin_logging/adapters/tests/test_urllib3/test_urllib3_client.py | [assertion] two tests skipped their header assertion when the kwarg was absent; [determinism] literal timeout | yes | Absent header checked with a default; shared timeout constant. |
| mixin_logging/adapters/tests/test_urllib3/test_urllib3_objects.py | [constants] literal length 129 | yes | Max-length constant used. |
| mixin_logging/adapters/tests/test_websocket/__init__.py | none | no | Package marker. |
| mixin_logging/adapters/tests/test_websocket/conftest.py | [duplication] autouse reset fixture repeated; [typing] fakes typed Any | yes | Reset moved to root; fakes typed with the ASGI aliases. |
| mixin_logging/adapters/tests/test_websocket/test_websocket_client.py | [typing] recording apps typed Any | yes | Typed with the ASGI aliases; supports the middleware annotations. |
| mixin_logging/adapters/tests/test_websocket/test_websocket_objects.py | [constants] hex alphabet and length literals | yes | Shared generated-ID shape constants. |
| mixin_logging/adapters/tests/test_wsgi/__init__.py | none | no | Package marker. |
| mixin_logging/adapters/tests/test_wsgi/conftest.py | [duplication] reset, service and capture fixtures repeated | yes | Fixtures moved to root conftest. |
| mixin_logging/adapters/tests/test_wsgi/test_wsgi_client.py | [coverage] no test for an empty correlation header; [constants] generated-ID literals | yes | Regression test added (fails on the prior WSGI code); shared constants. |
| mixin_logging/adapters/tests/test_wsgi/test_wsgi_objects.py | [coverage] no test for an empty correlation header; [constants] generated-ID literals | yes | Regression test added (fails on the prior WSGI code); shared constants. |
| mixin_logging/ambient/tests/__init__.py | none | no | Package marker. |
| mixin_logging/ambient/tests/test_ambient_client.py | [determinism] handlers attached to named global loggers and never removed; [duplication] private handler class repeated from the shared collector | yes | Per-test logger fixture detaches its handler and resets the level; shared collector used. |
| mixin_logging/common/tests/__init__.py | none | no | Package marker. |
| mixin_logging/common/tests/conftest.py | [duplication] autouse reset fixture repeated | yes | Reset moved to the root conftest. |
| mixin_logging/common/tests/test_public_api.py | [lint] suppression comments that do nothing (the S rules are not enabled) | yes | Comments removed. |
| mixin_logging/common/tests/test_version_lockstep.py | [assertion] distribution check skipped silently when the package is not installed; [duplication] suite-level version test repeated this check | yes | Distribution lookup fails loudly; the release pin moved here from the removed duplicate. |
| mixin_logging/context/tests/__init__.py | none | no | Package marker. |
| mixin_logging/context/tests/test_correlation/__init__.py | none | no | Package marker. |
| mixin_logging/context/tests/test_correlation/conftest.py | [duplication] autouse reset fixture repeated | yes | Reset moved to the root conftest. |
| mixin_logging/context/tests/test_correlation/test_correlation_client.py | [coverage] no test that a read in a new thread returns unset | yes | Regression test added; shown to fail on the prior ContextVar code. |
| mixin_logging/context/tests/test_correlation/test_correlation_objects.py | [naming] test name said false for an empty ID while the assertion and docstring say true; [lint] suppression comments that do nothing | yes | Renamed; comments removed. Bare FrozenInstanceError raises kept (see deferred). |
| mixin_logging/decorators/tests/__init__.py | none | no | Package marker. |
| mixin_logging/mixin/tests/__init__.py | none | no | Package marker. |
| mixin_logging/mixin/tests/test_mixin/__init__.py | none | no | Package marker. |
| mixin_logging/mixin/tests/test_mixin/conftest.py | [duplication] reset, service and capture fixtures repeated; [determinism] capture handler left attached to a shared logger | yes | Fixtures moved to root; capture detaches its handler on teardown. |
| mixin_logging/mixin/tests/test_mixin/test_mixin.py | [typing] capture tuple typed Any; [assertion] bare AttributeError raise kept (see deferred) | yes | Capture tuple typed with the collector type. |
| mixin_logging/redaction/tests/__init__.py | none | no | Package marker. |
| mixin_logging/redaction/tests/conftest.py | [determinism] logger filters not cleared between tests, so filter counts depended on order; [dead] unused handler fixture and class | yes | Cleared logger fixture with teardown; shared collector fixture; unused code removed. |
| mixin_logging/redaction/tests/test_redaction_client.py | [duplication] five local handler classes and inline records; [typing] type-ignore casts on filters; [assertion] lower-bound filter count | yes | Shared collector and record factory; exact filter count; direct filter calls. |
| mixin_logging/tests/helpers.py | [duplication] private collector duplicated in three conftests; [coverage] no shared fake clock | yes | Public collector and fake clock; logger factory alias for the ambient tests. |
| mixin_logging/tests/test_helpers.py | [naming] imports the collector under its old private name | yes | Renamed import. |
| mixin_logging/tests/test_suite_version_consistency.py | [duplication] suite-level version check repeated the lockstep check; [dead] file made redundant | yes | File removed; its release pin moved to the lockstep test. |
