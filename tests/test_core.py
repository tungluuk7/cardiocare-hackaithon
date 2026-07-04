"""
Bộ test tự động cho CardioCare — offline, tất định (không cần khoá VNPT/Twilio).
Chạy:  pytest -q
"""
import asyncio
import pytest

from database import get_conn
from services.triage_engine import analyze
from services.vnpt_ocr import parse_discharge, _bearer, OcrError, ocr_ready


# ── Health ────────────────────────────────────────────────────────────────────
def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


# ── Triage engine: RED/YELLOW/GREEN + phủ định ────────────────────────────────
TRIAGE_CASES = [
    ("bác cảm thấy bình thường, ăn uống tốt",   "GREEN"),
    ("hơi khó thở, chân cũng hơi sưng",          "YELLOW"),
    ("đau ngực dữ dội từ sáng, ngất một lần",    "RED"),
    ("không đau ngực",                           "GREEN"),   # phủ định
    ("con không lo, bác bị ngất sáng nay",       "RED"),
    ("không bị sốt, giờ lại sốt cao",            "YELLOW"),
    ("không thấy mệt nhưng bị đau ngực dữ dội",  "RED"),
]


@pytest.mark.parametrize("transcript,expected", TRIAGE_CASES)
def test_triage_levels(transcript, expected):
    assert asyncio.run(analyze(transcript)).level == expected


# Không dấu (STT/gõ thiếu dấu) + triệu chứng lâm sàng mở rộng + chống dương tính giả
TRIAGE_EXTENDED = [
    ("dau nguc du doi tu sang",              "RED"),     # không dấu → RED
    ("kho tho va sung chan",                 "YELLOW"),  # không dấu → YELLOW
    ("đi ngoài phân đen mấy hôm nay",        "RED"),     # xuất huyết tiêu hoá (DAPT)
    ("di ngoai phan den",                    "RED"),     # không dấu
    ("bác bị méo miệng, yếu nửa người",      "RED"),     # dấu hiệu đột quỵ
    ("mệt mỏi rã rời cả ngày",               "YELLOW"),  # mệt mỏi
    ("met moi ca ngay",                      "YELLOW"),  # không dấu
    ("buồn nôn, nôn ói nhiều",               "YELLOW"),  # buồn nôn/nôn
    ("bác ăn được một xíu, người khỏe",      "GREEN"),   # "xíu" KHÔNG được nhầm thành ngất
    ("con gọi hỏi thăm, bác nói chuyện bình thường", "GREEN"),  # "nói" KHÔNG thành nôn
    ("bác không thấy mệt, ăn uống tốt",      "GREEN"),   # phủ định mệt
]


@pytest.mark.parametrize("transcript,expected", TRIAGE_EXTENDED)
def test_triage_extended(transcript, expected):
    assert asyncio.run(analyze(transcript)).level == expected


# ── OCR: bóc tách giấy ra viện (2 layout khác nhau) ───────────────────────────
PAPER_1 = [
    "Họ và tên người bệnh: NGUYỄN VĂN HÙNG",
    "Ngày sinh: 12/03/1959          Tuổi: 67          Giới tính: Nam",
    "Mã bệnh nhân: BN2026-04821          Số thẻ BHYT: HT2010200456789",
    "Ngày ra viện: 28/06/2026          Tổng số ngày điều trị: 08 ngày",
    "Chẩn đoán ra viện: Bệnh tim thiếu máu cục bộ - Đã can thiệp động mạch",
    "Lời dặn của bác sĩ:",
    "Bác sĩ điều trị", "BS.CKII Trần Thị Lan",
]
PAPER_2 = [
    "Họ và tên: TRẦN THỊ MAI",
    "Sinh năm: 1954          Tuổi: 72          Giới tính: Nữ",
    "Số bệnh án: BA-2026-77812          Số thẻ BHYT: HN4010200778812",
    "Ra viện hồi: 10 giờ 30 phút, ngày 02/07/2026",
    "Chẩn đoán khi ra viện: Nhồi máu cơ tim cấp thành trước - Đã can thiệp",
    "Lời dặn của bác sĩ: Tái khám ngày 02/08/2026.",
    "Bác sĩ điều trị", "ThS.BS Lê Minh Quân",
]


def test_parse_discharge_paper1():
    d = parse_discharge(PAPER_1)
    assert d["name"] == "NGUYỄN VĂN HÙNG"
    assert d["age"] == 67
    assert d["pid"] == "BN2026-04821"
    assert d["discharge_date"] == "2026-06-28"
    assert d["doctor_name"] == "BS.CKII Trần Thị Lan"       # KHÔNG bị "Lời dặn của bác sĩ" cướp


def test_parse_discharge_paper2():
    d = parse_discharge(PAPER_2)
    assert d["name"] == "TRẦN THỊ MAI"
    assert d["age"] == 72
    assert d["pid"] == "BA-2026-77812"
    assert d["discharge_date"] == "2026-07-02"              # "10 giờ 30 phút, ngày 02/07/2026"
    assert d["doctor_name"] == "ThS.BS Lê Minh Quân"


def test_bearer_prefix():
    assert _bearer("abc123") == "Bearer abc123"
    assert _bearer("Bearer abc123") == "Bearer abc123"
    assert _bearer("") == ""


def test_ocr_error_short():
    assert OcrError("scan", 401, '{"message":"IDG-401"}').short() == "IDG-401"


# ── Patients API: SĐT bắt buộc ────────────────────────────────────────────────
def test_patient_requires_phone(client):
    assert client.post("/patients", json={"name": "Thiếu SĐT"}).status_code == 422


def test_patient_create_ok(client):
    r = client.post("/patients", json={"name": "BN Test", "phone": "0900000000"})
    assert r.status_code == 201 and r.json()["id"]


# ── OCR API gating ────────────────────────────────────────────────────────────
def test_ocr_status(client):
    assert client.get("/ocr/status").json() == {"enabled": ocr_ready()}


def test_ocr_discharge_without_config(client):
    if ocr_ready():
        pytest.skip("SmartReader đã cấu hình — bỏ qua case chưa cấu hình")
    r = client.post("/ocr/discharge",
                    files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")}).json()
    assert r["ok"] is False


# ── UX analytics ──────────────────────────────────────────────────────────────
def test_ux_rejects_unknown_event(client):
    assert client.post("/ux/events", json={"event": "hacker_evt"}).json()["ok"] is False


def test_ux_report_aggregates(client):
    with get_conn() as conn:                # bắt đầu từ trạng thái sạch cho tất định
        conn.execute("DELETE FROM ux_events")
    for w in (10, 20):
        client.post("/ux/events", json={"event": "red_acknowledged", "props": {"wait_seconds": w}})
    rep = client.get("/ux/report").json()
    assert rep["red_ack_count"] == 2
    assert rep["avg_red_wait_seconds"] == 15.0


# ── Chatbot: cộng dồn triệu chứng & leo thang mức độ ──────────────────────────
def test_chatbot_accumulates_and_escalates(client):
    sid = "pytest-sess"
    client.delete(f"/chatbot/session/{sid}")
    r1 = client.post("/chatbot/message",
                     json={"message": "bác hơi khó thở", "session_id": sid}).json()
    assert r1["triage_level"] in ("YELLOW", "RED")
    r2 = client.post("/chatbot/message",
                     json={"message": "giờ đau ngực dữ dội và bị ngất", "session_id": sid}).json()
    assert r2["triage_level"] == "RED"
    assert "kho_tho" in r2["symptoms"]      # triệu chứng lượt trước vẫn được giữ
