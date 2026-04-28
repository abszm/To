from __future__ import annotations

import signal
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .config import AppConfig
from .logger import setup_logger
from .metadata import MetadataHandler
from .queue_manager import QueueManager
from .transcoder import Transcoder


class AudioFileHandler(FileSystemEventHandler):
    SUPPORTED_EXTENSIONS = Transcoder.SUPPORTED_EXTENSIONS

    def __init__(self, queue_manager: QueueManager, log) -> None:
        self.queue_manager = queue_manager
        self.log = log

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle_event(event)

    def on_moved(self, event: FileSystemEvent) -> None:
        self._handle_event(event)

    def _handle_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        path = Path(getattr(event, "dest_path", event.src_path))
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            self.log.warning("跳过不支持格式: %s", path)
            return

        if not self.wait_for_file_complete(path):
            self.log.warning("文件写入超时，跳过: %s", path)
            return

        self.queue_manager.add(path)

    def wait_for_file_complete(self, path: Path, checks: int = 5, interval: float = 1.0) -> bool:
        stable_count = 0
        previous_size = -1

        for _ in range(checks * 3):
            if not path.exists():
                time.sleep(interval)
                continue

            current_size = path.stat().st_size
            if current_size > 0 and current_size == previous_size:
                stable_count += 1
                if stable_count >= checks:
                    return True
            else:
                stable_count = 0

            previous_size = current_size
            time.sleep(interval)
        return False


def _scan_existing_files(input_dir: Path, queue_manager: QueueManager, log) -> None:
    for file_path in input_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in AudioFileHandler.SUPPORTED_EXTENSIONS:
            log.info("发现启动前已存在文件，加入队列: %s", file_path)
            queue_manager.add(file_path)


def main() -> None:
    config = AppConfig.from_env()
    logger = setup_logger(config.log_level)

    input_dir = Path(config.input_dir)
    output_dir = Path(config.output_dir)
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    transcoder = Transcoder(
        input_dir=config.input_dir,
        output_dir=config.output_dir,
        output_format=config.convert_format,
        bitrate=config.bitrate,
    )
    metadata_handler = MetadataHandler()
    queue_manager = QueueManager(
        transcoder=transcoder,
        metadata_handler=metadata_handler,
        max_workers=config.max_threads,
        retry_limit=config.retry_limit,
        delete_source=config.delete_source,
        log=lambda level, msg, *args: getattr(logger, level)(msg, *args),
    )

    event_handler = AudioFileHandler(queue_manager=queue_manager, log=logger)
    observer = Observer()
    observer.schedule(event_handler, str(input_dir), recursive=True)
    observer.start()

    stop_event = threading.Event()

    def _shutdown(*_args) -> None:
        logger.info("收到停止信号，开始优雅退出")
        stop_event.set()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    _scan_existing_files(input_dir, queue_manager, logger)
    logger.info("开始监听目录: %s", input_dir)

    try:
        while not stop_event.is_set():
            time.sleep(1)
    finally:
        observer.stop()
        observer.join(timeout=10)
        queue_manager.shutdown()
        logger.info("服务已停止")


if __name__ == "__main__":
    main()
