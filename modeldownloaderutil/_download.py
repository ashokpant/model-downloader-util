"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm import tqdm

from .cache import commit_download, incomplete_path


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def download_http(url: str, destination: Path) -> Path:
    tmp = incomplete_path(destination)
    tmp.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        total = int(response.headers.get("Content-Length", 0)) or None
        with open(tmp, "wb") as handle, tqdm(total=total, unit="B", unit_scale=True, unit_divisor=1024, desc=destination.name, disable=total is None) as bar:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
                    bar.update(len(chunk))
    return commit_download(tmp, destination)


def download_s3_object(client, bucket: str, key: str, destination: Path) -> Path:
    tmp = incomplete_path(destination)
    tmp.parent.mkdir(parents=True, exist_ok=True)
    size = client.head_object(Bucket=bucket, Key=key).get("ContentLength")
    with tqdm(total=size, unit="B", unit_scale=True, unit_divisor=1024, desc=destination.name, disable=not size) as bar:
        client.download_file(bucket, key, str(tmp), Callback=lambda n: bar.update(n))
    return commit_download(tmp, destination)


def download_with_cache(destination: Path, fetch: Callable[[Path], Path], *, force: bool = False) -> Path:
    if destination.exists() and not force:
        return destination.resolve()
    fetch(destination)
    return destination.resolve()
