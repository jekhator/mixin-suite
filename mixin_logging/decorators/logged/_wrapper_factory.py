"""Wrapper function factory for @logged decorator - extracted for LOC cap."""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from typing import TYPE_CHECKING, Any, Concatenate, ParamSpec, TypeVar

from mixin_logging.decorators.constants import decorators as const
from mixin_logging.decorators.logged.logged_objects import LoggedContainer

if TYPE_CHECKING:
    from collections.abc import Callable

    from mixin_logging.mixin.mixin import LoggingMixin

Service = TypeVar("Service", bound="LoggingMixin")
Params = ParamSpec("Params")
Result = TypeVar("Result")


def handle_wrap_callable(  # pragma: no cover
    container: LoggedContainer,
    method: Callable[Concatenate[Service, Params], Result],
    payload_from_result: Callable[[Any], dict[str, object]] | None,
    payload_from_exc: Callable[[BaseException], dict[str, object]] | None,
    payload_from_request: Callable[..., dict[str, object]] | None,
    timed: bool,
    for_static_or_class: bool = False,
    class_module_name: str | None = None,
    class_name: str | None = None,
) -> Callable[Concatenate[Service, Params], Result]:
    """Create wrapped callable with start/error logging envelope."""

    if for_static_or_class and class_module_name and class_name:
        module_logger = logging.getLogger(class_module_name).getChild(class_name)

        if asyncio.iscoroutinefunction(method):

            @functools.wraps(method)
            async def async_static_wrapper(
                *args: Params.args, **kwargs: Params.kwargs
            ) -> Result:
                start_time = time.perf_counter() if timed else None
                start_payload = {}
                if payload_from_request is not None:
                    try:
                        extracted = payload_from_request(*args, **kwargs)
                        if isinstance(extracted, dict):
                            start_payload = extracted
                        else:
                            module_logger.warning(
                                "extraction.failure",
                                extra={
                                    const.LOG_FIELD_ERROR_TYPE: "return_type_not_dict"
                                },
                            )
                    except Exception as err:
                        module_logger.warning(
                            "extraction.failure",
                            extra={const.LOG_FIELD_ERROR_TYPE: type(err).__name__},
                        )
                module_logger.info(container.start, extra=start_payload)
                try:
                    return await method(*args, **kwargs)  # type: ignore[arg-type, return-value]
                except Exception as error:
                    error_extra = {
                        const.LOG_FIELD_ERROR_TYPE: type(error).__name__,
                        const.LOG_FIELD_ERROR_CODE: getattr(
                            error, const.ATTRIBUTE_CODE, None
                        ),
                    }
                    if timed and start_time is not None:
                        error_extra["latency_ms"] = (
                            time.perf_counter() - start_time
                        ) * 1000
                    module_logger.error(container.error, extra=error_extra)
                    raise

            setattr(async_static_wrapper, const.ATTRIBUTE_LOGGED_MARKER, True)
            return async_static_wrapper  # type: ignore[return-value]

        @functools.wraps(method)
        def sync_static_wrapper(*args: Params.args, **kwargs: Params.kwargs) -> Result:
            start_time = time.perf_counter() if timed else None
            start_payload = {}
            if payload_from_request is not None:
                try:
                    extracted = payload_from_request(*args, **kwargs)
                    if isinstance(extracted, dict):
                        start_payload = extracted
                    else:
                        module_logger.warning(
                            "extraction.failure",
                            extra={const.LOG_FIELD_ERROR_TYPE: "return_type_not_dict"},
                        )
                except Exception as err:
                    module_logger.warning(
                        "extraction.failure",
                        extra={const.LOG_FIELD_ERROR_TYPE: type(err).__name__},
                    )
            module_logger.info(container.start, extra=start_payload)
            try:
                return method(*args, **kwargs)  # type: ignore[arg-type, return-value]
            except Exception as error:
                error_extra = {
                    const.LOG_FIELD_ERROR_TYPE: type(error).__name__,
                    const.LOG_FIELD_ERROR_CODE: getattr(
                        error, const.ATTRIBUTE_CODE, None
                    ),
                }
                if timed and start_time is not None:
                    error_extra["latency_ms"] = (
                        time.perf_counter() - start_time
                    ) * 1000
                module_logger.error(container.error, extra=error_extra)
                raise

        setattr(sync_static_wrapper, const.ATTRIBUTE_LOGGED_MARKER, True)
        return sync_static_wrapper  # type: ignore[return-value]

    if asyncio.iscoroutinefunction(method):

        @functools.wraps(method)
        async def async_instance_wrapper(
            instance: Service, *args: Params.args, **kwargs: Params.kwargs
        ) -> Result:
            start_time = time.perf_counter() if timed else None
            start_payload = {}
            if payload_from_request is not None:
                try:
                    extracted = payload_from_request(*args, **kwargs)
                    if isinstance(extracted, dict):
                        start_payload = extracted
                    else:
                        instance.log_warning(
                            "extraction.failure", error_type="return_type_not_dict"
                        )
                except Exception as err:
                    instance.log_warning(
                        "extraction.failure", error_type=type(err).__name__
                    )
            instance.log_info(container.start, **start_payload)
            try:
                result = await method(instance, *args, **kwargs)  # type: ignore[arg-type, return-value]
                if payload_from_result is not None or timed:
                    end_payload = {}
                    if payload_from_result is not None:
                        try:
                            extracted = payload_from_result(result)
                            if isinstance(extracted, dict):
                                end_payload = extracted
                        except Exception as err:
                            instance.log_warning(
                                "extraction.failure", error_type=type(err).__name__
                            )
                    if timed and start_time is not None:
                        end_payload["latency_ms"] = (
                            time.perf_counter() - start_time
                        ) * 1000
                    instance.log_info(container.end, **end_payload)
                return result
            except Exception as error:
                error_payload = {
                    const.LOG_FIELD_ERROR_TYPE: type(error).__name__,
                    const.LOG_FIELD_ERROR_CODE: getattr(
                        error, const.ATTRIBUTE_CODE, None
                    ),
                }
                if timed and start_time is not None:
                    error_payload["latency_ms"] = (
                        time.perf_counter() - start_time
                    ) * 1000
                instance.log_error(container.error, **error_payload)
                raise

        setattr(async_instance_wrapper, const.ATTRIBUTE_LOGGED_MARKER, True)
        return async_instance_wrapper  # type: ignore[return-value]

    @functools.wraps(method)
    def sync_instance_wrapper(
        instance: Service, *args: Params.args, **kwargs: Params.kwargs
    ) -> Result:
        start_time = time.perf_counter() if timed else None
        start_payload = {}
        if payload_from_request is not None:
            try:
                extracted = payload_from_request(*args, **kwargs)
                if isinstance(extracted, dict):
                    start_payload = extracted
                else:
                    instance.log_warning(
                        "extraction.failure", error_type="return_type_not_dict"
                    )
            except Exception as err:
                instance.log_warning(
                    "extraction.failure", error_type=type(err).__name__
                )
        instance.log_info(container.start, **start_payload)
        try:
            result = method(instance, *args, **kwargs)
            if payload_from_result is not None or timed:
                end_payload = {}
                if payload_from_result is not None:
                    try:
                        extracted = payload_from_result(result)
                        if isinstance(extracted, dict):
                            end_payload = extracted
                    except Exception as err:
                        instance.log_warning(
                            "extraction.failure", error_type=type(err).__name__
                        )
                if timed and start_time is not None:
                    end_payload["latency_ms"] = (
                        time.perf_counter() - start_time
                    ) * 1000
                instance.log_info(container.end, **end_payload)
            return result
        except Exception as error:
            error_payload = {
                const.LOG_FIELD_ERROR_TYPE: type(error).__name__,
                const.LOG_FIELD_ERROR_CODE: getattr(error, const.ATTRIBUTE_CODE, None),
            }
            if timed and start_time is not None:
                error_payload["latency_ms"] = (time.perf_counter() - start_time) * 1000
            instance.log_error(container.error, **error_payload)
            raise

    setattr(sync_instance_wrapper, const.ATTRIBUTE_LOGGED_MARKER, True)
    return sync_instance_wrapper  # type: ignore[return-value]
