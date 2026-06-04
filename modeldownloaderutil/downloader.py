"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from .providers.gcs import GCSProvider
from .providers.git_lfs import GitLFSProvider
from .providers.http import HttpProvider
from .providers.local import LocalProvider
from .providers.s3 import S3Provider

_PROVIDERS = [
    LocalProvider(),
    HttpProvider(),
    S3Provider(),
    GCSProvider(),
    GitLFSProvider(),
]


def get_model(source: str) -> str:
    for provider in _PROVIDERS:
        if provider.can_handle(source):
            return provider.download(source)
    raise ValueError(f"Unsupported source: {source}")
