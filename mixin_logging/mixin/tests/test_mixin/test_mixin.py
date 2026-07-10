"""Tests for LoggingMixin class-bound logger with correlation ID injection."""

from __future__ import annotations

import logging
from typing import Any

import pytest

from mixin_logging import LoggingMixin, set_correlation_id
from mixin_logging.common.constants import tests as test_const
from mixin_logging.context.constants import correlation as correlation_const


class TestLoggingMixin:
    """Tests for LoggingMixin."""

    def test_mixin_has_slots(self) -> None:
        """LoggingMixin has __slots__ = () to allow slotted subclasses."""
        assert hasattr(LoggingMixin, "__slots__")
        assert LoggingMixin.__slots__ == ()

    def test_service_class_inherits_cleanly(
        self,
        service_class: type[LoggingMixin],
    ) -> None:
        """Service class with LoggingMixin + __slots__ has no __dict__."""
        svc = service_class()
        with pytest.raises(AttributeError):
            svc.__dict__

    def test_logger_per_class_by_name(self) -> None:
        """Each subclass gets a logger named <module>.<ClassName>."""

        class MyService(LoggingMixin):
            """Service for correlation context tests."""

            __slots__ = ()

        svc = MyService()
        logger = svc._logger
        expected_name = f"{MyService.__module__}.{MyService.__name__}"
        assert logger.name == expected_name

    def test_log_debug_emits_at_debug_level(
        self,
        log_capture: tuple[LoggingMixin, Any],
    ) -> None:
        """log_debug() emits a record at DEBUG level."""
        svc, collector = log_capture
        svc.log_debug("test event")

        assert len(collector.records) == 1
        assert collector.records[0].levelno == logging.DEBUG
        assert collector.records[0].getMessage() == "test event"

    def test_log_info_emits_at_info_level(
        self,
        log_capture: tuple[LoggingMixin, Any],
    ) -> None:
        """log_info() emits a record at INFO level."""
        svc, collector = log_capture
        svc.log_info("test event")

        assert len(collector.records) == 1
        assert collector.records[0].levelno == logging.INFO
        assert collector.records[0].getMessage() == "test event"

    def test_log_warning_emits_at_warning_level(
        self,
        log_capture: tuple[LoggingMixin, Any],
    ) -> None:
        """log_warning() emits a record at WARNING level."""
        svc, collector = log_capture
        svc.log_warning("test event")

        assert len(collector.records) == 1
        assert collector.records[0].levelno == logging.WARNING
        assert collector.records[0].getMessage() == "test event"

    def test_log_error_emits_at_error_level(
        self,
        log_capture: tuple[LoggingMixin, Any],
    ) -> None:
        """log_error() emits a record at ERROR level."""
        svc, collector = log_capture
        svc.log_error("test event")

        assert len(collector.records) == 1
        assert collector.records[0].levelno == logging.ERROR
        assert collector.records[0].getMessage() == "test event"

    def test_log_exception_emits_at_error_level_with_traceback(
        self,
        log_capture: tuple[LoggingMixin, Any],
    ) -> None:
        """log_exception() emits ERROR level record with traceback."""
        svc, collector = log_capture

        try:
            error_msg = "test error"
            raise ValueError(error_msg)  # noqa: EM101
        except ValueError:
            svc.log_exception("caught exception")

        assert len(collector.records) == 1
        assert collector.records[0].levelno == logging.ERROR
        assert collector.records[0].getMessage() == "caught exception"
        assert collector.records[0].exc_info is not None
        assert collector.records[0].exc_info[0] is ValueError

    def test_log_injects_correlation_id(
        self,
        log_capture: tuple[LoggingMixin, Any],
    ) -> None:
        """log_*() injects the current correlation_id into extra."""
        svc, collector = log_capture

        set_correlation_id(test_const.CORRELATION_ID_TRACE)
        svc.log_debug("test")

        assert len(collector.records) == 1
        assert (
            collector.records[0].__dict__[correlation_const.CORRELATION_ID_KEY]
            == test_const.CORRELATION_ID_TRACE
        )

    def test_log_injects_dash_when_correlation_id_unset(
        self,
        log_capture: tuple[LoggingMixin, Any],
    ) -> None:
        """log_*() injects "-" when no correlation_id is set."""
        svc, collector = log_capture
        svc.log_debug("test")

        assert len(collector.records) == 1
        assert (
            collector.records[0].__dict__[correlation_const.CORRELATION_ID_KEY]
            == test_const.UNSET_CORRELATION_MARKER
        )

    def test_log_merges_caller_extra_kwargs(
        self,
        log_capture: tuple[LoggingMixin, Any],
    ) -> None:
        """log_*() merges caller **extra kwargs into the log record."""
        svc, collector = log_capture

        svc.log_debug(
            "test",
            **{
                test_const.FIELD_USER_ID: test_const.USER_ID_42,
                test_const.FIELD_ACTION: test_const.ACTION_CREATE,
            },
        )

        assert len(collector.records) == 1
        assert (
            collector.records[0].__dict__[test_const.FIELD_USER_ID]
            == test_const.USER_ID_42
        )
        assert (
            collector.records[0].__dict__[test_const.FIELD_ACTION]
            == test_const.ACTION_CREATE
        )

    def test_log_extra_ignores_mask_for_logging(self) -> None:
        """_log_extra() ignores mask_for_logging, returns correlation_id + kwargs."""
        set_correlation_id(test_const.CORRELATION_ID_XYZ)

        class Svc(LoggingMixin):
            """Test service for mask_for_logging verification."""

            __slots__ = ()

            def mask_for_logging(self) -> dict[str, Any]:
                return {test_const.FIELD_MASKED: True}

        svc = Svc()
        result = svc._log_extra({test_const.FIELD_CUSTOM: "value"})

        assert (
            result[correlation_const.CORRELATION_ID_KEY]
            == test_const.CORRELATION_ID_XYZ
        )
        assert result[test_const.FIELD_CUSTOM] == "value"
        assert test_const.FIELD_INSTANCE not in result

    def test_log_extra_returns_correlation_and_caller_kwargs_only(
        self,
        service_class: type[LoggingMixin],
    ) -> None:
        """_log_extra() returns only correlation_id + caller kwargs."""
        set_correlation_id(test_const.CORRELATION_ID_XYZ_SHORT)

        svc = service_class()
        result = svc._log_extra(
            {
                test_const.FIELD_USER_ID: test_const.USER_ID_GENERIC,
                test_const.FIELD_ACTION: test_const.ACTION_CREATE,
            },
        )

        assert result == {
            correlation_const.CORRELATION_ID_KEY: test_const.CORRELATION_ID_XYZ_SHORT,
            test_const.FIELD_USER_ID: test_const.USER_ID_GENERIC,
            test_const.FIELD_ACTION: test_const.ACTION_CREATE,
        }

    def test_log_extra_returns_dash_when_no_correlation_id(
        self,
        service_class: type[LoggingMixin],
    ) -> None:
        """_log_extra() returns '-' for correlation_id when unset."""
        svc = service_class()
        result = svc._log_extra({test_const.FIELD_CUSTOM: "value"})

        assert (
            result[correlation_const.CORRELATION_ID_KEY]
            == test_const.UNSET_CORRELATION_MARKER
        )
        assert result[test_const.FIELD_CUSTOM] == "value"

    def test_multiple_service_classes_have_separate_loggers(self) -> None:
        """Different service classes get different logger names."""

        class ServiceA(LoggingMixin):
            """First test service for logger isolation."""

            __slots__ = ()

        class ServiceB(LoggingMixin):
            """Second test service for logger isolation."""

            __slots__ = ()

        svc_a = ServiceA()
        svc_b = ServiceB()

        assert svc_a._logger.name != svc_b._logger.name
        assert "ServiceA" in svc_a._logger.name
        assert "ServiceB" in svc_b._logger.name
