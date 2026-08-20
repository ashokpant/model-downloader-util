"""Multi-source download (comma-separated priority list)."""
from pathlib import Path

from modeldownloaderutil import download_model, sources, split_sources
from modeldownloaderutil.cache import cache_path


def test_split_and_sources() -> None:
    assert split_sources("a, b ,c") == ["a", "b", "c"]
    assert sources("a", "b") == "a,b"


def test_multi_source_tries_in_order(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path))
    tried: list[str] = []

    class Fake:
        def can_handle(self, source: str) -> bool:
            return True

        def download(self, source: str, *, force: bool = False) -> Path:
            tried.append(source)
            if source.startswith("rustfs://"):
                raise RuntimeError("404")
            dest = tmp_path / "out.onnx"
            dest.write_bytes(b"ok")
            return dest

    monkeypatch.setattr(
        "modeldownloaderutil.downloader._PROVIDERS",
        (Fake(),),
    )
    path = download_model(
        sources("rustfs://bucket/a.onnx", "git+https://x/y.git#a.onnx")
    )
    assert path.read_bytes() == b"ok"
    assert tried == ["rustfs://bucket/a.onnx", "git+https://x/y.git#a.onnx"]


def test_single_source_git_cache_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path))
    git = "git+https://github.com/org/repo.git#weights/a.onnx"

    class FakeGit:
        def can_handle(self, source: str) -> bool:
            return source.startswith("git+")

        def download(self, source: str, *, force: bool = False) -> Path:
            dest = cache_path(source)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"git")
            return dest

    monkeypatch.setattr(
        "modeldownloaderutil.downloader._PROVIDERS",
        (FakeGit(),),
    )
    path = download_model(git)
    assert path == cache_path(git)
    assert path.read_bytes() == b"git"
