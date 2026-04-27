from __future__ import annotations

import json
import subprocess
from pathlib import Path

from mutagen import File
from mutagen.mp4 import MP4Cover


class MetadataHandler:
    REQUIRED_TAGS = {
        "TITLE",
        "ARTIST",
        "ALBUM",
        "ALBUMARTIST",
        "TRACK",
        "DISC",
        "DATE",
        "GENRE",
        "COMPOSER",
        "COMMENT",
    }

    def verify_and_fix(self, input_path: str | Path, output_path: str | Path) -> None:
        source = Path(input_path)
        target = Path(output_path)

        source_tags = self._extract_tags(source)
        target_tags = self._extract_tags(target)
        missing = {k for k in source_tags.keys() if k not in target_tags}

        if missing:
            self._copy_missing_tags_with_mutagen(source, target, missing)

    def extract(self, path: str | Path) -> dict[str, str]:
        return self._extract_tags(Path(path))

    def _extract_tags(self, path: Path) -> dict[str, str]:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format_tags:stream_tags",
            "-of",
            "json",
            str(path),
        ]
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
        except subprocess.SubprocessError:
            return {}

        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            return {}

        tags = {}
        for scope in (payload.get("format", {}), *payload.get("streams", [])):
            for key, value in (scope.get("tags") or {}).items():
                norm_key = key.replace("_", "").upper()
                if value:
                    tags[norm_key] = str(value)
        return tags

    def _copy_missing_tags_with_mutagen(
        self,
        source_path: Path,
        target_path: Path,
        missing_tags: set[str],
    ) -> None:
        src = File(source_path)
        dst = File(target_path)
        if src is None or dst is None:
            return

        src_tags = getattr(src, "tags", None)
        dst_tags = getattr(dst, "tags", None)
        if src_tags is None or dst_tags is None:
            return

        for key, value in src_tags.items():
            norm_key = str(key).replace("_", "").upper()
            if norm_key in missing_tags and key not in dst_tags:
                dst_tags[key] = value

        if hasattr(src, "pictures") and not dst_tags.get("covr"):
            pictures = getattr(src, "pictures", [])
            if pictures:
                cover = pictures[0]
                image_format = MP4Cover.FORMAT_JPEG
                if getattr(cover, "mime", "") == "image/png":
                    image_format = MP4Cover.FORMAT_PNG
                dst_tags["covr"] = [MP4Cover(cover.data, imageformat=image_format)]

        dst.save()
