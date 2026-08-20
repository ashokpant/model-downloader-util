"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from __future__ import annotations

from pathlib import Path

from .env import load_env
from .progress import status
from .providers.base import ModelProvider
from .providers.gcs import GCSProvider
from .providers.git import GitProvider
from .providers.git_lfs import GitLFSProvider
from .providers.http import HttpProvider
from .providers.local import LocalProvider
from .providers.s3 import S3Provider
from .rustfs import (
    cache_destination,
    download_from_rustfs,
    is_usable_cached_file,
    rustfs_model_store,
    storage_key,
)

_PROVIDERS: tuple[ModelProvider, ...] = (
    LocalProvider(),
    HttpProvider(),
    S3Provider(),
    GCSProvider(),
    GitLFSProvider(),
    GitProvider(),
)


def download_model(source: str, *, force_download: bool = False) -> Path:
    """Resolve ``source`` to a local file.

    For ``git+`` URLs the lookup is **cache → RustFS → git**. RustFS uses the
    same object key as git (``{owner}/{repo}/{file_path}``) so model paths do
    not change across storage. Other schemes use their provider directly.
    """
    load_env()
    errors: list[str] = []

    for provider in _PROVIDERS:
        if isinstance(provider, LocalProvider) and provider.can_handle(source):
            return provider.download(source, force=force_download)

    dest = cache_destination(source)
    if dest is not None and not force_download and is_usable_cached_file(dest):
        return dest.resolve()

    if dest is not None and storage_key(source) and rustfs_model_store() is not None:
        try:
            path = download_from_rustfs(source, dest, force=force_download)
            if path is not None:
                return path
        except Exception as exc:
            msg = f"RustFS: {exc}"
            errors.append(msg)
            status(f"RustFS failed, trying next source ({exc})")

    if dest is not None and not force_download and is_usable_cached_file(dest):
        return dest.resolve()

    for provider in _PROVIDERS:
        if isinstance(provider, LocalProvider):
            continue
        if provider.can_handle(source):
            try:
                return provider.download(source, force=force_download)
            except Exception as exc:
                errors.append(f"{type(provider).__name__}: {exc}")
                break

    detail = "; ".join(errors) if errors else "no provider handled the source"
    raise RuntimeError(f"Could not download model {source}: {detail}")
