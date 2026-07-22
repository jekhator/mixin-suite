"""@logged: start/error logging envelope for LoggingMixin service methods."""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Concatenate, ParamSpec, TypeVar

from mixin_logging.decorators.constants import decorators as const
from mixin_logging.decorators.logged import logged_objects as objs
from mixin_logging.mixin.mixin import LoggingMixin

if TYPE_CHECKING:
    from collections.abc import Callable

Service = TypeVar("Service", bound=LoggingMixin)
Params = ParamSpec("Params")
Result = TypeVar("Result")


@dataclass(frozen=True, slots=True)
class LoggedClient:
    """Emit <event>.start / <event>.end / <event>.error on LoggingMixin methods."""

    container: objs.LoggedContainer
    payload_from_result: Callable[[Any], dict[str, object]] | None = None
    payload_from_exc: Callable[[BaseException], dict[str, object]] | None = None
    payload_from_request: Callable[..., dict[str, object]] | None = None
    timed: bool = False

    @classmethod
    def for_event(
        cls,
        event: str,
        payload_from_result: Callable[[Any], dict[str, object]] | None = None,
        payload_from_exc: Callable[[BaseException], dict[str, object]] | None = None,
        payload_from_request: Callable[..., dict[str, object]] | None = None,
        timed: bool = False,
    ) -> LoggedClient:
        """Create a LoggedClient from a base event name and optional callbacks."""
        return cls(
            objs.LoggedContainer(event),
            payload_from_result=payload_from_result,
            payload_from_exc=payload_from_exc,
            payload_from_request=payload_from_request,
            timed=timed,
        )

    def __call__(self, target: Any) -> Any:
        """Wrap a callable or fan out to all public methods of a class."""
        if inspect.isclass(target):
            return self._decorate_class(target)

        if callable(target):
            return self._wrap_callable(target)  # type: ignore[arg-type]

        msg = const.ERROR_MSG_TARGET_NOT_CLASS_OR_CALLABLE
        raise TypeError(msg)

    def _wrap_callable(  # type: ignore[misc]
        self,
        method: Callable[Concatenate[Service, Params], Result],
        for_static_or_class: bool = False,
        class_module_name: str | None = None,
        class_name: str | None = None,
    ) -> Callable[Concatenate[Service, Params], Result]:
        """Wrap a single callable with start/error logging envelope.

        Args:
            method: The callable to wrap.
            for_static_or_class: If True, use module-level logger fallback.
            class_module_name: Module of the decorated class (for fallback logger).
            class_name: Name of the decorated class (for fallback logger).
        """

        if for_static_or_class:
            if class_module_name and class_name:
                module_logger = logging.getLogger(class_module_name).getChild(
                    class_name,
                )

                if asyncio.iscoroutinefunction(method):

                    @functools.wraps(method)
                    async def async_static_or_class_wrapper(
                        *args: Params.args, **kwargs: Params.kwargs
                    ) -> Result:
                        start_time = time.perf_counter() if self.timed else None
                        start_payload = {}
                        if self.payload_from_request is not None:
                            try:
                                extracted = self.payload_from_request(*args, **kwargs)
                                if isinstance(extracted, dict):
                                    start_payload = extracted
                                else:
                                    module_logger.warning(
                                        "extraction.failure",
                                        extra={const.LOG_FIELD_ERROR_TYPE: "return_type_not_dict"},
                                    )
                            except Exception as error_in_extraction:
                                module_logger.warning(
                                    "extraction.failure",
                                    extra={const.LOG_FIELD_ERROR_TYPE: type(error_in_extraction).__name__},
                                )
                        module_logger.info(self.container.start, extra=start_payload)
                        try:
                            return await method(*args, **kwargs)  # type: ignore[arg-type, return-value]
                        except Exception as error:
                            error_extra = {
                                const.LOG_FIELD_ERROR_TYPE: type(
                                    error,
                                ).__name__,
                                const.LOG_FIELD_ERROR_CODE: getattr(
                                    error,
                                    const.ATTRIBUTE_CODE,
                                    None,
                                ),
                            }
                            if self.timed and start_time is not None:
                                latency_ms = (time.perf_counter() - start_time) * 1000
                                error_extra["latency_ms"] = latency_ms
                            module_logger.error(
                                self.container.error,
                                extra=error_extra,
                            )
                            raise

                    setattr(
                        async_static_or_class_wrapper,
                        const.ATTRIBUTE_LOGGED_MARKER,
                        True,
                    )
                    return async_static_or_class_wrapper  # type: ignore[return-value]

                @functools.wraps(method)
                def static_or_class_wrapper(
                    *args: Params.args, **kwargs: Params.kwargs
                ) -> Result:
                    start_time = time.perf_counter() if self.timed else None
                    start_payload = {}
                    if self.payload_from_request is not None:
                        try:
                            extracted = self.payload_from_request(*args, **kwargs)
                            if isinstance(extracted, dict):
                                start_payload = extracted
                            else:
                                module_logger.warning(
                                    "extraction.failure",
                                    extra={const.LOG_FIELD_ERROR_TYPE: "return_type_not_dict"},
                                )
                        except Exception as error_in_extraction:
                            module_logger.warning(
                                "extraction.failure",
                                extra={const.LOG_FIELD_ERROR_TYPE: type(error_in_extraction).__name__},
                            )
                    module_logger.info(self.container.start, extra=start_payload)
                    try:
                        return method(*args, **kwargs)  # type: ignore[arg-type, return-value]
                    except Exception as error:
                        error_extra = {
                            const.LOG_FIELD_ERROR_TYPE: type(error).__name__,
                            const.LOG_FIELD_ERROR_CODE: getattr(
                                error,
                                const.ATTRIBUTE_CODE,
                                None,
                            ),
                        }
                        if self.timed and start_time is not None:
                            latency_ms = (time.perf_counter() - start_time) * 1000
                            error_extra["latency_ms"] = latency_ms
                        module_logger.error(
                            self.container.error,
                            extra=error_extra,
                        )
                        raise

                setattr(static_or_class_wrapper, const.ATTRIBUTE_LOGGED_MARKER, True)
                return static_or_class_wrapper  # type: ignore[return-value]

            @functools.wraps(method)  # pragma: no cover
            def static_or_class_wrapper_no_logging(  # pragma: no cover
                *args: Params.args, **kwargs: Params.kwargs
            ) -> Result:  # pragma: no cover
                return method(*args, **kwargs)  # type: ignore[arg-type, return-value] # pragma: no cover

            setattr(  # pragma: no cover
                static_or_class_wrapper_no_logging,
                const.ATTRIBUTE_LOGGED_MARKER,
                True,
            )
            return static_or_class_wrapper_no_logging  # type: ignore[return-value] # pragma: no cover

        if asyncio.iscoroutinefunction(method):

            @functools.wraps(method)
            async def async_wrapper(
                instance: Service,
                *args: Params.args,
                **kwargs: Params.kwargs,
            ) -> Result:
                start_time = time.perf_counter() if self.timed else None
                start_payload = {}
                if self.payload_from_request is not None:
                    try:
                        extracted = self.payload_from_request(*args, **kwargs)
                        if isinstance(extracted, dict):
                            start_payload = extracted
                        else:
                            instance.log_warning(
                                "extraction.failure",
                                error="return_type_not_dict",
                            )
                    except Exception as error_in_extraction:
                        instance.log_warning(
                            "extraction.failure",
                            error=type(error_in_extraction).__name__,
                        )
                instance.log_info(self.container.start, **start_payload)
                try:
                    result = await method(instance, *args, **kwargs)  # type: ignore[arg-type, return-value]
                    if self.payload_from_result is not None or self.timed:
                        end_payload = {}
                        if self.payload_from_result is not None:
                            end_payload = self.payload_from_result(result)
                        if self.timed and start_time is not None:
                            latency_ms = (time.perf_counter() - start_time) * 1000
                            end_payload["latency_ms"] = latency_ms
                        instance.log_info(self.container.end, **end_payload)
                    return result
                except Exception as error:
                    error_payload = {
                        const.LOG_FIELD_ERROR_TYPE: type(error).__name__,
                        const.LOG_FIELD_ERROR_CODE: getattr(
                            error,
                            const.ATTRIBUTE_CODE,
                            None,
                        ),
                    }
                    if self.timed and start_time is not None:
                        latency_ms = (time.perf_counter() - start_time) * 1000
                        error_payload["latency_ms"] = latency_ms
                    instance.log_error(
                        self.container.error,
                        **error_payload,
                    )
                    raise

            setattr(async_wrapper, const.ATTRIBUTE_LOGGED_MARKER, True)
            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(method)
        def wrapper(
            instance: Service,
            *args: Params.args,
            **kwargs: Params.kwargs,
        ) -> Result:
            start_time = time.perf_counter() if self.timed else None
            start_payload = {}
            if self.payload_from_request is not None:
                try:
                    extracted = self.payload_from_request(*args, **kwargs)
                    if isinstance(extracted, dict):
                        start_payload = extracted
                    else:
                        instance.log_warning(
                            "extraction.failure",
                            error="return_type_not_dict",
                        )
                except Exception as error_in_extraction:
                    instance.log_warning(
                        "extraction.failure",
                        error=type(error_in_extraction).__name__,
                    )
            instance.log_info(self.container.start, **start_payload)
            try:
                result = method(instance, *args, **kwargs)
                if self.payload_from_result is not None or self.timed:
                    end_payload = {}
                    if self.payload_from_result is not None:
                        end_payload = self.payload_from_result(result)
                    if self.timed and start_time is not None:
                        latency_ms = (time.perf_counter() - start_time) * 1000
                        end_payload["latency_ms"] = latency_ms
                    instance.log_info(self.container.end, **end_payload)
                return result
            except Exception as error:
                error_payload = {
                    const.LOG_FIELD_ERROR_TYPE: type(error).__name__,
                    const.LOG_FIELD_ERROR_CODE: getattr(
                        error,
                        const.ATTRIBUTE_CODE,
                        None,
                    ),
                }
                if self.timed and start_time is not None:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    error_payload["latency_ms"] = latency_ms
                instance.log_error(
                    self.container.error,
                    **error_payload,
                )
                raise

        setattr(wrapper, const.ATTRIBUTE_LOGGED_MARKER, True)
        return wrapper

    def _decorate_class(self, cls: type) -> type:
        """Fan out decorator to all public methods of a class."""
        for name, value in cls.__dict__.items():
            if self._should_skip_member(name, value):
                continue

            if hasattr(value, const.ATTRIBUTE_LOGGED_MARKER):
                continue

            if isinstance(value, classmethod):
                method_event = f"{self.container.event}{const.EVENT_SEPARATOR}{name}"
                method_client = LoggedClient.for_event(
                    method_event,
                    payload_from_result=self.payload_from_result,
                    payload_from_exc=self.payload_from_exc,
                    payload_from_request=self.payload_from_request,
                    timed=self.timed,
                )
                wrapped = method_client._wrap_callable(  # type: ignore[arg-type, type-var]
                    value.__func__,
                    for_static_or_class=True,
                    class_module_name=cls.__module__,
                    class_name=cls.__name__,
                )
                setattr(cls, name, classmethod(wrapped))
            elif isinstance(value, staticmethod):
                method_event = f"{self.container.event}{const.EVENT_SEPARATOR}{name}"
                method_client = LoggedClient.for_event(
                    method_event,
                    payload_from_result=self.payload_from_result,
                    payload_from_exc=self.payload_from_exc,
                    payload_from_request=self.payload_from_request,
                    timed=self.timed,
                )
                wrapped = method_client._wrap_callable(  # type: ignore[arg-type, type-var]
                    value.__func__,
                    for_static_or_class=True,
                    class_module_name=cls.__module__,
                    class_name=cls.__name__,
                )
                setattr(cls, name, staticmethod(wrapped))
            elif callable(value):
                method_event = f"{self.container.event}{const.EVENT_SEPARATOR}{name}"
                method_client = LoggedClient.for_event(
                    method_event,
                    payload_from_result=self.payload_from_result,
                    payload_from_exc=self.payload_from_exc,
                    payload_from_request=self.payload_from_request,
                    timed=self.timed,
                )
                wrapped = method_client._wrap_callable(value)
                setattr(cls, name, wrapped)

        return cls

    @staticmethod
    def _should_skip_member(name: str, value: object) -> bool:
        """Check if a class member should be skipped from decoration."""
        if name.startswith("_"):
            return True

        if isinstance(value, property):
            return True

        if inspect.isclass(value):
            return True

        return False


logged = LoggedClient.for_event
"""Factory function to create @logged decorators from event names."""
