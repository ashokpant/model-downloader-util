"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
import requests

from .base import ModelProvider
from ..cache import cache_path


class HttpProvider(ModelProvider):

    def can_handle(
        self,
        source: str,
    ) -> bool:
        return source.startswith(
            ("http://", "https://")
        )

    def download(
        self,
        source: str,
    ) -> str:

        dst = cache_path(source)

        if dst.exists():
            return str(dst)

        with requests.get(
            source,
            stream=True,
            timeout=300,
        ) as r:
            r.raise_for_status()

            with open(dst, "wb") as f:
                for chunk in r.iter_content(
                    1024 * 1024
                ):
                    if chunk:
                        f.write(chunk)

        return str(dst)
