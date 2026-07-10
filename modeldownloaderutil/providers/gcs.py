"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from .._download import download_gcs_object, download_with_cache
from ..cache import cache_path
from .base import ModelProvider


class GCSProvider(ModelProvider):
    def can_handle(self, source: str) -> bool:
        return source.startswith("gs://")

    def download(self, source: str, *, force: bool = False) -> Path:
        destination = cache_path(source)
        parsed = urlparse(source)
        bucket = parsed.netloc
        blob_name = parsed.path.lstrip("/")
        if not bucket or not blob_name:
            raise ValueError(f"Invalid GCS URI: {source}")

        return download_with_cache(
            destination,
            lambda path: download_gcs_object(bucket, blob_name, path),
            force=force,
        )
