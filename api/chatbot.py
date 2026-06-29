"""
DEV 1 owns this file.
Chatbot endpoint — nhận text từ frontend, chạy NER+triage, trả lời tự nhiên.
Tích hợp với cửa sổ chat nổi trên dashboard (Dev 3 làm UI).

CONTRACT với Dev 3:
  POST /chatbot/message
    Body: {"message": "tôi khó thở", "session_id": "abc123", "patient_id": 4}
    Response: {
      "reply": "Bác đang khó thở...",
      "triage_level": "YELLOW",
      "symptoms": ["kho_tho"],
      "symptom_labels": ["Khó thở"],
      "turn": 2
    }

  POST /chatbot/transcribe   (multipart: audio=<file>)
    Response: {"text": "tôi bị đau ngực"}   — VNPT STT cho nút 🎙️ trong khung chat

  POST /chatbot/alert-patient
    Body: {"patient_id": 4, "level": "RED", "symptoms": ["dau_nguc"]}
    Response: {"sent": true, "method": "tts_call" | "dashboard_notify"}

  DELETE /chatbot/session/{session_id}   — reset cuộc hội thoại
"""
import json
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from services.triage_engine import analyze, _determine_level
from services.chatbot_flow import generate_reply, get_opening_question
from services.symptom_schema import SYMPTOM_LABELS
from services.vnpt_voice import speech_to_text
from services.alert import send_alert
from database import get_conn

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

# Session state: {session_id: {"symptoms": [...], "turn": 0}}
_sessions: dict[str, dict] = {}


class ChatIn(BaseModel):
    message: str
    session_id: str
    patient_id: int | None = None


class AlertPatientIn(BaseModel):
    patient_id: int
    level: str
    symptoms: list[str]
    symptom_labels: list[str]


@router.get("/opening")
def opening_message():
    """Dev 3 gọi khi mở cửa sổ chat — lấy câu chào đầu tiên."""
    return {"reply": get_opening_question(0), "triage_level": "GREEN", "turn": 0}


@router.post("/message")
async def chat_message(body: ChatIn):
    # Lấy hoặc tạo session
    session = _sessions.setdefault(body.session_id, {"symptoms": [], "turn": 0})
    turn = session["turn"]

    # Phân tích triệu chứng từ tin nhắn này
    result = await analyze(body.message)

    # Cộng dồn triệu chứng qua các turn
    for s in result.symptoms:
        if s not in session["symptoms"]:
            session["symptoms"].append(s)

    accumulated = session["symptoms"]
    session["turn"] = turn + 1

    # Triage dựa trên tất cả triệu chứng đã phát hiện
    final_level = _determine_level(accumulated)
    labels = [SYMPTOM_LABELS[s] for s in accumulated if s in SYMPTOM_LABELS]

    # Sinh câu trả lời
    reply = generate_reply(accumulated, final_level, turn)

    # Nếu RED/YELLOW — ghi vào DB để dashboard biết
    if final_level in ("RED", "YELLOW") and body.patient_id:
        _flag_patient(body.patient_id, final_level, accumulated)

    return {
        "reply":          reply,
        "triage_level":   final_level,
        "symptoms":       accumulated,
        "symptom_labels": labels,
        "turn":           session["turn"],
    }


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """
    Dev 3 (nút 🎙️): nhận file audio thu từ khung chat → VNPT STT → trả text
    để điền vào ô chat rồi tự động gửi qua /chatbot/message.
    """
    audio_bytes = await audio.read()
    text = await speech_to_text(audio_bytes, audio.filename or "chat.wav")
    return {"text": text}


@router.post("/alert-patient")
async def alert_patient(body: AlertPatientIn):
    """
    Gửi cảnh báo đến bệnh nhân/gia đình khi phát hiện RED/YELLOW.
    MVP: gửi email alert + đánh dấu trên dashboard.
    Phase 2: tích hợp VNPT SmartVoice để gọi lại cho bệnh nhân.
    """
    if body.level not in ("RED", "YELLOW"):
        return {"sent": False, "reason": "GREEN không cần alert"}

    # Lấy thông tin bệnh nhân
    with get_conn() as conn:
        patient = conn.execute(
            "SELECT * FROM patients WHERE id = ?", (body.patient_id,)
        ).fetchone()

    if not patient:
        return {"sent": False, "reason": "Không tìm thấy bệnh nhân"}

    # Cảnh báo điều dưỡng (in-app + email) — gắn patient_id để dashboard
    # hiển thị đúng và nút "📞 Gọi lại" hoạt động.
    sent = send_alert(
        patient_name=patient["name"],
        phone=patient["phone"],
        level=body.level,
        symptom_labels=body.symptom_labels,
        message="Phát hiện qua chatbot. Cần liên hệ bệnh nhân ngay.",
        patient_id=body.patient_id,
    )

    return {
        "sent":   sent,
        "method": "dashboard_notify",
        "patient": patient["name"],
        "level":   body.level,
    }


@router.delete("/session/{session_id}")
def clear_session(session_id: str):
    """Dev 3 gọi khi đóng cửa sổ chat — reset conversation."""
    _sessions.pop(session_id, None)
    return {"cleared": session_id}


def _flag_patient(patient_id: int, level: str, symptoms: list):
    """Ghi triage result vào DB từ chatbot (không qua call log)."""
    labels = [SYMPTOM_LABELS[s] for s in symptoms if s in SYMPTOM_LABELS]
    with get_conn() as conn:
        # Tạo call log giả cho chatbot session
        cur = conn.execute(
            "INSERT INTO call_logs (patient_id, transcript, status) VALUES (?, ?, ?)",
            (patient_id, "[chatbot session]", "chatbot"),
        )
        conn.execute(
            "INSERT INTO triage_results (call_log_id, level, symptoms, symptom_labels) VALUES (?, ?, ?, ?)",
            (cur.lastrowid, level, json.dumps(symptoms),
             json.dumps(labels, ensure_ascii=False)),
        )
