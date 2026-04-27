import math
import os
import shutil
import struct
import subprocess
import wave
from pathlib import Path

import pytest

from src.metadata import MetadataHandler
from src.transcoder import Transcoder


def _has_cmd(name: str) -> bool:
    return shutil.which(name) is not None


def _codec_available(codec_name: str) -> bool:
    if not _has_cmd("ffmpeg"):
        return False
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-encoders"],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    return codec_name in (result.stdout or "")


@pytest.fixture
def require_ffmpeg():
    if not _has_cmd("ffmpeg") or not _has_cmd("ffprobe"):
        pytest.skip("缺少 ffmpeg/ffprobe，跳过集成测试")


@pytest.fixture
def sample_wav(tmp_path: Path) -> Path:
    file_path = tmp_path / "input" / "tone.wav"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    framerate = 44100
    duration = 1.0
    frequency = 440.0
    amplitude = 32767
    frame_count = int(duration * framerate)

    with wave.open(str(file_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(framerate)
        for i in range(frame_count):
            sample = int(amplitude * math.sin(2 * math.pi * frequency * (i / framerate)))
            wav_file.writeframes(struct.pack("<h", sample))

    return file_path


@pytest.fixture
def source_with_tags(tmp_path: Path, require_ffmpeg) -> Path:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    wav_path = input_dir / "tagged.wav"
    flac_path = input_dir / "tagged.flac"

    framerate = 44100
    duration = 1.0
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(framerate)
        wav_file.writeframes(b"\x00\x00" * int(duration * framerate))

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-i",
        str(wav_path),
        "-metadata",
        "title=Integration Title",
        "-metadata",
        "artist=Integration Artist",
        "-metadata",
        "album=Integration Album",
        str(flac_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
    return flac_path


@pytest.mark.integration
def test_transcode_generated_wav_to_alac(require_ffmpeg, sample_wav: Path, tmp_path: Path):
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    transcoder = Transcoder(
        input_dir=str(tmp_path / "input"),
        output_dir=str(output_dir),
        output_format="alac",
        bitrate="320k",
    )
    out = transcoder.transcode(sample_wav)

    assert out.exists()
    assert out.suffix == ".m4a"
    assert out.stat().st_size > 0


@pytest.mark.integration
def test_transcode_preserves_basic_metadata(require_ffmpeg, source_with_tags: Path, tmp_path: Path):
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    transcoder = Transcoder(
        input_dir=str(tmp_path / "input"),
        output_dir=str(output_dir),
        output_format="alac",
        bitrate="320k",
    )
    out = transcoder.transcode(source_with_tags)

    handler = MetadataHandler()
    handler.verify_and_fix(source_with_tags, out)
    tags = handler.extract(out)

    assert tags.get("TITLE") == "Integration Title"
    assert tags.get("ARTIST") == "Integration Artist"
    assert tags.get("ALBUM") == "Integration Album"


@pytest.mark.integration
def test_transcode_real_sample_when_provided(require_ffmpeg, tmp_path: Path):
    sample_path_value = os.getenv("REAL_AUDIO_SAMPLE")
    if not sample_path_value:
        pytest.skip("未设置 REAL_AUDIO_SAMPLE，跳过真实样本测试")

    source = Path(sample_path_value)
    if not source.exists():
        pytest.skip("REAL_AUDIO_SAMPLE 文件不存在")
    if source.suffix.lower() not in Transcoder.SUPPORTED_EXTENSIONS:
        pytest.skip("REAL_AUDIO_SAMPLE 格式不受支持")

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    local_source = input_dir / source.name
    local_source.write_bytes(source.read_bytes())

    format_name = "aac" if _codec_available("libfdk_aac") else "alac"
    transcoder = Transcoder(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        output_format=format_name,
        bitrate="320k",
    )
    out = transcoder.transcode(local_source)

    assert out.exists()
    assert out.stat().st_size > 0
