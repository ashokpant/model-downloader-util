"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ..cache import git_file_path, git_repo_dir
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
        repo_dir = git_repo_dir(repo_url)
        if target.exists() and not force:
            return target.resolve()

        repo_dir.mkdir(parents=True, exist_ok=True)
        repo = str(repo_dir)
        if not (repo_dir / ".git").exists():
            self._run(["git", *_QUIET, "clone", "--quiet", "--filter=blob:none", "--no-checkout", repo_url, repo])
            self._run(_git(repo, "sparse-checkout", "init", "--no-cone"))

        self._run(_git(repo, "sparse-checkout", "set", sparse_path))
        self._run(_git(repo, "checkout", "-q", "HEAD"))
        self._run(_git(repo, "lfs", "pull", "--include", relative))

        if not target.exists():
            raise FileNotFoundError(f"File not found after git LFS pull: {file_path} in {repo_url}")
        return target.resolve()

    @staticmethod
    def _run(cmd: list[str]) -> None:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip() or f"exit {result.returncode}"
            raise RuntimeError(f"{' '.join(cmd)} failed: {detail}")
