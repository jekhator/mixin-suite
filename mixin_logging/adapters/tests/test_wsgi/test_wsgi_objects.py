"""Tests for WsgiCorrelation dataclass."""

from __future__ import annotations

import pytest

from mixin_logging.adapters.constants import wsgi as const
from mixin_logging.adapters.wsgi import wsgi_objects as wsgi_objs
from mixin_logging.common.constants import tests as test_const


class TestWsgiCorrelation:
    """Tests for WsgiCorrelation value object."""

    def test_from_header_present_extracts_correlation_id(
        self,
        make_environ,
    ) -> None:
        """from_environ() extracts X-Correlation-ID and sets from_header=True."""
        environ = make_environ({"X-Correlation-ID": test_const.CORRELATION_ID_ABC_123})
        correlation = wsgi_objs.WsgiCorrelation.from_environ(environ)
        assert correlation.correlation_id == test_const.CORRELATION_ID_ABC_123
        assert correlation.from_header is True

    def test_from_header_absent_generates_uuid(
        self,
        make_environ,
    ) -> None:
        """from_environ() generates uuid4 hex and sets from_header=False when missing."""
        environ = make_environ()
        correlation = wsgi_objs.WsgiCorrelation.from_environ(environ)
        assert correlation.from_header is False
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)

    @pytest.mark.parametrize("unsafe_char", ["\r", "\n", "\0"])
    def test_unsafe_chars_in_header_triggers_silent_regen(
        self,
        make_environ,
        unsafe_char,
    ) -> None:
        """from_environ() silently falls back to uuid4 if header contains \\r/\\n/\\0."""
        environ = make_environ({"X-Correlation-ID": f"abc{unsafe_char}xyz"})
        correlation = wsgi_objs.WsgiCorrelation.from_environ(environ)
        assert correlation.from_header is False
        assert correlation.correlation_id != f"abc{unsafe_char}xyz"
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)

    def test_overlong_header_triggers_silent_regen(
        self,
        make_environ,
    ) -> None:
        """from_environ() silently falls back to uuid4 if header exceeds MAX_LENGTH."""
        overlong = "a" * (const.CORRELATION_ID_MAX_LENGTH + 1)
        environ = make_environ({"X-Correlation-ID": overlong})
        correlation = wsgi_objs.WsgiCorrelation.from_environ(environ)
        assert correlation.from_header is False
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)

    def test_empty_correlation_id_raises_value_error(self) -> None:
        """__post_init__() raises ValueError if correlation_id is empty string."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_EMPTY):
            wsgi_objs.WsgiCorrelation(correlation_id="", from_header=False)

    def test_response_header_property_returns_tuple(self) -> None:
        """response_header property returns (header_name, correlation_id) tuple."""
        correlation = wsgi_objs.WsgiCorrelation(
            correlation_id=test_const.CORRELATION_ID_TEST,
            from_header=True,
        )
        header_name, header_value = correlation.response_header
        assert header_name == const.CORRELATION_ID_HEADER
        assert header_value == test_const.CORRELATION_ID_TEST
