"""Tests for CorrelationIdInjector (botocore before-sign adapter)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest import mock

from botocore.awsrequest import AWSRequest
from botocore.session import Session

from mixin_logging import set_correlation_id
from mixin_logging.adapters.botocore import botocore_client
from mixin_logging.adapters.constants import botocore as const
from mixin_logging.common.constants import tests as test_const


class TestCorrelationIdInjectorRegistration:
    """Tests for CorrelationIdInjector registration class methods."""

    def test_register_on_session_registers_before_sign_handler(self) -> None:
        """register_on_session() subscribes inject_before_sign to the before-sign event."""
        session = mock.Mock()
        botocore_client.CorrelationIdInjector.register_on_session(session)
        session.register.assert_called_once_with(
            const.BEFORE_SIGN_EVENT,
            botocore_client.CorrelationIdInjector.inject_before_sign,
        )

    def test_register_on_client_registers_before_sign_handler(self) -> None:
        """register_on_client() subscribes inject_before_sign on the client event system."""
        client = mock.Mock()
        botocore_client.CorrelationIdInjector.register_on_client(client)
        client.meta.events.register.assert_called_once_with(
            const.BEFORE_SIGN_EVENT,
            botocore_client.CorrelationIdInjector.inject_before_sign,
        )


class TestCorrelationIdInjectorInjectBeforeSign:
    """Tests for CorrelationIdInjector.inject_before_sign() class method."""

    def test_inject_with_set_correlation_writes_header(
        self,
        make_request: Callable[..., Any],
    ) -> None:
        """inject_before_sign() writes X-Correlation-ID header when correlation_id is set."""
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        request = make_request()
        botocore_client.CorrelationIdInjector.inject_before_sign(request=request)
        assert (
            request.headers[const.CORRELATION_ID_HEADER]
            == test_const.CORRELATION_ID_VALID_ID_123
        )

    def test_inject_without_context_is_noop(
        self,
        make_request: Callable[..., Any],
    ) -> None:
        """inject_before_sign() does nothing when context is not set."""
        request = make_request()
        botocore_client.CorrelationIdInjector.inject_before_sign(request=request)
        assert const.CORRELATION_ID_HEADER not in request.headers

    def test_inject_with_unsafe_context_is_noop(
        self,
        make_request: Callable[..., Any],
    ) -> None:
        """inject_before_sign() does nothing when context has an unsafe value."""
        set_correlation_id("bad\r\nvalue")
        request = make_request()
        botocore_client.CorrelationIdInjector.inject_before_sign(request=request)
        assert const.CORRELATION_ID_HEADER not in request.headers

    def test_inject_replaces_existing_header_without_duplicating(
        self,
        make_request: Callable[..., Any],
    ) -> None:
        """inject_before_sign() overwrites a pre-existing header rather than appending a duplicate."""
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        request = make_request()
        request.headers[const.CORRELATION_ID_HEADER] = "stale-value"
        botocore_client.CorrelationIdInjector.inject_before_sign(request=request)
        assert (
            request.headers[const.CORRELATION_ID_HEADER]
            == test_const.CORRELATION_ID_VALID_ID_123
        )
        assert request.headers.get_all(const.CORRELATION_ID_HEADER) == [
            test_const.CORRELATION_ID_VALID_ID_123,
        ]


class TestCorrelationIdInjectorRealDispatch:
    """Integration tests driving botocore's real before-sign event emitter."""

    def test_register_on_client_injects_via_real_event_dispatch(self) -> None:
        """A registered injector adds the header when botocore's real emitter fires before-sign."""
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        session = Session()
        client = session.create_client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )
        botocore_client.CorrelationIdInjector.register_on_client(client)
        request = AWSRequest(method="GET", url="https://s3.amazonaws.com/", headers={})
        client.meta.events.emit(
            "before-sign.s3.ListBuckets",
            request=request,
            signing_name="s3",
            region_name="us-east-1",
            signature_version="s3v4",
            request_signer=None,
            operation_name="ListBuckets",
        )
        assert (
            request.headers[const.CORRELATION_ID_HEADER]
            == test_const.CORRELATION_ID_VALID_ID_123
        )
