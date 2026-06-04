"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from __future__ import annotations

from pathlib import Path

_LOADED = False


def load_env() -> None:
    global _LOADED
    if _LOADED:
        return
    from dotenv import load_dotenv

    for path in _env_candidates():
        load_dotenv(path, override=False)
    _LOADED = True


def _env_candidates() -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for base in (Path.cwd(), Path(__file__).resolve().parents[1]):
        for parent in (base, *base.parents):
            env = (parent / ".env").resolve()
            if env.is_file() and env not in seen:
                seen.add(env)
                out.append(env)
    return out
