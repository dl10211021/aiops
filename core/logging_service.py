from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from core.request_context import current_request_id


LOG_FORMAT = "%(asctime)s [%(levelname)s] [request_id=%(request_id)s] %(message)s"


def build_request_id_log_record_factory(
    previous_factory: Callable[..., logging.LogRecord],
    request_id_getter: Callable[[], str | None] = current_request_id,
) -> Callable[..., logging.LogRecord]:
    def _record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = previous_factory(*args, **kwargs)
        record.request_id = request_id_getter() or "-"
        return record

    return _record_factory


def configure_logging(level: int) -> None:
    previous_factory = logging.getLogRecordFactory()
    logging.setLogRecordFactory(build_request_id_log_record_factory(previous_factory))
    logging.basicConfig(level=level, format=LOG_FORMAT)
