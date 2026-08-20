"""RustFS fallback and shared storage-key tests."""
from pathlib import Path

from modeldownloaderutil.cache import cache_path, parse_git_source
from modeldownloaderutil.downloader import download_model
from modeldownloaderutil.rustfs import (
    owner_repo,
    rustfs_model_store,
    storage_key,
)


GIT = "git+https://github.com/treeleaftech/biometricslib.git#biometricslib/models/model_4_kps.onnx.zip"


def test_parse_git_source() -> None:
    repo, path = parse_git_source(GIT)
    assert repo == "https://github.com/treeleaftech/biometricslib.git"
    assert path == "biometricslib/models/model_4_kps.onnx.zip"


def test_storage_key_matches_git_layout() -> None:
    assert storage_key(GIT) == (
        "treeleaftech/biometricslib/biometricslib/models/model_4_kps.onnx.zip"
    )
    assert storage_key(
        "git+https://github.com/treeleaftech/deepprint-fp.git#weights/deepprint512.onnx"
    ) == "treeleaftech/deepprint-fp/weights/deepprint512.onnx"


def test_owner_repo() -> None:
    assert owner_repo("https://github.com/treeleaftech/flare-fp.git") == (
        "treeleaftech",
        "flare-fp",
    )


def test_cache_path_git_plus(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path))
    path = cache_path(GIT)
    assert path == (
        tmp_path
        / "git"
        / "https_github.com_treeleaftech_biometricslib.git"
        / "biometricslib/models/model_4_kps.onnx.zip"
    )


def test_rustfs_store_requires_keys(monkeypatch) -> None:
    monkeypatch.delenv("RUSTFS_MODEL_ACCESS_KEY", raising=False)
    monkeypatch.delenv("RUSTFS_MODEL_SECRET_KEY", raising=False)
    monkeypatch.delenv("MODEL_ACCESS_KEY", raising=False)
    monkeypatch.delenv("MODEL_SECRET_KEY", raising=False)
    assert rustfs_model_store() is None


def test_rustfs_store_parses_endpoint_bucket(monkeypatch) -> None:
    monkeypatch.setenv("RUSTFS_MODEL_ACCESS_KEY", "ak")
    monkeypatch.setenv("RUSTFS_MODEL_SECRET_KEY", "sk")
    monkeypatch.setenv("RUSTFS_MODEL_ENDPOINT", "s3.treeleaf.ai/biometrics")
    store = rustfs_model_store()
    assert store is not None
    assert store.endpoint == "https://s3.treeleaf.ai"
    assert store.bucket == "biometrics"
    assert store.object_key("treeleaftech/biometricslib/a.onnx") == (
        "treeleaftech/biometricslib/a.onnx"
    )


def test_cache_hit_skips_rustfs_and_git(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path))
    dest = cache_path(GIT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"onnx-bytes")
    rustfs_called = []

    def boom(*_a, **_k):
        rustfs_called.append(1)
        raise AssertionError("rustfs should not run on cache hit")

    monkeypatch.setattr("modeldownloaderutil.downloader.download_from_rustfs", boom)
    monkeypatch.setattr(
        "modeldownloaderutil.downloader.rustfs_model_store",
        lambda: object(),
    )
    path = download_model(GIT)
    assert path.read_bytes() == b"onnx-bytes"
    assert rustfs_called == []


def test_rustfs_then_git_fallback(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("RUSTFS_MODEL_ACCESS_KEY", "ak")
    monkeypatch.setenv("RUSTFS_MODEL_SECRET_KEY", "sk")
    monkeypatch.setenv("RUSTFS_MODEL_ENDPOINT", "https://s3.treeleaf.ai")

    def rustfs_fail(*_a, **_k):
        raise RuntimeError("404")

    monkeypatch.setattr(
        "modeldownloaderutil.downloader.download_from_rustfs", rustfs_fail
    )

    class FakeGit:
        def can_handle(self, source: str) -> bool:
            return source.startswith("git+")

        def download(self, source: str, *, force: bool = False) -> Path:
            dest = cache_path(source)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"from-git")
            return dest

    monkeypatch.setattr(
        "modeldownloaderutil.downloader._PROVIDERS",
        (FakeGit(),),
    )
    path = download_model(GIT)
    assert path.read_bytes() == b"from-git"


def test_rustfs_success_writes_git_cache_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("RUSTFS_MODEL_ACCESS_KEY", "ak")
    monkeypatch.setenv("RUSTFS_MODEL_SECRET_KEY", "sk")

    def rustfs_ok(source, dest, *, force=False):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"from-rustfs")
        return dest.resolve()

    monkeypatch.setattr(
        "modeldownloaderutil.downloader.download_from_rustfs", rustfs_ok
    )

    class BoomGit:
        def can_handle(self, source: str) -> bool:
            return True

        def download(self, source: str, *, force: bool = False) -> Path:
            raise AssertionError("git should not run when rustfs succeeds")

    monkeypatch.setattr(
        "modeldownloaderutil.downloader._PROVIDERS",
        (BoomGit(),),
    )
    path = download_model(GIT)
    assert path.read_bytes() == b"from-rustfs"
    assert path == cache_path(GIT)
