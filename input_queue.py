import time
import threading
from collections import deque

_HAS_MSVCRT = False
try:
    import msvcrt
    _HAS_MSVCRT = True
except ImportError:
    pass


class StreamInputCapture:
    """
    Captures keystrokes via msvcrt (Windows only) while Rich Live is active.
    Background thread polls at 50 Hz. Main thread reads buffer/queue safely.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._buffer: str = ""
        self._queue: deque = deque()
        self._active = False
        self._thread: threading.Thread | None = None

    # ── Public read API ───────────────────────────────────────────────────────

    @property
    def buffer(self) -> str:
        with self._lock:
            return self._buffer

    @property
    def queue_size(self) -> int:
        with self._lock:
            return len(self._queue)

    def drain(self) -> list:
        """Return all completed (Enter-submitted) messages and clear the queue."""
        with self._lock:
            items = list(self._queue)
            self._queue.clear()
            return items

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        if not _HAS_MSVCRT:
            return
        self._active = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._active = False
        if self._thread:
            self._thread.join(timeout=0.3)

    # ── Capture loop (background thread) ──────────────────────────────────────

    def clear_buffer(self):
        """Descarta o conteúdo atual do buffer sem enviar para a fila."""
        with self._lock:
            self._buffer = ""

    def _capture_loop(self):
        while self._active:
            try:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    with self._lock:
                        if ch in ("\r", "\n"):
                            msg = self._buffer.strip()
                            if msg:
                                self._queue.append(msg)
                            self._buffer = ""
                        elif ch == "\x08":              # Backspace
                            self._buffer = self._buffer[:-1]
                        elif ch == "\x03":              # Ctrl+C — leave for main thread
                            pass
                        elif ch in ("\x00", "\xe0"):    # Special key prefix — consume next byte
                            if msvcrt.kbhit():
                                msvcrt.getwch()
                        elif ord(ch) >= 32:             # Printable character
                            self._buffer += ch
                else:
                    time.sleep(0.02)
            except Exception:
                time.sleep(0.05)


_global_capture: "StreamInputCapture | None" = None


def get_global_capture() -> "StreamInputCapture | None":
    """Retorna o singleton de captura de teclas, criando se necessário."""
    global _global_capture
    if not _HAS_MSVCRT:
        return None
    if _global_capture is None:
        _global_capture = StreamInputCapture()
    return _global_capture
