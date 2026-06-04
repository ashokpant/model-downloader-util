"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from __future__ import annotations

from pathlib import Path

from .env import load_env
from .providers.base import ModelProvider
from .providers.gcs import GCSProvider
from .providers.git_lfs import GitLFSProvider
from .providers.http import HttpProvider
from .providers.local import LocalProvider
from .providers.s3 import S3Provider

_PROVIDERS: tuple[ModelProvider, ...] = (
    LocalProvider(),
    HttpProvider(),
    S3Provider(),
    GCSProvider(),
    GitLFSProvider(),
)


def download_model(source: str, *, force_download: bool = False) -> Path:
    load_env()
    for provider in _PROVIDERS:
        if provider.can_handle(source):
            return provider.download(source, force=force_download)
    raise ValueError(f"Unsupported source: {source}")
