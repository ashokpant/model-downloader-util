"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from __future__ import annotations

import zipfile
from collections.abc import Sequence
from pathlib import Path

from .env import load_env
from .lock import exclusive_file_lock
from .progress import status
from .providers.base import ModelProvider
from .providers.gcs import GCSProvider
from .providers.git import GitProvider
from .providers.git_lfs import GitLFSProvider
from .providers.http import HttpProvider
from .providers.local import LocalProvider
from .providers.s3 import S3Provider

DEFAULT_SUFFIXES = (".onnx", ".pt", ".pth", ".tflite", ".safetensors")

_PROVIDERS: tuple[ModelProvider, ...] = (
    LocalProvider(),
    HttpProvider(),
    S3Provider(),
    GCSProvider(),
    GitLFSProvider(),
    GitProvider(),
)


def split_sources(source: str) -> list[str]:
    """Split a comma-separated source list (order = priority)."""
    if not source or not str(source).strip():
        return []
    return [p.strip() for p in str(source).split(",") if p.strip()]


def sources(*uris: str) -> str:
    """Join URIs into a comma-separated priority list for ``download_model``."""
    parts = [u.strip() for u in uris if u and str(u).strip()]
    if not parts:
        raise ValueError("sources() requires at least one URI")
    return ",".join(parts)


def download_model(source: str, *, force_download: bool = False) -> Path:
    """Resolve ``source`` to a local cached file.

    ``source`` is one URI, or several separated by commas (tried in order)::

        download_model("rustfs://bucket/key.onnx,git+https://host/repo.git#key.onnx")

    Supported schemes: local path, http(s), s3, minio, rustfs, gs, git+.
    """
    load_env()
    candidates = split_sources(source)
    if not candidates:
        raise ValueError("empty model source")

    errors: list[str] = []
    for candidate in candidates:
        try:
            return _download_one(candidate, force_download=force_download)
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")
            if len(candidates) > 1:
                status(f"Source failed, trying next ({exc})")

    detail = "; ".join(errors) if errors else "no provider handled the source"
    raise RuntimeError(f"Could not download model: {detail}")


def _download_one(source: str, *, force_download: bool) -> Path:
    for provider in _PROVIDERS:
        if provider.can_handle(source):
            return provider.download(source, force=force_download)
    raise ValueError(f"Unsupported source: {source}")


def extract_archive(path: Path, *, force: bool = False) -> Path:
    """If ``path`` is a zip, extract beside it and return the directory; otherwise return ``path``."""
    path = Path(path)
    if path.suffix.lower() != ".zip":
        return path
    dest = path.with_suffix("")
    lock = Path(str(path) + ".lock")
    with exclusive_file_lock(lock):
        if dest.exists() and not force:
            return dest
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path) as zf:
            zf.extractall(dest)
        return dest


def _normalize_suffixes(suffixes: Sequence[str] | None) -> tuple[str, ...]:
    if suffixes is None:
        return DEFAULT_SUFFIXES
    out: list[str] = []
    for s in suffixes:
        s = s.strip().lower()
        if not s:
            continue
        out.append(s if s.startswith(".") else f".{s}")
    return tuple(out) or DEFAULT_SUFFIXES


def find_file(path: Path, suffixes: Sequence[str] | None = None) -> Path:
    """Return ``path`` if it is a file; otherwise the first matching file under it."""
    path = Path(path)
    if path.is_file():
        return path
    if not path.is_dir():
        raise FileNotFoundError(f"No model file found in {path}")
    wanted = set(_normalize_suffixes(suffixes))
    matches = [f for f in path.rglob("*") if f.is_file() and f.suffix.lower() in wanted]
    if not matches:
        raise FileNotFoundError(f"No model file found in {path}")
    matches.sort(key=lambda p: (len(p.relative_to(path).parts), str(p).lower()))
    return matches[0]


def resolve_model(
    source: str,
    *,
    force_download: bool = False,
    suffixes: Sequence[str] | None = None,
) -> Path:
    """Download ``source``, unpack a zip if needed, and return the model file."""
    path = download_model(source, force_download=force_download)
    path = extract_archive(path, force=force_download)
    return find_file(path, suffixes=suffixes)
