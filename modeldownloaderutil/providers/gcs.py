"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from urllib.parse import urlparse

from google.cloud import storage

from .base import ModelProvider
from ..cache import cache_path


class GCSProvider(ModelProvider):

    def can_handle(
        self,
        source: str,
    ) -> bool:
        return source.startswith("gs://")

    def download(
        self,
        source: str,
    ) -> str:

        dst = cache_path(source)

        if dst.exists():
            return str(dst)

        parsed = urlparse(source)

        bucket = parsed.netloc
        blob = parsed.path.lstrip("/")

        client = storage.Client()

        client.bucket(bucket) \
            .blob(blob) \
            .download_to_filename(
                str(dst)
            )

        return str(dst)
