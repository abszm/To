from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AppConfig:
    input_dir: str = "/input"
    output_dir: str = "/output"
    convert_format: str = "aac"
    bitrate: str = "320k"
    max_threads: int = 2
    delete_source: bool = False
    log_level: str = "INFO"
    retry_limit: int = 3

    @classmethod
    def from_env(cls) -> "AppConfig":
        convert_format = os.getenv("CONVERT_FORMAT", "aac").strip().lower()
        if convert_format not in {"aac", "alac"}:
            raise ValueError("CONVERT_FORMAT must be 'aac' or 'alac'")

        max_threads = int(os.getenv("MAX_THREADS", "2"))
        if max_threads < 1:
            raise ValueError("MAX_THREADS must be >= 1")

        retry_limit = int(os.getenv("RETRY_LIMIT", "3"))
        if retry_limit < 0:
            raise ValueError("RETRY_LIMIT must be >= 0")

        return cls(
            input_dir=os.getenv("INPUT_DIR", "/input"),
            output_dir=os.getenv("OUTPUT_DIR", "/output"),
            convert_format=convert_format,
            bitrate=os.getenv("BITRATE", "320k"),
            max_threads=max_threads,
            delete_source=_as_bool(os.getenv("DELETE_SOURCE"), default=False),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            retry_limit=retry_limit,
        )
