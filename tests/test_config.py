import os

from src.config import AppConfig


def test_config_defaults(monkeypatch):
    for key in [
        "INPUT_DIR",
        "OUTPUT_DIR",
        "CONVERT_FORMAT",
        "BITRATE",
        "MAX_THREADS",
        "DELETE_SOURCE",
        "LOG_LEVEL",
        "RETRY_LIMIT",
    ]:
        monkeypatch.delenv(key, raising=False)

    cfg = AppConfig.from_env()
    assert cfg.input_dir == "/input"
    assert cfg.output_dir == "/output"
    assert cfg.convert_format == "aac"
    assert cfg.bitrate == "320k"
    assert cfg.max_threads == 2
    assert cfg.delete_source is False
    assert cfg.retry_limit == 3


def test_invalid_convert_format(monkeypatch):
    monkeypatch.setenv("CONVERT_FORMAT", "mp3")
    try:
        AppConfig.from_env()
        assert False, "should raise"
    except ValueError as exc:
        assert "CONVERT_FORMAT" in str(exc)
