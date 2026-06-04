"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.config import Config

from .._download import download_s3_object, download_with_cache
from ..cache import cache_path, normalize_s3_uri
from .base import ModelProvider

_S3_CONFIG = Config(signature_version="s3v4", s3={"addressing_style": "path"})
_SCHEME_ENV = {"minio://": "MINIO_ENDPOINT", "rustfs://": "RUSTFS_ENDPOINT"}


class S3Provider(ModelProvider):
    def can_handle(self, source: str) -> bool:
        return source.startswith(("s3://", "minio://", "rustfs://"))

    def download(self, source: str, *, force: bool = False) -> Path:
        scheme = source.split("://", 1)[0] + "://"
        normalized, endpoint = normalize_s3_uri(source)
        if scheme in _SCHEME_ENV and not endpoint:
            env_name = _SCHEME_ENV[scheme]
            raise ValueError(f"{env_name} is not set (check .env)")
        if not os.environ.get("MODEL_ACCESS_KEY") or not os.environ.get("MODEL_SECRET_KEY"):
            raise ValueError("MODEL_ACCESS_KEY and MODEL_SECRET_KEY are not set (check .env)")

        destination = cache_path(normalized)
        parsed = urlparse(normalized)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        if not bucket or not key:
            raise ValueError(f"Invalid S3 URI: {source}")

        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=os.environ.get("MODEL_ACCESS_KEY"),
            aws_secret_access_key=os.environ.get("MODEL_SECRET_KEY"),
            config=_S3_CONFIG,
        )
        return download_with_cache(destination, lambda path: download_s3_object(client, bucket, key, path), force=force)
