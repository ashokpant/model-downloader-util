"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path

from ..cache import git_file_path, git_repo_dir, git_repo_lock_path
from ..lock import exclusive_file_lock
from ..progress import (
    byte_bar,
    lfs_pointer_size,
    progress_enabled,
    status,
    update_bar_from_progress_file,
)
from .base import ModelProvider

_QUIET = ["-c", "advice.statusUptoDate=false", "-c", "advice.detachedHead=false"]


def _git_paths(file_path: str) -> tuple[str, str]:
    relative = file_path.lstrip("/")
    if not relative:
        raise ValueError("Git file path cannot be empty")
    return relative, f"/{relative}"


def _git(repo_dir: str, *args: str) -> list[str]:
    return ["git", *_QUIET, "-C", repo_dir, *args]


def _is_usable_cached_file(path: Path) -> bool:
    """True when ``path`` exists and is not an unresolved Git LFS pointer stub."""
    if not path.is_file():
        return False
    # Pointer files are tiny text stubs; treating them as cache hits causes
    # ONNXRuntime INVALID_PROTOBUF / "Protobuf parsing failed".
    return lfs_pointer_size(path) is None


def _ensure_git_lfs() -> None:
    """Fail fast when the ``git lfs`` subcommand is missing."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    result = subprocess.run(
        ["git", "lfs", "version"],
        capture_output=True,
        text=True,
        env=env,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode == 0:
        return
    detail = (result.stderr or result.stdout or "").strip()
    raise RuntimeError(
        "git-lfs is required to download git+ model weights, but "
        f"`git lfs` is unavailable ({detail or f'exit {result.returncode}'}). "
        "Install git-lfs (e.g. `apt-get install -y git-lfs && git lfs install`) "
        "and retry."
    )


def _unlink_lfs_pointer_stub(path: Path) -> None:
    """Remove an unresolved LFS pointer so checkout/pull can replace it."""
    if path.is_file() and lfs_pointer_size(path) is not None:
        path.unlink(missing_ok=True)


class GitLFSProvider(ModelProvider):
    def can_handle(self, source: str) -> bool:
        return source.startswith("git+")

    def download(self, source: str, *, force: bool = False) -> Path:
        canonical = source[4:]
        repo_url, _, file_path = canonical.partition("#")
        if not repo_url or not file_path:
            raise ValueError(f"Invalid git source (expected git+<url>#<path>): {source}")

        relative, sparse_path = _git_paths(file_path)
        target = git_file_path(repo_url, relative)
        if not force and _is_usable_cached_file(target):
            return target.resolve()

        _ensure_git_lfs()

        repo_dir = git_repo_dir(repo_url)
        with exclusive_file_lock(git_repo_lock_path(repo_url)):
            # Another process may have finished while we waited for the lock.
            if not force and _is_usable_cached_file(target):
                return target.resolve()

            # Drop leftover pointer stubs from clones done without git-lfs.
            _unlink_lfs_pointer_stub(target)

            repo_dir.mkdir(parents=True, exist_ok=True)
            repo = str(repo_dir)
            if not (repo_dir / ".git").exists():
                status(f"Cloning {repo_url} …")
                self._run(
                    [
                        "git",
                        *_QUIET,
                        "clone",
                        "--quiet",
                        "--filter=blob:none",
                        "--no-checkout",
                        repo_url,
                        repo,
                    ]
                )
                self._run(_git(repo, "sparse-checkout", "init", "--no-cone"))
            else:
                status(f"Updating {repo_url} …")
                self._update_repo(repo)

            # Use `add` (not `set`) so previously cached files from this repo are kept.
            self._run(_git(repo, "sparse-checkout", "add", sparse_path))
            self._run(_git(repo, "checkout", "-q", "HEAD"))
            self._lfs_pull(repo, relative, target)

            if not target.exists():
                raise FileNotFoundError(
                    f"File not found after git LFS pull: {file_path} in {repo_url}"
                )
            if lfs_pointer_size(target) is not None:
                raise RuntimeError(
                    f"Git LFS pull left a pointer stub at {target}. "
                    "Install git-lfs (`git lfs install`) and ensure credentials "
                    "can fetch LFS objects, then retry with force_download=True."
                )
            return target.resolve()

    def _lfs_pull(self, repo: str, relative: str, target: Path) -> None:
        """Run ``git lfs pull`` with a tqdm byte progress bar when possible."""
        name = Path(relative).name
        total = lfs_pointer_size(target)
        show = progress_enabled()

        if not show:
            self._run(_git(repo, "lfs", "pull", "--include", relative))
            return

        fd, progress_name = tempfile.mkstemp(prefix="mdl-lfs-", suffix=".progress")
        os.close(fd)
        progress_file = Path(progress_name)
        try:
            env = {
                **os.environ,
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_LFS_PROGRESS": str(progress_file),
            }
            proc = subprocess.Popen(
                _git(repo, "lfs", "pull", "--include", relative),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                stdin=subprocess.DEVNULL,
            )
            last = 0
            with byte_bar(name, total) as bar:
                while proc.poll() is None:
                    last = update_bar_from_progress_file(progress_file, bar, last)
                    time.sleep(0.05)
                last = update_bar_from_progress_file(progress_file, bar, last)
                if total and bar.n < total:
                    bar.update(total - bar.n)
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                detail = (stderr or stdout or "").strip() or f"exit {proc.returncode}"
                raise RuntimeError(
                    f"git lfs pull --include {relative} failed: {detail}"
                )
        finally:
            progress_file.unlink(missing_ok=True)

    def _update_repo(self, repo: str) -> None:
        """Fast-forward the cache clone so newly published remote files are visible."""
        self._run(_git(repo, "fetch", "--quiet", "--prune", "origin"))
        remote = self._remote_head(repo)
        self._run(_git(repo, "checkout", "-q", "-B", "_mdl_cache", remote))

    @staticmethod
    def _remote_head(repo: str) -> str:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        result = subprocess.run(
            _git(repo, "symbolic-ref", "-q", "refs/remotes/origin/HEAD"),
            capture_output=True,
            text=True,
            env=env,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        for candidate in ("refs/remotes/origin/main", "refs/remotes/origin/master"):
            check = subprocess.run(
                _git(repo, "rev-parse", "--verify", "-q", candidate),
                capture_output=True,
                text=True,
                env=env,
                stdin=subprocess.DEVNULL,
            )
            if check.returncode == 0:
                return candidate
        return "FETCH_HEAD"

    @staticmethod
    def _run(cmd: list[str]) -> None:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        result = subprocess.run(
            cmd, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip() or f"exit {result.returncode}"
            raise RuntimeError(f"{' '.join(cmd)} failed: {detail}")
