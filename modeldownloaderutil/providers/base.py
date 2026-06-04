"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class ModelProvider(ABC):
    @abstractmethod
    def can_handle(self, source: str) -> bool: ...

    @abstractmethod
    def download(self, source: str, *, force: bool = False) -> Path: ...
