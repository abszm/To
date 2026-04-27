from __future__ import annotations

import subprocess
from pathlib import Path


class TranscodeError(RuntimeError):
    """Raised when transcoding fails."""


class Transcoder:
    SUPPORTED_EXTENSIONS = {".flac", ".wav", ".ogg", ".opus"}

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
        return "libfdk_aac" if self.output_format == "aac" else "alac"

    def build_output_path(self, input_path: Path) -> Path:
        relative = input_path.resolve().relative_to(self.input_dir.resolve())
        return (self.output_dir / relative).with_suffix(".m4a")

    def build_command(self, input_path: Path, output_path: Path) -> list[str]:
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-i",
            str(input_path),
            "-c:a",
            self.codec,
        ]
        if self.codec == "libfdk_aac":
            cmd.extend(["-b:a", self.bitrate])

        cmd.extend(
            [
                "-map_metadata",
                "0",
                "-map",
                "0:a",
                "-map",
                "0:v?",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )
        return cmd

    def transcode(self, input_path: str | Path) -> Path:
        in_path = Path(input_path)
        if in_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise TranscodeError(f"Unsupported input format: {in_path.suffix}")

        out_path = self.build_output_path(in_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = self.build_command(in_path, out_path)
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=3600)
        except subprocess.CalledProcessError as exc:
            raise TranscodeError(exc.stderr.strip() or "ffmpeg failed") from exc
        except subprocess.TimeoutExpired as exc:
            raise TranscodeError("ffmpeg timeout") from exc

        if not out_path.exists() or out_path.stat().st_size <= 0:
            raise TranscodeError(f"Output validation failed: {out_path}")
        return out_path
