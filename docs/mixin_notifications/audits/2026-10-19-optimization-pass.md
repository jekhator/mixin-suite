# Optimization pass audit (2026-10-19): mixin_notifications

## Purpose

This document records an optimization pass over every Python file under mixin_notifications/ (27 files, source and tests). The pass looked for correctness defects, dead and duplicated code, control-flow simplifications, typing precision, constants placement, naming, per-call performance, test determinism and docs truth. The backends, the egress gate, the suppression tracker and the event factory were the focus. Each file is listed in the table at the end with its findings, whether it changed, and a note.

## Method

- Scope: all .py files under mixin_notifications/ (source and tests), 27 files after the pass. dispatch/_client.py is the ruff format carve-out; it was edited by hand and no formatter was run over it.
- Lenses: correctness, dead and duplicated code, control flow, typing, constants, naming, performance, tests, docs truth.
- Verification: defects were confirmed where they could be shown by running code: small probes ran against the pre-pass tree (commit 3a57a8b) and against the changed tree on Python 3.12.
- Changes were committed one group at a time (source, then tests), each after the local gates passed.

## Summary

- Files reviewed: 27
- Files changed or added: 16
- Files unchanged: 11 (each with its reason in the table)
- Files with at least one finding: 15
- Findings by lens (a file can carry more than one): assertion 3, behavior 2, constants 7, control flow 1, correctness 3, coverage 1, deferred 3, determinism 1, duplication 9, modernization 1, performance 9, typing 4
- Tests before and after: 69 before, 78 after (pytest collection of mixin_notifications)
- Coverage: 100 percent branch coverage of the whole suite before and after; see the repository section in the mixin_logging audit for the gate outputs.

## Behavior changes

1. SES attachment header. The attachment filename is quoted in Content-Disposition (for example filename="quarterly report.txt"); previously it was written unquoted after an equals sign with a space, which breaks on names with spaces or semicolons. CHANGELOG Fixed entry: SES attachment filename.
2. AWS error classification. An error whose response attribute is not a mapping no longer raises while the failure is classified; the failure is reported with the exception class name. CHANGELOG Fixed entry: AWS error classification.
3. Suppression eviction. At capacity the tracker removes the least recently recorded key in constant time, instead of the entry with the smallest timestamp after a full scan. The two agree when the clock is monotonic. CHANGELOG Changed entry: Suppression eviction.
4. Dead-letter warning text. The warning logged when the dead_letter backend fails uses one message for both fallback paths: "Dead-letter backend failed (<prefix>)". The exhaustion path previously logged "Dead-letter backend failed during exhaustion fallback". CHANGELOG Changed entry: Dead-letter warning text.
5. Constants location. Backend detail text, the retryable AWS error codes, the redacted egress body and the count metadata key moved to constants modules. None of these names are exported from the package root. CHANGELOG Changed entries: Notification backend constants and Egress constants.
6. Egress gating, suppression keys, result shapes and the public names are unchanged.

## Deferred candidates

These were found during the pass and left unchanged, because the change alters behavior beyond the objective or needs a design decision.

- Egress gate and SNS topic override. The egress gate replaces event metadata with a count for external backends, and SNSBackend is an external backend. The per-event topic_arn override therefore never applies through the Dispatcher: a probe sent the event directly to the override topic and, through notify, to the default topic. The test test_external_backend_metadata_reduced_to_counts pins the reduction. Whether a routing key may survive egress is a design decision for the maintainer.
- SES content type. SESBackend writes every attachment part as application/octet-stream and ignores Attachment.content_type. Using the declared type needs a validated type and subtype split first; that changes outbound messages and is deferred.
- Suppression clock. The window uses time.time(), a wall clock that can step. A monotonic source is more robust but changes the meaning of the stored timestamps and the test seam; deferred.
- Retry predicate scope. RetryingBackend retries whatever the policy predicate accepts, including BaseException subclasses such as KeyboardInterrupt if the caller allows them. This is the caller choice under the predicate contract and is recorded, not changed.
- docs/mixin_notifications/README.md. The attachment example passes attachments= to NotificationEventClient.create(), which does not accept it; running the example raises TypeError (verified). The RetryingBackend example output and the SNS and SES usage text are not verified against 0.7.0. architecture/flow-trace.md and the 0.6.0 reviews name module paths that no longer exist (dispatch_client.py, events_client.py). All of this is deferred to the documentation pass.
- Method docstrings are kept; the method docstring ruling is pending.

## Per-file table

Each Python file under mixin_notifications/ appears once. Findings carry a lens tag in brackets.

