"""In-process pub/sub bus bridging the (sync, threaded) scan runner to (async)
WebSocket subscribers.

The runner publishes events from a worker thread; subscribers are asyncio queues
owned by the event loop. ``publish`` is therefore thread-safe: it hops onto the
loop via ``call_soon_threadsafe``. When the runner is later moved to a separate
RQ worker process, swap this module's transport for Redis pub/sub — the
``publish`` / ``subscribe`` interface stays the same.
"""

import asyncio
import contextlib
from typing import Any

_loop: asyncio.AbstractEventLoop | None = None
_subscribers: dict[int, set[asyncio.Queue]] = {}


def set_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def subscribe(assessment_id: int) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    _subscribers.setdefault(assessment_id, set()).add(q)
    return q


def unsubscribe(assessment_id: int, q: asyncio.Queue) -> None:
    subs = _subscribers.get(assessment_id)
    if subs:
        subs.discard(q)
        if not subs:
            _subscribers.pop(assessment_id, None)


def publish(assessment_id: int, event: dict[str, Any]) -> None:
    """Deliver an event to all subscribers. Safe to call from any thread."""
    if _loop is None:
        return
    subs = _subscribers.get(assessment_id)
    if not subs:
        return

    def _deliver() -> None:
        for q in list(subs):
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait(event)

    with contextlib.suppress(RuntimeError):  # loop closed / shutting down
        _loop.call_soon_threadsafe(_deliver)
