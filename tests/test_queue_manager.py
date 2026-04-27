from pathlib import Path

from src.queue_manager import QueueManager


class FakeTranscoder:
    def __init__(self):
        self.calls = 0

    def transcode(self, path):
        self.calls += 1
        output = Path(str(path).replace(".flac", ".m4a"))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"ok")
        return output


class FakeMetadata:
    def __init__(self):
        self.calls = 0

    def verify_and_fix(self, _source, _target):
        self.calls += 1


def test_queue_manager_processes_file(tmp_path: Path):
    src = tmp_path / "a.flac"
    src.write_bytes(b"src")

    transcoder = FakeTranscoder()
    metadata = FakeMetadata()
    logs = []

    manager = QueueManager(
        transcoder=transcoder,
        metadata_handler=metadata,
        max_workers=1,
        retry_limit=2,
        delete_source=False,
        log=lambda level, msg, *args: logs.append((level, msg % args if args else msg)),
    )
    fut = manager.add(src)
    assert fut is not None
    fut.result(timeout=5)
    manager.shutdown()

    assert transcoder.calls == 1
    assert metadata.calls == 1
    assert src in {tmp_path / "a.flac"}
