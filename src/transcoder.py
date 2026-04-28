from __future__ import annotations

import subprocess
from pathlib import Path


class TranscodeError(RuntimeError):
    """Raised when transcoding fails."""


class Transcoder:
    SUPPORTED_EXTENSIONS = {
        ".flac",
        ".wav",
        ".ogg",
        ".opus",
        ".mp3",
        ".m4a",
        ".aac",
        ".wma",
        ".aiff",
        ".aif",
        ".amr",
        ".ape",
        ".mka",
        ".webm",
        ".ac3",
    }
    OUTPUT_PROFILES = {
        "aac": {"codec": "libfdk_aac", "extension": ".m4a", "supports_bitrate": True},
        "alac": {"codec": "alac", "extension": ".m4a", "supports_bitrate": False},
        "mp3": {"codec": "libmp3lame", "extension": ".mp3", "supports_bitrate": True},
        "opus": {"codec": "libopus", "extension": ".opus", "supports_bitrate": True},
        "flac": {"codec": "flac", "extension": ".flac", "supports_bitrate": False},
        "wav": {"codec": "pcm_s16le", "extension": ".wav", "supports_bitrate": False},
        "ogg": {"codec": "libvorbis", "extension": ".ogg", "supports_bitrate": True},
    }

    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        output_format: str = "aac",
        bitrate: str = "320k",
    ) -> None:
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_format = output_format
        self.bitrate = bitrate

    @property
    def codec(self) -> str:
        profile = self.OUTPUT_PROFILES.get(self.output_format)
        if profile is None:
            raise TranscodeError(f"Unsupported output format: {self.output_format}")
        return str(profile["codec"])

    @classmethod
    def supported_output_formats(cls) -> tuple[str, ...]:
        return tuple(cls.OUTPUT_PROFILES.keys())

    @classmethod
    def _validate_output_format(cls, output_format: str) -> str:
        normalized = output_format.strip().lower()
        if normalized not in cls.OUTPUT_PROFILES:
            choices = ", ".join(cls.supported_output_formats())
            raise TranscodeError(f"Unsupported output format: {output_format}. choose from: {choices}")
        return normalized

    def build_output_path(self, input_path: Path, output_format: str | None = None) -> Path:
        selected_format = self._validate_output_format(output_format or self.output_format)
        output_ext = str(self.OUTPUT_PROFILES[selected_format]["extension"])
        relative = input_path.resolve().relative_to(self.input_dir.resolve())
        return (self.output_dir / relative).with_suffix(output_ext)

    def build_command(
        self,
        input_path: Path,
        output_path: Path,
        output_format: str | None = None,
        bitrate: str | None = None,
    ) -> list[str]:
        selected_format = self._validate_output_format(output_format or self.output_format)
        profile = self.OUTPUT_PROFILES[selected_format]
        codec = str(profile["codec"])
        resolved_bitrate = (bitrate or self.bitrate).strip()

        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-i",
            str(input_path),
            "-c:a",
            codec,
        ]
        if bool(profile.get("supports_bitrate")) and resolved_bitrate:
            cmd.extend(["-b:a", resolved_bitrate])

        cmd.extend([
            "-map_metadata",
            "0",
            "-map",
            "0:a",
        ])
        if output_path.suffix.lower() == ".m4a":
            cmd.extend(["-movflags", "+faststart"])
        cmd.append(str(output_path))
        return cmd

    def transcode(
        self,
        input_path: str | Path,
        output_format: str | None = None,
        bitrate: str | None = None,
    ) -> Path:
        in_path = Path(input_path)
        if in_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise TranscodeError(f"Unsupported input format: {in_path.suffix}")

        selected_format = self._validate_output_format(output_format or self.output_format)
        out_path = self.build_output_path(in_path, output_format=selected_format)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = self.build_command(
            in_path,
            out_path,
            output_format=selected_format,
            bitrate=bitrate,
        )
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=3600)
        except subprocess.CalledProcessError as exc:
            raise TranscodeError(exc.stderr.strip() or "ffmpeg failed") from exc
        except subprocess.TimeoutExpired as exc:
            raise TranscodeError("ffmpeg timeout") from exc

        if not out_path.exists() or out_path.stat().st_size <= 0:
            raise TranscodeError(f"Output validation failed: {out_path}")
        return out_path
