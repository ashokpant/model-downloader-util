"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse

from platformdirs import user_cache_dir

APP_NAME = "model_registry"
APP_AUTHOR = "treeleaf"
_SCHEME_ALIASES = {"minio": "s3", "rustfs": "s3"}


def cache_dir() -> Path:
    if cache := os.environ.get("MODEL_CACHE_DIR"):
        return Path(cache).expanduser()
    return Path(user_cache_dir(APP_NAME, appauthor=APP_AUTHOR))


def cache_path(source: str) -> Path:
    parsed = urlparse(source)
    scheme = _SCHEME_ALIASES.get(parsed.scheme, parsed.scheme)
    root = cache_dir()

    if scheme in ("s3", "gs"):
        key = parsed.path.lstrip("/")
        if not parsed.netloc or not key:
            raise ValueError(f"Invalid object URI: {source}")
        return root / scheme / parsed.netloc / key

    if scheme in ("http", "https"):
        path = parsed.path.lstrip("/") or "download"
        return root / "url" / _safe_segment(parsed.netloc) / path

    if scheme == "git":
        file_path = parsed.fragment
        if not file_path:
            raise ValueError(f"Invalid git URI (missing #<path>): {source}")
        repo_url = f"{parsed.netloc}{parsed.path}" if parsed.netloc else parsed.path.lstrip("/")
        if not repo_url:
            raise ValueError(f"Invalid git URI: {source}")
        return git_file_path(repo_url, file_path)

    raise ValueError(f"Cannot derive cache path for: {source}")


def git_repo_dir(repo_url: str) -> Path:
    return cache_dir() / "git" / _safe_segment(repo_url)


def git_file_path(repo_url: str, file_path: str) -> Path:
    return git_repo_dir(repo_url) / file_path


def incomplete_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".incomplete")


def commit_download(tmp: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp.replace(destination)
    return destination


def _safe_segment(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value)


def normalize_s3_uri(source: str) -> tuple[str, str | None]:
    endpoint: str | None = None
    if source.startswith("minio://"):
        endpoint = os.environ.get("MINIO_ENDPOINT")
        source = "s3://" + source[len("minio://") :]
    elif source.startswith("rustfs://"):
        endpoint = os.environ.get("RUSTFS_ENDPOINT")
        source = "s3://" + source[len("rustfs://") :]
    return source, endpoint
