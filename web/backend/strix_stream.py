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
    except Exception as exc:  # noqa: BLE001
        print(
            f"[strix_stream] Rich render failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )


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
#
# When PYTHONPATH contains an explicit Strix package (as in the streaming
# regression test), load that exact entry-point file.  This avoids Windows
# import-order/package-cache issues where another local Strix installation can
# otherwise be selected.
import importlib.util

def _find_strix_entrypoint():
    raw = os.environ.get("PYTHONPATH", "")
    for entry in raw.split(os.pathsep):
        if not entry:
            continue
        try:
            root = os.path.abspath(entry)
            main_py = os.path.join(root, "strix", "interface", "main.py")
            if os.path.isfile(main_py):
                return root, main_py
        except (OSError, TypeError):
            continue
    return None, None


def _load_entrypoint():
    root, main_py = _find_strix_entrypoint()

    if main_py is not None:
        # Make the selected package root authoritative for imports performed by
        # the entry point itself.
        sys.path[:] = [
            p for p in sys.path
            if os.path.abspath(p or os.curdir) != root
        ]
        sys.path.insert(0, root)

        # Remove any already-loaded Strix modules.
        for name in list(sys.modules):
            if name == "strix" or name.startswith("strix."):
                del sys.modules[name]

        # Load the exact file selected from PYTHONPATH.  This is deterministic
        # on Windows and works with the temporary stub used by pytest.
        spec = importlib.util.spec_from_file_location(
            "strix.interface.main",
            main_py,
            submodule_search_locations=None,
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load Strix entry point: {main_py}")

        module = importlib.util.module_from_spec(spec)
        sys.modules["strix.interface.main"] = module
        spec.loader.exec_module(module)

        entrypoint = getattr(module, "main", None)
        if entrypoint is None:
            raise AttributeError(f"No main() function found in {main_py}")
        return entrypoint

    # Normal production path: use the installed/local Strix package.
    try:
        from strix.interface.main import main  # noqa: E402
        return main
    except Exception as exc:
        print(
            f"[strix_stream] Failed to import strix.interface.main: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise


sys.argv[0] = "strix"
main = _load_entrypoint()

try:
    result = main()
except Exception as exc:
    print(
        f"[strix_stream] Strix main() failed: "
        f"{type(exc).__name__}: {exc}",
        file=sys.stderr,
        flush=True,
    )
    raise

sys.exit(result or 0)