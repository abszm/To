#!/bin/bash
set -euo pipefail

echo "=== Audio Transcoder Starting ==="
echo "Input Directory: ${INPUT_DIR:-/input}"
echo "Output Directory: ${OUTPUT_DIR:-/output}"
echo "Output Format: ${CONVERT_FORMAT:-aac}"
echo "Bitrate: ${BITRATE:-320k}"
echo "Max Threads: ${MAX_THREADS:-2}"
echo "Delete Source: ${DELETE_SOURCE:-false}"

if [ ! -d "${INPUT_DIR:-/input}" ]; then
  echo "[ERROR] Input directory not found: ${INPUT_DIR:-/input}"
  exit 1
fi

if [ ! -d "${OUTPUT_DIR:-/output}" ]; then
  echo "[ERROR] Output directory not found: ${OUTPUT_DIR:-/output}"
  exit 1
fi

echo "[INFO] FFmpeg version:"
ffmpeg -version | sed -n '1p'

echo "[INFO] Starting file watcher..."
exec python3 -u -m src.watcher
