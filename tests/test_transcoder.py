from pathlib import Path
from unittest.mock import patch

import pytest

from src.transcoder import TranscodeError, Transcoder


def test_build_command_for_aac(tmp_path: Path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    input_path = input_dir / "song.flac"

    transcoder = Transcoder(str(input_dir), str(output_dir), output_format="aac", bitrate="256k")
    output_path = transcoder.build_output_path(input_path)
    cmd = transcoder.build_command(input_path, output_path)

    assert "libfdk_aac" in cmd
    assert "256k" in cmd
    assert str(output_path).endswith(".m4a")


def test_transcode_rejects_unsupported_ext(tmp_path: Path):
    transcoder = Transcoder(str(tmp_path), str(tmp_path))
    with pytest.raises(TranscodeError):
        transcoder.transcode(tmp_path / "test.mp3")


def test_transcode_success_calls_ffmpeg(tmp_path: Path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    source = input_dir / "song.flac"
    source.write_bytes(b"dummy")

    transcoder = Transcoder(str(input_dir), str(output_dir))
    expected_output = transcoder.build_output_path(source)
    expected_output.parent.mkdir(parents=True, exist_ok=True)
    expected_output.write_bytes(b"ok")

    with patch("subprocess.run") as run_mock:
        out = transcoder.transcode(source)

    assert out == expected_output
    run_mock.assert_called_once()
