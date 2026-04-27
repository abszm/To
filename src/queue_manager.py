from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from .metadata import MetadataHandler
from .transcoder import TranscodeError, Transcoder


class QueueManager:
    def __init__(
        self,
        transcoder: Transcoder,
        metadata_handler: MetadataHandler,
        max_workers: int,
        retry_limit: int,
        delete_source: bool,
        log: Callable[..., None],
    ) -> None:
        self.transcoder = transcoder
        self.metadata_handler = metadata_handler
        self.retry_limit = retry_limit
        self.delete_source = delete_source
        self.log = log

        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.processing: set[Path] = set()
        self.failed: set[Path] = set()
        self._lock = threading.Lock()

    def add(self, filepath: str | Path) -> Future[None] | None:
        path = Path(filepath)
        with self._lock:
            if path in self.processing:
                self.log("debug", "文件已在处理中，跳过: %s", path)
                return None
            self.processing.add(path)

        return self.executor.submit(self._process_with_retry, path)

    def _process_with_retry(self, filepath: Path) -> None:
        try:
            last_error: Exception | None = None
            for attempt in range(1, self.retry_limit + 2):
                try:
                    self.log("info", "开始转码(%s/%s): %s", attempt, self.retry_limit + 1, filepath)
                    output_path = self.transcoder.transcode(filepath)
                    self.metadata_handler.verify_and_fix(filepath, output_path)
                    if self.delete_source:
                        filepath.unlink(missing_ok=True)
                    self.log("info", "处理完成: %s", output_path)
                    return
                except (TranscodeError, OSError, RuntimeError) as exc:
                    last_error = exc
                    if attempt <= self.retry_limit:
                        self.log("warning", "转码失败，准备重试(%s/%s): %s", attempt, self.retry_limit, exc)
                    else:
                        self.log("error", "转码失败达到最大重试次数: %s", filepath)

            self.failed.add(filepath)
            raise RuntimeError(str(last_error) if last_error else "Unknown transcode error")
        finally:
            with self._lock:
                self.processing.discard(filepath)

    def shutdown(self) -> None:
        self.executor.shutdown(wait=True)
