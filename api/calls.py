"""
DEV 1 owns this file.
Endpoint nhận audio từ frontend → chạy full pipeline → trả kết quả triage.

CONTRACT với Dev 3 (frontend):
  POST /calls/simulate
    Form: patient_id (int), audio_file (file upload), scenario (optional: green/yellow/red)
    Response: {call_log_id, transcript, level, symptoms, symptom_labels, message, alert_sent}

  GET /calls/{call_log_id}
    Response: chi tiết 1 cuộc gọi + triage result

  GET /dashboard
    Response: danh sách bệnh nhân với triage gần nhất (cho Dev 3 render bảng)
"""
import json
import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from database import get_conn
from services.vnpt_voice import text_to_speech, build_callback_message
from services.pipeline import process_response   # pipeline dùng chung (STT→triage→alert)

router = APIRouter(tags=["calls"])

AUDIO_DIR = "audio_uploads"
CALLBACK_DIR = "callbacks"
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(CALLBACK_DIR, exist_ok=True)


@router.post("/calls/simulate")
async def simulate_call(
    patient_id: int    = Form(...),
    audio_file: UploadFile | None = File(default=None),
    scenario: str      = Form(default=""),     # "green"|"yellow"|"red" — dùng khi test không có audio
):
    # 1. Lấy thông tin bệnh nhân
    with get_conn() as conn:
        patient = conn.execute(
            "SELECT * FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
    if not patient:
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh nhân")

    # 2. Lấy transcript từ audio hoặc mock, rồi chạy pipeline dùng chung
    if audio_file:
        audio_bytes = await audio_file.read()
        audio_path  = f"{AUDIO_DIR}/{patient_id}_{audio_file.filename}"
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)
        return await process_response(
            patient_id, audio_bytes=audio_bytes, filename=audio_file.filename,
            audio_path=audio_path, source="completed",
        )
    else:
        # Demo mode: không cần audio thật
        return await process_response(
            patient_id, scenario=scenario or "green", source="completed",
        )


@router.get("/calls/{call_log_id}")
def get_call(call_log_id: int):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT cl.*, tr.level, tr.symptoms, tr.symptom_labels, tr.alert_sent, tr.created_at AS triaged_at
            FROM call_logs cl
            LEFT JOIN triage_results tr ON tr.call_log_id = cl.id
            WHERE cl.id = ?
        """, (call_log_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc gọi")
    d = dict(row)
    if d.get("symptoms"):
        try:
            d["symptoms"] = json.loads(d["symptoms"])
        except Exception:
            pass
    return d


@router.post("/calls/{patient_id}/callback")
async def make_callback(patient_id: int):
    """
    Voicebot tự động gọi lại bệnh nhân khi phát hiện RED/YELLOW.
    Sinh lời nhắn thoại cá nhân hoá bằng VNPT TTS, lưu file để phát lại.

    DEV 3: gọi endpoint này khi điều dưỡng bấm "Gọi lại bệnh nhân",
    rồi phát audio_url qua thẻ <audio> để mô phỏng cuộc gọi.

    Response: {patient_name, phone, level, symptom_labels, message, audio_url}
    """
    # 1. Lấy bệnh nhân + triage gần nhất
    with get_conn() as conn:
        patient = conn.execute(
            "SELECT * FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
        if not patient:
            raise HTTPException(status_code=404, detail="Không tìm thấy bệnh nhân")
        triage = conn.execute("""
            SELECT tr.level, tr.symptom_labels
            FROM   triage_results tr
            JOIN   call_logs cl ON cl.id = tr.call_log_id
            WHERE  cl.patient_id = ?
            ORDER BY tr.id DESC LIMIT 1
        """, (patient_id,)).fetchone()

    if not triage or triage["level"] == "GREEN":
        raise HTTPException(status_code=400,
                            detail="Bệnh nhân không ở mức cần gọi lại (RED/YELLOW)")

    level = triage["level"]
    try:
        labels = json.loads(triage["symptom_labels"]) if triage["symptom_labels"] else []
    except Exception:
        labels = []

    # 2. Dựng lời nhắn + sinh giọng nói (VNPT TTS, fallback gTTS)
    message = build_callback_message(patient["name"], level, labels)
    audio = await text_to_speech(message)

    # 3. Lưu file để dashboard phát lại (phục vụ qua mount /callbacks)
    audio_path = f"{CALLBACK_DIR}/{patient_id}.wav"
    with open(audio_path, "wb") as f:
        f.write(audio)

    return {
        "patient_name":   patient["name"],
        "phone":          patient["phone"],
        "level":          level,
        "symptom_labels": labels,
        "message":        message,
        "audio_url":      f"/callbacks/{patient_id}.wav",
    }


@router.get("/dashboard")
def dashboard():
    """
    DEV 3 gọi endpoint này để render bảng bệnh nhân.
    Trả về danh sách bệnh nhân đã sắp xếp: RED trên cùng → YELLOW → GREEN.
    """
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT p.id, p.name, p.phone, p.age, p.discharge_date, p.call_time,
                   p.last_answered_at,
                   t.level, t.symptoms, t.created_at AS last_call_at
            FROM   patients p
            LEFT JOIN (
                SELECT tr.level, tr.symptoms, tr.created_at, cl.patient_id
                FROM   triage_results tr
                JOIN   call_logs cl ON cl.id = tr.call_log_id
                JOIN (
                    SELECT cl2.patient_id, MAX(tr2.id) AS max_triage_id
                    FROM   triage_results tr2
                    JOIN   call_logs cl2 ON cl2.id = tr2.call_log_id
                    GROUP BY cl2.patient_id
                ) latest ON latest.patient_id = cl.patient_id
                         AND latest.max_triage_id = tr.id
            ) t ON t.patient_id = p.id
            ORDER BY
                CASE t.level WHEN 'RED' THEN 0 WHEN 'YELLOW' THEN 1 ELSE 2 END,
                p.id DESC
        """).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        if d.get("symptoms"):
            try:
                d["symptoms"] = json.loads(d["symptoms"])
            except Exception:
                pass
        result.append(d)
    return result


@router.get("/alerts")
def get_alerts(limit: int = 20):
    """
    DEV 3 gọi endpoint này để hiển thị thông báo alert trên dashboard.
    Trả về các alert YELLOW/RED chưa xem, mới nhất trước.
    """
    try:
        with get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM alerts
                ORDER BY id DESC LIMIT ?
            """, (limit,)).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("symptoms"):
                try:
                    d["symptoms"] = json.loads(d["symptoms"])
                except Exception:
                    pass
            result.append(d)
        return result
    except Exception:
        return []  # bảng alerts chưa tồn tại thì trả list rỗng


@router.post("/alerts/{alert_id}/seen")
def mark_alert_seen(alert_id: int):
    """Đánh dấu alert đã xem — Dev 3 gọi khi điều dưỡng click vào."""
    with get_conn() as conn:
        conn.execute("UPDATE alerts SET seen=1 WHERE id=?", (alert_id,))
    return {"ok": True}
