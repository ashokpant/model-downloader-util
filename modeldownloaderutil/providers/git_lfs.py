"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ..cache import git_file_path, git_repo_dir, git_repo_lock_path
from ..lock import exclusive_file_lock
from .base import ModelProvider

_QUIET = ["-c", "advice.statusUptoDate=false", "-c", "advice.detachedHead=false"]


def _git_paths(file_path: str) -> tuple[str, str]:
    relative = file_path.lstrip("/")
    if not relative:
        raise ValueError("Git file path cannot be empty")
    return relative, f"/{relative}"


def _git(repo_dir: str, *args: str) -> list[str]:
    return ["git", *_QUIET, "-C", repo_dir, *args]


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
        if target.exists() and not force:
            return target.resolve()

        repo_dir = git_repo_dir(repo_url)
        with exclusive_file_lock(git_repo_lock_path(repo_url)):
            # Another process may have finished while we waited for the lock.
            if target.exists() and not force:
                return target.resolve()

            repo_dir.mkdir(parents=True, exist_ok=True)
            repo = str(repo_dir)
            if not (repo_dir / ".git").exists():
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
                self._update_repo(repo)

            # Use `add` (not `set`) so previously cached files from this repo are kept.
            self._run(_git(repo, "sparse-checkout", "add", sparse_path))
            self._run(_git(repo, "checkout", "-q", "HEAD"))
            self._run(_git(repo, "lfs", "pull", "--include", relative))

            if not target.exists():
                raise FileNotFoundError(
                    f"File not found after git LFS pull: {file_path} in {repo_url}"
                )
            return target.resolve()

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
