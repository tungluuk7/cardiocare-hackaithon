"""
UX Analytics — thu thập & tổng hợp tương tác người dùng trên web.

Đây là LỚP THU THẬP NỘI BỘ (fallback) cho tiêu chí "Trải nghiệm người dùng":
  - Frontend gọi UX.track(event, props) (static/js/ux.js) → POST /ux/events.
  - Khi Ban tổ chức cấp credentials VNPT SmartUX, chỉ cần bật nhánh SmartUX
    trong ux.js; schema event giữ nguyên nên bảng số liệu không đổi.

Endpoints:
  POST /ux/events   → ghi 1 sự kiện (ẩn danh)
  GET  /ux/report   → số liệu tổng hợp (đổ vào static/ux.html để trực quan hoá)

Lưu ý phạm vi: SmartUX/ lớp này chỉ đo được KÊNH WEB (dashboard, chat).
Kênh gọi điện (giao diện chính của bệnh nhân) được đo bằng dữ liệu backend
(call_logs, patients.last_answered_at, triage_results.confidence).
"""
import json
from fastapi import APIRouter
from pydantic import BaseModel
from database import get_conn
from config import settings

router = APIRouter(prefix="/ux", tags=["ux-analytics"])


@router.get("/config")
def ux_config():
    """
    Cấu hình SmartUX cho frontend (static/js/smartux.js đọc endpoint này).
    Giữ app_key trong .env thay vì nhúng cứng vào HTML — cùng pattern với các
    dịch vụ VNPT khác của dự án. enabled=false ⇒ trang web bỏ qua, không lỗi.
    """
    return {
        "enabled":  bool(settings.SMARTUX_APP_KEY),
        "app_key":  settings.SMARTUX_APP_KEY,
        "url":      settings.SMARTUX_URL,
        "sdk_path": settings.SMARTUX_SDK_PATH,
    }

# Danh sách event hợp lệ — chốt cứng để tránh rác dữ liệu và để bảng report ổn định.
KNOWN_EVENTS = {
    "dashboard_view",       # điều dưỡng mở dashboard          (Adoption)
    "filter_used",          # lọc theo mức RED/YELLOW/GREEN     (Engagement)
    "patient_link_click",   # bấm vào tên bệnh nhân             (Engagement)
    "patient_detail_view",  # mở trang chi tiết bệnh nhân       (Adoption)
    "call_initiated",       # bấm "Gọi lại"                     (Task efficiency)
    "red_acknowledged",     # bấm gọi 1 ca RED + wait_seconds   (Task efficiency ⭐)
    "chat_open",            # mở cửa sổ chat                    (Engagement)
    "chat_send",            # gửi tin nhắn văn bản              (Engagement)
    "chat_mic",             # dùng micro                       (Engagement)
    "chat_completed",       # nhận kết quả triage từ chat       (Task success)
}


class UXEvent(BaseModel):
    event: str
    props: dict | None = None
    session_id: str | None = None
    page: str | None = None


@router.post("/events", status_code=201)
def track_event(e: UXEvent):
    """Ghi 1 sự kiện tương tác. Bỏ qua âm thầm nếu event không nằm trong whitelist."""
    if e.event not in KNOWN_EVENTS:
        return {"ok": False, "reason": "unknown_event"}
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO ux_events (session_id, event, props, page) VALUES (?, ?, ?, ?)",
            (e.session_id, e.event, json.dumps(e.props or {}, ensure_ascii=False), e.page),
        )
    return {"ok": True}


@router.get("/report")
def report():
    """
    Số liệu UX tổng hợp cho trang trực quan hoá (static/ux.html).
    Trả về các chỉ số gắn thẳng vào bảng UX Metrics trong proposal.
    """
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM ux_events").fetchone()[0]
        sessions = conn.execute(
            "SELECT COUNT(DISTINCT session_id) FROM ux_events"
        ).fetchone()[0]

        # Đếm theo loại sự kiện
        by_event = {
            r["event"]: r["n"]
            for r in conn.execute(
                "SELECT event, COUNT(*) AS n FROM ux_events GROUP BY event"
            ).fetchall()
        }

        # ⭐ Chỉ số vàng: thời gian phản ứng với ca RED (giây) — lấy từ props.wait_seconds
        red_rows = conn.execute(
            "SELECT props FROM ux_events WHERE event = 'red_acknowledged'"
        ).fetchall()
        waits = []
        for r in red_rows:
            try:
                w = json.loads(r["props"] or "{}").get("wait_seconds")
                if isinstance(w, (int, float)) and w >= 0:
                    waits.append(w)
            except Exception:
                pass
        avg_red_wait = round(sum(waits) / len(waits), 1) if waits else None

        # Bộ lọc dùng nhiều nhất
        filter_breakdown = {}
        for r in conn.execute(
            "SELECT props FROM ux_events WHERE event = 'filter_used'"
        ).fetchall():
            try:
                risk = json.loads(r["props"] or "{}").get("risk", "?")
                filter_breakdown[risk] = filter_breakdown.get(risk, 0) + 1
            except Exception:
                pass

    return {
        "total_events": total,
        "sessions": sessions,
        "by_event": by_event,
        "avg_red_wait_seconds": avg_red_wait,
        "red_ack_count": len(waits),
        "filter_breakdown": filter_breakdown,
        # Cột "Đo bằng" của proposal: web = lớp này/SmartUX; thoại = backend DB.
        "source": "internal-fallback (sẵn sàng chuyển sang VNPT SmartUX)",
    }
