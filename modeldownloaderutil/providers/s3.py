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

from .._download import download_s3_object, download_with_cache
from ..cache import cache_path, normalize_s3_uri
from .base import ModelProvider


class S3Provider(ModelProvider):
    def can_handle(self, source: str) -> bool:
        return source.startswith(("s3://", "minio://", "rustfs://"))

    def download(self, source: str, *, force: bool = False) -> Path:
        normalized, endpoint = normalize_s3_uri(source)
        destination = cache_path(normalized)
        parsed = urlparse(normalized)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        if not bucket or not key:
            raise ValueError(f"Invalid S3 URI: {source}")
        client = boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=os.environ.get("MODEL_ACCESS_KEY"), aws_secret_access_key=os.environ.get("MODEL_SECRET_KEY"))
        return download_with_cache(destination, lambda path: download_s3_object(client, bucket, key, path), force=force)
