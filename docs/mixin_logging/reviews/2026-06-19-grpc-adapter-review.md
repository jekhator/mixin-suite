# gRPC Adapter Review

**Date:** 2026-06-19  
**Branch:** `feature/add_inbound_adapters`  
**Reviewer:** Code Reviewer  
**Scope:** gRPC inbound correlation-ID extraction adapter (objects, client, constants, tests)

---

## Review Summary

The gRPC adapter extends the gRPC `ServerInterceptor` protocol to extract correlation IDs from inbound invocation metadata and set up the correlation context for downstream RPC handlers. The design follows the inbound-adapter pattern established by ASGI and WSGI adapters, with metadata validation and safe fallback generation on miss/unsafe.

**Scope of review:**
- `mixin_logging/adapters/grpc/grpc_objects.py` (44 LOC)
- `mixin_logging/adapters/grpc/grpc_client.py` (28 LOC)
- `mixin_logging/adapters/grpc/__init__.py` (15 LOC)
- `mixin_logging/adapters/constants/grpc.py` (32 LOC)
- `mixin_logging/adapters/tests/test_grpc/test_grpc_objects.py` (173 LOC)
- `mixin_logging/adapters/tests/test_grpc/test_grpc_client.py` (175 LOC)
- `mixin_logging/adapters/tests/test_grpc/conftest.py` (17 LOC)
- `mixin_logging/adapters/tests/test_grpc/__init__.py` (1 LOC)

Total: 485 LOC across 8 files, all under 300-line LOC cap per file.

---

## Checklist Verdicts

### 1. DTO Golden Standard: frozen, slots, post_init, classmethod, property, staticmethod

**PASS**

- `@dataclass(frozen=True, slots=True)` on GRPCCorrelation (line 16, grpc_objects.py): correct.
- `__post_init__` validates invariant, raises ValueError on unsafe correlation_id (lines 23-26): correct, one-liner docstring present ("Validate correlation_id against safety rules; raise on invariant breach.").
- `_is_safe` is `@staticmethod` (line 39): correct, returns bool, checks empty/length/unsafe chars.
- `from_metadata` is `@classmethod` returning `Self` (lines 28-37): correct, handles missing/unsafe gracefully via regeneration (not silent skip; always returns a valid instance), one-liner docstring present ("Extract correlation_id from gRPC invocation metadata; generate if absent or unsafe.").

**Evidence:** grpc_objects.py lines 16-44.

---

### 2. Object/Client Split

**PASS**

- `grpc_objects.py` contains DTOs + type alias only: GRPCCorrelation + Metadata type alias.
- `grpc_client.py` contains executable middleware: CorrelationInterceptor (extends grpc.ServerInterceptor, overrides intercept_service).
- `__init__.py` is module-docstring-only, one-liner scope statement.

**Evidence:** grpc_objects.py, grpc_client.py structure matches asgi/wsgi canonical pattern.

---

### 3. ABC Types at API Boundary

**PASS**

- ServerInterceptor.intercept_service() receives `continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler | None]` (line 17-18): correct, matches gRPC's public protocol.
- `handler_call_details: grpc.HandlerCallDetails` (line 19): correct, type from grpc library.
- `metadata: objs.Metadata` (line 22) uses the type alias from grpc_objects.py (Metadata = tuple[tuple[str, str | bytes], ...]).
- Return type `grpc.RpcMethodHandler | None` (line 20): correct per ServerInterceptor protocol.
- Docstring one-liner: "Extract and set the correlation ID from gRPC invocation metadata."

**Evidence:** grpc_client.py lines 16-21.

---

### 4. Constants Golden Standard: Final, frozenset, ERR_* messages, section dividers

**PASS**

- All constants use `Final` type annotation (grpc.py lines 18, 23, 24, 25, 31-32): correct.
- `UNSAFE_CHARS` is `frozenset` (line 25): correct, contains CR/LF/null.
- `ERR_CORRELATION_ID_UNSAFE` present as constant (line 30-32): matches field-level validation message.
- Section dividers use bare string-literal docstrings with 2 blank lines above + 1 below:
  - Line 16 ("Metadata extraction key."): 2 blanks above (line 14-15), 1 below (line 19): **correct**.
  - Line 21 ("Validation."): 2 blanks above (line 19-20), 1 below (line 26): **correct**.
  - Line 28 ("Error messages."): 2 blanks above (line 26-27), 1 below (line 33): **correct**.

**Evidence:** grpc.py lines 1-33.

---

### 5. Validate-and-Regenerate Semantics

**PASS**

