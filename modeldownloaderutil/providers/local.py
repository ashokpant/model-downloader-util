"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""

from pathlib import Path

from .base import ModelProvider


class LocalProvider(ModelProvider):

    def can_handle(self, source: str) -> bool:
        path = Path(source).expanduser()
        return path.exists()

    def download(self, source: str) -> str:
        path = Path(source).expanduser()
        return str(path.resolve())
