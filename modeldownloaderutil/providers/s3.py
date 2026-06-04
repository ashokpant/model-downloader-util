"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
import os
from urllib.parse import urlparse

import boto3

from .base import ModelProvider
from ..cache import cache_path


class S3Provider(ModelProvider):

    def can_handle(
            self,
            source: str,
    ) -> bool:
        return source.startswith(
            (
                "s3://",
                "minio://",
                "rustfs://",
            )
        )

    def download(
            self,
            source: str,
    ) -> str:

        endpoint = None

        if source.startswith("minio://"):
            endpoint = os.getenv(
                "MINIO_ENDPOINT"
            )
            source = source.replace(
                "minio://",
                "s3://",
                1,
            )

        elif source.startswith(
                "rustfs://"
        ):
            endpoint = os.getenv(
                "RUSTFS_ENDPOINT"
            )
            source = source.replace(
                "rustfs://",
                "s3://",
                1,
            )

        dst = cache_path(source)

        if dst.exists():
            return str(dst)

        parsed = urlparse(source)

        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        print(f"Downloading from bucket: {bucket}, key: {key} to {dst}")
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=os.getenv(
                "MODEL_ACCESS_KEY"
            ),
            aws_secret_access_key=os.getenv(
                "MODEL_SECRET_KEY"
            ),
        )

        client.download_file(bucket, key, str(dst))

        return str(dst)
