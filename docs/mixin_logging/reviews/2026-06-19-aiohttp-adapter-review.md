# Aiohttp Adapter Review

**Date:** 2026-06-19  
**Branch:** `feature/add_outbound_adapters`  
**Reviewer:** Code Reviewer  
**Scope:** aiohttp outbound correlation-ID injection adapter (objects, client, constants, tests)

---

## Review Summary

The aiohttp adapter extends aiohttp's trace system to inject correlation IDs into outbound HTTP headers. The design leverages `TraceConfig.on_request_start` to inject asynchronously at the correct lifecycle point, and provides a single `trace_config()` factory method for returning a pre-configured TraceConfig ready for attachment to any ClientSession.

**Scope of review:**
- `mixin_logging/adapters/aiohttp/aiohttp_objects.py` (44 LOC)
- `mixin_logging/adapters/aiohttp/aiohttp_client.py` (34 LOC)
- `mixin_logging/adapters/aiohttp/__init__.py` (1 LOC)
- `mixin_logging/adapters/constants/aiohttp.py` (35 LOC)
- `mixin_logging/adapters/tests/test_aiohttp/test_aiohttp_objects.py` (106 LOC)
- `mixin_logging/adapters/tests/test_aiohttp/test_aiohttp_client.py` (90 LOC)
- `mixin_logging/adapters/tests/test_aiohttp/conftest.py` (36 LOC)
- `mixin_logging/adapters/tests/test_aiohttp/__init__.py` (1 LOC)

Total: 347 LOC across 8 files, all under 300-LOC cap per file, under 694-line cap per LOC gate.

---

## Checklist Verdicts

### 1. DTO Golden Standard: frozen, slots, post_init, classmethod, property, staticmethod

**PASS**

- `@dataclass(frozen=True, slots=True)` on AiohttpCorrelation (line 14, aiohttp_objects.py): correct.
- `__post_init__` validates invariant, raises ValueError on unsafe correlation_id (lines 20-23): correct, one-liner docstring present.
- `_is_safe` is `@staticmethod` (line 38): correct, returns bool, checks empty/length/unsafe chars via membership test.
- `from_context` is `@classmethod` returning `Self | None` (lines 25-31): correct, handles unset/unsafe gracefully with silent skip, one-liner docstring.
- `header_tuple` is `@property` returning tuple[str, str] (lines 33-36): correct, one-liner docstring.

**Evidence:** aiohttp_objects.py lines 14-43.

---

### 2. Object/Client Split

**PASS**

- `aiohttp_objects.py` contains DTOs only: AiohttpCorrelation.
- `aiohttp_client.py` contains executable middleware: CorrelationIdInjector (provides trace_config() factory and _inject hook).
- `__init__.py` is module-docstring-only, alphabetically-sorted __all__ with both exports.

**Evidence:** aiohttp_objects.py, aiohttp_client.py structure matches requests/httpx canonical pattern.

---

### 3. ABC Types at API Boundary

**PASS**

- `_inject` receives `session: aiohttp.ClientSession, trace_config_ctx: object, params: aiohttp.TraceRequestStartParams` (lines 23-26, aiohttp_client.py): correct per aiohttp's on_request_start hook signature.
- `Self` from `typing` (line 6, aiohttp_objects.py): correct for return type on classmethod.
- Method signatures use `Self | None` union, tuple[str, str], str, bool; no TypeVar violations.

**Evidence:** aiohttp_objects.py lines 1-43, aiohttp_client.py lines 23-26.

---

### 4. Constants Golden Standard: Final, frozenset, ERR_* messages, section dividers

**PASS**

- All constants use `Final` type annotation (constants/aiohttp.py lines 17, 22, 27, 32): correct.
- `UNSAFE_HEADER_CHARS` is `frozenset({"\r", "\n", "\0"})` (line 27): correct, contains CR/LF/null.
- `ERR_CORRELATION_ID_UNSAFE` present as constant (lines 32-34): matches field-level validation message (aiohttp_objects.py line 23).
- Section dividers use bare string-literal docstrings with 2 blank lines above + 1 below: lines 15, 20, 25, 30 all correct. Even single-section file starts with divider above first constant (per requests.py canonical).

**Evidence:** constants/aiohttp.py lines 1-34.

---

### 5. Validate-and-Regenerate Semantics (or Silent Skip on Unsafe)

**PASS**

- `from_context` silently returns None on unsafe (aiohttp_objects.py lines 29-30): documented in docstring, no log_warning or raise.
- `_inject` silently returns on unset/unsafe context (aiohttp_client.py lines 30-31): matches pattern, no side effects.
- `__post_init__` raises on direct construction with unsafe value (aiohttp_objects.py lines 20-23): boundary enforcement.

**Evidence:** aiohttp_objects.py lines 25-31 (from_context), aiohttp_client.py lines 29-31 (_inject return guard).

---

### 6. Lifecycle: TraceConfig and _inject Hook Design

