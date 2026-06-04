"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from abc import ABC, abstractmethod


class ModelProvider(ABC):

    @abstractmethod
    def can_handle(
        self,
        source: str,
    ) -> bool:
        pass

    @abstractmethod
    def download(
        self,
        source: str,
    ) -> str:
        pass
