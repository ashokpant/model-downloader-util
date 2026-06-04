"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from google.cloud import storage

from .._download import download_with_cache
from ..cache import cache_path, commit_download, incomplete_path
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

        def fetch(path: Path) -> Path:
            tmp = incomplete_path(path)
            tmp.parent.mkdir(parents=True, exist_ok=True)
            storage.Client().bucket(bucket).blob(blob_name).download_to_filename(str(tmp))
            return commit_download(tmp, path)

        return download_with_cache(destination, fetch, force=force)
