"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
import time
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


def test_git_lfs_parallel_downloads_serialize(monkeypatch, tmp_path: Path) -> None:
    """Concurrent downloads of the same repo must not overlap git mutations."""
    import threading
    import time

    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path))
    provider = GitLFSProvider()
    active = 0
    max_active = 0
    lock = threading.Lock()
    barrier = threading.Barrier(2)

    def run_create(cmd: list[str]) -> None:
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        try:
            time.sleep(0.05)
            if "clone" in cmd:
                Path(cmd[-1], ".git").mkdir(parents=True, exist_ok=True)
            if "lfs" in cmd and "pull" in cmd:
                rel = cmd[cmd.index("--include") + 1]
                repo = Path(cmd[cmd.index("-C") + 1])
                out = repo / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"x")
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(provider, "_run", run_create)
    monkeypatch.setattr(provider, "_update_repo", lambda repo: None)

    errors: list[BaseException] = []
    results: list[Path] = []

    def worker(name: str) -> None:
        try:
            barrier.wait(timeout=5)
            results.append(
                provider.download(f"git+https://github.com/org/repo.git#weights/{name}.onnx")
            )
        except BaseException as exc:  # noqa: BLE001 — collect for assertion
            errors.append(exc)

    threads = [
        threading.Thread(target=worker, args=("a",)),
        threading.Thread(target=worker, args=("b",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert errors == []
    assert len(results) == 2
    assert all(p.exists() for p in results)
    assert max_active == 1


def test_exclusive_file_lock_blocks(tmp_path: Path) -> None:
    import threading

    from modeldownloaderutil.lock import exclusive_file_lock

    lock_path = tmp_path / "x.lock"
    held = threading.Event()
    release = threading.Event()
    second_started = threading.Event()
    order: list[str] = []

    def holder() -> None:
        with exclusive_file_lock(lock_path, timeout=5):
            order.append("holder-enter")
            held.set()
            assert release.wait(timeout=5)
            order.append("holder-exit")

    def waiter() -> None:
        assert held.wait(timeout=5)
        second_started.set()
        with exclusive_file_lock(lock_path, timeout=5):
            order.append("waiter-enter")

    t1 = threading.Thread(target=holder)
    t2 = threading.Thread(target=waiter)
    t1.start()
    assert held.wait(timeout=5)
    t2.start()
    assert second_started.wait(timeout=5)
    time.sleep(0.1)
    assert order == ["holder-enter"]
    release.set()
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert order == ["holder-enter", "holder-exit", "waiter-enter"]
