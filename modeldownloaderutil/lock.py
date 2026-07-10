"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 10/07/2026

Cross-process exclusive file locks for shared cache mutations (e.g. git repos).
"""
from __future__ import annotations

import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


@contextmanager
def exclusive_file_lock(
    lock_path: Path,
    *,
    timeout: float = 600.0,
    poll: float = 0.05,
) -> Iterator[None]:
    """Block until an exclusive lock on ``lock_path`` is held, then release on exit."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lock_path, "a+b")
    try:
        _acquire(fh, timeout=timeout, poll=poll, lock_path=lock_path)
        yield
    finally:
        try:
            _release(fh)
        finally:
            fh.close()


def _acquire(fh, *, timeout: float, poll: float, lock_path: Path) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            if sys.platform == "win32":
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except OSError:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for lock: {lock_path}") from None
            time.sleep(poll)


def _release(fh) -> None:
    if sys.platform == "win32":
        try:
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
    else:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
