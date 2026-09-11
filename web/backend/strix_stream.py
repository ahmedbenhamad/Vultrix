"""Runs the Strix CLI so that the web console sees the same content as
interactive mode over a plain pipe.

Strix's interactive TUI uses ``rich.live.Live`` to redraw a status panel (agent
count, iterations, tokens, cost, severity breakdown) via cursor-move ANSI. Those
redraws are invisible when stdout is captured to a pipe — that's why the web
console previously stalled after the startup banner.

We monkey-patch ``rich.live.Live`` so that instead of cursor-based redraws it
just ``console.print()``s each new renderable once (throttled). Strix's own
update thread already refreshes every ~2s, so we get the same content — banner,
live-stats panel, per-vulnerability panels, final summary — as a stream of
plain prints that the backend can capture and forward to the frontend.
"""

import os
import sys
import time

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["PYTHONUNBUFFERED"] = "1"
try:
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
except AttributeError:
    pass

# ── Patch Rich Live ─────────────────────────────────────────────────────────
import rich.console
import rich.live

_MIN_PRINT_INTERVAL = 2.0  # seconds between live-panel prints (matches Strix's own update tick)

_orig_init = rich.live.Live.__init__


def _patched_init(self, renderable=None, *args, **kwargs):
    _orig_init(self, renderable, *args, **kwargs)
    self._patched_last_print = 0.0
    self._patched_current = renderable


def _print_now(self):
    r = getattr(self, "_patched_current", None) or getattr(self, "renderable", None)
    if r is None:
        return
    console = self.console or rich.console.Console()
    try:
        console.print(r)
    except Exception:  # noqa: BLE001
        pass


def _patched_enter(self):
    # Show the initial panel immediately so the user sees it right away.
    _print_now(self)
    self._patched_last_print = time.time()
    return self


def _patched_exit(self, *args, **kwargs):
    # Print the final state once so the last stats frame is preserved.
    _print_now(self)
    return False


def _patched_update(self, renderable=None, *args, **kwargs):
    if renderable is not None:
        self._patched_current = renderable
    now = time.time()
    if now - getattr(self, "_patched_last_print", 0.0) >= _MIN_PRINT_INTERVAL:
        self._patched_last_print = now
        _print_now(self)


def _noop(*args, **kwargs):
    return None


rich.live.Live.__init__ = _patched_init
rich.live.Live.__enter__ = _patched_enter
rich.live.Live.__exit__ = _patched_exit
rich.live.Live.update = _patched_update
rich.live.Live.refresh = _noop
rich.live.Live.start = _noop
rich.live.Live.stop = _noop

# ── Hand off to Strix ────────────────────────────────────────────────────────
sys.argv[0] = "strix"
from strix.interface.main import main  # noqa: E402

sys.exit(main() or 0)
