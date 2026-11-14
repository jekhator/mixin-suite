# Optimization pass audit (2026-10-19): mixin_retry

## Purpose

This document records an optimization pass over every Python file under mixin_retry/ (11 files, source and tests). The pass looked for correctness defects, dead and duplicated code, control-flow simplifications, typing precision, constants placement, naming, per-call performance, test determinism and docs truth. The retry executor was the focus: the wrappers, the backoff arithmetic and the test tree. Each file is listed in the table at the end with its findings, whether it changed, and a note.

## Method

- Scope: all .py files under mixin_retry/ (source and tests), 11 files after the pass including one new constants module.
- Lenses: correctness, dead and duplicated code, control flow, typing, constants, naming, performance, tests, docs truth.
- Verification: defects were confirmed where they could be shown by running code: small probes ran against the pre-pass tree (commit 3a57a8b) and against the changed tree on Python 3.12.
- Changes were committed one group at a time (source, then tests), each after the local gates passed.

## Summary

- Files reviewed: 11
- Files changed or added: 5
- Files unchanged: 6 (each with its reason in the table)
- Files with at least one finding: 3
- Findings by lens (a file can carry more than one): constants 3, control flow 1, correctness 1, coverage 1, determinism 1, typing 1
- Tests before and after: 26 before, 28 after (pytest collection of mixin_retry)
- Coverage: 100 percent branch coverage of the whole suite before and after; see the repository section in the mixin_logging audit for the gate outputs.

## Behavior changes

1. Backoff growth overflow. The exponential term raised OverflowError when the growth factor left float range, for example a multiplier of 2.0 at attempt 1100 with a large max_attempts. The delay is now the maximum backoff (zero when the base is zero). CHANGELOG Fixed entry: Retry backoff overflow.
2. Attempt loop. The loop runs max_attempts - 1 guarded attempts and then one direct call. The attempts made, the predicate call sites and the exception that reaches the caller are unchanged; no other observable behavior changed.

## Deferred candidates

These were found during the pass and left unchanged, because the change alters behavior beyond the objective or needs a design decision.

- docs/mixin_retry (README.md and architecture/flow-trace.md) described the removed @retried decorator, RetryClient and a Python 3.11 floor; both files were rewritten for RetryPolicy and RetryExecutor in the documentation pass.
- The jitter draws from the module-level random generator. Injecting a generator would make the jitter tests exact, but it changes the constructor surface, so it is deferred.
- `RetryExecutor.call` keeps `policy=None` as its default and raises ValueError for it. A required keyword-only policy would be a breaking signature change and is deferred.
- Method docstrings on the wrap helpers and call are kept pending a separate decision.

## Per-file table

Each Python file under mixin_retry/ appears once. Findings carry a lens tag in brackets.

| Path | Findings | Changed | Note |
| --- | --- | --- | --- |
| mixin_retry/__init__.py | none | no | Curated public API; exports unchanged. |
| mixin_retry/common/__init__.py | none | no | Package docstring only. |
| mixin_retry/common/constants/__init__.py | none | yes | Re-exports the new backoff module alongside errors. |
| mixin_retry/common/constants/backoff.py | [constants] jitter bounds 0.9 and 1.1 were literals in executor | yes (new) | JITTER_MIN_FACTOR and JITTER_MAX_FACTOR. |
| mixin_retry/common/constants/errors.py | none | no | Error messages already named; no change. |
| mixin_retry/config/__init__.py | none | no | Package docstring only. |
| mixin_retry/config/_version.py | none | yes | Version bump to 0.7.0 (release lockstep); not a finding. |
| mixin_retry/executor.py | [typing] _wrap_sync and _wrap_async returned a callable typed with Any; [control flow] per-attempt last-attempt check and unreachable tail with pragma; [correctness] multiplier ** attempt raises OverflowError for large attempt counts; [constants] jitter literals | yes | Helpers typed with the wrap type parameter (async helper types the awaited result; one cast in wrap); loop runs max_attempts - 1 guarded attempts then one direct call; growth overflow capped at the maximum; jitter bounds from constants. |
| mixin_retry/policy.py | none | no | Validation complete; jitter and predicate docstrings match the executor. |
| mixin_retry/tests/__init__.py | none | no | Package marker. |
| mixin_retry/tests/test_retry_executor.py | [constants] literal policy-required message and jitter bounds; [determinism] per-test time import; [coverage] no regression for the overflowing backoff | yes | Constants in assertions; module-level time import; overflow regression with zero and positive base; a probe on the pre-pass tree raises OverflowError for this input. |
