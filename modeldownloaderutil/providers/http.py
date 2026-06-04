"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from __future__ import annotations

from pathlib import Path

from .._download import download_http, download_with_cache
from ..cache import cache_path
from .base import ModelProvider


class HttpProvider(ModelProvider):
    def can_handle(self, source: str) -> bool:
        return source.startswith(("http://", "https://"))

    def download(self, source: str, *, force: bool = False) -> Path:
        destination = cache_path(source)
        return download_with_cache(destination, lambda path: download_http(source, path), force=force)
