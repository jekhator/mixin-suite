"""Comprehensive tests for WrapperFactory: all four wrapper legs, all payload/timed paths."""

from __future__ import annotations

import asyncio
import logging

import pytest

from mixin_logging import LoggingMixin
from mixin_logging.decorators.logged._wrapper_factory import WrapperFactory
from mixin_logging.decorators.logged.logged_objects import LoggedContainer
from mixin_logging.tests.helpers import _RecordCollector


class TestWrapperStaticSync:
    """Sync static wrapper: payload_from_request success/exception/non-dict, timed latency."""

    def test_sync_static_payload_from_request_success(self) -> None:
        """Sync static: extraction success sets start_payload."""
        collector = _RecordCollector()
        logger = logging.getLogger("test_wrapper").getChild("StaticSyncClass")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(collector)

        def extract(x: int) -> dict[str, object]:  # type: ignore[misc]
            return {"value": x}

        def method(x: int) -> int:  # type: ignore[misc]
            return x * 2

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            method,
            None,
            None,
            extract,
            False,
            for_static_or_class=True,  # type: ignore[arg-type]
            class_module_name="test_wrapper",
            class_name="StaticSyncClass",
        )

        result = wrapped(5)  # type: ignore
        assert result == 10
        logger.removeHandler(collector)
        start_recs = [r for r in collector.records if r.getMessage() == "op.start"]
        assert len(start_recs) == 1
        assert start_recs[0].__dict__.get("value") == 5

    def test_sync_static_payload_from_request_exception(self) -> None:
        """Sync static: extraction exception sets no start_payload, logs warning."""
        collector = _RecordCollector()
        logger = logging.getLogger("test_wrapper").getChild("StaticSyncClass")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(collector)

        def extract(x: int) -> dict[str, object]:  # type: ignore[misc]
            return 1 / 0  # type: ignore

        def method(x: int) -> int:  # type: ignore[misc]
            return x * 2

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            method,
            None,
            None,
            extract,
            False,
            for_static_or_class=True,  # type: ignore[arg-type]
            class_module_name="test_wrapper",
            class_name="StaticSyncClass",
        )

        result = wrapped(5)  # type: ignore
        assert result == 10
        logger.removeHandler(collector)
        warn_recs = [r for r in collector.records if r.levelname == "WARNING"]
        assert len(warn_recs) >= 1

    def test_sync_static_payload_from_request_non_dict(self) -> None:
        """Sync static: extraction non-dict return sets no start_payload, logs warning."""
        collector = _RecordCollector()
        logger = logging.getLogger("test_wrapper").getChild("StaticSyncClass")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(collector)

        def extract(x: int) -> object:  # type: ignore[misc]
            return "not-dict"

        def method(x: int) -> int:  # type: ignore[misc]
            return x * 2

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            method,
            None,
            None,
            extract,  # type: ignore
            False,
            for_static_or_class=True,  # type: ignore[arg-type]
            class_module_name="test_wrapper",
            class_name="StaticSyncClass",
        )

        result = wrapped(5)  # type: ignore
        assert result == 10
        logger.removeHandler(collector)
        warn_recs = [r for r in collector.records if r.levelname == "WARNING"]
        assert len(warn_recs) >= 1

    def test_sync_static_method_raises_with_timed(self) -> None:
        """Sync static: timed=True adds latency_ms to error event."""
        collector = _RecordCollector()
        logger = logging.getLogger("test_wrapper").getChild("StaticSyncClass")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(collector)

        def method() -> None:  # type: ignore[misc]
            raise ValueError("test")

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            method,  # type: ignore
            None,
            None,
            None,
            True,
            for_static_or_class=True,  # type: ignore[arg-type]
            class_module_name="test_wrapper",
            class_name="StaticSyncClass",
        )

        with pytest.raises(ValueError):
            wrapped()  # type: ignore

        logger.removeHandler(collector)
        error_recs = [r for r in collector.records if r.getMessage() == "op.error"]
        assert len(error_recs) == 1
        assert "latency_ms" in error_recs[0].__dict__


