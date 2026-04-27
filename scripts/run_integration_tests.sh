#!/bin/bash
set -euo pipefail

# Run integration tests that depend on ffmpeg/ffprobe.
pytest -m integration -q