- `from_metadata` checks safety at line 32 and REGENERATES on miss/unsafe (lines 34-37), not silent skip: documented in docstring ("generate if absent or unsafe").
- `__post_init__` raises ValueError on unsafe (lines 23-26): boundary enforcement at construction.
- `intercept_service` calls `from_metadata` once (line 23) and uses the result without re-validation (result is guaranteed safe by from_metadata's construction): correct pattern.

**Evidence:** grpc_objects.py lines 28-37 (from_metadata regenerates), grpc_client.py lines 23-24 (uses result directly).

---

### 6. Lifecycle: ServerInterceptor Protocol

**PASS**

- CorrelationInterceptor extends grpc.ServerInterceptor (line 13, grpc_client.py): standard gRPC pattern.
- `intercept_service()` overrides the required method signature (lines 16-28): correct.
- Line 25: `set_correlation_id(correlation.correlation_id)` sets context at entry.
- Line 26: `return continuation(handler_call_details)` delegates to next interceptor or handler.
- Line 27-28: finally block unconditionally calls `clear_correlation_id()`, ensuring cleanup even on exception.
- No __init__ override: interceptor is stateless.

**Test evidence:** test_grpc_client.py lines 62-78 (test_intercept_clears_correlation_even_if_continuation_raises) verify finally-block cleanup on exception.

**Evidence:** grpc_client.py lines 13-28.

---

### 7. Docstrings: File-Scoped, No Cross-System Refs

**PASS**

- File docstrings scoped to file only:
  - grpc_objects.py (line 1): "GRPCCorrelation value object for gRPC adapter." ✓
  - grpc_client.py (line 1): "CorrelationInterceptor: gRPC inbound entry surface for correlation-ID setup." ✓
  - __init__.py (line 1): Describes module scope. ✓
- Class docstrings one-liner:
  - GRPCCorrelation (line 18): "Correlation-ID value object resolved from gRPC invocation metadata or generated." ✓
  - CorrelationInterceptor (line 14): "Entry surface for extracting correlation-ID from inbound gRPC metadata." ✓
- Method docstrings one-liner for all (from_metadata, __post_init__, _is_safe, intercept_service): ✓
- No references to internal process terms or cross-system framing: ✓

**Evidence:** grpc_objects.py lines 1, 18; grpc_client.py lines 1, 14; all method docstrings on lines 24, 30, 40, 21.

---

### 8. Spacing: Constants Dividers, Module Post-Imports, No Em Dashes

**PASS**

- Constants section dividers (grpc.py): Lines 16, 21, 28 all have 2 blank lines above + 1 below. ✓
- Module spacing (grpc_objects.py): 2 blank lines after imports (line 10) before __all__ (line 11): ✓
- Module spacing (grpc_client.py): 2 blank lines after imports (line 10) before class (line 13): ✓
- conftest.py: 2 blank lines after imports (line 11) before fixture (line 12): ✓
- No em dashes detected across all 8 files (grep confirms): ✓

**Evidence:** grpc.py lines 14-28, grpc_objects.py lines 9-12, grpc_client.py lines 10-13, conftest.py lines 11-12.

---

### 9. Test Parity with ASGI/WSGI Pattern

**PASS**

- Test organization mirrors ASGI/WSGI: test classes group related test methods:
  - TestGRPCCorrelationFromMetadata (8 tests): with_present_safe_id, without_id_generates, unsafe_carriage_return, unsafe_newline, unsafe_null_byte, oversized, hex_id, empty_metadata.
  - TestGRPCCorrelationIsSafe (9 tests): empty, valid_id, hex_id, carriage_return, newline, null_byte, oversized, at_max_boundary, just_under_max.
  - TestGRPCCorrelationPostInit (4 tests): unsafe, empty, oversized, accepts_safe.
  - TestCorrelationInterceptorIntercept (8 tests): extracts_and_sets, clears_after_return, clears_on_exception, returns_result, generates_when_absent, generates_when_unsafe, empty_metadata, inheritance.
- conftest provides autouse `reset_correlation` fixture (lines 12-17) for test isolation, mirrors ASGI/WSGI conftest pattern. ✓
- Test constants use `test_const.CORRELATION_ID_VALID_ID_123`, `test_const.CORRELATION_ID_HEX`, etc. from shared tests.py (no new entries added to shared file): ✓

**Evidence:** test_grpc_objects.py classes 12-174 (21 tests), test_grpc_client.py classes 16-176 (8 tests), conftest.py lines 12-17.

---

### 10. Coverage: 100% Objects, 100% Client

**PASS**

- **grpc_objects.py coverage:**
  - Line 18: @dataclass decorator ✓
  - Lines 20-21: fields (correlation_id, extracted) ✓
  - Lines 23-26: __post_init__ validation ✓
  - Lines 28-37: from_metadata classmethod (safe branch, unsafe/absent branch) ✓
  - Lines 39-44: _is_safe staticmethod (empty, length, chars checks) ✓
  - **Total: 41 statements, 41 covered = 100%** per impl report.

- **grpc_client.py coverage:**
  - Lines 13-14: class definition ✓
  - Lines 16-20: intercept_service signature ✓
  - Line 22: metadata assignment ✓
  - Line 23: GRPCCorrelation.from_metadata call ✓
  - Line 24: set_correlation_id call ✓
  - Lines 25-26: try block, continuation call ✓
  - Lines 27-28: finally block, clear_correlation_id call ✓
  - **Total: 13 statements, 13 covered = 100%** per impl report.

- **Test count: 29 tests** (21 objects + 8 client) covering all branches and edge cases.

**Evidence:** impl report confirms "objects_coverage: 100%, client_coverage: 100%, test_count: 29" with all 29 tests passing.

---

## Architecture Observations

### Strengths

1. **ServerInterceptor protocol is correct.** The `intercept_service()` method implements gRPC's required interceptor interface. The method fires at the right point (before handler invocation) and delegates cleanly via `continuation()`.

2. **Try-finally is airtight.** Context cleanup in finally block is unconditional, ensuring isolation between requests even on exception.

3. **Validation is rigorous.** Metadata is validated at two gates: `from_metadata()` (factory) and `__post_init__` (invariant). Unsafe values are rejected and replaced with fresh UUIDs.

4. **Metadata handling is type-safe.** The union type `Metadata = tuple[tuple[str, str | bytes], ...]` is captured, and the factory correctly checks isinstance(value, str) before validation.

5. **Test isolation is airtight.** autouse reset_correlation fixture ensures every test starts and ends with blank context; mock MagicMock objects for handler_call_details prevent real gRPC calls.

6. **Parametrized tests cover unsafe chars.** All three unsafe characters (CR, LF, null) are tested individually in from_metadata and _is_safe.

### Minor Notes (Not Blockers)

1. **Byte metadata is silently rejected.** The adapter only accepts string values (line 32 of grpc_objects.py checks isinstance(candidate, str)). Byte values are rejected and replaced with generated IDs. This is safe and acceptable, but differs from ASGI/WSGI adapters which decode bytes. The asymmetry is documented in the security audit.

2. **Case-sensitive key lookup.** Metadata keys are case-sensitive; "x-correlation-id" ≠ "X-CORRELATION-ID". Uppercase metadata will not be recognized and will trigger generation. This aligns with gRPC/HTTP/2 convention but may surprise HTTP-framework users.

3. **Mock-based testing.** Tests use MagicMock for gRPC objects (handler_call_details, RpcMethodHandler). This is appropriate for unit tests but integration tests with real grpc.testing servers would be valuable in later phases.

---

## Security Audit Findings Integration

Cross-referencing with `docs/audits/2026-06-19-grpc-adapter-security-audit.md`:

**All 7 threat questions resolve to NO ISSUE:**

1. **ServerInterceptor hook firing** (NO ISSUE) :  Hook runs before handler invocation, receives read-only metadata, delegates cleanly.
2. **Metadata type coercion** (NO ISSUE) :  Explicit isinstance(str) check; bytes are rejected and regenerated.
3. **Validation and regeneration** (NO ISSUE) :  Two-gate validation; unsafe values are rejected.
4. **Context isolation via finally** (NO ISSUE) :  Finally block runs unconditionally, even on exception.
5. **Case-sensitive key lookup** (NO ISSUE) :  Acceptable per gRPC spec; fallback generation ensures no tracing loss.
6. **Metadata passthrough** (NO ISSUE) :  Adapter reads context, handler receives original metadata; separation of concerns is clean.
7. **UUID4 entropy** (NO ISSUE) :  48-bit entropy (UUID4 truncated to 12 hex chars) is sufficient for correlation-ID use.

**No security blockers. Adapter is safe for production use.**

---

## Verdict

**SHIP**

All checklist items pass. Code is production-ready:

- DTOs follow frozen/slots/docstring golden standard.
- ServerInterceptor protocol is correctly implemented with try-finally cleanup.
- Constants use Final, frozenset, ERR_* messages, and section dividers per standing rule.
- Tests cover 29 scenarios across objects and client with edge cases (unsafe chars, empty, oversized, exception handling).
- All imports properly ordered (stdlib → third-party → first-party).
- No docstring cross-system refs, no em dashes, no inline comments, no employer/AI-assistant attribution.
- LOC under cap on all files (max 175 LOC).
- Security audit confirms no code defects; all threat questions resolve to NO ISSUE.
- Coverage 100% objects, 100% client (exceeds 95% gate).

**Recommended merge:** Code is ready for integration. No changes needed. The adapter is a clean, reusable addition to logging-mixin's inbound-adapter family.
