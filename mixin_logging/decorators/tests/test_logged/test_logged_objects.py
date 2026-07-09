"""Tests for LoggedContainer dataclass."""

from __future__ import annotations

import pytest

from mixin_logging import LoggedContainer
from mixin_logging.common.constants import tests as test_const


class TestLoggedContainer:
    """Tests for LoggedContainer: log-event name derivation."""

    def test_logged_container_start_property(self) -> None:
        """LoggedContainer.start derives <event>.start."""
        container = LoggedContainer(test_const.EVENT_AUDIT)
        assert container.start == test_const.EVENT_AUDIT_START

    def test_logged_container_error_property(self) -> None:
        """LoggedContainer.error derives <event>.error."""
        container = LoggedContainer(test_const.EVENT_AUDIT)
        assert container.error == test_const.EVENT_AUDIT_ERROR

    def test_logged_container_empty_event_raises_value_error(
        self,
    ) -> None:
        """LoggedContainer("") raises ValueError."""
        with pytest.raises(
            ValueError,
            match=test_const.RAISE_MATCH_LOGGED_CONTAINER_EVENT_EMPTY,
        ):
            LoggedContainer("")
