"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from ..cache import git_file_path, git_repo_dir
from .base import ModelProvider


class GitLFSProvider(ModelProvider):
    def can_handle(self, source: str) -> bool:
        return source.startswith("git+")

    def download(self, source: str, *, force: bool = False) -> Path:
        canonical = source[4:]
        repo_url, _, file_path = canonical.partition("#")
        if not repo_url or not file_path:
            raise ValueError(f"Invalid git source (expected git+<url>#<path>): {source}")

        target = git_file_path(repo_url, file_path)
        repo_dir = git_repo_dir(repo_url)
        if target.exists() and not force:
            return target.resolve()

        repo_dir.mkdir(parents=True, exist_ok=True)
        if not (repo_dir / ".git").exists():
            self._run(["git", "clone", "--filter=blob:none", "--no-checkout", repo_url, str(repo_dir)])
            self._run(["git", "-C", str(repo_dir), "sparse-checkout", "init", "--no-cone"])

        self._run(["git", "-C", str(repo_dir), "sparse-checkout", "set", file_path])
        self._run(["git", "-C", str(repo_dir), "checkout", "HEAD"])
        self._run(["git", "-C", str(repo_dir), "lfs", "pull", "--include", file_path])

        if not target.exists():
            raise FileNotFoundError(f"File not found after git LFS pull: {file_path} in {repo_url}")
        return target.resolve()

    @staticmethod
    def _run(cmd: list[str]) -> None:
        subprocess.run(cmd, check=True)
