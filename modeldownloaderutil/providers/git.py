"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 01/07/2026
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ..cache import git_repo_dir, git_repo_lock_path
from ..lock import exclusive_file_lock
from ..progress import progress_enabled, status
from .base import ModelProvider

_QUIET = ["-c", "advice.statusUptoDate=false", "-c", "advice.detachedHead=false"]


def _git(repo: Path, *args: str) -> list[str]:
    return ["git", *_QUIET, "-C", str(repo), *args]


class GitProvider(ModelProvider):
    """Source: git://https://host/repo.git#path/to/file"""

    def can_handle(self, source: str) -> bool:
        return source.startswith("git://")

    def download(self, source: str, *, force: bool = False) -> Path:
        repo_url, _, relative = source[6:].partition("#")
        if not repo_url or not relative:
            raise ValueError(f"Invalid git source: {source}")

        relative = relative.lstrip("/")
        repo = git_repo_dir(repo_url)
        target = repo / relative

        if target.exists() and not force:
            return target.resolve()

        with exclusive_file_lock(git_repo_lock_path(repo_url)):
            if target.exists() and not force:
                return target.resolve()

            repo.mkdir(parents=True, exist_ok=True)
            show = progress_enabled()

            if not (repo / ".git").exists():
                status(f"Cloning {repo_url} …")
                flags = ["--progress"] if show else ["--quiet"]
                self._run(
                    ["git", *_QUIET, "clone", "--depth=1", *flags, repo_url, str(repo)],
                    inherit_stderr=show,
                )
            else:
                status(f"Updating {repo_url} …")
                flags = ["--progress"] if show else ["--quiet"]
                self._run(_git(repo, "pull", "--ff-only", *flags), inherit_stderr=show)

            target = repo / relative
            if target.exists():
                return target.resolve()

            raise FileNotFoundError(f"{relative} not found in {repo_url}")

    @staticmethod
    def _run(cmd: list[str], *, inherit_stderr: bool = False) -> None:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        if inherit_stderr:
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=None, text=True, env=env, stdin=subprocess.DEVNULL
            )
            detail = (result.stdout or "").strip()
        else:
            result = subprocess.run(
                cmd, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL
            )
            detail = (result.stderr or result.stdout or "").strip()
        if result.returncode:
            raise RuntimeError(f"{' '.join(cmd)} failed: {detail or f'exit {result.returncode}'}")
