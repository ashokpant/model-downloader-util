"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from pathlib import Path

import pytest

from modeldownloaderutil.cache import cache_path, normalize_s3_uri
from modeldownloaderutil.providers.git_lfs import GitLFSProvider


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


def test_git_lfs_uses_sparse_checkout_add(monkeypatch, tmp_path: Path) -> None:
    """Downloading a second file must add to sparse-checkout, not replace it."""
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path))
    provider = GitLFSProvider()
    calls: list[list[str]] = []

    def run_create(cmd: list[str]) -> None:
        calls.append(cmd)
        if "clone" in cmd:
            Path(cmd[-1], ".git").mkdir(parents=True, exist_ok=True)
        if "lfs" in cmd and "pull" in cmd:
            rel = cmd[cmd.index("--include") + 1]
            repo = Path(cmd[cmd.index("-C") + 1])
            out = repo / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"x")

    monkeypatch.setattr(provider, "_run", run_create)

    p1 = provider.download("git+https://github.com/org/repo.git#weights/a.onnx")
    p2 = provider.download("git+https://github.com/org/repo.git#weights/b.onnx")

    assert p1.exists() and p2.exists()
    add_cmds = [c for c in calls if "sparse-checkout" in c and "add" in c]
    set_cmds = [c for c in calls if "sparse-checkout" in c and "set" in c]
    assert len(add_cmds) >= 2
    assert set_cmds == []
    assert p1.exists()
