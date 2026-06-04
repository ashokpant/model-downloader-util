"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from pathlib import Path
import hashlib
import os


def get_cache_dir() -> Path:
    return Path(
        os.getenv(
            "MODEL_CACHE_DIR",
            str(Path.home() / ".treeleaf_model_registry"),
        )
    )


def cache_path(source: str) -> Path:
    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256(
        source.encode()
    ).hexdigest()[:16]

    return cache_dir / digest