**PASS**

- `CorrelationIdInjector.trace_config()` creates a new `aiohttp.TraceConfig()` instance (line 18, aiohttp_client.py): standard aiohttp pattern.
- `_inject` is appended to `on_request_start` hooks (line 19): fires before transmission, after request creation.
- `_inject` is `@staticmethod` (line 22): correct, no instance state needed; hooks are called by aiohttp's trace system, not by CorrelationIdInjector instances.
- Async hook signature matches aiohttp contract: `async def _inject(session, trace_config_ctx, params)`.
- No TraceConfig subclassing; composition via hook list is correct.

**Evidence:** aiohttp_client.py lines 15-33.

---

### 7. Docstrings: File-Scoped, No Cross-System Refs

**PASS**

- File docstrings scoped to file only: aiohttp_objects.py (line 1) describes 'AiohttpCorrelation value object for aiohttp adapter', aiohttp_client.py (line 1) describes 'CorrelationIdInjector: stateless TraceConfig surface for aiohttp ClientSession'.
- No references to 'per qhcg canonical', 'mirrors requests', 'async version of', or other cross-system framing: all docstrings are standalone descriptive.
- `__init__.py` docstring (line 1) correctly identifies module scope; __all__ alphabetically sorted.
- Class docstrings (line 15, aiohttp_objects.py; line 13, aiohttp_client.py) are one-liners describing role.
- Every method has one-liner docstring: `__post_init__` (line 21), `from_context` (line 26), `header_tuple` (line 34), `_is_safe` (line 39) in objects; `trace_config` (line 16), `_inject` (line 28) in client.

**Evidence:** aiohttp_objects.py lines 1, 15, 21, 26, 34, 39; aiohttp_client.py lines 1, 13, 16, 28; __init__.py line 1.

---

### 8. Spacing: Constants Dividers, Module Post-Imports, No Em Dashes

**PASS**

- Constants section dividers (constants/aiohttp.py): 2 blank lines above, 1 blank line below, on lines 15, 20, 25, 30.
- Module spacing (aiohttp_objects.py): 2 blank lines after imports (line 12) before @dataclass (line 14).
- Module spacing (aiohttp_client.py): 2 blank lines after imports (line 11) before class (line 13).
- conftest.py: 2 blank lines after imports (line 12) before autouse fixture (line 15).
- No em dashes detected across all 8 files (confirmed: each file uses hyphens only).

**Evidence:** constants/aiohttp.py lines 15-34; aiohttp_objects.py lines 11-14; aiohttp_client.py lines 10-13; conftest.py lines 11-15.

---

### 9. Test Parity with Requests/HTTPX Pattern

**PASS**

- Test organization mirrors requests/httpx canonical: test classes group related test methods (TestAiohttpCorrelationFromContext, TestAiohttpCorrelationConstruction, TestAiohttpCorrelationHeaderTuple, TestAiohttpCorrelationIsSafe, TestCorrelationIdInjectorTraceConfig, TestCorrelationIdInjectorInject).
- conftest.py provides autouse `reset_correlation` fixture (lines 15-20) for test isolation, clears before+after, matches requests/httpx pattern exactly.
- Factory fixture `make_trace_params` (lines 23-35) correctly creates a mock aiohttp.TraceRequestStartParams object.
- Test constants use `test_const.HTTPX_CORR_ID_*` alias (shared pool with httpx tests per collision-avoidance rule).
- Parametrized tests cover all 3 unsafe chars via @pytest.mark.parametrize (line 28 in test_aiohttp_objects.py, line 101 in test_aiohttp_objects.py).
- Async tests marked with @pytest.mark.asyncio (lines 38, 57, 73 in test_aiohttp_client.py).

**Evidence:** test_aiohttp_objects.py classes 13-106; test_aiohttp_client.py classes 18-90; conftest.py lines 14-35.

---

### 10. Coverage: 100% Objects, 100% Client

**PASS**

- `test_aiohttp_objects.py`: 13 test methods covering AiohttpCorrelation across 4 test classes:
  - TestAiohttpCorrelationFromContext: set/unset/unsafe-char (parametrized, 3 unsafe chars)/overlong (4 test methods).
  - TestAiohttpCorrelationConstruction: unsafe-char/empty/overlong raises ValueError (3 test methods).
  - TestAiohttpCorrelationHeaderTuple: returns canonical pair (1 test method).
  - TestAiohttpCorrelationIsSafe: valid/empty/overlong/exactly-max/unsafe-char (parametrized, 3 unsafe chars) (5 test methods).

- `test_aiohttp_client.py`: 5 async test methods covering CorrelationIdInjector across 2 test classes:
  - TestCorrelationIdInjectorTraceConfig: returns TraceConfig instance (1 test), appends _inject hook (1 test).
  - TestCorrelationIdInjectorInject: set correlation writes header (1 async test), unset is noop (1 async test), unsafe context is noop (1 async test).

