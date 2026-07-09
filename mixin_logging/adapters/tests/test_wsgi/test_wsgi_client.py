"""Tests for WSGI middleware and app wrapper."""

from __future__ import annotations

import pytest

from mixin_logging import get_correlation_id
from mixin_logging.adapters.constants import wsgi as const
from mixin_logging.adapters.wsgi import wsgi_client, wsgi_objects as wsgi_objs
from mixin_logging.common.constants import tests as test_const


class TestCorrelationIdMiddleware:
    """Tests for CorrelationIdMiddleware WSGI middleware."""

    def test_happy_path_correlation_extracted_and_response_header_set(
        self,
        make_environ,
        start_response_capture,
        mock_app_that_calls_start_response,
    ) -> None:
        """CorrelationIdMiddleware extracts header and injects response header."""
        captured, start_response = start_response_capture
        environ = make_environ({"X-Correlation-ID": test_const.CORRELATION_ID_ABC_123})
        middleware = wsgi_client.CorrelationIdMiddleware(
            mock_app_that_calls_start_response
        )
        iterable = middleware(environ, start_response)
        list(iterable)
        assert len(captured) == 1
        status, headers = captured[0]
        header_dict = dict(headers)
        assert (
            header_dict.get(const.CORRELATION_ID_HEADER)
            == test_const.CORRELATION_ID_ABC_123
        )

    def test_absent_header_generates_and_sets_response_header(
        self,
        make_environ,
        start_response_capture,
        mock_app_that_calls_start_response,
    ) -> None:
        """CorrelationIdMiddleware generates uuid4 and injects response header when absent."""
        captured, start_response = start_response_capture
        environ = make_environ()
        middleware = wsgi_client.CorrelationIdMiddleware(
            mock_app_that_calls_start_response
        )
        iterable = middleware(environ, start_response)
        list(iterable)
        assert len(captured) == 1
        status, headers = captured[0]
        header_dict = dict(headers)
        generated_id = header_dict.get(const.CORRELATION_ID_HEADER)
        assert generated_id is not None
        assert len(generated_id) == 12
        assert all(char in "0123456789abcdef" for char in generated_id)

    def test_correlation_cleared_after_response_iteration_completes(
        self,
        make_environ,
        start_response_capture,
        mock_app_that_calls_start_response,
    ) -> None:
        """CorrelationIdMiddleware clears context after wrapped app iteration finishes."""
        captured, start_response = start_response_capture
        environ = make_environ({"X-Correlation-ID": test_const.CORRELATION_ID_TEST})
        middleware = wsgi_client.CorrelationIdMiddleware(
            mock_app_that_calls_start_response
        )
        iterable = middleware(environ, start_response)
        list(iterable)
        assert get_correlation_id() is None

    def test_correlation_cleared_even_if_wrapped_app_raises(
        self,
        make_environ,
        start_response_capture,
    ) -> None:
        """CorrelationIdMiddleware clears context even if wrapped app raises exception."""

        def failing_app(environ, start_response):
            raise RuntimeError(test_const.RAISE_MATCH_BOOM)

        captured, start_response = start_response_capture
        environ = make_environ({"X-Correlation-ID": test_const.CORRELATION_ID_TEST})
        middleware = wsgi_client.CorrelationIdMiddleware(failing_app)
        with pytest.raises(RuntimeError, match=test_const.RAISE_MATCH_BOOM):
            iterable = middleware(environ, start_response)
            list(iterable)
        assert get_correlation_id() is None

    def test_wrapped_app_called_with_correct_environ_and_start_response(
        self,
        make_environ,
        start_response_capture,
    ) -> None:
        """CorrelationIdMiddleware passes environ and start_response to wrapped app."""
        captured_args = {}

        def recording_app(environ, start_response):
            captured_args["environ"] = environ
            captured_args["start_response"] = start_response
            start_response(test_const.HTTP_STATUS_200_OK, [])
            return iter([])

        captured, start_response = start_response_capture
        environ = make_environ({"X-Correlation-ID": test_const.CORRELATION_ID_TEST})
        middleware = wsgi_client.CorrelationIdMiddleware(recording_app)
        iterable = middleware(environ, start_response)
        list(iterable)
        assert captured_args["environ"] is environ
        assert callable(captured_args["start_response"])


class TestWsgiApp:
    """Tests for WsgiApp WSGI app wrapper."""

    def test_sets_correlation_id_into_context_before_calling_wrapped_app(
        self,
        make_environ,
        start_response_capture,
    ) -> None:
        """WsgiApp sets preset correlation ID into context before calling wrapped app."""
        captured_correlation_ids = []

        def recording_app(environ, start_response):
            from mixin_logging import get_correlation_id

            captured_correlation_ids.append(get_correlation_id())
            start_response(test_const.HTTP_STATUS_200_OK, [])
            return iter([])

        captured, start_response = start_response_capture
        environ = make_environ()
        correlation = wsgi_objs.WsgiCorrelation(
            correlation_id=test_const.CORRELATION_ID_PRESET_ID_123,
            from_header=True,
        )
        app_wrapper = wsgi_client.WsgiApp(app=recording_app, correlation=correlation)
        iterable = app_wrapper(environ, start_response)
        list(iterable)
        assert captured_correlation_ids[0] == test_const.CORRELATION_ID_PRESET_ID_123

    def test_delegates_to_wrapped_app_with_correct_environ_and_start_response(
        self,
        make_environ,
        start_response_capture,
    ) -> None:
        """WsgiApp passes environ and start_response to wrapped app."""
        captured_args = {}

        def recording_app(environ, start_response):
            captured_args["environ"] = environ
            captured_args["start_response"] = start_response
            start_response(test_const.HTTP_STATUS_200_OK, [])
            return iter([b"response"])

        captured, start_response = start_response_capture
        environ = make_environ()
        correlation = wsgi_objs.WsgiCorrelation(
            correlation_id=test_const.CORRELATION_ID_TEST_ID_456,
            from_header=False,
        )
        app_wrapper = wsgi_client.WsgiApp(app=recording_app, correlation=correlation)
        iterable = app_wrapper(environ, start_response)
        response = list(iterable)
        assert captured_args["environ"] is environ
        assert callable(captured_args["start_response"])
        assert response == [b"response"]