class TestWrapperStaticAsync:
    """Async static wrapper: payload_from_request success/exception/non-dict, timed latency."""

    def test_async_static_payload_from_request_success(self) -> None:
        """Async static: extraction success sets start_payload."""
        collector = _RecordCollector()
        logger = logging.getLogger("test_wrapper").getChild("StaticAsyncClass")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(collector)

        def extract(x: int) -> dict[str, object]:  # type: ignore[misc]
            return {"value": x}

        async def method(x: int) -> int:  # type: ignore[misc]
            await asyncio.sleep(0)
            return x * 2

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            method,
            None,
            None,
            extract,
            False,
            for_static_or_class=True,  # type: ignore[arg-type]
            class_module_name="test_wrapper",
            class_name="StaticAsyncClass",
        )

        result = asyncio.run(wrapped(5))  # type: ignore
        assert result == 10
        logger.removeHandler(collector)
        start_recs = [r for r in collector.records if r.getMessage() == "op.start"]
        assert len(start_recs) == 1
        assert start_recs[0].__dict__.get("value") == 5

    def test_async_static_payload_from_request_exception(self) -> None:
        """Async static: extraction exception logs warning."""
        collector = _RecordCollector()
        logger = logging.getLogger("test_wrapper").getChild("StaticAsyncClass")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(collector)

        def extract(x: int) -> dict[str, object]:  # type: ignore[misc]
            return 1 / 0  # type: ignore

        async def method(x: int) -> int:  # type: ignore[misc]
            await asyncio.sleep(0)
            return x * 2

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            method,
            None,
            None,
            extract,
            False,
            for_static_or_class=True,  # type: ignore[arg-type]
            class_module_name="test_wrapper",
            class_name="StaticAsyncClass",
        )

        result = asyncio.run(wrapped(5))  # type: ignore
        assert result == 10
        logger.removeHandler(collector)
        warn_recs = [r for r in collector.records if r.levelname == "WARNING"]
        assert len(warn_recs) >= 1

    def test_async_static_payload_from_request_non_dict(self) -> None:
        """Async static: extraction non-dict return logs warning."""
        collector = _RecordCollector()
        logger = logging.getLogger("test_wrapper").getChild("StaticAsyncClass")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(collector)

        def extract(x: int) -> object:  # type: ignore[misc]
            return "not-dict"

        async def method(x: int) -> int:  # type: ignore[misc]
            await asyncio.sleep(0)
            return x * 2

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            method,
            None,
            None,
            extract,  # type: ignore
            False,
            for_static_or_class=True,  # type: ignore[arg-type]
            class_module_name="test_wrapper",
            class_name="StaticAsyncClass",
        )

        result = asyncio.run(wrapped(5))  # type: ignore
        assert result == 10
        logger.removeHandler(collector)
        warn_recs = [r for r in collector.records if r.levelname == "WARNING"]
        assert len(warn_recs) >= 1

    def test_async_static_method_raises_with_timed(self) -> None:
        """Async static: timed=True adds latency_ms to error event."""
        collector = _RecordCollector()
        logger = logging.getLogger("test_wrapper").getChild("StaticAsyncClass")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(collector)

        async def method() -> None:  # type: ignore[misc]
            await asyncio.sleep(0)
            raise ValueError("test")

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            method,  # type: ignore
            None,
            None,
            None,
            True,
            for_static_or_class=True,  # type: ignore[arg-type]
            class_module_name="test_wrapper",
            class_name="StaticAsyncClass",
        )

        with pytest.raises(ValueError):
            asyncio.run(wrapped())  # type: ignore

        logger.removeHandler(collector)
        error_recs = [r for r in collector.records if r.getMessage() == "op.error"]
        assert len(error_recs) == 1
        assert "latency_ms" in error_recs[0].__dict__


class TestWrapperInstanceSyncWithRequest:
    """Sync instance wrapper with payload_from_request: success/exception/non-dict."""

    def test_instance_sync_payload_from_request_success(self) -> None:
        """Sync instance: request extraction success sets start_payload."""

        class Svc(LoggingMixin):
            __slots__ = ()

            def process(self, x: int) -> int:
                return x * 2

        def extract_req(x: int) -> dict[str, object]:  # type: ignore[misc]
            return {"input": x}

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            None,
            None,
            extract_req,
            False,  # type: ignore[arg-type]
        )

        svc = Svc()
        result = wrapped(svc, 5)  # type: ignore
        assert result == 10

    def test_instance_sync_payload_from_request_exception(self) -> None:
        """Sync instance: request extraction exception logs warning."""

        class Svc(LoggingMixin):
            __slots__ = ()

            def process(self, x: int) -> int:
                return x * 2

        def extract_req(x: int) -> dict[str, object]:  # type: ignore[misc]
            return 1 / 0  # type: ignore

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            None,
            None,
            extract_req,
            False,  # type: ignore[arg-type]
        )

        svc = Svc()
        result = wrapped(svc, 5)  # type: ignore
        assert result == 10

    def test_instance_sync_payload_from_request_non_dict(self) -> None:
        """Sync instance: request extraction non-dict return logs warning."""

        class Svc(LoggingMixin):
            __slots__ = ()

            def process(self, x: int) -> int:
                return x * 2

        def extract_req(x: int) -> object:  # type: ignore[misc]
            return "not-dict"

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            None,
            None,
            extract_req,  # type: ignore
            False,  # type: ignore[arg-type]
        )

        svc = Svc()
        result = wrapped(svc, 5)  # type: ignore
        assert result == 10


