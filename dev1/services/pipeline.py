"""
Pipeline xử lý 1 câu trả lời của bệnh nhân — dùng chung cho:
  - POST /calls/simulate         (upload / mock)
  - Scheduler tự động gọi         (mô phỏng khi chưa có telephony)
  - Webhook ghi âm Stringee        (gọi thật)

Luồng: (audio→STT) hoặc transcript có sẵn → triage → lưu DB → cảnh báo.
"""
import json
from database import get_conn
from services.vnpt_voice import speech_to_text, speech_to_text_mock
from services.triage_engine import analyze
from services.alert import send_alert


async def process_response(
    patient_id: int,
    *,
    transcript: str | None = None,
    audio_bytes: bytes | None = None,
    filename: str = "audio.wav",
    audio_path: str | None = None,
    scenario: str = "",
    source: str = "call",
) -> dict:
    """
    Chạy full pipeline cho 1 câu trả lời. Trả về dict kết quả (giống /calls/simulate).
    Ưu tiên: transcript (nếu truyền sẵn) > audio_bytes (STT) > scenario (mock).
    """
    with get_conn() as conn:
        patient = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not patient:
        raise ValueError(f"Không tìm thấy bệnh nhân id={patient_id}")

    # 1. Lấy transcript
    if transcript is None:
        if audio_bytes is not None:
            transcript = await speech_to_text(audio_bytes, filename)
        else:
            transcript = await speech_to_text_mock(scenario or "green")

    # 2. Lưu call log
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO call_logs (patient_id, transcript, audio_path, status) VALUES (?, ?, ?, ?)",
            (patient_id, transcript, audio_path, source),
        )
        call_log_id = cur.lastrowid

    # 3. Triage
    result = await analyze(transcript)

    # 4. Lưu triage result
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO triage_results (call_log_id, level, symptoms, symptom_labels) VALUES (?, ?, ?, ?)",
            (call_log_id, result.level, json.dumps(result.symptoms),
             json.dumps(result.symptom_labels, ensure_ascii=False)),
        )

    # 5. Cảnh báo nếu RED/YELLOW
    alert_sent = send_alert(
        patient_name=patient["name"],
        phone=patient["phone"],
        level=result.level,
        symptom_labels=result.symptom_labels,
        message=result.message,
        patient_id=patient_id,
    )

    return {
        "call_log_id":    call_log_id,
        "patient_id":     patient_id,
        "transcript":     transcript,
        "level":          result.level,
        "symptoms":       result.symptoms,
        "symptom_labels": result.symptom_labels,
        "message":        result.message,
        "alert_sent":     alert_sent,
        "callback_available": result.level in ("RED", "YELLOW"),
    }
