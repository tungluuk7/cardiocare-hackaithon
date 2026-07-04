#!/usr/bin/env bash
# CardioCare — chạy test tự động bằng 1 lệnh (Linux/macOS).  bash run_tests.sh
set -e
cd "$(dirname "$0")"

PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "==> Tạo virtualenv..."
  python3 -m venv .venv
fi
echo "==> Cài dependencies..."
"$PY" -m pip install -q -r requirements.txt

export PYTHONUTF8=1
echo "==> Chạy pytest..."
exec "$PY" -m pytest
