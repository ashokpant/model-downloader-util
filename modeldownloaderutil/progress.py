"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 10/07/2026

Download progress helpers (tqdm + Git LFS GIT_LFS_PROGRESS).
"""
from __future__ import annotations

import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from tqdm import tqdm

_LFS_POINTER_SIZE = re.compile(r"^size\s+(\d+)\s*$", re.MULTILINE)


def progress_enabled() -> bool:
    flag = os.environ.get("MODEL_DOWNLOAD_PROGRESS", "1").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    return not os.environ.get("TQDM_DISABLE")


def status(message: str) -> None:
    if progress_enabled():
        tqdm.write(message)


@contextmanager
def byte_bar(desc: str, total: int | None = None) -> Iterator[tqdm]:
    """Byte progress bar; no-ops visually when progress is disabled."""
    with tqdm(
        total=total if total and total > 0 else None,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc=desc,
        disable=not progress_enabled(),
        leave=True,
    ) as bar:
        yield bar


def lfs_pointer_size(path: Path) -> int | None:
    """Return LFS object size from a pointer file, or None if not a pointer."""
    try:
        if not path.is_file() or path.stat().st_size > 1024:
            return None
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    if "git-lfs.github.com/spec/v1" not in text:
        return None
    match = _LFS_POINTER_SIZE.search(text)
    return int(match.group(1)) if match else None


def parse_lfs_progress_line(line: str) -> tuple[int, int] | None:
    """Parse ``GIT_LFS_PROGRESS`` line → (bytes_so_far, total_bytes)."""
    parts = line.strip().split()
    # <direction> <current>/<total files> <current>/<total bytes> <name...>
    if len(parts) < 4:
        return None
    byte_part = parts[2]
    if "/" not in byte_part:
        return None
    current_s, total_s = byte_part.split("/", 1)
    try:
        current, total = int(current_s), int(total_s)
    except ValueError:
        return None
    return current, total


def update_bar_from_progress_file(progress_path: Path, bar: tqdm, last_bytes: int) -> int:
    """Read new GIT_LFS_PROGRESS lines and advance ``bar``. Returns latest byte count."""
    try:
        text = progress_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return last_bytes
    for line in text.splitlines():
        parsed = parse_lfs_progress_line(line)
        if not parsed:
            continue
        current, total = parsed
        if total and bar.total != total:
            bar.total = total
            bar.refresh()
        if current > last_bytes:
            bar.update(current - last_bytes)
            last_bytes = current
    return last_bytes
