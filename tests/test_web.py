from __future__ import annotations

import io
from pathlib import Path

from src.config import AppConfig
from src.web import create_app


class FakeTranscoder:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.last_output_format = None
        self.last_bitrate = None

    def transcode(self, _input_path: Path, output_format: str | None = None, bitrate: str | None = None) -> Path:
        self.last_output_format = output_format
        self.last_bitrate = bitrate
        suffix = ".m4a"
        if output_format in {"mp3", "opus", "flac", "wav", "ogg"}:
            suffix = f".{output_format}"
        out = self.output_dir / f"fake-output{suffix}"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"fake")
        return out


class FakeMetadata:
    def verify_and_fix(self, _source, _target) -> None:
        return None


def test_upload_page_contains_form(tmp_path: Path):
    cfg = AppConfig(input_dir=str(tmp_path / "input"), output_dir=str(tmp_path / "output"))
    app = create_app(app_config=cfg)
    client = app.test_client()

    response = client.get("/")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "上传并转码" in text
    assert ".mp3" in text
    assert "name=\"output_format\"" in text


def test_upload_then_show_download_button(tmp_path: Path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    cfg = AppConfig(input_dir=str(input_dir), output_dir=str(output_dir), delete_source=False)
    fake_transcoder = FakeTranscoder(output_dir=output_dir)
    app = create_app(
        app_config=cfg,
        transcoder=fake_transcoder,
        metadata_handler=FakeMetadata(),
    )
    client = app.test_client()

    data = {
        "audio": (io.BytesIO(b"RIFF....WAVE"), "sample.wav"),
        "output_format": "mp3",
        "bitrate": "192k",
    }
    response = client.post("/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "下载转码文件" in text
    assert "/download/fake-output.mp3" in text
    assert fake_transcoder.last_output_format == "mp3"
    assert fake_transcoder.last_bitrate == "192k"


def test_download_output_file(tmp_path: Path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / "demo.m4a"
    file_path.write_bytes(b"demo")

    cfg = AppConfig(input_dir=str(input_dir), output_dir=str(output_dir))
    app = create_app(app_config=cfg)
    client = app.test_client()

    response = client.get("/download/demo.m4a")
    assert response.status_code == 200
    assert response.data == b"demo"


def test_upload_common_format_mp3_is_accepted(tmp_path: Path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    cfg = AppConfig(input_dir=str(input_dir), output_dir=str(output_dir), delete_source=False)
    app = create_app(
        app_config=cfg,
        transcoder=FakeTranscoder(output_dir=output_dir),
        metadata_handler=FakeMetadata(),
    )
    client = app.test_client()

    data = {
        "audio": (io.BytesIO(b"ID3fake"), "sample.mp3"),
        "output_format": "aac",
        "bitrate": "320k",
    }
    response = client.post("/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    assert "下载转码文件" in response.get_data(as_text=True)


def test_upload_invalid_format_is_rejected(tmp_path: Path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    cfg = AppConfig(input_dir=str(input_dir), output_dir=str(output_dir), delete_source=False)
    app = create_app(
        app_config=cfg,
        transcoder=FakeTranscoder(output_dir=output_dir),
        metadata_handler=FakeMetadata(),
    )
    client = app.test_client()

    data = {
        "audio": (io.BytesIO(b"plain text"), "sample.txt"),
        "output_format": "aac",
        "bitrate": "320k",
    }
    response = client.post("/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    assert "仅支持以下常见音频格式" in response.get_data(as_text=True)


def test_upload_invalid_output_format_is_rejected(tmp_path: Path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    cfg = AppConfig(input_dir=str(input_dir), output_dir=str(output_dir), delete_source=False)
    app = create_app(
        app_config=cfg,
        transcoder=FakeTranscoder(output_dir=output_dir),
        metadata_handler=FakeMetadata(),
    )
    client = app.test_client()

    data = {
        "audio": (io.BytesIO(b"RIFF....WAVE"), "sample.wav"),
        "output_format": "xyz",
        "bitrate": "320k",
    }
    response = client.post("/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    assert "输出格式不支持" in response.get_data(as_text=True)
