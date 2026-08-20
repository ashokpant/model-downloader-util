"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from .cache import cache_dir
from .downloader import download_model
from .rustfs import storage_key

__all__ = ["download_model", "cache_dir", "storage_key"]
__version__ = "1.1.0"
