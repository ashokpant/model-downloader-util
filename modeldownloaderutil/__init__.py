"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from .cache import cache_dir
from .downloader import download_model

__all__ = ["download_model", "cache_dir"]
__version__ = "2.0.0"
