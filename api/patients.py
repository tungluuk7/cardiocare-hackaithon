"""
DEV 1 owns this file.
CRUD endpoints cho bệnh nhân.

CONTRACT với Dev 3 (frontend):
  POST /patients              → tạo bệnh nhân mới
  GET  /patients              → danh sách tất cả
  GET  /patients/{id}         → chi tiết 1 bệnh nhân
  GET  /patients/{id}/history → lịch sử tất cả cuộc gọi + triage của 1 bệnh nhân
"""
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_conn

router = APIRouter(prefix="/patients", tags=["patients"])


class PatientIn(BaseModel):
    name: str
    phone: str | None = None          # có thể bổ sung sau (giấy ra viện thường không có SĐT)
    age: int | None = None
    doctor_name: str | None = None
    discharge_date: str | None = None
    diagnosis: str | None = None
    family_phone: str | None = None   # SĐT người thân — nhận Zalo khi RED


@router.post("", status_code=201)
def create_patient(data: PatientIn):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO patients (name, phone, age, doctor_name, discharge_date, diagnosis, family_phone)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (data.name, data.phone or "", data.age, data.doctor_name,
             data.discharge_date, data.diagnosis, data.family_phone),
        )
        return {"id": cur.lastrowid, **data.model_dump(), "phone": data.phone or ""}


@router.get("")
def list_patients():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT p.*,
                   t.level       AS last_triage,
                   t.symptoms    AS last_symptoms,
                   t.created_at  AS last_call_at
            FROM   patients p
            LEFT JOIN (
                SELECT tr.call_log_id, tr.level, tr.symptoms, tr.created_at,
                       cl.patient_id
                FROM   triage_results tr
                JOIN   call_logs cl ON cl.id = tr.call_log_id
                WHERE  tr.id = (
                    SELECT MAX(tr2.id)
                    FROM   triage_results tr2
                    JOIN   call_logs cl2 ON cl2.id = tr2.call_log_id
                    WHERE  cl2.patient_id = cl.patient_id
                )
            ) t ON t.patient_id = p.id
            ORDER BY COALESCE(t.level = 'RED', 0) DESC,
                     COALESCE(t.level = 'YELLOW', 0) DESC,
                     p.created_at DESC
        """).fetchall()
    return [_row_to_dict(r) for r in rows]


@router.get("/{patient_id}")
def get_patient(patient_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh nhân")
    return _row_to_dict(row)


@router.get("/{patient_id}/history")
def get_patient_history(patient_id: int):
    """
    Lịch sử đầy đủ của 1 bệnh nhân: tất cả cuộc gọi (call_logs) kèm kết quả
    triage tương ứng, sắp xếp mới nhất trước.

    DEV 3: gọi endpoint này khi điều dưỡng bấm vào 1 bệnh nhân để xem timeline.

    Response: {
        patient: {...},                     # thông tin bệnh nhân
        history: [
            {call_log_id, called_at, transcript, audio_path, status,
             level, symptoms, symptom_labels, confidence, alert_sent, triaged_at},
            ...
        ]
    }
    """
    with get_conn() as conn:
        patient = conn.execute(
            "SELECT * FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
        if not patient:
            raise HTTPException(status_code=404, detail="Không tìm thấy bệnh nhân")

        rows = conn.execute("""
            SELECT cl.id          AS call_log_id,
                   cl.called_at,
                   cl.transcript,
                   cl.audio_path,
                   cl.status,
                   tr.level,
                   tr.symptoms,
                   tr.symptom_labels,
                   tr.confidence,
                   tr.alert_sent,
                   tr.created_at  AS triaged_at
            FROM   call_logs cl
            LEFT JOIN triage_results tr ON tr.call_log_id = cl.id
            WHERE  cl.patient_id = ?
            ORDER BY cl.id DESC
        """, (patient_id,)).fetchall()

    history = []
    for r in rows:
        d = dict(r)
        for key in ("symptoms", "symptom_labels"):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except Exception:
                    pass
        history.append(d)

    return {"patient": _row_to_dict(patient), "history": history}


@router.delete("/{patient_id}")
def delete_patient(patient_id: int):
    """Xóa 1 bệnh nhân + toàn bộ call_logs / triage_results / alerts liên quan."""
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM patients WHERE id = ?", (patient_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy bệnh nhân")
        conn.execute(
            "DELETE FROM triage_results WHERE call_log_id IN "
            "(SELECT id FROM call_logs WHERE patient_id = ?)", (patient_id,)
        )
        conn.execute("DELETE FROM call_logs WHERE patient_id = ?", (patient_id,))
        conn.execute("DELETE FROM alerts WHERE patient_id = ?", (patient_id,))
        conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
    return {"ok": True, "deleted": patient_id}


def _row_to_dict(row) -> dict:
    d = dict(row)
    if "last_symptoms" in d and d["last_symptoms"]:
        try:
            d["last_symptoms"] = json.loads(d["last_symptoms"])
        except Exception:
            pass
    return d
