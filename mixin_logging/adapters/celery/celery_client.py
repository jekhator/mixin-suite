"""CorrelationSignals: stateless signal-hook surface for celery task boundary correlation-ID propagation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from celery.signals import before_task_publish, task_postrun, task_prerun

from mixin_logging import clear_correlation_id, set_correlation_id
from mixin_logging.adapters.celery import celery_objects as objs
from mixin_logging.adapters.constants import celery as const


@dataclass(frozen=True, slots=True)
class CorrelationSignals:
    """Stateless surface wiring correlation-ID propagation across the celery producer/worker boundary via signals."""

    @classmethod
    def connect(cls) -> None:
        """Register the publish/prerun/postrun handlers on the celery signals (weak=False to survive GC)."""
        before_task_publish.connect(cls.inject_on_publish, weak=False)
        task_prerun.connect(cls.restore_on_prerun, weak=False)
        task_postrun.connect(cls.clear_on_postrun, weak=False)

    @classmethod
    def inject_on_publish(cls, headers: Any = None, **kwargs: Any) -> None:
        """Write the current correlation_id into the outgoing task message headers (producer side)."""
        correlation = objs.CeleryCorrelation.from_context()
        if correlation is None or headers is None:
            return
        name, value = correlation.header_pair
        headers[name] = value

    @classmethod
    def restore_on_prerun(cls, task: Any = None, **kwargs: Any) -> None:
        """Restore the correlation_id from the task message headers into context (worker side)."""
        if task is None:
            return
        headers = getattr(task.request, "headers", None) or {}
        raw_value = headers.get(const.CORRELATION_ID_HEADER)
        if raw_value is not None and objs.CeleryCorrelation._is_safe(raw_value):
            set_correlation_id(raw_value)

    @classmethod
    def clear_on_postrun(cls, **kwargs: Any) -> None:
        """Clear the correlation context after the task completes (worker side)."""
        clear_correlation_id()
