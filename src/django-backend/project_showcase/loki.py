"""Custom logging handler that pushes logs directly to Loki."""

import atexit
import contextlib
import json
import logging
import queue
import threading
import time
import urllib.request


class LokiHandler(logging.Handler):
    """Logging handler that pushes log entries to a Loki HTTP endpoint.

    Uses a background thread with a queue so log calls never block the
    application.  Records are batched and flushed every ``flush_interval``
    seconds or when the batch reaches ``batch_size`` entries.

    Parameters
    ----------
    url : str
        Full Loki push URL, e.g.
        ``https://<cockpit-push-url>/loki/api/v1/push``.
    auth_token : str
        Token sent in the ``X-Token`` header for authentication.
    labels : dict[str, str]
        Extra static labels attached to every log stream (e.g.
        ``{"service": "backend"}``).
    batch_size : int
        Max entries per batch before an early flush (default 100).
    flush_interval : float
        Seconds between periodic flushes (default 1.0).
    """

    def __init__(  # noqa: ANN204
        self,
        url: str,
        auth_token: str,
        labels: dict[str, str] | None = None,
        batch_size: int = 100,
        flush_interval: float = 1.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.url = url
        self.auth_token = auth_token
        self.static_labels = labels or {}
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        self._queue: queue.Queue[logging.LogRecord | None] = queue.Queue()
        self._shutdown = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        atexit.register(self.close)

    # -- public interface -----------------------------------------------------

    def emit(self, record: logging.LogRecord) -> None:
        if self._shutdown.is_set():
            return
        with contextlib.suppress(queue.Full):
            self._queue.put_nowait(record)

    def close(self) -> None:
        if self._shutdown.is_set():
            return
        self._shutdown.set()
        self._queue.put(None)  # sentinel to wake the thread
        self._thread.join(timeout=5)
        super().close()

    # -- background thread ----------------------------------------------------

    def _run(self) -> None:
        batch: list[logging.LogRecord] = []
        deadline = time.monotonic() + self.flush_interval

        while True:
            timeout = max(0, deadline - time.monotonic())
            try:
                record = self._queue.get(timeout=timeout)
            except queue.Empty:
                record = None

            if record is None and self._shutdown.is_set():
                # Final flush on shutdown
                if batch:
                    self._flush(batch)
                return

            if record is not None:
                batch.append(record)

            now = time.monotonic()
            if len(batch) >= self.batch_size or now >= deadline:
                if batch:
                    self._flush(batch)
                    batch = []
                deadline = now + self.flush_interval

    # -- Loki push ------------------------------------------------------------

    def _flush(self, batch: list[logging.LogRecord]) -> None:
        # Group records by (level, logger) so each combination is its own
        # Loki stream (required for correct label indexing).
        streams: dict[tuple[str, str], list[tuple[str, str]]] = {}
        for record in batch:
            key = (record.levelname.lower(), record.name)
            entry = (str(int(record.created * 1e9)), self.format(record))
            streams.setdefault(key, []).append(entry)

        payload = {
            "streams": [
                {
                    "stream": {
                        **self.static_labels,
                        "level": level,
                        "logger": logger_name,
                    },
                    "values": values,
                }
                for (level, logger_name), values in streams.items()
            ]
        }

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(  # noqa: S310
                self.url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "X-Token": self.auth_token,
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5):  # noqa: S310
                pass
        except Exception:  # noqa: BLE001, S110
            # Never crash the app because of a logging failure.
            pass
