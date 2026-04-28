from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from flask import Flask, Response, request, send_file
from werkzeug.utils import secure_filename

from .config import AppConfig
from .logger import setup_logger
from .metadata import MetadataHandler
from .transcoder import TranscodeError, Transcoder


SUPPORTED_EXTENSIONS_TEXT = "/".join(ext[1:].upper() for ext in sorted(Transcoder.SUPPORTED_EXTENSIONS))
SUPPORTED_EXTENSIONS_ACCEPT = ",".join(sorted(Transcoder.SUPPORTED_EXTENSIONS))
OUTPUT_FORMAT_OPTIONS = {
    "aac": "AAC (.m4a)",
    "alac": "ALAC (.m4a)",
    "mp3": "MP3 (.mp3)",
    "opus": "Opus (.opus)",
    "flac": "FLAC (.flac)",
    "wav": "WAV (.wav)",
    "ogg": "OGG Vorbis (.ogg)",
}


def _render_page(
    message: str = "",
    download_path: str = "",
    selected_output_format: str = "aac",
    bitrate: str = "320k",
) -> str:
    button_block = ""
    if download_path:
        button_block = (
            '<div class="result">'
            '<p>转码完成，可以下载文件。</p>'
            f'<a class="btn" href="{download_path}">下载转码文件</a>'
            "</div>"
        )

    message_block = f'<p class="msg">{message}</p>' if message else ""
    options = "".join(
        (
            f'<option value="{key}"'
            + (" selected" if key == selected_output_format else "")
            + f'>{label}</option>'
        )
        for key, label in OUTPUT_FORMAT_OPTIONS.items()
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>音频转码</title>
  <style>
    :root {{
      --bg: linear-gradient(135deg, #f6f2e8, #dceaf2);
      --ink: #22313f;
      --card: #ffffff;
      --accent: #1f6f8b;
      --accent-2: #145374;
      --ok: #2f7d32;
      --err: #b23a48;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
      background: var(--bg);
      color: var(--ink);
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 24px;
    }}
    .card {{
      width: min(680px, 100%);
      background: var(--card);
      border-radius: 18px;
      box-shadow: 0 18px 40px rgba(34, 49, 63, 0.12);
      padding: 26px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    p.desc {{ margin: 0 0 20px; opacity: 0.85; }}
    form {{ display: grid; gap: 12px; }}
    input[type="file"] {{
      border: 1px solid #d8e2e8;
      border-radius: 10px;
      padding: 10px;
      background: #fafcfd;
    }}
    button, .btn {{
      display: inline-block;
      border: 0;
      border-radius: 10px;
      background: var(--accent);
      color: white;
      font-weight: 700;
      padding: 10px 16px;
      text-decoration: none;
      transition: transform 0.15s ease, background 0.15s ease;
      cursor: pointer;
    }}
    button:hover, .btn:hover {{ background: var(--accent-2); transform: translateY(-1px); }}
    .msg {{ margin: 12px 0 0; color: var(--err); }}
    .result {{ margin-top: 16px; padding: 12px; border-radius: 10px; background: #eff8f0; }}
    .result p {{ margin: 0 0 8px; color: var(--ok); }}
  </style>
</head>
<body>
  <main class="card">
    <h1>音频转码</h1>
    <p class="desc">支持常见音频格式（{SUPPORTED_EXTENSIONS_TEXT}），可选择目标格式后转码并下载。</p>
    <form method="post" action="/upload" enctype="multipart/form-data">
      <input type="file" name="audio" accept="{SUPPORTED_EXTENSIONS_ACCEPT}" required />
      <select name="output_format" required>{options}</select>
      <input type="text" name="bitrate" value="{bitrate}" placeholder="码率，如 320k" />
      <button type="submit">上传并转码</button>
    </form>
    {message_block}
    {button_block}
  </main>
</body>
</html>
"""


def create_app(
    app_config: AppConfig | None = None,
    transcoder: Transcoder | None = None,
    metadata_handler: MetadataHandler | None = None,
) -> Flask:
    config = app_config or AppConfig.from_env()
    logger = setup_logger(config.log_level)

    input_dir = Path(config.input_dir)
    output_dir = Path(config.output_dir)
    upload_dir = input_dir / "uploads"

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    upload_dir.mkdir(parents=True, exist_ok=True)

    trans = transcoder or Transcoder(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        output_format=config.convert_format,
        bitrate=config.bitrate,
    )
    meta = metadata_handler or MetadataHandler()

    app = Flask(__name__)
    app.config["INPUT_DIR"] = str(input_dir)
    app.config["OUTPUT_DIR"] = str(output_dir)

    @app.get("/")
    def index() -> Response:
        return Response(
            _render_page(
                selected_output_format=config.convert_format,
                bitrate=config.bitrate,
            ),
            mimetype="text/html",
        )

    @app.post("/upload")
    def upload() -> Response:
        file = request.files.get("audio")
        chosen_output = request.form.get("output_format", config.convert_format).strip().lower()
        chosen_bitrate = request.form.get("bitrate", config.bitrate).strip() or config.bitrate

        if file is None or file.filename is None or file.filename.strip() == "":
            return Response(
                _render_page(
                    message="请选择要上传的音频文件。",
                    selected_output_format=chosen_output,
                    bitrate=chosen_bitrate,
                ),
                mimetype="text/html",
            )

        if chosen_output not in Transcoder.supported_output_formats():
            choices = ", ".join(Transcoder.supported_output_formats())
            return Response(
                _render_page(
                    message=f"输出格式不支持，请选择: {choices}",
                    selected_output_format=config.convert_format,
                    bitrate=chosen_bitrate,
                ),
                mimetype="text/html",
            )

        filename = secure_filename(file.filename)
        suffix = Path(filename).suffix.lower()
        if suffix not in Transcoder.SUPPORTED_EXTENSIONS:
            return Response(
                _render_page(
                    message=f"仅支持以下常见音频格式: {SUPPORTED_EXTENSIONS_TEXT}",
                    selected_output_format=chosen_output,
                    bitrate=chosen_bitrate,
                ),
                mimetype="text/html",
            )

        stored_name = f"{uuid4().hex}{suffix}"
        stored_path = upload_dir / stored_name
        file.save(stored_path)

        try:
            output_path = trans.transcode(
                stored_path,
                output_format=chosen_output,
                bitrate=chosen_bitrate,
            )
            meta.verify_and_fix(stored_path, output_path)
            logger.info("网页转码成功: %s -> %s", stored_path, output_path)
        except (TranscodeError, RuntimeError, OSError) as exc:
            logger.error("网页转码失败: %s", exc)
            return Response(
                _render_page(
                    message=f"转码失败: {exc}",
                    selected_output_format=chosen_output,
                    bitrate=chosen_bitrate,
                ),
                mimetype="text/html",
            )
        finally:
            if config.delete_source:
                stored_path.unlink(missing_ok=True)

        download_name = output_path.name
        return Response(
            _render_page(
                download_path=f"/download/{download_name}",
                selected_output_format=chosen_output,
                bitrate=chosen_bitrate,
            ),
            mimetype="text/html",
        )

    @app.get("/download/<name>")
    def download(name: str):
        safe_name = secure_filename(name)
        file_path = output_dir / safe_name
        if not file_path.exists() or not file_path.is_file():
            return Response(_render_page(message="下载文件不存在或已失效。"), mimetype="text/html", status=404)
        return send_file(file_path, as_attachment=True, download_name=file_path.name)

    return app


def main() -> None:
    app = create_app()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