- **Total: 18 test methods** across 11 domain paths (AiohttpCorrelation.from_context, .__post_init__, ._is_safe, .header_tuple, CorrelationIdInjector.trace_config, ._inject).
- Parametrized tests via @pytest.mark.parametrize cover all 3 unsafe chars (CR, LF, null).
- Boundary tests for exactly-max length (128 chars) and overlong (129 chars) validate edge cases.

**Coverage report (from implementation):**
- aiohttp_objects.py: 100% statement + branch coverage (26 stmts, 6 branches)
- aiohttp_client.py: 100% statement + branch coverage (17 stmts, 2 branches)

**Evidence:** test_aiohttp_objects.py lines 13-106 (13 test methods); test_aiohttp_client.py lines 18-90 (5 test methods); pytest coverage output shows 100% on both modules.

---

## Architecture Observations

### Strengths

1. **Async hook is correctly placed.** The `on_request_start` hook fires after request creation but before transmission, at the ideal injection point. Async signature matches aiohttp's contract exactly.

2. **Single factory pattern.** `trace_config()` returns a pre-configured TraceConfig ready for any ClientSession. Simpler than requests' dual-pattern (register_on_session + correlation_session) because aiohttp attaches TraceConfigs to sessions, not adapters to schemes.

3. **Stateless design.** CorrelationIdInjector is all classmethods/staticmethods; no instance state. TraceConfig created fresh each call, no shared mutable state.

4. **Silent fallback on unsafe.** `_inject()` silently returns on unset/unsafe context, never raising or logging. Matches requests/httpx/botocore semantics.

5. **Type safety is tight.** Frozen dataclass, union patterns, staticmethod on _is_safe, property on header_tuple prevent field mutation and unintended state changes.

6. **Test isolation is airtight.** autouse reset_correlation fixture ensures every test starts with blank context. mock.MagicMock(spec=...) objects isolate tests from real network calls and from aiohttp internals.

7. **Parametrization covers all boundaries.** Tests verify exactly-max-length (128 chars), overlong (129 chars), all 3 unsafe chars via parametrize, unset context, and async hook execution.

### Minor Notes (Not Blockers)

1. **TraceConfig immutability.** Each call to `trace_config()` creates a new config object. This is correct and prevents shared state. No issue.

2. **Exception handling in _inject.** The method has no explicit try/except. If params.headers is unexpectedly immutable or session is malformed, the exception bubbles to aiohttp's trace handler (which logs but does not crash the request). This is acceptable for a monitoring hook. Adding try/except would mask aiohttp bugs.

---

## Security Audit Findings Integration

Cross-referencing with `docs/audits/2026-06-19-aiohttp-adapter-security-audit.md`:

**8 NO ISSUE verdicts:**

1. **TraceConfig hook lifecycle and timing** (NO ISSUE) - Hook fires at correct point (after request creation, before transmission).
2. **Context-var read and validation** (NO ISSUE) - `from_context()` re-validates before injection; unsafe values are filtered.
3. **TraceConfig multiplexing and state leakage** (NO ISSUE) - Each config is independent; multiple sessions read the same ContextVar (correct).
4. **Async hook signature compliance** (NO ISSUE) - Signature matches aiohttp's on_request_start contract.
5. **Exception handling in injection hook** (NO ISSUE, acceptable risk) - No explicit try/except is correct; bubbling to aiohttp's trace handler is acceptable.
6. **Aiohttp library version compatibility** (NO ISSUE) - Uses only stable, public APIs (TraceConfig, on_request_start, TraceRequestStartParams); compatible with aiohttp 3.0+.
7. **Denial-of-tracing via unsafe context pollution** (NO ISSUE) - Skip-on-unsafe pattern is acceptable; caller needs code execution to pollute context.
8. **Header value disclosure and passthrough** (NO ISSUE) - Correlation IDs are non-sensitive metadata; no masking needed.

**Verdict on all audits:** All pass. No code defects. Production-ready.

---

## Verdict

**SHIP**

All checklist items pass. Code is production-ready:

- DTOs follow frozen/slots/docstring golden standard.
- TraceConfig factory and async hook adhere to canonical aiohttp pattern.
- Constants use Final, frozenset, ERR_* messages, and section dividers per standing rule.
- Tests cover 18 test methods across both objects and client with parametrization and async hook tests.
- No docstring cross-system refs, no em dashes, no inline comments, no employer/platform attribution.
- LOC under cap on all files (max 106 LOC in test file, 44 LOC in objects, 34 LOC in client, 35 LOC in constants).
- Security audit confirms no code defects; all threats evaluated and resolved.
- 100% coverage on both aiohttp_objects.py and aiohttp_client.py.

**Recommended merge:** No code changes needed. The adapter is ready for integration into the feature branch and eventual release. All verification gates pass.

**Note for follow-up:** The optional enhancement (expanded docstring in `_inject` clarifying silent no-op on unsafe context) can be added now or deferred to a documentation pass. It is non-blocking.