| Path | Findings | Changed | Note |
| --- | --- | --- | --- |
| mixin_notifications/__init__.py | none | no | Curated public API; exports unchanged. |
| mixin_notifications/backends/__init__.py | none | no | Re-exports only; the AWS error helper stays internal. |
| mixin_notifications/backends/_client.py | [duplication] four copies of the dead-letter fallback; [duplication] retry predicate and policy rebuilt field by field; [performance] exception class and executor created per send; [performance] severity map built per log call; [constants] literal detail strings; [typing] constructor without return annotation | yes | One fallback helper and one exception class at module level; policy rebuilt with replace; severity map a class constant keyed by Severity; detail text from constants. |
| mixin_notifications/backends/_objects.py | none | no | Protocol and result value object; no finding. |
| mixin_notifications/backends/aws_errors.py | [duplication] SES and SNS each carried the same error classification; [correctness] a non-mapping response attribute raised while the failure was being classified | yes (new) | Shared AwsErrorClassifier; code extraction type-checks each level and falls back to the exception class name. |
| mixin_notifications/backends/ses.py | [typing] client typed Any; [correctness] attachment filename unquoted in Content-Disposition; [performance] email imports inside send; [duplication] classification copied from SNS; [behavior, deferred] attachment content_type is never used for the MIME type | yes | Client typed by a Protocol; filename quoted by the header API; imports at module level; classification shared. The content_type gap is deferred. |
| mixin_notifications/backends/sns.py | [typing] client typed Any; [performance] constants imported inside send; [duplication] classification copied from SES; [control flow] temporary variables for title and body | yes | Client typed by a Protocol; module-level import; shared classification; attribute literal documented as the AWS request shape. |
| mixin_notifications/common/__init__.py | none | no | Package docstring only. |
| mixin_notifications/common/constants/__init__.py | none | no | Package docstring only. |
| mixin_notifications/common/constants/backends.py | [constants] backend detail text and AWS error codes lived in the backend modules | yes (new) | RETRY_*, DEAD_LETTER_* detail constants and RETRYABLE_AWS_ERROR_CODES under the const alias. |
| mixin_notifications/common/constants/events.py | [constants] redacted body text and count metadata key were literals in the egress gate | yes | EGRESS_REDACTED_BODY and EGRESS_COUNT_METADATA_KEY added. |
| mixin_notifications/config/__init__.py | none | no | Package docstring only. |
| mixin_notifications/config/_version.py | none | yes | Version bump to 0.7.0 (release lockstep); not a finding. |
| mixin_notifications/dispatch/__init__.py | none | no | Re-exports only. |
| mixin_notifications/dispatch/_client.py | [correctness] truthiness tests on policy and tracker objects instead of identity checks; [constants] redacted body and metadata key literals; [performance] constants imported inside the egress gate on every external send; [behavior, deferred] egress gate drops metadata, so SNS per-event topic override never applies through the Dispatcher; [deferred] suppression window uses wall-clock time | yes | is-not-None checks; constants module-level. Carve-out file edited by hand only; the metadata and wall-clock items are deferred. |
| mixin_notifications/dispatch/_objects.py | none | no | Result value object; no finding. |
| mixin_notifications/events/__init__.py | none | no | Re-exports only. |
| mixin_notifications/events/_client.py | [performance] correlation helper imported inside create on every event; [modernization] timezone.utc instead of datetime.UTC | yes | Module-level import; datetime.UTC. |
| mixin_notifications/events/_objects.py | [performance] constants module imported inside two __post_init__ validators | yes | Module-level import. |
| mixin_notifications/suppression/__init__.py | none | no | Re-exports only. |
| mixin_notifications/suppression/_objects.py | [performance] eviction scanned every entry on each insert at capacity; [performance] is_suppressed looked up the key twice | yes | Re-recorded keys move to the end; eviction removes the first key in constant time; single lookup with get. |
| mixin_notifications/tests/__init__.py | none | no | Package marker. |
| mixin_notifications/tests/conftest.py | [typing] capturing backends returned dicts where DeliveryResult is the contract; [duplication] two event fixtures with the same body and one unused; [duplication] capturing backends written out twice | yes | One typed CapturingBackend; one event fixture with a Used-by docstring. |
| mixin_notifications/tests/test_backends.py | [duplication] inline DeliveryResult imports in fake backends; [assertion] one assertion accepted either of two strings; [coverage] classifier branches, SNS attributes and SES attachment header untested; [constants] literal detail strings | yes | Imports at module level; single constant assertion; classifier, attribute and header tests added; constants used. |
| mixin_notifications/tests/test_dispatch.py | [determinism] time.sleep(1.1) for the window test; [duplication] FailingBackend defined twice; [assertion] eviction test read private storage without checking which key was evicted | yes | Clock patched through monkeypatch; one module-level FailingBackend; eviction asserts the surviving keys and a re-record test added. |
| mixin_notifications/tests/test_egress_gate.py | [constants] literal redacted body and metadata key | yes | Constants in assertions. |
| mixin_notifications/tests/test_events.py | [constants] literal error messages in pytest.raises; [assertion] broad pytest.raises(Exception) for frozen check | yes | Constants matched; FrozenInstanceError asserted. |
