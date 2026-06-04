"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from __future__ import annotations

from pathlib import Path

from .base import ModelProvider


class LocalProvider(ModelProvider):
    def can_handle(self, source: str) -> bool:
        return Path(source).expanduser().exists()

    def download(self, source: str, *, force: bool = False) -> Path:
        path = Path(source).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(source)
        return path
