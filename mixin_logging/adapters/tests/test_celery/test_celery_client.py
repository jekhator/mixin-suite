"""Tests for CorrelationSignals (celery signal handlers for correlation-ID propagation)."""

from __future__ import annotations

from typing import Any
from unittest import mock

from mixin_logging import get_correlation_id, set_correlation_id
from mixin_logging.adapters.celery import celery_client
from mixin_logging.adapters.constants import celery as const
from mixin_logging.common.constants import tests as test_const


class TestCorrelationSignalsInjectOnPublish:
    """Tests for CorrelationSignals.inject_on_publish() class method."""

    def test_inject_on_publish_with_set_correlation_writes_header(self) -> None:
        """inject_on_publish() writes correlation_id into headers dict when context set."""
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        headers: dict[str, str] = {}
        celery_client.CorrelationSignals.inject_on_publish(headers=headers)
        assert (
            headers[const.CORRELATION_ID_HEADER]
            == test_const.CORRELATION_ID_VALID_ID_123
        )

    def test_inject_on_publish_without_context_is_noop(self) -> None:
        """inject_on_publish() does nothing when context is not set."""
        headers: dict[str, str] = {}
        celery_client.CorrelationSignals.inject_on_publish(headers=headers)
        assert const.CORRELATION_ID_HEADER not in headers

    def test_inject_on_publish_with_unsafe_context_is_noop(self) -> None:
        """inject_on_publish() does nothing when context has an unsafe value."""
        set_correlation_id("bad\r\nvalue")
        headers: dict[str, str] = {}
        celery_client.CorrelationSignals.inject_on_publish(headers=headers)
        assert const.CORRELATION_ID_HEADER not in headers

    def test_inject_on_publish_with_none_headers_is_noop(self) -> None:
        """inject_on_publish() does nothing when headers is None."""
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        celery_client.CorrelationSignals.inject_on_publish(headers=None)

    def test_inject_on_publish_overwrites_existing_header(self) -> None:
        """inject_on_publish() overwrites a pre-existing header."""
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        headers: dict[str, str] = {const.CORRELATION_ID_HEADER: "stale-value"}
        celery_client.CorrelationSignals.inject_on_publish(headers=headers)
        assert (
            headers[const.CORRELATION_ID_HEADER]
            == test_const.CORRELATION_ID_VALID_ID_123
        )


class TestCorrelationSignalsRestoreOnPrerun:
    """Tests for CorrelationSignals.restore_on_prerun() class method."""

    def test_restore_on_prerun_with_header_sets_context(self) -> None:
        """restore_on_prerun() sets correlation context from task.request.headers."""
        task = mock.Mock()
        task.request.headers = {
            const.CORRELATION_ID_HEADER: test_const.CORRELATION_ID_VALID_ID_123
        }
        celery_client.CorrelationSignals.restore_on_prerun(task=task)
        assert get_correlation_id() == test_const.CORRELATION_ID_VALID_ID_123

    def test_restore_on_prerun_without_task_is_noop(self) -> None:
        """restore_on_prerun() does nothing when task is None."""
        celery_client.CorrelationSignals.restore_on_prerun(task=None)
        assert get_correlation_id() is None

    def test_restore_on_prerun_without_header_is_noop(self) -> None:
        """restore_on_prerun() does nothing when header is absent."""
        task = mock.Mock()
        task.request.headers = {}
        celery_client.CorrelationSignals.restore_on_prerun(task=task)
        assert get_correlation_id() is None

    def test_restore_on_prerun_without_request_headers_is_noop(self) -> None:
        """restore_on_prerun() does nothing when task.request.headers is None."""
        task = mock.Mock()
        task.request.headers = None
        celery_client.CorrelationSignals.restore_on_prerun(task=task)
        assert get_correlation_id() is None

    def test_restore_on_prerun_with_unsafe_header_is_noop(self) -> None:
        """restore_on_prerun() does nothing when header value is unsafe."""
        task = mock.Mock()
        task.request.headers = {const.CORRELATION_ID_HEADER: "bad\r\nvalue"}
        celery_client.CorrelationSignals.restore_on_prerun(task=task)
        assert get_correlation_id() is None

    def test_restore_on_prerun_overwrites_existing_context(self) -> None:
        """restore_on_prerun() overwrites an existing correlation context."""
        set_correlation_id(test_const.CORRELATION_ID_SHOULD_BE_CLEARED)
        task = mock.Mock()
        task.request.headers = {
            const.CORRELATION_ID_HEADER: test_const.CORRELATION_ID_VALID_ID_123
        }
        celery_client.CorrelationSignals.restore_on_prerun(task=task)
        assert get_correlation_id() == test_const.CORRELATION_ID_VALID_ID_123


