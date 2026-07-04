#!/usr/bin/env bash
# CardioCare — chạy 1 lệnh trên Linux/macOS (bản không dùng Docker).
#   bash run.sh          → khởi động server
#   bash run.sh --seed   → seed dữ liệu demo rồi khởi động
set -e
cd "$(dirname "$0")"

PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "==> Tạo virtualenv..."
  python3 -m venv .venv
fi

echo "==> Cài dependencies..."
"$PY" -m pip install -q --upgrade pip
"$PY" -m pip install -q -r requirements.txt

export PYTHONUTF8=1 PYTHONIOENCODING=utf-8

if [ "$1" = "--seed" ]; then
  echo "==> Seed dữ liệu demo..."
  "$PY" seed_demo.py --reset
fi

echo ""
echo "==> CardioCare: http://localhost:8000/static/index.html"
echo "    API docs : http://localhost:8000/docs   (Ctrl+C để dừng)"
echo ""
exec "$PY" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
