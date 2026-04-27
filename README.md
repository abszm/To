# Audio Transcoder

自动化音频转码容器服务：监听输入目录中的音频文件，按配置并发转码为 `.m4a`，并尽可能保留元数据。

## 功能

- 支持输入格式：`.flac`、`.wav`、`.ogg`、`.opus`
- 支持输出编码：`aac`（`libfdk_aac`）和 `alac`
- 支持并发队列与失败重试（默认最多 3 次）
- 转码后校验输出文件有效性（存在且大小 > 0）
- 元数据校验与补充（基于 `ffprobe` + `mutagen`）

## 环境变量

- `INPUT_DIR`：输入目录，默认 `/input`
- `OUTPUT_DIR`：输出目录，默认 `/output`
- `CONVERT_FORMAT`：`aac` 或 `alac`，默认 `aac`
- `BITRATE`：AAC 比特率，默认 `320k`
- `MAX_THREADS`：最大并发数，默认 `2`
- `DELETE_SOURCE`：转码成功后是否删除源文件，默认 `false`
- `LOG_LEVEL`：日志级别，默认 `INFO`
- `RETRY_LIMIT`：失败重试次数，默认 `3`

## 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m src.watcher
```

## Docker 运行

```bash
docker compose up -d --build
docker compose logs -f
```

## 测试

```bash
pytest
```

## 集成测试（不依赖 Docker）

```bash
./scripts/run_integration_tests.sh
```

可选真实样本测试（设置后会额外执行 1 个用例）：

```bash
export REAL_AUDIO_SAMPLE=/absolute/path/to/sample.flac
./scripts/run_integration_tests.sh
```
