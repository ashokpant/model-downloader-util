"""
RustFS model store: same object key as git (`{owner}/{repo}/{file_path}`).

Download order for git+ sources is cache → RustFS → git. Enable RustFS with
RUSTFS_MODEL_ENDPOINT plus RUSTFS_MODEL_ACCESS_KEY / RUSTFS_MODEL_SECRET_KEY.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

import boto3
from botocore.config import Config

from ._download import download_s3_object
from .cache import git_file_path, parse_git_source
from .progress import lfs_pointer_size, status

_S3_CONFIG = Config(signature_version="s3v4", s3={"addressing_style": "path"})
DEFAULT_ENDPOINT = "https://s3.treeleaf.ai"
DEFAULT_BUCKET = "biometrics"


@dataclass(frozen=True)
class RustFSModelStore:
    endpoint: str
    bucket: str
    prefix: str
    access_key: str
    secret_key: str

    def object_key(self, storage_key: str) -> str:
        key = storage_key.lstrip("/")
        if self.prefix:
            return f"{self.prefix.rstrip('/')}/{key}"
        return key


def rustfs_model_store() -> RustFSModelStore | None:
    """Return the model store when access/secret are set; otherwise None."""
    access = (
        os.environ.get("RUSTFS_MODEL_ACCESS_KEY", "").strip()
        or os.environ.get("MODEL_ACCESS_KEY", "").strip()
    )
    secret = (
        os.environ.get("RUSTFS_MODEL_SECRET_KEY", "").strip()
        or os.environ.get("MODEL_SECRET_KEY", "").strip()
    )
    if not access or not secret:
        return None

    raw = (
        os.environ.get("RUSTFS_MODEL_ENDPOINT", "").strip()
        or DEFAULT_ENDPOINT
    )
    if "://" not in raw:
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    if not parsed.netloc:
        return None
    endpoint = f"{parsed.scheme}://{parsed.netloc}"
    parts = [p for p in parsed.path.split("/") if p]
    bucket = parts[0] if parts else DEFAULT_BUCKET
    prefix = "/".join(parts[1:])
    return RustFSModelStore(
        endpoint=endpoint,
        bucket=bucket,
        prefix=prefix,
        access_key=access,
        secret_key=secret,
    )


def owner_repo(repo_url: str) -> tuple[str, str]:
    parsed = urlparse(repo_url)
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"Cannot derive owner/repo from {repo_url}")
    owner = parts[-2]
    repo = parts[-1]
    if repo.endswith(".git"):
        repo = repo[: -len(".git")]
    return owner, repo


def storage_key(source: str) -> str | None:
    """Canonical object path shared by git, RustFS, and the local cache layout.

    ``git+https://github.com/treeleaftech/biometricslib.git#biometricslib/models/a.onnx.zip``
    → ``treeleaftech/biometricslib/biometricslib/models/a.onnx.zip``
    """
    parsed = parse_git_source(source)
    if parsed is None:
        return None
    repo_url, file_path = parsed
    owner, repo = owner_repo(repo_url)
    return f"{owner}/{repo}/{file_path}"


def cache_destination(source: str):
    parsed = parse_git_source(source)
    if parsed is None:
        return None
    repo_url, file_path = parsed
    return git_file_path(repo_url, file_path)


def is_usable_cached_file(path) -> bool:
    if path is None or not path.is_file():
        return False
    return lfs_pointer_size(path) is None


def rustfs_s3_client(store: RustFSModelStore):
    return boto3.client(
        "s3",
        endpoint_url=store.endpoint,
        aws_access_key_id=store.access_key,
        aws_secret_access_key=store.secret_key,
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        config=_S3_CONFIG,
    )


def download_from_rustfs(source: str, destination, *, force: bool = False):
    store = rustfs_model_store()
    key = storage_key(source)
    if store is None or key is None:
        return None
    dest = destination or cache_destination(source)
    if dest is None:
        return None
    if not force and is_usable_cached_file(dest):
        return dest.resolve()
    object_key = store.object_key(key)
    status(f"RustFS {store.bucket}/{object_key} → {dest.name}")
    client = rustfs_s3_client(store)
    download_s3_object(client, store.bucket, object_key, dest)
    if not is_usable_cached_file(dest):
        raise RuntimeError(f"RustFS download left an unusable file at {dest}")
    return dest.resolve()