class TestWrapperInstanceSync:
    """Sync instance wrapper: payload_from_result success/exception/non-dict, timed latency."""

    def test_instance_sync_payload_from_result_success(self) -> None:
        """Sync instance: result extraction success sets end_payload."""

        class Svc(LoggingMixin):
            __slots__ = ()

            def process(self) -> int:
                return 42

        def extract(r: object) -> dict[str, object]:  # type: ignore[misc]
            return {"result": r}

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            extract,
            None,
            None,
            False,  # type: ignore[arg-type]
        )

        svc = Svc()
        result = wrapped(svc)  # type: ignore
        assert result == 42

    def test_instance_sync_payload_from_result_exception(self) -> None:
        """Sync instance: result extraction exception logs warning, .end emitted."""

        class Svc(LoggingMixin):
            __slots__ = ()

            def process(self) -> int:
                return 42

        def extract(r: object) -> dict[str, object]:  # type: ignore[misc]
            return 1 / 0  # type: ignore

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            extract,
            None,
            None,
            False,  # type: ignore[arg-type]
        )

        svc = Svc()
        result = wrapped(svc)  # type: ignore
        assert result == 42

    def test_instance_sync_payload_from_result_non_dict(self) -> None:
        """Sync instance: result extraction non-dict return logs warning."""

        class Svc(LoggingMixin):
            __slots__ = ()

            def process(self) -> int:
                return 42

        def extract(r: object) -> object:  # type: ignore[misc]
            return "not-dict"

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            extract,  # type: ignore
            None,
            None,
            False,  # type: ignore[arg-type]
        )

        svc = Svc()
        result = wrapped(svc)  # type: ignore
        assert result == 42

    def test_instance_sync_with_timed_and_result_extraction(self) -> None:
        """Sync instance: timed=True + result extraction adds latency_ms to .end."""

        class Svc(LoggingMixin):
            __slots__ = ()

            def process(self) -> int:
                return 42

        def extract(r: object) -> dict[str, object]:  # type: ignore[misc]
            return {"result": r}

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            extract,
            None,
            None,
            True,  # type: ignore[arg-type]
        )

        svc = Svc()
        result = wrapped(svc)  # type: ignore
        assert result == 42

    def test_instance_sync_error_with_timed_and_result_extraction(self) -> None:
        """Sync instance: error with timed=True + result extraction adds latency_ms to .error."""

        class Svc(LoggingMixin):
            __slots__ = ()

            def process(self) -> None:
                raise ValueError("test")

        def extract(r: object) -> dict[str, object]:  # type: ignore[misc]
            return {"result": r}

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            extract,
            None,
            None,
            True,  # type: ignore[arg-type]
        )

        svc = Svc()
        with pytest.raises(ValueError):
            wrapped(svc)  # type: ignore

    def test_instance_sync_timed_only_no_result_extraction(self) -> None:
        """Sync instance: timed=True with NO result extraction -> .end with latency_ms only."""

        class Svc(LoggingMixin):
            __slots__ = ()

            def process(self) -> int:
                return 42

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            None,
            None,
            None,
            True,  # type: ignore[arg-type]
        )

        svc = Svc()
        result = wrapped(svc)  # type: ignore
        assert result == 42


