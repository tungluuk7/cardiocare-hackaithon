r"""
Seed dữ liệu demo cho CardioCare.
Tạo sẵn vài bệnh nhân để dashboard không trống khi demo.

Chạy:  .venv\Scripts\python seed_demo.py
        .venv\Scripts\python seed_demo.py --reset   (xoá sạch rồi seed lại)
"""
import sys
import json
import asyncio
from database import create_tables, get_conn
from services.triage_engine import analyze
from services.alert import send_alert

DEMO_PATIENTS = [
    # (name, phone, age, doctor, discharge_date, diagnosis, family_phone, kịch bản transcript)
    ("Nguyễn Văn An",  "0901234567", 71, "BS. Trần Minh", "2026-06-25",
     "Sau đặt stent mạch vành (PCI)", "0988000001", "Bác cảm thấy bình thường, ăn uống được, đi lại nhẹ nhàng."),
    ("Trần Thị Bình",  "0912345678", 68, "BS. Lê Hoa",   "2026-06-26",
     "Sau nong mạch vành", "0988000002", "Bác hơi khó thở, đi lại thì mệt hơn, chân cũng hơi sưng."),
    ("Lê Văn Cường",   "0923456789", 75, "BS. Trần Minh", "2026-06-24",
     "Sau PCI nhồi máu cơ tim", "0988000003", "Bác đau ngực dữ dội từ sáng, bị ngất một lần, giờ rất khó thở."),
    ("Phạm Thị Dung",  "0934567890", 64, "BS. Nguyễn Lan", "2026-06-27",
     "Theo dõi sau can thiệp tim", "0988000004", "Bác thấy hồi hộp, tim đập nhanh, thỉnh thoảng chóng mặt."),
    ("Hoàng Văn Em",   "0945678901", 70, "BS. Lê Hoa",   "2026-06-28",
     "Sau đặt stent", "0988000005", "Bác khoẻ, không có gì bất thường, ngủ ngon."),
]


async def main(reset: bool):
    create_tables()

    if reset:
        with get_conn() as conn:
            for t in ("triage_results", "call_logs", "alerts", "patients"):
                conn.execute(f"DELETE FROM {t}")
            conn.execute(
                "DELETE FROM sqlite_sequence WHERE name IN "
                "('patients','call_logs','triage_results','alerts')"
            )
        print("🧹 Đã xoá sạch dữ liệu cũ")

    for name, phone, age, doctor, discharge, diagnosis, family_phone, transcript in DEMO_PATIENTS:
        with get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO patients (name, phone, age, doctor_name, discharge_date, diagnosis, family_phone)
                   VALUES (?,?,?,?,?,?,?)""",
                (name, phone, age, doctor, discharge, diagnosis, family_phone),
            )
            pid = cur.lastrowid

        result = await analyze(transcript)

        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO call_logs (patient_id, transcript, status) VALUES (?,?,?)",
                (pid, transcript, "completed"),
            )
            clid = cur.lastrowid
            conn.execute(
                """INSERT INTO triage_results (call_log_id, level, symptoms, symptom_labels)
                   VALUES (?,?,?,?)""",
                (clid, result.level, json.dumps(result.symptoms),
                 json.dumps(result.symptom_labels, ensure_ascii=False)),
            )

        if result.level in ("RED", "YELLOW"):
            send_alert(name, phone, result.level,
                       result.symptom_labels, result.message, pid)

        print(f"  + {name:18} → {result.level:6} {result.symptom_labels}")

    with get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
        a = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    print(f"\n✅ Seed xong: {n} bệnh nhân, {a} cảnh báo. Mở http://localhost:8000/static/index.html")


if __name__ == "__main__":
    asyncio.run(main(reset="--reset" in sys.argv))
