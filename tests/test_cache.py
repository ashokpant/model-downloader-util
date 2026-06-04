"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from pathlib import Path

import pytest

from modeldownloaderutil.cache import cache_path, normalize_s3_uri


def test_cache_path_s3(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path))
    assert cache_path("s3://my-bucket/path/to/model.onnx") == tmp_path / "s3" / "my-bucket" / "path/to/model.onnx"


def test_cache_path_http(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path))
    assert cache_path("https://example.com/v1/model.onnx") == tmp_path / "url" / "example.com" / "v1/model.onnx"


def test_cache_path_git(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path))
    path = cache_path("git://github.com/org/repo.git#weights/a.onnx")
    assert path == tmp_path / "git" / "github.com_org_repo.git" / "weights/a.onnx"


def test_normalize_minio_uri(monkeypatch) -> None:
    monkeypatch.setenv("MINIO_ENDPOINT", "http://localhost:9000")
    uri, endpoint = normalize_s3_uri("minio://bucket/key")
    assert uri == "s3://bucket/key"
    assert endpoint == "http://localhost:9000"


def test_cache_path_invalid_s3() -> None:
    with pytest.raises(ValueError, match="Invalid object URI"):
        cache_path("s3://bucket-only")