class TestCorrelationSignalsClearOnPostrun:
    """Tests for CorrelationSignals.clear_on_postrun() class method."""

    def test_clear_on_postrun_clears_correlation_context(self) -> None:
        """clear_on_postrun() clears the correlation context."""
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        celery_client.CorrelationSignals.clear_on_postrun()
        assert get_correlation_id() is None


class TestCorrelationSignalsConnect:
    """Tests for CorrelationSignals.connect() class method."""

    def test_connect_registers_signal_handlers(self) -> None:
        """connect() registers all three handlers on celery signals (weak=False)."""
        with mock.patch(
            "mixin_logging.adapters.celery.celery_client.before_task_publish"
        ) as mock_publish:
            with mock.patch(
                "mixin_logging.adapters.celery.celery_client.task_prerun"
            ) as mock_prerun:
                with mock.patch(
                    "mixin_logging.adapters.celery.celery_client.task_postrun"
                ) as mock_postrun:
                    celery_client.CorrelationSignals.connect()
                    mock_publish.connect.assert_called_once_with(
                        celery_client.CorrelationSignals.inject_on_publish,
                        weak=False,
                    )
                    mock_prerun.connect.assert_called_once_with(
                        celery_client.CorrelationSignals.restore_on_prerun,
                        weak=False,
                    )
                    mock_postrun.connect.assert_called_once_with(
                        celery_client.CorrelationSignals.clear_on_postrun,
                        weak=False,
                    )


class TestCorrelationSignalsRealCeleryIntegration:
    """Integration tests driving celery's real signal machinery end-to-end."""

    def test_real_celery_publish_prerun_postrun_roundtrip(
        self,
        celery_app: Any,
    ) -> None:
        """Real celery app with CorrelationSignals drives correlation_id through publish→prerun→postrun."""
        app = celery_app()
        celery_client.CorrelationSignals.connect()
        context_values: list[str | None] = []

        @app.task
        def tracked_task() -> None:
            """Task that captures correlation_id inside prerun and postrun."""
            context_values.append(get_correlation_id())

        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        tracked_task.apply_async()
        assert context_values[0] == test_const.CORRELATION_ID_VALID_ID_123
        assert get_correlation_id() is None

    def test_real_celery_no_context_on_publish_skips_injection(
        self,
        celery_app: Any,
    ) -> None:
        """Real celery app with no context does not inject header on publish."""
        app = celery_app()
        celery_client.CorrelationSignals.connect()
        context_values: list[str | None] = []

        @app.task
        def untracked_task() -> None:
            """Task without correlation context."""
            context_values.append(get_correlation_id())

        untracked_task.apply_async()
        assert context_values[0] is None

    def test_real_celery_signal_isolation_between_tests(
        self,
        celery_app: Any,
    ) -> None:
        """Real celery signals do not leak between test tasks via fresh app."""
        app1 = celery_app()
        celery_client.CorrelationSignals.connect()

        context_values: list[str | None] = []

        @app1.task
        def task_one() -> None:
            """First task."""
            context_values.append(get_correlation_id())

        set_correlation_id(test_const.CORRELATION_ID_TRACE)
        task_one.apply_async()
        app1.connection().close()
        assert context_values[0] == test_const.CORRELATION_ID_TRACE
