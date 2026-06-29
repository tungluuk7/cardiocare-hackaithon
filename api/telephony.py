"""
DEV 1 owns this file.
API cho tính năng tự động gọi điện theo lịch (Twilio) + webhook ghi âm.

CONTRACT với Dev 3 (frontend):
  PUT  /telephony/schedule/{patient_id}   Body {"call_time":"09:00"}  → cài giờ gọi
  POST /telephony/call/{patient_id}        → gọi NGAY 1 bệnh nhân (nút "Gọi ngay")
  POST /telephony/run-now                  → chạy vòng gọi các ca tới hạn ngay
  GET  /telephony/status                   → trạng thái cấu hình (real/simulation)
  GET  /telephony/question.wav             → audio câu hỏi (VNPT TTS) cho Twilio <Play>

Webhook cho Twilio (không phải Dev 3 gọi):
  POST /telephony/twilio-recording?patient_id=..  → nhận file ghi âm → VNPT STT → triage
"""
from fastapi import APIRouter, Request, HTTPException, Response
from pydantic import BaseModel
from database import get_conn
from config import settings
from services import scheduler, telephony
from services.pipeline import process_response
from services.vnpt_voice import text_to_speech, PHONE_QUESTION

router = APIRouter(prefix="/telephony", tags=["telephony"])

# Cache audio câu hỏi (VNPT TTS) để Twilio <Play> không phải sinh lại mỗi cuộc gọi
_question_audio: bytes | None = None


class ScheduleIn(BaseModel):
    call_time: str   # "HH:MM"


@router.get("/status")
def status():
    ready = telephony.is_configured()
    return {
        "telephony_ready": ready,
        "mode": "real" if ready else "simulation",
        "provider": "twilio" if ready else "none",
        "scheduler_enabled": settings.CALL_SCHEDULER_ENABLED,
        "public_base_url": settings.PUBLIC_BASE_URL or None,
        "from_number": settings.TWILIO_FROM_NUMBER or None,
    }


@router.get("/question.wav")
async def question_audio():
    """Phát câu hỏi cho cuộc gọi — audio sinh bởi VNPT TTS. Twilio <Play> lấy ở đây."""
    global _question_audio
    if _question_audio is None:
        _question_audio = await text_to_speech(PHONE_QUESTION)
    return Response(content=_question_audio, media_type="audio/wav")


@router.post("/twilio-recording")
async def twilio_recording(request: Request, patient_id: int):
    """
    WEBHOOK cho Twilio (sau <Record>). Twilio POST form-encoded có 'RecordingUrl'.
    Tải file → VNPT STT → triage → cảnh báo. Trả TwiML để Twilio kết thúc cuộc gọi.
    """
    form = await request.form()
    rec_url = form.get("RecordingUrl")
    if rec_url:
        try:
            # Có RecordingUrl = bệnh nhân ĐÃ NHẤC MÁY và trả lời → ghi lại thời điểm
            with get_conn() as conn:
                conn.execute(
                    "UPDATE patients SET last_answered_at = datetime('now','localtime') WHERE id = ?",
                    (patient_id,),
                )
            audio = await telephony.download_recording(rec_url)
            result = await process_response(
                patient_id, audio_bytes=audio, filename="twilio.wav", source="phone-call"
            )
            print(f"[telephony/twilio] BN {patient_id}: {result['level']} — {result['symptom_labels']}")
        except Exception as e:
            print(f"[telephony/twilio] xử lý ghi âm lỗi: {e}")
    else:
        print(f"[telephony/twilio] webhook không có RecordingUrl. form={dict(form)}")
    # Trả TwiML kết thúc (Twilio cần XML)
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>',
        media_type="application/xml",
    )


@router.put("/schedule/{patient_id}")
def set_schedule(patient_id: int, body: ScheduleIn):
    """Cài giờ gọi tự động hằng ngày cho 1 bệnh nhân."""
    # validate HH:MM
    try:
        hh, mm = body.call_time.split(":")
        assert 0 <= int(hh) <= 23 and 0 <= int(mm) <= 59
    except Exception:
        raise HTTPException(400, "call_time phải dạng HH:MM (vd 09:00)")

    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE patients SET call_time=?, last_call_date=NULL WHERE id=?",
            (body.call_time, patient_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "Không tìm thấy bệnh nhân")
    return {"ok": True, "patient_id": patient_id, "call_time": body.call_time}


@router.post("/call/{patient_id}")
async def call_now(patient_id: int):
    """Gọi NGAY cho 1 bệnh nhân (bỏ qua giờ hẹn). Nút demo 'Gọi ngay'."""
    with get_conn() as conn:
        p = conn.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone()
    if not p:
        raise HTTPException(404, "Không tìm thấy bệnh nhân")
    # reset last_call_date để chắc chắn gọi được
    with get_conn() as conn:
        conn.execute("UPDATE patients SET last_call_date=NULL WHERE id=?", (patient_id,))
    result = await scheduler.initiate_call(dict(p))
    return result


@router.post("/run-now")
async def run_now():
    """Chạy ngay vòng kiểm tra các bệnh nhân tới hạn theo call_time."""
    results = await scheduler.run_due_now()
    return {"called": len(results), "results": results}
