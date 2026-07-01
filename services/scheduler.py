"""
Bộ lập lịch tự động gọi điện cho bệnh nhân theo khung giờ đã cài.

- Vòng lặp nền chạy mỗi 30s, tìm bệnh nhân có call_time == giờ hiện tại (HH:MM)
  và chưa được gọi hôm nay → khởi tạo cuộc gọi.
- initiate_call:
    + Có Twilio + PUBLIC_BASE_URL → GỌI THẬT (Twilio phát câu hỏi, ghi âm,
      webhook /telephony/twilio-recording chạy VNPT STT + triage).
    + Chưa cấu hình → MÔ PHỎNG: chạy pipeline với transcript mock để dashboard
      vẫn cập nhật (chứng minh tính tự động).
"""
import asyncio
from database import get_conn
from config import settings, now_vn
from services.telephony import is_configured, call_patient

_task: asyncio.Task | None = None
_TICK_SECONDS = 30


def _today() -> str:
    # Giờ Hà Nội (UTC+7) — nếu dùng giờ máy chủ (UTC trên Render) sẽ lệch 7h,
    # khiến giờ hẹn gọi so sánh sai và ngày "đã gọi hôm nay" nhảy sớm.
    return now_vn().strftime("%Y-%m-%d")


def _now_hhmm() -> str:
    return now_vn().strftime("%H:%M")


def _mark_called(pid: int):
    with get_conn() as conn:
        conn.execute("UPDATE patients SET last_call_date=? WHERE id=?", (_today(), pid))


async def initiate_call(patient: dict, force_scenario: str = "") -> dict:
    """
    Khởi tạo 1 cuộc gọi cho bệnh nhân.
    CHỈ đánh dấu "đã gọi hôm nay" khi khởi tạo THÀNH CÔNG — để cuộc gọi lỗi
    (vd số sai) không chặn lần sau.
    """
    pid = patient["id"]

    if is_configured() and not force_scenario:
        # GỌI THẬT qua Twilio
        try:
            res = await call_patient(pid, patient["phone"])
            if res.get("ok"):
                _mark_called(pid)
            else:
                print(f"[scheduler] gọi BN {pid} thất bại: {res.get('status')} {res.get('body','')[:200]}")
            return {"mode": "real", "patient_id": pid, "phone": patient["phone"], **res}
        except Exception as e:
            return {"mode": "real", "patient_id": pid, "ok": False, "error": str(e)}
    else:
        # MÔ PHỎNG (chưa có telephony) — chạy pipeline với mock để dashboard cập nhật
        from services.pipeline import process_response
        scenario = force_scenario or "yellow"
        result = await process_response(pid, scenario=scenario, source="scheduled-sim")
        _mark_called(pid)
        return {"mode": "simulation", "patient_id": pid,
                "level": result["level"], "transcript": result["transcript"]}


async def run_due_now() -> list[dict]:
    """Tìm và gọi ngay các bệnh nhân tới hạn (theo call_time). Dùng cho nút 'Chạy vòng gọi'."""
    hhmm, today = _now_hhmm(), _today()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM patients WHERE call_time = ? "
            "AND (last_call_date IS NULL OR last_call_date != ?)",
            (hhmm, today),
        ).fetchall()
    return [await initiate_call(dict(p)) for p in rows]


async def _loop():
    while True:
        try:
            await run_due_now()
        except Exception as e:
            print(f"[scheduler] lỗi tick: {e}")
        await asyncio.sleep(_TICK_SECONDS)


def start():
    """Gọi trong startup của FastAPI."""
    global _task
    if not settings.CALL_SCHEDULER_ENABLED:
        print("[scheduler] tắt (CALL_SCHEDULER_ENABLED=false)")
        return
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop())
        mode = "GỌI THẬT (Stringee)" if is_configured() else "MÔ PHỎNG (chưa có telephony)"
        print(f"[scheduler] đã bật — chế độ: {mode}, kiểm tra mỗi {_TICK_SECONDS}s")
