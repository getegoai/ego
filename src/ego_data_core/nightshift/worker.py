"""Single-process Night Shift worker."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import time
from typing import Any

from ego_data_core.kernel.logging import get_logger, log_exception, safe_error_message
from ego_data_core.nightshift.queue import JobRecord, NightShiftQueue


JobHandler = Callable[[JobRecord], Mapping[str, Any] | None]
logger = get_logger(__name__)


class NightShiftWorker:
    def __init__(
        self,
        queue: NightShiftQueue | None = None,
        *,
        poll_interval_seconds: float = 1.0,
    ) -> None:
        self.queue = queue or NightShiftQueue()
        self.poll_interval_seconds = poll_interval_seconds
        self._handlers: dict[str, JobHandler] = {}
        self._stop_requested = False

    @property
    def stop_requested(self) -> bool:
        return self._stop_requested

    def register_handler(self, job_type: str, handler: JobHandler) -> None:
        normalized_type = job_type.strip()
        if not normalized_type:
            raise ValueError("job_type must not be empty")
        self._handlers[normalized_type] = handler

    def request_stop(self) -> None:
        self._stop_requested = True

    def run_once(self) -> bool:
        job = self.queue.claim_next_job()
        if job is None:
            return False

        handler = self._handlers.get(job.job_type)
        if handler is None:
            self.queue.mark_blocked(job.job_id, f"No handler registered for {job.job_type}")
            return True

        try:
            output = handler(job)
        except Exception as exc:
            log_exception(
                logger,
                "Night Shift job failed",
                exc,
                context={
                    "job_id": job.job_id,
                    "job_type": job.job_type,
                    "input": job.input,
                },
            )
            self.queue.mark_failed(job.job_id, safe_error_message(exc))
            return True

        self.queue.mark_succeeded(job.job_id, output or {})
        return True

    def run_forever(self, *, max_iterations: int | None = None) -> int:
        processed_count = 0
        iterations = 0

        while not self._stop_requested:
            if max_iterations is not None and iterations >= max_iterations:
                break
            iterations += 1

            processed = self.run_once()
            if processed:
                processed_count += 1
                continue
            time.sleep(self.poll_interval_seconds)

        return processed_count
