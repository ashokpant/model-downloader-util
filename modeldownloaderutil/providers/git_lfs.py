"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
import hashlib
import subprocess

from .base import ModelProvider
from ..cache import get_cache_dir


class GitLFSProvider(ModelProvider):

    def can_handle(
        self,
        source: str,
    ) -> bool:
        return source.startswith("git+")

    def download(
        self,
        source: str,
    ) -> str:

        source = source[4:]

        repo_url, file_path = source.split(
            "#",
            1,
        )

        repo_hash = hashlib.sha256(
            repo_url.encode()
        ).hexdigest()[:16]

        repo_dir = (
            get_cache_dir()
            / f"repo_{repo_hash}"
        )

        target = repo_dir / file_path

        if target.exists():
            return str(target)

        if not repo_dir.exists():

            subprocess.run(
                [
                    "git",
                    "clone",
                    "--filter=blob:none",
                    "--no-checkout",
                    repo_url,
                    str(repo_dir),
                ],
                check=True,
            )

            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_dir),
                    "sparse-checkout",
                    "init",
                    "--no-cone",
                ],
                check=True,
            )

        subprocess.run(
            [
                "git",
                "-C",
                str(repo_dir),
                "sparse-checkout",
                "set",
                file_path,
            ],
            check=True,
        )

        subprocess.run(
            [
                "git",
                "-C",
                str(repo_dir),
                "checkout",
                "HEAD",
            ],
            check=True,
        )

        subprocess.run(
            [
                "git",
                "-C",
                str(repo_dir),
                "lfs",
                "pull",
                "--include",
                file_path,
            ],
            check=True,
        )

        return str(target)