class TestWrapperInstanceAsyncWithRequest:
    """Async instance wrapper with payload_from_request: success/exception/non-dict."""

    def test_instance_async_payload_from_request_success(self) -> None:
        """Async instance: request extraction success sets start_payload."""

        class Svc(LoggingMixin):
            __slots__ = ()

            async def process(self, x: int) -> int:
                await asyncio.sleep(0)
                return x * 2

        def extract_req(x: int) -> dict[str, object]:  # type: ignore[misc]
            return {"input": x}

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            None,
            None,
            extract_req,
            False,  # type: ignore[arg-type]
        )

        svc = Svc()
        result = asyncio.run(wrapped(svc, 5))  # type: ignore
        assert result == 10

    def test_instance_async_payload_from_request_exception(self) -> None:
        """Async instance: request extraction exception logs warning."""

        class Svc(LoggingMixin):
            __slots__ = ()

            async def process(self, x: int) -> int:
                await asyncio.sleep(0)
                return x * 2

        def extract_req(x: int) -> dict[str, object]:  # type: ignore[misc]
            return 1 / 0  # type: ignore

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            None,
            None,
            extract_req,
            False,  # type: ignore[arg-type]
        )

        svc = Svc()
        result = asyncio.run(wrapped(svc, 5))  # type: ignore
        assert result == 10

    def test_instance_async_payload_from_request_non_dict(self) -> None:
        """Async instance: request extraction non-dict return logs warning."""

        class Svc(LoggingMixin):
            __slots__ = ()

            async def process(self, x: int) -> int:
                await asyncio.sleep(0)
                return x * 2

        def extract_req(x: int) -> object:  # type: ignore[misc]
            return "not-dict"

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            None,
            None,
            extract_req,  # type: ignore
            False,  # type: ignore[arg-type]
        )

        svc = Svc()
        result = asyncio.run(wrapped(svc, 5))  # type: ignore
        assert result == 10


class TestWrapperInstanceAsync:
    """Async instance wrapper: payload_from_result success/exception/non-dict, timed latency."""

    def test_instance_async_payload_from_result_success(self) -> None:
        """Async instance: result extraction success sets end_payload."""

        class Svc(LoggingMixin):
            __slots__ = ()

            async def process(self) -> int:
                await asyncio.sleep(0)
                return 42

        def extract(r: object) -> dict[str, object]:  # type: ignore[misc]
            return {"result": r}

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            extract,
            None,
            None,
            False,  # type: ignore[arg-type]
        )

        svc = Svc()
        result = asyncio.run(wrapped(svc))  # type: ignore
        assert result == 42

    def test_instance_async_payload_from_result_exception(self) -> None:
        """Async instance: result extraction exception logs warning, .end emitted."""

        class Svc(LoggingMixin):
            __slots__ = ()

            async def process(self) -> int:
                await asyncio.sleep(0)
                return 42

        def extract(r: object) -> dict[str, object]:  # type: ignore[misc]
            return 1 / 0  # type: ignore

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            extract,
            None,
            None,
            False,  # type: ignore[arg-type]
        )

        svc = Svc()
        result = asyncio.run(wrapped(svc))  # type: ignore
        assert result == 42

    def test_instance_async_payload_from_result_non_dict(self) -> None:
        """Async instance: result extraction non-dict return logs warning."""

        class Svc(LoggingMixin):
            __slots__ = ()

            async def process(self) -> int:
                await asyncio.sleep(0)
                return 42

        def extract(r: object) -> object:  # type: ignore[misc]
            return "not-dict"

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            extract,  # type: ignore
            None,
            None,
            False,  # type: ignore[arg-type]
        )

        svc = Svc()
        result = asyncio.run(wrapped(svc))  # type: ignore
        assert result == 42

    def test_instance_async_with_timed_and_result_extraction(self) -> None:
        """Async instance: timed=True + result extraction adds latency_ms to .end."""

        class Svc(LoggingMixin):
            __slots__ = ()

            async def process(self) -> int:
                await asyncio.sleep(0)
                return 42

        def extract(r: object) -> dict[str, object]:  # type: ignore[misc]
            return {"result": r}

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            extract,
            None,
            None,
            True,  # type: ignore[arg-type]
        )

        svc = Svc()
        result = asyncio.run(wrapped(svc))  # type: ignore
        assert result == 42

    def test_instance_async_error_with_timed_and_result_extraction(self) -> None:
        """Async instance: error with timed=True + result extraction adds latency_ms to .error."""

        class Svc(LoggingMixin):
            __slots__ = ()

            async def process(self) -> None:
                await asyncio.sleep(0)
                raise ValueError("test")

        def extract(r: object) -> dict[str, object]:  # type: ignore[misc]
            return {"result": r}

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            extract,
            None,
            None,
            True,  # type: ignore[arg-type]
        )

        svc = Svc()
        with pytest.raises(ValueError):
            asyncio.run(wrapped(svc))  # type: ignore

    def test_instance_async_timed_only_no_result_extraction(self) -> None:
        """Async instance: timed=True with NO result extraction -> .end with latency_ms only."""

        class Svc(LoggingMixin):
            __slots__ = ()

            async def process(self) -> int:
                await asyncio.sleep(0)
                return 42

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(  # type: ignore
            container,
            Svc.process,
            None,
            None,
            None,
            True,  # type: ignore[arg-type]
        )

        svc = Svc()
        result = asyncio.run(wrapped(svc))  # type: ignore
        assert result == 42
