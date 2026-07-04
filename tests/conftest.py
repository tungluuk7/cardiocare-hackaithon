"""
Cấu hình chung cho test — chạy HOÀN TOÀN OFFLINE, không cần khoá VNPT/Twilio.

Đặt DB tạm + tắt scheduler TRƯỚC khi import app/config (config đọc env lúc import).
"""
import os
import sys
import tempfile
import pathlib

# Import được package gốc khi chạy pytest từ thư mục dự án
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

# DB tạm riêng cho test, không đụng cardiocare.db thật
os.environ.setdefault("DB_PATH", os.path.join(tempfile.gettempdir(), "cardiocare_pytest.db"))
os.environ.setdefault("CALL_SCHEDULER_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def _fresh_db():
    """Xoá DB tạm & tạo bảng mới cho mỗi phiên test."""
    p = os.environ["DB_PATH"]
    if os.path.exists(p):
        os.remove(p)
    from database import create_tables
    create_tables()
    yield
    # Dọn dẹp best-effort (Windows có thể còn giữ file SQLite → bỏ qua nếu khoá).
    try:
        if os.path.exists(p):
            os.remove(p)
    except OSError:
        pass


@pytest.fixture()
def client():
    import main
    return TestClient(main.app)
